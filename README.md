# lifx.py

A simple CLI for controlling LIFX smart bulbs on your local network.

## Features

- **Single-file executable** - Uses `uv run --script` with inline dependencies (PEP 723)
- **Local network control** - Direct LAN protocol, no cloud or API keys required
- **Device discovery** - Find all LIFX bulbs on your network
- **Power control** - Turn lights on/off with optional transitions
- **Color control** - Set hue, saturation, brightness, and color temperature (HSBK)
- **Multiple lights per command** - Repeat `--label`/`--mac`/`--ip`; one discovery, transitions run together
- **Verified changes** - `--verify` reads state back and retries until the bulbs report what was asked for
- **Device management** - Rename lights directly from CLI
- **Cron container** - Docker + [Supercronic](https://github.com/aptible/supercronic) for scheduled lighting

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- LIFX bulbs on your local network
- Docker and Docker Compose on a Linux host (scheduled lighting container)

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
| `on` | Turn on lights (by label, IP, or MAC) |
| `off` | Turn off lights (by label, IP, or MAC) |
| `set` | Set color/brightness properties (HSBK), optionally turning lights on |
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
lifx.py off --label "Office" --label "Desk"   # several lights
```

### Set color/brightness
```bash
# Brightness only
lifx.py set --label "Desk" --brightness 32768

# Full HSBK color
lifx.py set --label "Desk" --hue 43690 --saturation 65535 --brightness 52428 --kelvin 4000

# Turn on if off, fading up straight into the new color
lifx.py set --label "Desk" --saturation 0 --brightness 32768 --kelvin 2700 --duration 2000 --on
```

`set` never changes power unless `--on` is given. A light that is off stays off and keeps the
new color for the next time it is turned on - so a scheduled dim won't turn back on a light
someone switched off by hand. With `--on`, a light that is off has its color set first and is
then powered on with the transition, so it never flashes its previous color.

### Verified changes
```bash
lifx.py set --label "Office" --label "Desk" --brightness 16384 --duration 2000 --verify
lifx.py off --label "Office" --verify --attempts 5
```

`--verify` makes each change fault tolerant:

- Lights missing from discovery are searched for again, up to `--attempts` times
- Every light gets the command first, then after the transition finishes each light's state is read back and compared to what was requested
  (within ~1% for hue/saturation/brightness; kelvin may be clamped to the bulb's supported range)
- Only lights that don't match get the command again, up to `--attempts` times (default 3)
- The exit code is non-zero if any light is still wrong, and each failed attempt is logged to stderr

Without `--verify` each command is sent once, and success means the bulb acknowledged it.

### Rename lights
```bash
lifx.py rename --label "Old Name" "New Name"
```

### Composing behaviors
```bash
# Turn on and set to warm dim
lifx.py set --label "Bedroom" --brightness 6554 --saturation 0 --kelvin 2700 --on

# Set multiple lights to the same values
lifx.py set --label "Office" --label "Desk" --label "Hallway" --brightness 32768

# Different values per light
lifx.py set --label "Office" --brightness 32768 --verify; \
lifx.py set --label "Desk" --brightness 16384 --verify
```

## Set Command Options

Set any combination of HSBK properties; unspecified values are preserved from current state.

```bash
lifx.py set --label "Desk" --hue 43690 --saturation 65535 --brightness 52428 --kelvin 4000 --duration 1000
```

| Option | Description |
|--------|-------------|
| `--label`, `-l` | Light name (case-insensitive), repeatable |
| `--ip`, `-i` | Light IP address, repeatable |
| `--mac`, `-m` | Light MAC address, repeatable |
| `--hue` | Hue (0-65535) |
| `--saturation`, `-s` | Saturation (0-65535) |
| `--brightness`, `-b` | Brightness (0-65535) |
| `--kelvin`, `-k` | Color temperature (2500-9000) |
| `--duration`, `-d` | Transition time in milliseconds |
| `--on` | Turn the light on if it is off (default: never change power) |
| `--verify` | Read state back and retry until it matches (also on `on`/`off`) |
| `--attempts` | Attempts for discovery and the change with `--verify` (default: 3) |

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

## Scheduled Lighting (Docker)

The repo includes a cron container that runs `lifx.py` commands on a schedule via [Supercronic](https://github.com/aptible/supercronic).

```
Supercronic (cron) → lifx.py CLI → LIFX LAN protocol → Bulbs
```

The container installs `lifx.py` from the repo at build time (COPY, no downloads) and reads the crontab from a bind-mounted file, so editing the schedule never requires a rebuild. Setup:

```bash
# 1. configure environment
cp .env.example .env
# edit .env: TZ

# 2. define the schedule
cp crontab.template crontab
# edit crontab (examples included, all commented out) - it's gitignored
# so you can freely edit it without committing your personal schedule

# 3. build and run
docker compose up -d --build
```

Supercronic runs with `-inotify`, so it watches `/crontab` and reloads automatically when the file changes - no restart needed after editing the schedule.

LIFX discovery is a UDP broadcast on the local network, so the container uses `network_mode: host`. That only reaches the LAN on a Linux host - Docker Desktop (macOS/Windows) runs containers in a VM and discovery finds no lights.

### Writing the schedule

- Crontab entries call `lifx.py` directly - no wrapper scripts
- Add `--verify` to every scheduled command so dropped packets and sleepy bulbs get retried, and failures show up in the logs with a non-zero exit
- Use `set ... --on` for the job that lights things up, and plain `set` (no `--on`) for later changes, so a light someone turned off by hand stays off
- Jobs on the same minute run in parallel - put lights that change together on one line, repeating `--label` for shared values and chaining different values with `;`

```
0 18 * * * lifx.py set --label "Office" --label "Desk" --saturation 0 --brightness 45875 --kelvin 3000 --duration 2000 --on --verify
0 21 * * * lifx.py set --label "Office" --brightness 13107 --duration 2000 --verify; lifx.py set --label "Desk" --brightness 6554 --duration 2000 --verify
0 7  * * * lifx.py off --label "Office" --label "Desk" --duration 1000 --verify
```

### Container Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Debian slim + uv + Supercronic + lifx.py (copied from repo) |
| `docker-compose.yml` | Service definition, host network, binds `./crontab:/crontab` |
| `crontab.template` | Template schedule, tracked in git |
| `crontab` | Your schedule - edit times and tasks here (gitignored, copy from `crontab.template`) |
| `.env` | `TZ` |

### Managing the Container

```bash
# build + start
docker compose up -d --build

# view logs (supercronic logs every job run)
docker compose logs -f

# run a command manually inside the container
docker compose exec cron lifx.py list

# stop
docker compose down
```

### Troubleshooting

**"No LIFX lights found on network"**: the container can't reach the LAN broadcast - confirm `network_mode: host` and that the host is Linux (not Docker Desktop).

**A job logs `attempt 1/3 failed` but finishes verified**: normal - a dropped packet or a bulb waking from Wi-Fi power save was retried.

**A job exits non-zero with `Light not found`**: the bulb didn't answer three discoveries - usually powered off at the wall switch. Lights in the same command are still set.

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
