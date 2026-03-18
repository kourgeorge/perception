# Time Game — Phaser Edition

A polished Pac-Man-style foraging task built with **Phaser 3**. Same mechanics as the Python/Pygame version, with smoother visuals, animations, and a modern UI.

## Features

- **Smooth movement** — Cell-to-cell tweening for snappy feel
- **Polished visuals** — Rounded walls, glowing pellets, pulsing quarantine halo
- **Ghost animations** — Subtle bobbing and direction-aware eyes
- **Collect effects** — Quick burst when picking up pellets
- **Caught feedback** — Camera shake and overlay
- **Responsive HUD** — Score, lives, invincibility indicator

## Run

Open the game in a browser. Phaser requires HTTP (not `file://`), so use the bundled server if you want central server-side logging.

**Foreground** (stops when you close the terminal):

```bash
# From the phaser/ directory:
python3 server.py --port 8080
```

**Background** (keeps running after you disconnect, e.g. over SSH):

```bash
# From the repo root:
nohup python3 phaser/server.py --port 8080 > phaser-server.log 2>&1 &
# Optional: note the PID to stop later with kill <PID>
echo $!
```

Then visit: **http://localhost:8080**

## Server Logs

The bundled server appends important gameplay events for all users to:

- `logs/phaser_events.sqlite`
- `logs/phaser_events.csv`

Health check:

```bash
curl http://localhost:8080/api/logs/health
```

## Controls

- **↑↓←→** — Move (tap for one cell, hold for continuous)
- **SPACE** — Unfreeze when quarantined (after 5 or 10 seconds)

## Game Rules

- Collect pellets (gold = high-value zones, gray = low-value)
- Avoid ghosts — touching one costs a life (3 lives total)
- Occasionally you're frozen in place — wait 5 or 10 sec, then press SPACE
- Premature SPACE adds a 2s penalty each time
