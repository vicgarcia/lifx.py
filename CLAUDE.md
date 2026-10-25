# CLAUDE.md — lifx.py implementation notes

## Architecture

Single-file PEP 723 script (`uv run --script`), Python 3.10+. All logic lives in `lifx.py`. The main class is `LifxClient`, which wraps [lifxlan](https://github.com/mclarkk/lifxlan) (`lifxlan>=1.2.0`, LAN protocol over UDP 56700, no cloud).

This repo also contains the cron container for scheduled lighting (Dockerfile, docker-compose.yml, crontab):

```
Supercronic (cron) → lifx.py CLI → LIFX LAN protocol → Bulbs
```

- The Dockerfile COPYs `lifx.py` from the repo into `~/.local/bin` (no downloads) and pre-warms uv deps with `lifx.py --help`
- The crontab is bind-mounted (`./crontab:/crontab:ro`), not COPYed into the image, so schedule edits don't require a rebuild. `crontab.template` is the tracked template; `crontab` (the working copy, gitignored so personal schedules never get committed) is created from it. `CMD` runs `supercronic -inotify /crontab` so the schedule reloads automatically on change — no restart needed either
- `network_mode: host` is required — discovery is a UDP broadcast on the LAN. Only works on Linux hosts; Docker Desktop's VM never sees the LAN broadcast and `list` finds nothing
- No entrypoint/uid remapping (unlike containers with writable bind mounts) — the only mount is the read-only crontab, so the image runs as its `app` user directly
- Crontab entries call `lifx.py` directly — no wrapper scripts. Supercronic runs same-minute entries in parallel, so lights that change together go on one line

## lifxlan behavior that shapes the code

### One attempt per request

lifxlan's `DEFAULT_ATTEMPTS = 1` and `DEFAULT_TIMEOUT = 1` (second) apply to every request — discovery broadcast, label lookups, gets, and acked sets. A single dropped UDP packet fails the call. This is the root cause of "flaky bulbs"; `--verify` exists to handle it at the outcome level rather than per packet.

### Discovery bypasses `LifxLAN.get_lights()`

`get_lights()` → `discover_devices()` sends `GetVersion` to every responding device twice: `is_light()` (timeout caught) and then `is_switch()` (timeout **not** caught). One unanswered reply from any bulb raises `WorkflowException` out of discovery and aborts the whole command — observed on real hardware. `LifxClient._get_lights()` instead calls `broadcast_with_resp(GetService, StateService)` and builds `Light` objects straight from the responses. Side effects: no per-device probes during discovery (faster), and `light.product` starts as `None`, so `get_product_name()` / `get_product_features()` issue a `GetVersion` on first use (always wrapped in try/except).

Discovery itself can still miss a bulb (dropped reply, Wi-Fi power save) — roughly 1 in 5 `list` runs on a 10-bulb network saw 9. `find_lights()` rediscovers up to `--attempts` times when `--verify` is set.

### One read returns everything

`light.get_color()` sends `LightGet` and the `LightState` reply carries color, power level, and label; lifxlan stores `light.power_level` and `light.label` as a side effect. `get_state()` uses this for verification (one round trip per light), and `find_light()` reuses a cached `light.label` before asking again.

## Command semantics

### `set` and power

- `set` without `--on` **never sends a power command**. LIFX bulbs accept `LightSetColor` while off: the color is stored, the bulb stays dark, and `LightState` reports the stored color (verified on hardware). This is what keeps a scheduled dim from turning back on a light someone switched off by hand — there is no read-then-decide race because power is never touched
- `set --on` on an off light: `set_color(duration=0)` then `set_power(on, duration)`, so the bulb fades up straight into the new color with no flash of the old one. On a light that is already on it's a single `set_color(duration)`
- Unspecified HSBK components are merged from the light's current color on every attempt

### `--verify` / `--attempts`

`apply_all()` batches the work:

1. Send the command to every pending light (a send that raises marks that light failed)
2. Sleep once for `duration / 1000 + SETTLE_SECONDS` — reading mid-transition returns intermediate values
3. Read each light back and compare
4. Lights that missed go around again after a linear backoff (1s, 2s, …)

Sending to all lights before the single wait is deliberate: one-light-at-a-time verification made multi-light fades ripple (3 lights × 3s fade ≈ 11s); batched it's one fade.

Comparison (`hsbk_mismatches()`) only checks components that were requested:
- H/S/B tolerance `HSB_TOLERANCE` (~1% of 65535); hue compared with wraparound and skipped when the bulb reports ~zero saturation or is white-only
- Kelvin passes if it matches either the requested value or the value clamped to the product's `min_kelvin`/`max_kelvin` (bulbs clamp out-of-range kelvin)
- With `--on`, power must read on; without `--on`, power is never checked (an off light is a success)

Without `--verify`: one attempt, no read-back, no rediscovery — identical to the original behavior, and success means the bulb acked.

Exit code is 1 if any target was not found or not verified; every failed attempt is logged to stderr with the reason.

### Targets

`--label` / `--mac` / `--ip` are repeatable and collected in command-line order by `TargetAction` into `args.targets` as `(kind, value)` tuples. `rename` keeps single, non-repeatable selectors.

## Testing

There is no test suite in the repo. Changes to discovery, `apply_all()`, or comparison logic should be exercised against fake `Light` objects (patch `LifxClient._get_lights` and `time.sleep`) and then on real bulbs — always record a bulb's `list` state first and restore it afterwards.

## IDE import warning

The IDE warns that `lifxlan` imports can't be resolved. Expected — the package is installed at runtime by `uv run --script`, not in the local environment.
