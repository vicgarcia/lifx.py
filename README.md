# lifx.py

A simple CLI for controlling LIFX smart bulbs on your local network.

## Installation

### Prerequisites

Install [uv](https://docs.astral.sh/uv/) (Python package manager):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### User Install (Recommended)

Install to `~/.local/bin` (doesn't require sudo):

```bash
# Download and install
mkdir -p ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/vicgarcia/lifx.py/main/lifx -o ~/.local/bin/lifx
chmod +x ~/.local/bin/lifx

# Ensure ~/.local/bin is in your PATH (most distros already have this)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify installation:

```bash
lifx --help
```

### System-Wide Install (Alternative)

Install to `/usr/local/bin` (requires sudo, available to all users):

```bash
# Download and install
sudo curl -fsSL https://raw.githubusercontent.com/vicgarcia/lifx.py/main/lifx -o /usr/local/bin/lifx
sudo chmod +x /usr/local/bin/lifx
```

Verify installation:

```bash
lifx --help
```

## Usage

### List All Lights

Discover all LIFX bulbs on your network:

```bash
lifx list
```

Output shows: NAME, IP, MAC, MODEL, POWER, COLOR (HSBK values)

### Power Control

```bash
# Turn on by name
lifx on --label "Office"

# Turn off by IP
lifx off --ip 192.168.1.100

# Turn on by MAC
lifx on --mac d0:73:d5:xx:xx:xx

# With transition duration (milliseconds)
lifx on --label "Bedroom" --duration 1000
```

### Set Color and Brightness

LIFX uses HSBK (Hue, Saturation, Brightness, Kelvin) with 16-bit values:

```bash
# Set brightness only (50% = 32768/65535)
lifx set --label "Desk" --brightness 32768

# Set hue only (keeps other properties)
lifx set --label "Desk" --hue 21845

# Set full color
lifx set --label "Desk" --hue 43690 --saturation 65535 --brightness 52428 --kelvin 4000

# With transition
lifx set --label "Office" --brightness 65535 --duration 2000
```

### Rename Lights

```bash
lifx rename --label "Old Name" "New Name"
```

### HSBK Color Model

| Property | Range | Description |
|----------|-------|-------------|
| **Hue** | 0-65535 | Color wheel position. ~182 units per degree. 0=red, 21845=green, 43690=blue |
| **Saturation** | 0-65535 | Color intensity. 0=white, 65535=full color |
| **Brightness** | 0-65535 | Light intensity. 0=off, 65535=full brightness |
| **Kelvin** | 2500-9000 | Color temperature. Only visible at low saturation. 2500=warm, 9000=cool |

### Common Colors

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

### Brightness Levels

| Percentage | Raw Value |
|------------|-----------|
| 100% | 65535 |
| 75% | 49151 |
| 50% | 32768 |
| 25% | 16384 |
| 10% | 6554 |
| 1% | 655 |

### Composing Complex Behaviors

Chain multiple commands for complex operations:

```bash
# Turn on and set to warm dim
lifx on --label "Bedroom" && \
lifx set --label "Bedroom" --brightness 6554 --saturation 0 --kelvin 2700

# Set multiple lights
for light in "Office" "Desk" "Hallway"; do
  lifx set --label "$light" --brightness 32768
done

# Morning routine
lifx on --label "Bedroom" --duration 5000 && \
sleep 1 && \
lifx set --label "Bedroom" --brightness 32768 --saturation 0 --kelvin 4000 --duration 30000
```

### How It Works

- Uses [lifxlan](https://github.com/mclarkk/lifxlan) library for direct LAN protocol communication
- Runs via `uv` with inline script dependencies (PEP 723)
- First run takes ~3 seconds to set up dependencies, subsequent runs are instant
- Works on a network where your LIFX bulbs are accessible
