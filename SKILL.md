---
name: lifx.py
description: Control LIFX smart bulbs on the local network. Use when the user wants to control lights, change colors, adjust brightness, or manage smart lighting. Supports discovery, power control, and HSBK color settings via direct LAN protocol.
compatibility: Requires 'lifx.py' script in PATH on a network with LIFX bulbs.
---

# LIFX Smart Bulb Control

Control LIFX bulbs on your local network using the `lifx.py` CLI. Uses direct LAN protocol - no cloud, no API keys, no latency.

## Commands Reference

### Discover Lights
```bash
lifx.py list
```
Returns all LIFX bulbs on the network with: NAME, IP, MAC, MODEL, POWER state, COLOR (HSBK values).

### Power Control
```bash
# Turn on/off by label (case-insensitive)
lifx.py on --label "Office"
lifx.py off --label "Bedroom"

# By IP address
lifx.py on --ip 192.168.1.100
lifx.py off --ip 192.168.1.100

# By MAC address
lifx.py on --mac d0:73:d5:xx:xx:xx

# With transition duration (milliseconds)
lifx.py on --label "Bedroom" --duration 2000   # 2 second fade in
lifx.py off --label "Bedroom" --duration 5000  # 5 second fade out
```

### Set Color/Brightness
```bash
# Set brightness only (preserves current color)
lifx.py set --label "Desk" --brightness 32768

# Set hue only (preserves other properties)
lifx.py set --label "Desk" --hue 21845

# Set full HSBK color
lifx.py set --label "Desk" --hue 43690 --saturation 65535 --brightness 52428 --kelvin 4000

# With transition
lifx.py set --label "Office" --brightness 65535 --duration 2000
```

### Rename Lights
```bash
lifx.py rename --label "Old Name" "New Name"
```

## HSBK Color Model

LIFX uses 16-bit values (0-65535) for color properties:

| Property | Range | Description |
|----------|-------|-------------|
| **Hue** | 0-65535 | Color wheel position (~182 units per degree) |
| **Saturation** | 0-65535 | 0 = white/gray, 65535 = full color |
| **Brightness** | 0-65535 | 0 = off, 65535 = maximum brightness |
| **Kelvin** | 2500-9000 | Color temperature (only visible at low saturation) |

## Quick Reference Tables

### Common Colors (Hue Values)
| Color | Hue | Example Command |
|-------|-----|-----------------|
| Red | 0 | `lifx.py set --label "Light" --hue 0 --saturation 65535 --brightness 65535` |
| Orange | 5461 | `lifx.py set --label "Light" --hue 5461 --saturation 65535 --brightness 65535` |
| Yellow | 10922 | `lifx.py set --label "Light" --hue 10922 --saturation 65535 --brightness 65535` |
| Green | 21845 | `lifx.py set --label "Light" --hue 21845 --saturation 65535 --brightness 65535` |
| Cyan | 32768 | `lifx.py set --label "Light" --hue 32768 --saturation 65535 --brightness 65535` |
| Blue | 43690 | `lifx.py set --label "Light" --hue 43690 --saturation 65535 --brightness 65535` |
| Purple | 49151 | `lifx.py set --label "Light" --hue 49151 --saturation 65535 --brightness 65535` |
| Magenta | 54613 | `lifx.py set --label "Light" --hue 54613 --saturation 65535 --brightness 65535` |

### Brightness Levels
| Level | Value | Command |
|-------|-------|---------|
| 100% | 65535 | `lifx.py set --label "Light" --brightness 65535` |
| 75% | 49151 | `lifx.py set --label "Light" --brightness 49151` |
| 50% | 32768 | `lifx.py set --label "Light" --brightness 32768` |
| 25% | 16384 | `lifx.py set --label "Light" --brightness 16384` |
| 10% | 6554 | `lifx.py set --label "Light" --brightness 6554` |
| 1% | 655 | `lifx.py set --label "Light" --brightness 655` |

### White Light (Kelvin Values)
| Temperature | Kelvin | Use Case |
|-------------|--------|----------|
| Warm/Candle | 2500 | Relaxing, evening ambiance |
| Soft White | 2700 | Living rooms, bedrooms |
| Warm White | 3000 | General home lighting |
| Neutral | 4000 | Kitchens, bathrooms |
| Cool White | 5000 | Office, task lighting |
| Daylight | 6500 | Alertness, focus |
| Cool/Blue | 9000 | Maximum cool tone |

For pure white, set saturation to 0:
```bash
lifx.py set --label "Office" --saturation 0 --brightness 65535 --kelvin 4000
```

## Example Workflows

### Morning Wake-Up (Gradual Bright Cool Light)
```bash
lifx.py on --label "Bedroom" --duration 5000
lifx.py set --label "Bedroom" --brightness 65535 --saturation 0 --kelvin 5000 --duration 30000
```

### Evening Relax (Dim Warm Light)
```bash
lifx.py set --label "Living Room" --brightness 16384 --saturation 0 --kelvin 2700 --duration 3000
```

### Movie Mode (Dim Blue Accent)
```bash
lifx.py set --label "TV Light" --hue 43690 --saturation 65535 --brightness 6554 --duration 1000
```

### Party Mode (Bright Saturated Color)
```bash
lifx.py set --label "Party" --hue 54613 --saturation 65535 --brightness 65535
```

### All Lights Off
```bash
for light in "Office" "Bedroom" "Kitchen"; do
  lifx.py off --label "$light" --duration 1000
done
```

### Set Multiple Lights to Same Color
```bash
for light in "Office" "Desk" "Hallway"; do
  lifx.py set --label "$light" --brightness 32768 --saturation 0 --kelvin 4000
done
```

## Tips

- Use `list` first to see light names, IPs, and current state
- Label matching is case-insensitive ("Office" = "office" = "OFFICE")
- Set `--duration` for smooth transitions instead of instant changes
- For white light: set saturation to 0, control warmth with kelvin
- Chain commands with `&&` for multi-step operations
- The `--brightness` flag alone preserves current hue/saturation
- First run may take ~3 seconds for uv to install dependencies
