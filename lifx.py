#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "lifxlan>=1.2.0",
# ]
# ///

import sys
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

Compose complex behaviors by chaining calls:
  lifx on --label "Room1" && lifx set --label "Room1" --hue 21845 --saturation 65535 --brightness 45875
"""


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
                    if light.get_label().lower() == label_lower:
                        return light
                except:
                    pass

        return None

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


def cmd_on(args):
    """Turn on a light."""
    client = LifxClient()
    light = client.find_light(mac=args.mac, ip=args.ip, label=args.label)

    if not light:
        print(f"Light not found")
        return 1

    client.set_power(light, True, duration=args.duration)
    label = light.get_label() if hasattr(light, 'get_label') else 'Light'
    print(f"{label} turned on")
    return 0


def cmd_off(args):
    """Turn off a light."""
    client = LifxClient()
    light = client.find_light(mac=args.mac, ip=args.ip, label=args.label)

    if not light:
        print(f"Light not found")
        return 1

    client.set_power(light, False, duration=args.duration)
    label = light.get_label() if hasattr(light, 'get_label') else 'Light'
    print(f"{label} turned off")
    return 0


def cmd_set(args):
    """Set light color/brightness properties."""
    client = LifxClient()
    light = client.find_light(mac=args.mac, ip=args.ip, label=args.label)

    if not light:
        print(f"Light not found")
        return 1

    # Must specify at least one color property
    if not any(x is not None for x in [args.hue, args.saturation, args.brightness, args.kelvin]):
        print("Error: must specify at least one property to set (--hue, --saturation, --brightness, --kelvin)")
        return 1

    light_label = light.get_label() if hasattr(light, 'get_label') else 'Light'
    changes = []

    try:
        # Get current color
        current = light.get_color()
        h, s, b, k = current

        # Override with provided values (raw LIFX values 0-65535)
        if args.hue is not None:
            h = args.hue
            changes.append(f"hue={args.hue}")

        if args.saturation is not None:
            s = args.saturation
            changes.append(f"saturation={args.saturation}")

        if args.brightness is not None:
            b = args.brightness
            changes.append(f"brightness={args.brightness}")

        if args.kelvin is not None:
            k = args.kelvin
            changes.append(f"kelvin={args.kelvin}")

        client.set_color(light, h, s, b, k, duration=args.duration)
    except Exception as e:
        print(f"Failed to set color: {e}")
        return 1

    print(f"{light_label}: {', '.join(changes)}")
    return 0


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
    on_parser = subparsers.add_parser('on', help='Turn on a light')
    on_parser.add_argument('--mac', '-m', help='MAC address of light')
    on_parser.add_argument('--ip', '-i', help='IP address of light')
    on_parser.add_argument('--label', '-l', help='Label/name of light')
    on_parser.add_argument('--duration', '-d', type=int, default=0, help='Transition duration in ms (default: 0)')
    on_parser.set_defaults(func=cmd_on)

    # Off command
    off_parser = subparsers.add_parser('off', help='Turn off a light')
    off_parser.add_argument('--mac', '-m', help='MAC address of light')
    off_parser.add_argument('--ip', '-i', help='IP address of light')
    off_parser.add_argument('--label', '-l', help='Label/name of light')
    off_parser.add_argument('--duration', '-d', type=int, default=0, help='Transition duration in ms (default: 0)')
    off_parser.set_defaults(func=cmd_off)

    # Set command
    set_parser = subparsers.add_parser('set', help='Set light color/brightness (HSBK)')
    set_parser.add_argument('--mac', '-m', help='MAC address of light')
    set_parser.add_argument('--ip', '-i', help='IP address of light')
    set_parser.add_argument('--label', '-l', help='Label/name of light')
    set_parser.add_argument('--hue', type=int, help='Hue (0-65535)')
    set_parser.add_argument('--saturation', '-s', type=int, help='Saturation (0-65535)')
    set_parser.add_argument('--brightness', '-b', type=int, help='Brightness (0-65535)')
    set_parser.add_argument('--kelvin', '-k', type=int, help='Kelvin (2500-9000)')
    set_parser.add_argument('--duration', '-d', type=int, default=0, help='Transition duration in ms (default: 0)')
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
