#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "lifxlan>=1.2.0",
# ]
# ///

import sys
import time
import argparse
from typing import Optional
from lifxlan import LifxLAN


CLI_EPILOG = """
Examples:
  lifx list                                         # List all lights
  lifx on --label "Office"                          # Turn on by name
  lifx off --ip 192.168.1.100                       # Turn off by IP
  lifx set --label "Desk" --brightness 32768        # Set brightness to 50% (32768/65535)
  lifx set --label "Desk" --hue 21845               # Change hue, keep other properties
  lifx set --mac d0:73:xx --hue 43690 --saturation 65535 --brightness 52428 --kelvin 4000
  lifx rename --label "Old Name" "New Name"         # Rename a light

Target several lights at once by repeating --label/--mac/--ip:
  lifx off --label "Office" --label "Desk"

Turn on (if off) and set color in one step, then confirm the bulbs took it:
  lifx set --label "Office" --label "Desk" --saturation 0 --brightness 32768 --kelvin 2700 --on --verify

Without --on, set never changes power: off bulbs stay off and take the new color for when they next turn on.
"""

# verification tolerances
HSB_TOLERANCE = 655         # ~1% of the 16-bit hue/saturation/brightness range
KELVIN_TOLERANCE = 50
SETTLE_SECONDS = 0.5        # extra wait after a transition before reading state back


class LifxClient:
    """Simple LIFX client for individual bulb operations."""

    def __init__(self):
        self.lan = LifxLAN()
        self._lights_cache = None

    def _get_lights(self):
        """Get all lights, using cache if available."""
        if self._lights_cache is None:
            self._lights_cache = self.lan.get_lights()
        return self._lights_cache

    def rediscover(self):
        """Drop the cached discovery so the next lookup broadcasts again."""
        self._lights_cache = None

    def list_lights(self) -> list[dict]:
        """Discover and return info about all lights."""
        lights = self._get_lights()
        results = []

        for light in lights:
            info = {
                'mac': light.mac_addr,
                'ip': light.ip_addr,
                'label': 'Unknown',
                'power': 'Unknown',
                'color': None,
                'product': 'Unknown'
            }

            try:
                info['label'] = light.get_label()
            except:
                pass

            try:
                power_level = light.get_power()
                info['power'] = 'On' if power_level > 0 else 'Off'
            except:
                pass

            try:
                info['color'] = light.get_color()
            except:
                pass

            try:
                product_name = light.get_product_name()
                info['product'] = product_name if product_name else 'Unknown'
            except:
                pass

            results.append(info)

        return results

    def find_light(self, mac: Optional[str] = None, ip: Optional[str] = None, label: Optional[str] = None):
        """Find a light by MAC, IP, or label."""
        lights = self._get_lights()

        if mac:
            mac = mac.lower()
            for light in lights:
                if light.mac_addr.lower() == mac:
                    return light

        if ip:
            for light in lights:
                if light.ip_addr == ip:
                    return light

        if label:
            label_lower = label.lower()
            for light in lights:
                try:
                    # lifxlan keeps the label on the light once fetched
                    if (light.label or light.get_label()).lower() == label_lower:
                        return light
                except:
                    pass

        return None

    def find_lights(self, targets: list[tuple[str, str]], attempts: int = 1):
        """Resolve (kind, value) targets to lights, rediscovering until all are found.

        Returns (found, missing): found is a list of (target, light) in target order.
        """
        found = {}

        for attempt in range(1, attempts + 1):
            for target in targets:
                if target not in found:
                    kind, value = target
                    light = self.find_light(**{kind: value})
                    if light:
                        found[target] = light

            missing = [t for t in targets if t not in found]
            if not missing or attempt == attempts:
                break

            names = ', '.join(value for _, value in missing)
            print(f"Not found: {names} - rediscovering (attempt {attempt + 1}/{attempts})", file=sys.stderr)
            time.sleep(attempt)
            self.rediscover()

        return [(t, found[t]) for t in targets if t in found], missing

    def get_state(self, light) -> tuple[int, tuple]:
        """Read power level and color in a single request."""
        color = light.get_color()
        return light.power_level, color

    def set_power(self, light, on: bool, duration: int = 0):
        """Turn light on or off."""
        light.set_power(on, duration=duration)

    def set_color(self, light, h: int, s: int, b: int, k: int, duration: int = 0):
        """Set light color (HSBK)."""
        color = (h, s, b, k)
        light.set_color(color, duration=duration)

    def set_label(self, light, new_label: str):
        """Rename a light."""
        if len(new_label) > 32:
            new_label = new_label[:32]
        light.set_label(new_label)


class TargetAction(argparse.Action):
    """Collect --mac/--ip/--label values into args.targets, keeping command-line order."""

    def __call__(self, parser, namespace, values, option_string=None):
        targets = list(getattr(namespace, 'targets', None) or [])
        targets.append((self.dest, values))
        namespace.targets = targets


def light_name(light, target) -> str:
    """Best name for output without another network request."""
    return light.label or target[1]


def product_features(light) -> dict:
    """Product features (color support, kelvin range), or {} if unknown."""
    try:
        return light.get_product_features() or {}
    except:
        return {}


def hsbk_mismatches(light, requested: tuple, actual: tuple) -> list[str]:
    """Describe requested HSBK values the bulb does not report, within tolerance.

    requested holds None for components that were not asked for.
    """
    h, s, b, k = requested
    ah, as_, ab, ak = actual
    features = product_features(light)
    supports_color = features.get('color', True)
    problems = []

    # hue is meaningless on white-only bulbs or at zero saturation
    if h is not None and supports_color and as_ > HSB_TOLERANCE:
        distance = abs(h - ah) % 65536
        if min(distance, 65536 - distance) > HSB_TOLERANCE:
            problems.append(f"hue {ah} != {h}")

    if s is not None and supports_color and abs(s - as_) > HSB_TOLERANCE:
        problems.append(f"saturation {as_} != {s}")

    if b is not None and abs(b - ab) > HSB_TOLERANCE:
        problems.append(f"brightness {ab} != {b}")

    if k is not None:
        # bulbs may clamp kelvin to their supported range
        clamped = min(max(k, features.get('min_kelvin', k)), features.get('max_kelvin', k))
        if abs(k - ak) > KELVIN_TOLERANCE and abs(clamped - ak) > KELVIN_TOLERANCE:
            problems.append(f"kelvin {ak} != {k}")

    return problems


def run_attempts(name: str, apply, check, settle: float, attempts: int) -> bool:
    """Apply a change, and when check is given, read back and retry until it holds.

    apply() sends the command; check() reads the bulb and returns a list of problems.
    Without check there is a single attempt and success means the bulb acknowledged.
    """
    for attempt in range(1, attempts + 1):
        try:
            apply()
            if check is None:
                return True
            time.sleep(settle)
            problems = check()
        except Exception as e:
            problems = [str(e)]

        if not problems:
            return True

        print(f"{name}: attempt {attempt}/{attempts} failed: {'; '.join(problems)}", file=sys.stderr)
        if attempt < attempts:
            time.sleep(attempt)

    return False


def resolve_targets(client, args):
    """Find the targeted lights, reporting any that are missing."""
    if not args.targets:
        print("Error: specify a light with --label, --mac, or --ip")
        return None, True

    attempts = args.attempts if args.verify else 1
    found, missing = client.find_lights(args.targets, attempts=attempts)

    for _, value in missing:
        print(f"Light not found: {value}")

    return found, bool(missing)


def cmd_list(args):
    """List all LIFX lights on the network."""
    client = LifxClient()
    lights = client.list_lights()

    if not lights:
        print("No LIFX lights found on network")
        return 1

    # Calculate column widths
    name_width = max(max(len(l['label']) for l in lights), len("NAME"))
    ip_width = max(max(len(l['ip']) for l in lights), len("IP"))
    mac_width = max(max(len(l['mac']) for l in lights), len("MAC"))
    model_width = max(max(len(str(l['product'])) for l in lights), len("MODEL"))
    power_width = max(max(len(l['power']) for l in lights), len("POWER"))

    # Print header
    header = f"{'NAME':<{name_width}}  {'IP':<{ip_width}}  {'MAC':<{mac_width}}  {'MODEL':<{model_width}}  {'POWER':<{power_width}}  COLOR"
    print(header)
    print("-" * len(header))

    # Print lights
    for info in lights:
        color_info = ""
        if info['color']:
            h, s, b, k = info['color']
            color_info = f"HSBK({h},{s},{b},{k})"

        row = f"{info['label']:<{name_width}}  {info['ip']:<{ip_width}}  {info['mac']:<{mac_width}}  {str(info['product']):<{model_width}}  {info['power']:<{power_width}}  {color_info}"
        print(row)

    return 0


def cmd_rename(args):
    """Rename a light."""
    client = LifxClient()
    light = client.find_light(mac=args.mac, ip=args.ip, label=args.label)

    if not light:
        print(f"Light not found")
        return 1

    old_label = light.get_label()
    client.set_label(light, args.name)
    print(f"Light renamed from '{old_label}' to '{args.name}'")
    return 0


def power_command(args, on: bool):
    """Turn targeted lights on or off, optionally verifying the result."""
    client = LifxClient()
    found, failed = resolve_targets(client, args)
    if found is None:
        return 1

    attempts = args.attempts if args.verify else 1
    settle = args.duration / 1000 + SETTLE_SECONDS
    state = 'on' if on else 'off'

    for target, light in found:
        name = light_name(light, target)

        def apply():
            client.set_power(light, on, duration=args.duration)

        def check():
            power, _ = client.get_state(light)
            return [] if (power > 0) == on else [f"power is {'on' if power > 0 else 'off'}"]

        if run_attempts(name, apply, check if args.verify else None, settle, attempts):
            print(f"{name} turned {state}{' (verified)' if args.verify else ''}")
        else:
            print(f"{name}: failed to turn {state}")
            failed = True

    return 1 if failed else 0


def cmd_on(args):
    """Turn on a light."""
    return power_command(args, True)


def cmd_off(args):
    """Turn off a light."""
    return power_command(args, False)


def cmd_set(args):
    """Set light color/brightness properties."""
    # Must specify at least one color property
    requested = (args.hue, args.saturation, args.brightness, args.kelvin)
    if all(x is None for x in requested):
        print("Error: must specify at least one property to set (--hue, --saturation, --brightness, --kelvin)")
        return 1

    client = LifxClient()
    found, failed = resolve_targets(client, args)
    if found is None:
        return 1

    attempts = args.attempts if args.verify else 1
    settle = args.duration / 1000 + SETTLE_SECONDS
    changes = [f"{name}={value}" for name, value in zip(('hue', 'saturation', 'brightness', 'kelvin'), requested) if value is not None]
    if args.on:
        changes.append("on")

    for target, light in found:
        name = light_name(light, target)

        def apply():
            # Override current color with provided values (raw LIFX values 0-65535)
            power, current = client.get_state(light)
            h, s, b, k = (new if new is not None else cur for new, cur in zip(requested, current))

            if args.on and power == 0:
                # set the color while still off, then fade up straight into it
                client.set_color(light, h, s, b, k, duration=0)
                client.set_power(light, True, duration=args.duration)
            else:
                # never touches power - an off bulb keeps the color for its next power on
                client.set_color(light, h, s, b, k, duration=args.duration)

        def check():
            power, actual = client.get_state(light)
            problems = hsbk_mismatches(light, requested, actual)
            if args.on and power == 0:
                problems.append("power is off")
            return problems

        if run_attempts(name, apply, check if args.verify else None, settle, attempts):
            print(f"{name}: {', '.join(changes)}{' (verified)' if args.verify else ''}")
        else:
            print(f"{name}: failed to set {', '.join(changes)}")
            failed = True

    return 1 if failed else 0


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def add_target_args(parser):
    """Repeatable light selectors, collected in order into args.targets."""
    parser.set_defaults(targets=[])
    parser.add_argument('--mac', '-m', action=TargetAction, help='MAC address of light (repeatable)')
    parser.add_argument('--ip', '-i', action=TargetAction, help='IP address of light (repeatable)')
    parser.add_argument('--label', '-l', action=TargetAction, help='Label/name of light (repeatable)')


def add_verify_args(parser):
    parser.add_argument('--verify', action='store_true', help='Read state back after the change and retry until it matches')
    parser.add_argument('--attempts', type=positive_int, default=3, help='Attempts for discovery and the change when verifying (default: 3)')


def main():
    parser = argparse.ArgumentParser(
        description="LIFX - Control individual LIFX smart bulbs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=CLI_EPILOG
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # List command
    list_parser = subparsers.add_parser('list', help='List all lights')
    list_parser.set_defaults(func=cmd_list)

    # Rename command
    rename_parser = subparsers.add_parser('rename', help='Rename a light')
    rename_parser.add_argument('--mac', '-m', help='MAC address of light')
    rename_parser.add_argument('--ip', '-i', help='IP address of light')
    rename_parser.add_argument('--label', '-l', help='Current label/name of light')
    rename_parser.add_argument('name', help='New name for the light (max 32 chars)')
    rename_parser.set_defaults(func=cmd_rename)

    # On command
    on_parser = subparsers.add_parser('on', help='Turn on lights')
    add_target_args(on_parser)
    on_parser.add_argument('--duration', '-d', type=int, default=0, help='Transition duration in ms (default: 0)')
    add_verify_args(on_parser)
    on_parser.set_defaults(func=cmd_on)

    # Off command
    off_parser = subparsers.add_parser('off', help='Turn off lights')
    add_target_args(off_parser)
    off_parser.add_argument('--duration', '-d', type=int, default=0, help='Transition duration in ms (default: 0)')
    add_verify_args(off_parser)
    off_parser.set_defaults(func=cmd_off)

    # Set command
    set_parser = subparsers.add_parser('set', help='Set light color/brightness (HSBK)')
    add_target_args(set_parser)
    set_parser.add_argument('--hue', type=int, help='Hue (0-65535)')
    set_parser.add_argument('--saturation', '-s', type=int, help='Saturation (0-65535)')
    set_parser.add_argument('--brightness', '-b', type=int, help='Brightness (0-65535)')
    set_parser.add_argument('--kelvin', '-k', type=int, help='Kelvin (2500-9000)')
    set_parser.add_argument('--duration', '-d', type=int, default=0, help='Transition duration in ms (default: 0)')
    set_parser.add_argument('--on', action='store_true', help='Turn the light on if it is off (default: never change power)')
    add_verify_args(set_parser)
    set_parser.set_defaults(func=cmd_set)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
