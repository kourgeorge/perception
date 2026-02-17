# Time Game – Pac-Man-Style Foraging Task

A simplified Pac-Man-style foraging task for sampling subjective timing during navigation. Participants collect pellets in a 20×14 grid arena with three high-value "hot zones," avoid three ghosts, and respond to timing gates (teleport + 3s/5s lock with key-to-exit).

## Requirements

- Python 3.10+
- Pygame 2.5+

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python run_experiment.py
```

Or with a custom config path:

```bash
python run_experiment.py --config experiment_config.json
```

## Configuration

Edit `experiment_config.json` to set:

- **blocks**: List of blocks; each has `left_gate_row` and `right_gate_row` (0–13). Gate positions can be "close" or "far" from hot zones.
- **teleport_interval_sec**: Min seconds between teleports (e.g. 60–90).
- **teleports_per_block**: Optional cap (e.g. 2–3) per block.
- **cell_size**: Pixels per grid cell (default 40).
- **practice_block**: Set to true to run one practice block first.

## Phaser Edition

A polished web version built with **Phaser 3** lives in `phaser/` with smoother visuals and animations. Run a local server from `phaser/` (e.g. `python3 -m http.server 8080`) and open http://localhost:8080. See `phaser/README.md` for details.

## Logs

Session data is written to `logs/` as JSON:

- `logs/session_<session_id>_<timestamp>.json`

Includes: session metadata, block configs, gate events (teleport/exit times, early tap), pellet collections, ghost contacts, and keypress timestamps.
