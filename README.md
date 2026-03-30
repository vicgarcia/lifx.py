# lifx.py

A simple CLI for controlling LIFX smart bulbs on your local network.

## Features

- **Single-file executable** - Uses `uv run --script` with inline dependencies (PEP 723)
- **Local network control** - Direct LAN protocol, no cloud or API keys required
- **Device discovery** - Find all LIFX bulbs on your network
- **Power control** - Turn lights on/off with optional transitions
- **Color control** - Set hue, saturation, brightness, and color temperature (HSBK)
- **Device management** - Rename lights directly from CLI

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- LIFX bulbs on your local network

## Installation

```bash
# Clone and make executable
git clone https://github.com/vicgarcia/lifx.py.git
cd lifx.py
chmod +x lifx.py

# Run
./lifx.py --help

# Install
cp lifx.py ~/.local/bin
chmod +x ~/.local/bin/lifx.py
```

## Commands

| Command | Description |
|---------|-------------|
| `list` | Discover and list all LIFX bulbs on network |
| `on` | Turn on a light (by label, IP, or MAC) |
| `off` | Turn off a light (by label, IP, or MAC) |
| `set` | Set color/brightness properties (HSBK) |
| `rename` | Rename a light |

## Usage

### List lights
```bash
lifx.py list
```

### Power control
```bash
lifx.py on --label "Office"
lifx.py off --label "Bedroom"
lifx.py on --label "Bedroom" --duration 1000  # with transition
```

### Set color/brightness
```bash
# Brightness only
lifx.py set --label "Desk" --brightness 32768

# Full HSBK color
lifx.py set --label "Desk" --hue 43690 --saturation 65535 --brightness 52428 --kelvin 4000
```

### Rename lights
```bash
lifx.py rename --label "Old Name" "New Name"
```

### Composing behaviors
```bash
# Turn on and set to warm dim
lifx.py on --label "Bedroom" && \
lifx.py set --label "Bedroom" --brightness 6554 --saturation 0 --kelvin 2700

# Set multiple lights
for light in "Office" "Desk" "Hallway"; do
  lifx.py set --label "$light" --brightness 32768
done
```

## Set Command Options

Set any combination of HSBK properties; unspecified values are preserved from current state.

```bash
lifx.py set --label "Desk" --hue 43690 --saturation 65535 --brightness 52428 --kelvin 4000 --duration 1000
```

| Option | Description |
|--------|-------------|
| `--label`, `-l` | Light name (case-insensitive) |
| `--ip`, `-i` | Light IP address |
| `--mac`, `-m` | Light MAC address |
| `--hue` | Hue (0-65535) |
| `--saturation`, `-s` | Saturation (0-65535) |
| `--brightness`, `-b` | Brightness (0-65535) |
| `--kelvin`, `-k` | Color temperature (2500-9000) |
| `--duration`, `-d` | Transition time in milliseconds |

## HSBK Color Model

LIFX uses 16-bit values (0-65535) for color properties:

| Property | Range | Description |
|----------|-------|-------------|
| **Hue** | 0-65535 | Color wheel position. ~182 units per degree. 0=red, 21845=green, 43690=blue |
| **Saturation** | 0-65535 | Color intensity. 0=white, 65535=full color |
| **Brightness** | 0-65535 | Light intensity. 0=off, 65535=full brightness |
| **Kelvin** | 2500-9000 | Color temperature. Only visible at low saturation. 2500=warm, 9000=cool |

## Common Colors

| Color | Hue |
|-------|-----|
| Red | 0 |
| Orange | 5461 |
| Yellow | 10922 |
| Green | 21845 |
| Cyan | 32768 |
| Blue | 43690 |
| Purple | 49151 |
| Magenta | 54613 |

For white light, set saturation to 0 and control warmth with kelvin (2500-3000 = warm white, 5000-6500 = cool white).

## Brightness Levels

| Percentage | Raw Value |
|------------|-----------|
| 100% | 65535 |
| 75% | 49151 |
| 50% | 32768 |
| 25% | 16384 |
| 10% | 6554 |
| 1% | 655 |

## Agent Skill

This project includes a `SKILL.md` file for use with AI coding agents (Claude Code, etc.). The skill enables natural language control of your lights.

### Installation

```bash
# Create skills directory
mkdir -p /path/to/agent/skills

# Copy SKILL.md
cp /path/to/lifx.py/SKILL.md /path/to/agent/skills/lifx/SKILL.md

# Ensure lifx.py is executable and in PATH
chmod +x ~/.local/bin/lifx.py
```

### Usage with Claude Code

Add the skills directory to your agent configuration, then interact naturally:

> "Turn on the office light"
> "Set the bedroom to a warm dim glow"
> "Turn all the lights blue"
> "List all lights on the network"

The agent reads `SKILL.md` to understand available commands, HSBK color values, and how to compose operations.
