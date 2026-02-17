# Time Game — Phaser Edition

A polished Pac-Man-style foraging task built with **Phaser 3**. Same mechanics as the Python/Pygame version, with smoother visuals, animations, and a modern UI.

## Features

- **Smooth movement** — Cell-to-cell tweening for snappy feel
- **Polished visuals** — Rounded walls, glowing pellets, pulsing quarantine halo
- **Ghost animations** — Subtle bobbing and direction-aware eyes
- **Collect effects** — Quick burst when picking up pellets
- **Death feedback** — Camera shake and overlay
- **Responsive HUD** — Score, lives, invincibility indicator

## Run

Open the game in a browser. Phaser requires HTTP (not `file://`), so use a local server:

```bash
# From the phaser/ directory:
python3 -m http.server 8080
# or
npx serve .
```

Then visit: **http://localhost:8080**

## Controls

- **↑↓←→** — Move (tap for one cell, hold for continuous)
- **SPACE** — Unfreeze when quarantined (after 3 seconds)

## Game Rules

- Collect pellets (gold = high-value zones, gray = low-value)
- Avoid ghosts — touching one costs a life (3 lives total)
- Occasionally you're teleported to a gate — wait 3s, then press SPACE
- Premature SPACE adds a 2s penalty each time
