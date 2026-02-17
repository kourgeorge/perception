/**
 * Time Game — Phaser 3 Pac-Man-Style Foraging
 * Polished visuals, smooth animations, modern UI
 */

// ─── Constants (matching Python grid) ─────────────────────────────────────
const COLS = 20, ROWS = 14;
const PLAYABLE_COL_MIN = 1, PLAYABLE_COL_MAX = 18;
const PLAYABLE_ROW_MIN = 1, PLAYABLE_ROW_MAX = 12;
const CELL_SIZE = 40;
const HUD_OFFSET_Y = 90; // Header above game board for score, clock, etc.
const CENTER_COL = 10, CENTER_ROW = 7;
const DISK_RADIUS_COLS = 2, DISK_RADIUS_ROWS = 2;
const TOP_STRIPE_ROWS = [1, 2], BOTTOM_STRIPE_ROWS = [11, 12];
const MAZE_ROWS = [
  '  ###    ###      ', '  #  #   #  #  #  ', '  #      #     #  ',
  '    ######  ###   ', '  #    #    #  #  ', '  #  #    #    #  ',
  '  #    #  #  #    ', '    ###  ######   ', '  #  #      #  #  ',
  '  #     #     #   ', '  #  #   #  #  #  ', '  ###      ###    '
];
const HIGH_VALUE = 'high', LOW_VALUE = 'low';
const POINTS_HIGH = 10, POINTS_LOW = 1;
const MIN_WAIT_SEC = 3, HIGH_RISK_WAIT_SEC = 5, PENALTY_PER_EARLY_TAP = 2, MAX_WAIT_SEC = 12;
const PLAYER_MOVE_DELAY_MS = 120, GHOST_MOVE_DELAY_MS = 550;
const RESPAWN_INVINCIBILITY_MS = 2000;
const FREEZE_INTERVAL_SEC = 30;
const FREEZE_DURATION_MS = 3000;
const FREEZE_DURATION_HIGH_VALUE_MS = 6000;
const COLD_ZONE_PELLET_FRACTION = 0.35;
// 5 levels: 2 min, then 20 sec less each (120, 100, 80, 60, 40)
const LEVEL_BASE_TIME_SEC = 120;
const LEVEL_TIME_DECREMENT_SEC = 20;
const LEVEL_COUNT = 5;
const LEVEL_MIN_TIME_SEC = 40;

// Random names when user doesn't enter one on intro screen
const RANDOM_NAMES = [
  'Blinky', 'Pinky', 'Inky', 'Clyde', 'Pac', 'Dot', 'Cherry', 'Strawberry',
  'Orange', 'Apple', 'Melon', 'Galaxian', 'Galaga', 'Digger', 'Runner',
  'Forager', 'Speedy', 'Shadow', 'Bashful', 'Pokey', 'Ghost', 'Spirit'
];

// ─── Session CSV logging (registry-backed; download at GameOver) ───────────
const CSV_COLUMNS = ['event_type', 'timestamp_iso', 'session_id', 'player_name', 'level_index', 'level_score', 'total_score', 'reason', 'freeze_duration_ms', 'in_high_value', 'space_clicks_during_freeze', 'penalty_seconds', 'lives_left'];

function gameLogEvent(registry, eventObj) {
  const events = registry.get('gameLogEvents');
  if (events && Array.isArray(events)) events.push(eventObj);
}

function csvEscape(val) {
  if (val === undefined || val === null) return '';
  const s = String(val);
  if (s.includes(',') || s.includes('"') || s.includes('\n')) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

function buildSessionCsv(events) {
  const rows = [CSV_COLUMNS.join(',')];
  events.forEach((e) => {
    const row = CSV_COLUMNS.map((col) => csvEscape(e[col]));
    rows.push(row.join(','));
  });
  return rows.join('\n');
}

function downloadCsv(csv, filename) {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// Maze walls from string grid
const MAZE_WALLS = (() => {
  const set = new Set();
  MAZE_ROWS.forEach((line, r) => {
    const row = r + PLAYABLE_ROW_MIN;
    for (let c = 0; c < line.length; c++) {
      if (line[c] === '#') set.add(`${c + PLAYABLE_COL_MIN},${row}`);
    }
  });
  return set;
})();

function isWall(col, row) {
  if (col < 0 || col >= COLS || row < 0 || row >= ROWS) return true;
  if (row < PLAYABLE_ROW_MIN || row > PLAYABLE_ROW_MAX) return true;
  if (col < PLAYABLE_COL_MIN || col > PLAYABLE_COL_MAX) return true;
  return MAZE_WALLS.has(`${col},${row}`);
}

function inBounds(col, row) {
  return col >= 0 && col < COLS && row >= 0 && row < ROWS;
}

function isPlayableCell(col, row) {
  if (col < PLAYABLE_COL_MIN || col > PLAYABLE_COL_MAX || row < PLAYABLE_ROW_MIN || row > PLAYABLE_ROW_MAX)
    return false;
  return !MAZE_WALLS.has(`${col},${row}`);
}

function getPlayableCells() {
  const out = [];
  for (let c = PLAYABLE_COL_MIN; c <= PLAYABLE_COL_MAX; c++)
    for (let r = PLAYABLE_ROW_MIN; r <= PLAYABLE_ROW_MAX; r++)
      if (!MAZE_WALLS.has(`${c},${r}`)) out.push([c, r]);
  return out;
}

function getLevelTimeSec(levelIndex) {
  if (levelIndex >= LEVEL_COUNT) return LEVEL_MIN_TIME_SEC;
  return Math.max(LEVEL_MIN_TIME_SEC, LEVEL_BASE_TIME_SEC - levelIndex * LEVEL_TIME_DECREMENT_SEC);
}

function formatCountdown(remainingMs) {
  if (remainingMs <= 0) return '0:00';
  const sec = Math.ceil(remainingMs / 1000);
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m + ':' + (s < 10 ? '0' : '') + s;
}

function isInHotZone(col, row) {
  return TOP_STRIPE_ROWS.includes(row) || BOTTOM_STRIPE_ROWS.includes(row) ||
    (Math.abs(col - CENTER_COL) <= DISK_RADIUS_COLS && Math.abs(row - CENTER_ROW) <= DISK_RADIUS_ROWS);
}

function getHotZoneCells() {
  const out = [];
  for (let c = 1; c < COLS; c++) {
    for (let r = PLAYABLE_ROW_MIN; r <= PLAYABLE_ROW_MAX; r++) {
      if (!isPlayableCell(c, r)) continue;
      if (isInHotZone(c, r)) out.push([c, r]);
    }
  }
  return out;
}

function isHighRiskGateRow(row) {
  return TOP_STRIPE_ROWS.includes(row) || BOTTOM_STRIPE_ROWS.includes(row) ||
    (Math.abs(row - CENTER_ROW) <= DISK_RADIUS_ROWS);
}

function getColdZoneCells() {
  const out = [];
  for (let c = PLAYABLE_COL_MIN; c <= PLAYABLE_COL_MAX; c++)
    for (let r = PLAYABLE_ROW_MIN; r <= PLAYABLE_ROW_MAX; r++) {
      if (!isPlayableCell(c, r)) continue;
      if (!TOP_STRIPE_ROWS.includes(r) && !BOTTOM_STRIPE_ROWS.includes(r) &&
          !(Math.abs(c - CENTER_COL) <= DISK_RADIUS_COLS && Math.abs(r - CENTER_ROW) <= DISK_RADIUS_ROWS))
        out.push([c, r]);
    }
  return out;
}

function cellToPixel(col, row) {
  return [(col + 0.5) * CELL_SIZE, (row + 0.5) * CELL_SIZE];
}

function buildPellets(seed) {
  const rng = seed != null ? seededRandom(seed) : Math.random;
  const result = [];
  getHotZoneCells().forEach(([c, r]) => result.push([[c, r], HIGH_VALUE]));
  const cold = getColdZoneCells();
  const n = Math.max(1, Math.floor(cold.length * COLD_ZONE_PELLET_FRACTION));
  const indices = shuffle([...cold.keys()], n, rng);
  indices.forEach(i => result.push([cold[i], LOW_VALUE]));
  return result;
}

function seededRandom(seed) {
  return () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
}

function shuffle(arr, count, rng) {
  for (let i = 0; i < count; i++) {
    const j = i + Math.floor(rng() * (arr.length - i));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr.slice(0, count);
}

// ─── Boot ─────────────────────────────────────────────────────────────────
class BootScene extends Phaser.Scene {
  constructor() { super({ key: 'Boot' }); }
  create() { this.scene.start('Instructions'); }
}

// ─── Instructions ─────────────────────────────────────────────────────────
class InstructionsScene extends Phaser.Scene {
  constructor() { super({ key: 'Instructions' }); }

  create() {
    const w = this.cameras.main.width, h = this.cameras.main.height;
    const bg = this.add.graphics();
    bg.fillStyle(0x0d0d18, 1);
    bg.fillRect(0, 0, w, h);

    const title = this.add.text(w / 2, 70, 'PAC-MAN FORAGING', {
      fontSize: 28, color: '#ffd54f', fontFamily: 'Georgia, serif'
    }).setOrigin(0.5);
    const sub = this.add.text(w / 2, 105, 'Collect pellets. Avoid ghosts.', {
      fontSize: 16, color: '#b0b0c0'
    }).setOrigin(0.5);

    const lines = [
      '↑↓←→ Move (or hold to move continuously)',
      'Collect as many pellets as you can before time runs out',
      '5 levels: Level 1 = 2 min, each level 20 sec less. Score adds up.',
      'High-value zones (gold) worth more. Avoid ghosts (3 lives).',
      'Freeze: entire screen pauses. Wait 3 or 6 sec (longer in high-value areas), then press SPACE to continue.',
      'Pressing SPACE before the wait adds +2s penalty and keeps you in freeze. Clock turns red under 30s.'
    ];
    const wrapWidth = w - 60;
    let y = 165;
    lines.forEach((line) => {
      const t = this.add.text(w / 2, y, line, {
        fontSize: 15, color: '#c0c0d0', align: 'center',
        wordWrap: { width: wrapWidth }, lineSpacing: 4
      }).setOrigin(0.5, 0);
      y += t.height + 12;
    });

    // Name input (optional); prefilled with a random name + number, user can change or clear
    this.add.text(w / 2, h - 130, 'Your name (optional)', {
      fontSize: 16, color: '#b0b0c0'
    }).setOrigin(0.5);
    const randomNameWithNumber = () => {
      const base = RANDOM_NAMES[Math.floor(Math.random() * RANDOM_NAMES.length)];
      const num = 100 + Math.floor(Math.random() * 900); // 100–999
      return base + '_' + num;
    };
    const defaultName = randomNameWithNumber();
    const inputStyle = 'width:220px;padding:8px 12px;font-size:16px;text-align:center;background:#1a1525;color:#e0e0e0;border:2px solid #4a6ab8;border-radius:8px;outline:none;';
    const nameDom = this.add.dom(w / 2, h - 95).createFromHTML(
      '<input type="text" placeholder="Leave empty for random name" maxlength="24" value="' + defaultName + '" style="' + inputStyle + '">'
    );
    nameDom.setOrigin(0.5);

    this.add.text(w / 2, h - 50, 'Press SPACE to start', {
      fontSize: 20, color: '#ffd54f'
    }).setOrigin(0.5);

    const startGame = () => {
      const inputEl = nameDom.node && nameDom.node.tagName === 'INPUT' ? nameDom.node : (nameDom.node && nameDom.node.querySelector && nameDom.node.querySelector('input'));
      const rawName = inputEl ? (inputEl.value || '').trim() : '';
      let name = rawName;
      if (!name) name = randomNameWithNumber();
      if (nameDom.node) nameDom.node.style.display = 'none';
      this.scene.start('Main', { blockIndex: 0, levelIndex: 0, totalScore: 0, playerName: name });
    };
    this.input.keyboard.once('keydown-SPACE', startGame);
  }
}

// ─── Main Game Scene ──────────────────────────────────────────────────────
class MainScene extends Phaser.Scene {
  constructor() { super({ key: 'Main' }); }

  init(data) {
    this.blockIndex = data.blockIndex ?? 0;
    this.blocksConfig = data.blocksConfig ?? [
      { left_gate_row: 1, right_gate_row: 12 },
      { left_gate_row: 6, right_gate_row: 7 },
      { left_gate_row: 2, right_gate_row: 11 }
    ];
    this.totalScore = data.totalScore ?? 0;
    this.levelIndex = data.levelIndex ?? 0;
    this.playerName = data.playerName ?? 'Player';
  }

  create() {
    const bc = this.blocksConfig[this.blockIndex];
    this.blockConfig = { left: bc.left_gate_row, right: bc.right_gate_row };
    this.cellSize = CELL_SIZE;
    this.lastPlayerMove = 0;
    this.lastGhostMove = 0;
    this.nextFreezeTime = this.time.now + FREEZE_INTERVAL_SEC * 1000 * (0.7 + 0.3 * Math.random());
    this.freezeInPlaceUntil = 0;
    this.currentFreezeDurationMs = 0;
    this.levelTimeSec = getLevelTimeSec(this.levelIndex);
    this.levelEndTime = this.time.now + this.levelTimeSec * 1000;

    // Session log: init when first level, then always log level_start
    if (this.levelIndex === 0) {
      const sessionId = Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
      this.registry.set('gameLogSessionId', sessionId);
      this.registry.set('gameLogPlayerName', this.playerName);
      this.registry.set('gameLogEvents', []);
      gameLogEvent(this.registry, {
        event_type: 'session_start',
        timestamp_iso: new Date().toISOString(),
        session_id: sessionId,
        player_name: this.playerName
      });
    }
    const sid = this.registry.get('gameLogSessionId');
    const pname = this.registry.get('gameLogPlayerName') ?? this.playerName;
    gameLogEvent(this.registry, {
      event_type: 'level_start',
      timestamp_iso: new Date().toISOString(),
      session_id: sid,
      player_name: pname,
      level_index: this.levelIndex,
      total_score: this.totalScore
    });

    const playable = getPlayableCells();
    const start = playable[Math.floor(Math.random() * playable.length)];
    const others = playable.filter(c => c[0] !== start[0] || c[1] !== start[1]);
    const ghostStarts = [];
    while (ghostStarts.length < 3 && others.length > 0) {
      const idx = Math.floor(Math.random() * others.length);
      ghostStarts.push(others.splice(idx, 1)[0]);
    }

    const [px, py] = cellToPixel(start[0], start[1]);
    this.hudOffsetY = HUD_OFFSET_Y;
    this.player = {
      col: start[0], row: start[1], dir: null, frozen: false,
      score: 0, lives: 3, invincibleUntil: 0,
      playerTargetX: px, playerTargetY: py + this.hudOffsetY, moving: false
    };

    this.ghosts = ghostStarts.map(([c, r], i) => ({
      id: i, col: c, row: r,
      dir: [[0, -1], [0, 1], [-1, 0], [1, 0]][Math.floor(Math.random() * 4)],
      removed: false, bobPhase: Math.random() * Math.PI * 2
    }));

    this.pellets = new Map();
    buildPellets(this.blockIndex).forEach(([[c, r], type]) => this.pellets.set(`${c},${r}`, type));

    this.cursors = this.input.keyboard.createCursorKeys();
    this.spaceKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE);

    this.buildArena();
    this.buildPellets();
    this.buildPlayer();
    this.buildGhosts();
    this.buildHUD();
    this.buildFreezeHalo();
  }

  buildArena() {
    const g = this.add.graphics();
    this.arenaGraphics = g;

    // Floor & hot zones (all hot areas same color)
    const HOT_ZONE_FLOOR = 0x2a3d35;
    const oy = this.hudOffsetY ?? HUD_OFFSET_Y;
    for (let r = PLAYABLE_ROW_MIN; r <= PLAYABLE_ROW_MAX; r++) {
      for (let c = PLAYABLE_COL_MIN; c <= PLAYABLE_COL_MAX; c++) {
        if (MAZE_WALLS.has(`${c},${r}`)) continue;
        const x = c * this.cellSize, y = r * this.cellSize + oy;
        const fill = isInHotZone(c, r) ? HOT_ZONE_FLOOR : 0x1a1525;
        g.fillStyle(fill, 0.95);
        g.fillRoundedRect(x + 1, y + 1, this.cellSize - 2, this.cellSize - 2, 2);
      }
    }

    // Walls (Pac-Man style blue) — full grid including side columns
    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < COLS; c++) {
        if (!isWall(c, r)) continue;
        const isLeftGate = c === 0 && r === this.blockConfig.left;
        const isRightGate = c === COLS - 1 && r === this.blockConfig.right;
        if (isLeftGate || isRightGate) continue; // gates drawn below
        const x = c * this.cellSize, y = r * this.cellSize + oy;
        g.fillStyle(0x2a3a6e, 1);
        g.fillRoundedRect(x + 2, y + 2, this.cellSize - 4, this.cellSize - 4, 4);
        g.lineStyle(2, 0x4a6ab8, 0.9);
        g.strokeRoundedRect(x + 1, y + 1, this.cellSize - 2, this.cellSize - 2, 4);
      }
    }

    // Gate cells on left and right (so sides are complete, no missing blocks)
    const gateFill = 0x384060;
    const gateStroke = 0x6068a0;
    [this.blockConfig.left, this.blockConfig.right].forEach((gateRow, idx) => {
      const col = idx === 0 ? 0 : COLS - 1;
      const x = col * this.cellSize, y = gateRow * this.cellSize + oy;
      g.fillStyle(gateFill, 1);
      g.fillRoundedRect(x + 2, y + 2, this.cellSize - 4, this.cellSize - 4, 4);
      g.lineStyle(2, gateStroke, 0.9);
      g.strokeRoundedRect(x + 1, y + 1, this.cellSize - 2, this.cellSize - 2, 4);
    });
  }

  buildPellets() {
    this.pelletGraphics = this.add.graphics();
    this.pelletGlow = this.add.graphics();
  }

  drawPellets() {
    this.pelletGraphics.clear();
    this.pelletGlow.clear();
    const oy = this.hudOffsetY ?? HUD_OFFSET_Y;
    this.pellets.forEach((type, key) => {
      const [c, r] = key.split(',').map(Number);
      const [x, y0] = cellToPixel(c, r);
      const y = y0 + oy;
      const isHigh = type === HIGH_VALUE;
      const radius = isHigh ? this.cellSize * 0.22 : this.cellSize * 0.1;
      this.pelletGraphics.fillStyle(isHigh ? 0xffb347 : 0x9090a0, 1);
      this.pelletGraphics.fillCircle(x, y, radius);
    });
  }

  buildPlayer() {
    const [x, y0] = cellToPixel(this.player.col, this.player.row);
    const y = y0 + (this.hudOffsetY ?? HUD_OFFSET_Y);
    this.playerGraphics = this.add.graphics();
    this.playerContainer = this.add.container(x, y);
    this.playerContainer.add(this.playerGraphics);
  }

  drawPlayer() {
    this.playerGraphics.clear();
    const p = this.player;
    const oy = this.hudOffsetY ?? HUD_OFFSET_Y;
    const x = p.playerTargetX ?? cellToPixel(p.col, p.row)[0];
    const y = p.playerTargetY ?? cellToPixel(p.col, p.row)[1] + oy;
    this.playerContainer.setPosition(x, y);

    let baseAngle = 0;
    if (p.dir) {
      if (p.dir[0] === 1) baseAngle = 0;
      else if (p.dir[0] === -1) baseAngle = Math.PI;
      else if (p.dir[1] === -1) baseAngle = -Math.PI / 2;
      else baseAngle = Math.PI / 2;
    }
    const mouthSpread = 0.4 + 0.15 * Math.sin(this.time.now * 0.01);
    const r = this.cellSize / 2 - 3;
    const spreadRad = mouthSpread * Math.PI / 2;

    // Yellow Pac-Man body: pie slice (full circle minus mouth wedge)
    this.playerGraphics.fillStyle(0xffdd00, 1);
    this.playerGraphics.lineStyle(1, 0xffcc00, 0.8);
    this.playerGraphics.beginPath();
    this.playerGraphics.slice(0, 0, r, baseAngle + spreadRad, baseAngle - spreadRad, false);
    this.playerGraphics.fillPath();
    this.playerGraphics.strokePath();

    if (this.time.now < p.invincibleUntil && Math.floor(this.time.now / 80) % 2 === 0) {
      this.playerGraphics.lineStyle(2, 0xffffff, 0.9);
      this.playerGraphics.strokeCircle(0, 0, r + 4);
    }
  }

  buildGhosts() {
    this.ghostGraphics = this.ghosts.map(() => this.add.graphics());
  }

  drawGhosts() {
    const colors = [0xff4444, 0xffb6c1, 0x00ffff];
    const oy = this.hudOffsetY ?? HUD_OFFSET_Y;
    this.ghosts.forEach((g, i) => {
      if (g.removed) return;
      const gr = this.ghostGraphics[i];
      gr.clear();
      const [x, y0] = cellToPixel(g.col, g.row);
      const y = y0 + oy;
      const bob = Math.sin(this.time.now * 0.003 + g.bobPhase) * 2;
      gr.setPosition(x, y + bob);
      const w = this.cellSize * 0.85, h = this.cellSize * 0.9;
      gr.fillStyle(colors[g.id % 3], 1);
      gr.fillRoundedRect(-w / 2, -h / 2, w, h, this.cellSize * 0.2);
      for (let j = 0; j < 4; j++) {
        const fx = -w / 2 + (j + 0.5) * (w / 4);
        gr.fillCircle(fx, h / 2, this.cellSize * 0.12);
      }
      gr.fillStyle(0xffffff, 1);
      const eyeY = -h * 0.15;
      const [dc, dr] = g.dir && (g.dir[0] !== 0 || g.dir[1] !== 0) ? g.dir : [1, 0];
      const pupilOff = 3;
      gr.fillEllipse(-this.cellSize * 0.2, eyeY, this.cellSize * 0.18, this.cellSize * 0.22);
      gr.fillEllipse(this.cellSize * 0.1, eyeY, this.cellSize * 0.18, this.cellSize * 0.22);
      gr.fillStyle(0x000080, 1);
      gr.fillCircle(-this.cellSize * 0.2 + dc * pupilOff, eyeY + dr * pupilOff, 3);
      gr.fillCircle(this.cellSize * 0.1 + dc * pupilOff, eyeY + dr * pupilOff, 3);
    });
  }

  buildHUD() {
    const w = this.cameras.main.width;
    this.playerNameText = this.add.text(w - 12, 10, 'Player: ' + (this.playerName || 'Player'), { fontSize: 16, color: '#b0b0c0' }).setOrigin(1, 0);
    this.scoreText = this.add.text(12, 12, 'This level: 0', { fontSize: 18, color: '#e0e0e0' });
    this.totalScoreText = this.add.text(12, 32, 'Total: 0', { fontSize: 18, color: '#ffd54f' });
    this.livesText = this.add.text(12, 52, 'Lives: 3', { fontSize: 18, color: '#e0e0e0' });
    this.levelText = this.add.text(12, 72, 'Level 1', { fontSize: 16, color: '#b0b0c0' });
    this.invText = this.add.text(w - 120, 32, 'Invincible', { fontSize: 16, color: '#ffdd55' }).setVisible(false);
    // Prominent countdown clock (center-top, large, with background)
    const clockY = 38;
    this.clockBg = this.add.graphics();
    this.clockBg.fillStyle(0x1a1525, 0.95);
    this.clockBg.fillRoundedRect(w / 2 - 72, clockY - 22, 144, 44, 8);
    this.clockBg.lineStyle(2, 0x4a6ab8, 0.8);
    this.clockBg.strokeRoundedRect(w / 2 - 72, clockY - 22, 144, 44, 8);
    this.clockText = this.add.text(w / 2, clockY, formatCountdown(this.levelTimeSec * 1000), {
      fontSize: 28, color: '#ffffff', fontFamily: 'monospace',
      stroke: '#0d0d18', strokeThickness: 2
    }).setOrigin(0.5);
  }

  buildFreezeHalo() {
    this.freezeHalo = this.add.graphics();
    this.freezeHalo.setVisible(false);
  }

  drawFreezeHalo() {
    if (this.freezeInPlaceUntil <= 0) {
      this.freezeHalo.setVisible(false);
      return;
    }
    this.freezeHalo.setVisible(true);
    this.freezeHalo.clear();
    const [x, y0] = cellToPixel(this.player.col, this.player.row);
    const y = y0 + (this.hudOffsetY ?? HUD_OFFSET_Y);
    const pulse = 0.7 + 0.15 * Math.sin(this.time.now * 0.005);
    this.freezeHalo.lineStyle(3, 0xffdd55, 0.6);
    this.freezeHalo.strokeCircle(x, y, this.cellSize * pulse);
    this.freezeHalo.lineStyle(1, 0xffee88, 0.4);
    this.freezeHalo.strokeCircle(x, y, this.cellSize * pulse - 4);
  }

  movePlayer(dc, dr) {
    const p = this.player;
    if (p.frozen || p.moving) return;
    const nc = p.col + dc, nr = p.row + dr;
    if (isWall(nc, nr) || !inBounds(nc, nr)) return;
    p.col = nc; p.row = nr; p.dir = [dc, dr];
    p.moving = true;
    const [tx, ty0] = cellToPixel(nc, nr);
    const ty = ty0 + (this.hudOffsetY ?? HUD_OFFSET_Y);
    this.tweens.add({
      targets: p,
      playerTargetX: tx,
      playerTargetY: ty,
      duration: 80,
      ease: 'Power2',
      onComplete: () => { p.moving = false; }
    });

    const key = `${nc},${nr}`;
    if (this.pellets.has(key)) {
      const type = this.pellets.get(key);
      this.pellets.delete(key);
      p.score += type === HIGH_VALUE ? POINTS_HIGH : POINTS_LOW;
      this.addCollectEffect(nc, nr, type);
    }
  }

  addCollectEffect(col, row, type) {
    const [x, y0] = cellToPixel(col, row);
    const y = y0 + (this.hudOffsetY ?? HUD_OFFSET_Y);
    const g = this.add.graphics();
    g.setPosition(x, y);
    g.fillStyle(type === HIGH_VALUE ? 0xffb347 : 0x9090a0, 0.9);
    g.fillCircle(0, 0, 6);
    this.tweens.add({
      targets: g,
      alpha: 0,
      scale: 2.5,
      duration: 250,
      ease: 'Power2',
      onComplete: () => g.destroy()
    });
  }

  moveGhosts() {
    const dirs = [[0, -1], [0, 1], [-1, 0], [1, 0]];
    this.ghosts.forEach(g => {
      if (g.removed) return;
      if (Math.random() < 0.3 || (g.dir[0] === 0 && g.dir[1] === 0))
        g.dir = dirs[Math.floor(Math.random() * 4)];
      let nc = g.col + g.dir[0], nr = g.row + g.dir[1];
      if (isWall(nc, nr)) {
        g.dir = dirs[Math.floor(Math.random() * 4)];
        nc = g.col + g.dir[0]; nr = g.row + g.dir[1];
      }
      if (inBounds(nc, nr)) { g.col = nc; g.row = nr; }
    });
  }

  checkGhostCollision() {
    const p = this.player;
    if (this.time.now < p.invincibleUntil) return [];
    return this.ghosts.filter(g => !g.removed && g.col === p.col && g.row === p.row).map(g => g.id);
  }

  update(time, delta) {
    if (this.pendingRespawn) {
      this.pendingRespawn = false;
      const p = this.player;
      if (p.lives <= 0) return;
      // Respawn player in the same place where they died (and ghosts stay where they are)
      const [sx, sy0] = cellToPixel(p.col, p.row);
      const oy = this.hudOffsetY ?? HUD_OFFSET_Y;
      p.playerTargetX = sx; p.playerTargetY = sy0 + oy;
      p.invincibleUntil = time + RESPAWN_INVINCIBILITY_MS;
      p.dir = null;
      return;
    }
    // Freeze just ended (player pressed SPACE): clear state and apply penalty if early
    if (this.registry.get('freezeJustEnded')) {
      this.registry.remove('freezeJustEnded');
      const penaltySec = this.registry.get('freezePenaltySeconds');
      if (penaltySec != null) {
        this.registry.remove('freezePenaltySeconds');
        this.levelEndTime -= penaltySec * 1000;
      }
      this.player.frozen = false;
      this.freezeInPlaceUntil = 0;
      this.currentFreezeDurationMs = 0;
      this.player.invincibleUntil = this.time.now + RESPAWN_INVINCIBILITY_MS;
      // Next freeze ~30 sec from end of this freeze
      this.nextFreezeTime = this.time.now + FREEZE_INTERVAL_SEC * 1000 * (0.7 + 0.3 * Math.random());
    }
    // Resumed from death: schedule next freeze ~30 sec from now
    if (this.registry.get('resumedFromDeath')) {
      this.registry.remove('resumedFromDeath');
      this.nextFreezeTime = this.time.now + FREEZE_INTERVAL_SEC * 1000 * (0.7 + 0.3 * Math.random());
    }

    if (!this.player.frozen) {
      // Player movement: immediate on keypress, or one cell per delay when held
      const p = this.player;
      const justLeft = Phaser.Input.Keyboard.JustDown(this.cursors.left);
      const justRight = Phaser.Input.Keyboard.JustDown(this.cursors.right);
      const justUp = Phaser.Input.Keyboard.JustDown(this.cursors.up);
      const justDown = Phaser.Input.Keyboard.JustDown(this.cursors.down);
      const heldDelay = !p.moving && (time - this.lastPlayerMove >= PLAYER_MOVE_DELAY_MS);
      if (justLeft || (heldDelay && this.cursors.left.isDown)) { this.lastPlayerMove = time; this.movePlayer(-1, 0); }
      else if (justRight || (heldDelay && this.cursors.right.isDown)) { this.lastPlayerMove = time; this.movePlayer(1, 0); }
      else if (justUp || (heldDelay && this.cursors.up.isDown)) { this.lastPlayerMove = time; this.movePlayer(0, -1); }
      else if (justDown || (heldDelay && this.cursors.down.isDown)) { this.lastPlayerMove = time; this.movePlayer(0, 1); }
    }

    // Trigger freeze in place (instead of teleport)
    const p = this.player;
    if (time >= this.nextFreezeTime && this.freezeInPlaceUntil <= 0) {
      const inHighValue = isInHotZone(p.col, p.row);
      const durationMs = inHighValue ? FREEZE_DURATION_HIGH_VALUE_MS : FREEZE_DURATION_MS;
      gameLogEvent(this.registry, {
        event_type: 'freeze_start',
        timestamp_iso: new Date().toISOString(),
        session_id: this.registry.get('gameLogSessionId'),
        player_name: this.registry.get('gameLogPlayerName'),
        level_index: this.levelIndex,
        freeze_duration_ms: durationMs,
        in_high_value: inHighValue
      });
      this.player.frozen = true;
      this.freezeInPlaceUntil = 1;
      this.currentFreezeDurationMs = durationMs;
      // nextFreezeTime is set when this freeze ends (~30 sec after unfreeze)
      // Main keeps running so the clock continues; only ghosts/player are stopped via p.frozen
      this.scene.launch('FreezeOverlay', { durationMs, freezeStartGameTime: time, levelIndex: this.levelIndex });
    }

    {
      // Ghost movement — only when not frozen (entire game stops except clock during freeze)
      if (!p.frozen && time - this.lastGhostMove >= GHOST_MOVE_DELAY_MS) {
        this.lastGhostMove = time;
        this.moveGhosts();
      }

      // Ghost collision (no damage while frozen)
      const hit = !p.frozen ? this.checkGhostCollision() : [];
      if (hit.length > 0) {
        p.lives--;
        gameLogEvent(this.registry, {
          event_type: 'death',
          timestamp_iso: new Date().toISOString(),
          session_id: this.registry.get('gameLogSessionId'),
          player_name: this.registry.get('gameLogPlayerName'),
          level_index: this.levelIndex,
          lives_left: p.lives,
          total_score: this.totalScore
        });
        this.cameras.main.shake(200, 0.01);
        this.pendingRespawn = true;
        this.scene.launch('Death', {
          lives: p.lives,
          totalScore: this.totalScore,
          blocksConfig: this.blocksConfig,
          playerName: this.playerName
        });
        this.scene.pause();
      }
    }

    const levelRemainingMs = this.levelEndTime - time;
    this.clockBg.setVisible(true);
    this.clockText.setVisible(true);
    this.clockText.setText(formatCountdown(levelRemainingMs));
    if (levelRemainingMs <= 0) {
      const levelScore = this.player.score;
      const newTotal = this.totalScore + levelScore;
      gameLogEvent(this.registry, {
        event_type: 'level_end',
        timestamp_iso: new Date().toISOString(),
        session_id: this.registry.get('gameLogSessionId'),
        player_name: this.registry.get('gameLogPlayerName'),
        level_index: this.levelIndex,
        level_score: levelScore,
        total_score: newTotal,
        reason: 'time_up'
      });
      this.scene.start('LevelComplete', {
        levelIndex: this.levelIndex,
        levelScore,
        totalScore: newTotal,
        nextLevelTimeSec: getLevelTimeSec(this.levelIndex + 1),
        blocksConfig: this.blocksConfig,
        blockIndex: this.blockIndex,
        playerName: this.playerName
      });
      return;
    }
    if (levelRemainingMs < 30000) this.clockText.setColor('#ff6666');
    else this.clockText.setColor('#ffffff');

    // All pellets collected before time runs out — level complete
    if (this.pellets.size === 0) {
      const levelScore = this.player.score;
      const newTotal = this.totalScore + levelScore;
      gameLogEvent(this.registry, {
        event_type: 'level_end',
        timestamp_iso: new Date().toISOString(),
        session_id: this.registry.get('gameLogSessionId'),
        player_name: this.registry.get('gameLogPlayerName'),
        level_index: this.levelIndex,
        level_score: levelScore,
        total_score: newTotal,
        reason: 'all_pellets'
      });
      this.scene.start('LevelComplete', {
        levelIndex: this.levelIndex,
        levelScore,
        totalScore: newTotal,
        nextLevelTimeSec: getLevelTimeSec(this.levelIndex + 1),
        blocksConfig: this.blocksConfig,
        blockIndex: this.blockIndex,
        allPellets: true,
        playerName: this.playerName
      });
      return;
    }

    this.drawPellets();
    this.drawPlayer();
    this.drawGhosts();
    this.drawFreezeHalo();

    this.scoreText.setText('This level: ' + this.player.score);
    this.totalScoreText.setText('Total: ' + this.totalScore);
    this.livesText.setText('Lives: ' + this.player.lives);
    this.levelText.setText('Level ' + (this.levelIndex + 1));
    this.invText.setVisible(time < this.player.invincibleUntil);

    if (this.freezeMsg) this.freezeMsg.setVisible(false);
  }
}

// ─── Freeze Overlay ─────────────────────────────────────────────────────────
// SPACE during freeze is handled ONLY here:
//   - create(): spaceKey created (line ~664)
//   - update(): JustDown(spaceKey) at line ~677; if pastThreshold → unfreeze (679-681), else +2s penalty and stay in freeze (682-685)
// Main scene does NOT handle SPACE (spaceKey at 252 is never used). Main keeps running during freeze so the clock continues; only ghosts and player movement are stopped.
class FreezeOverlayScene extends Phaser.Scene {
  constructor() { super({ key: 'FreezeOverlay' }); }

  init(data) {
    this.durationMs = data.durationMs ?? FREEZE_DURATION_MS;
    this.freezeStartGameTime = data.freezeStartGameTime ?? 0;
    this.levelIndex = data.levelIndex ?? 0;
  }

  create() {
    const w = this.cameras.main.width;
    const h = this.cameras.main.height;
    this.penaltySeconds = 0;

    // Semi-transparent overlay over entire board — entire screen is paused
    const overlay = this.add.graphics();
    overlay.fillStyle(0x0d0d18, 0.75);
    overlay.fillRect(0, 0, w, h);

    const totalSec = this.durationMs / 1000;
    this.add.text(w / 2, h / 2 - 50, 'FREEZE', {
      fontSize: 42, color: '#ffdd55', fontFamily: 'Georgia, serif'
    }).setOrigin(0.5);
    this.durationText = this.add.text(w / 2, h / 2 + 10, `Wait ${totalSec} sec, then press SPACE`, {
      fontSize: 22, color: '#e0e0e0'
    }).setOrigin(0.5);
    this.countdownText = this.add.text(w / 2, h / 2 + 55, '', {
      fontSize: 22, color: '#b0b0c0'
    }).setOrigin(0.5);
    this.pressSpaceText = this.add.text(w / 2, h / 2 + 95, '', {
      fontSize: 20, color: '#ffdd55'
    }).setOrigin(0.5);
    this.earlyPenaltyText = this.add.text(w / 2, h / 2 + 130, '', {
      fontSize: 18, color: '#ff6666'
    }).setOrigin(0.5).setVisible(false);

    // ─── ONLY place that handles SPACE during freeze ─────────────────────────
    this.spaceKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE);
  }

  update(time) {
    // Elapsed = game time since freeze started (passed from Main so timing is correct)
    const elapsed = time - this.freezeStartGameTime;
    // Required wait = base duration + penalty (each early SPACE adds time you must wait AND reduces level time)
    const requiredWaitMs = this.durationMs + this.penaltySeconds * 1000;
    const remainingMs = Math.max(0, requiredWaitMs - elapsed);
    const remainingSec = Math.ceil(remainingMs / 1000);
    const pastThreshold = elapsed >= requiredWaitMs;

    // ─── SPACE during freeze: only unfreeze after duration + all penalties have passed; else +2s penalty and stay frozen ───
    if (Phaser.Input.Keyboard.JustDown(this.spaceKey)) {
      if (pastThreshold) {
        gameLogEvent(this.registry, {
          event_type: 'freeze_end',
          timestamp_iso: new Date().toISOString(),
          session_id: this.registry.get('gameLogSessionId'),
          player_name: this.registry.get('gameLogPlayerName'),
          level_index: this.levelIndex,
          space_clicks_during_freeze: Math.floor(this.penaltySeconds / PENALTY_PER_EARLY_TAP),
          penalty_seconds: this.penaltySeconds
        });
        if (this.penaltySeconds > 0) this.registry.set('freezePenaltySeconds', this.penaltySeconds);
        this.registry.set('freezeJustEnded', true);
        this.scene.stop('FreezeOverlay');
        this.scene.resume('Main');
      } else {
        this.penaltySeconds += PENALTY_PER_EARLY_TAP;
        this.earlyPenaltyText.setText(`Too early! +${PENALTY_PER_EARLY_TAP}s penalty (total +${this.penaltySeconds}s). Wait longer.`).setVisible(true);
      }
    }
  }
}

// ─── Death Overlay ────────────────────────────────────────────────────────
class DeathScene extends Phaser.Scene {
  constructor() { super({ key: 'Death' }); }

  init(data) {
    this.lives = data.lives ?? 0;
    this.totalScore = data.totalScore ?? 0;
    this.blocksConfig = data.blocksConfig ?? [];
    this.playerName = data.playerName ?? 'Player';
  }

  create() {
    const w = this.cameras.main.width, h = this.cameras.main.height;
    const overlay = this.add.graphics();
    overlay.fillStyle(0x400000, 0.85);
    overlay.fillRect(0, 0, w, h);
    this.add.text(w / 2, h / 2 - 30, 'You died!', { fontSize: 36, color: '#ff6666' }).setOrigin(0.5);
    this.add.text(w / 2, h / 2 + 20, this.lives > 0 ? 'Lives left: ' + this.lives : 'No lives left!', { fontSize: 22, color: '#e0e0e0' }).setOrigin(0.5);
    this.continueText = this.add.text(w / 2, h / 2 + 70, '', { fontSize: 18, color: '#ffaa66' }).setOrigin(0.5).setVisible(false);
    this.time.delayedCall(3000, () => {
      this.continueText.setText('Press SPACE to continue').setVisible(true);
      this.input.keyboard.once('keydown-SPACE', () => {
        this.scene.stop('Death');
        if (this.lives <= 0) {
          this.scene.start('GameOver', { score: this.totalScore, playerName: this.playerName });
        } else {
          this.registry.set('resumedFromDeath', true);
          this.scene.resume('Main');
        }
      });
    });
  }
}

// ─── Level Complete (time up or all pellets) ───────────────────────────────
class LevelCompleteScene extends Phaser.Scene {
  constructor() { super({ key: 'LevelComplete' }); }

  init(data) {
    this.levelIndex = data.levelIndex ?? 0;
    this.levelScore = data.levelScore ?? 0;
    this.totalScore = data.totalScore ?? 0;
    this.nextLevelTimeSec = data.nextLevelTimeSec ?? 110;
    this.blocksConfig = data.blocksConfig ?? [];
    this.blockIndex = data.blockIndex ?? 0;
    this.allPellets = data.allPellets ?? false;
    this.playerName = data.playerName ?? 'Player';
  }

  create() {
    const w = this.cameras.main.width, h = this.cameras.main.height;
    this.add.rectangle(0, 0, w, h, 0x0d0d18).setOrigin(0);
    const levelNum = this.levelIndex + 1;
    const title = this.allPellets ? 'All pellets collected!' : 'Time\'s up!';
    this.add.text(w / 2, 70, 'Level ' + levelNum + ' complete', { fontSize: 22, color: '#b0b0c0' }).setOrigin(0.5);
    this.add.text(w / 2, 115, title, { fontSize: 26, color: '#ffd54f' }).setOrigin(0.5);
    this.add.text(w / 2, 175, 'This level: +' + this.levelScore + ' pts', { fontSize: 24, color: '#c0c0e0' }).setOrigin(0.5);
    this.add.text(w / 2, 220, 'Total score: ' + this.totalScore, { fontSize: 24, color: '#ffd54f' }).setOrigin(0.5);
    const nextLevelIndex = this.levelIndex + 1;
    if (nextLevelIndex < LEVEL_COUNT) {
      this.add.text(w / 2, 280, 'Next level: ' + this.nextLevelTimeSec + ' sec', { fontSize: 18, color: '#a0a0b0' }).setOrigin(0.5);
      this.add.text(w / 2, h - 50, 'Press SPACE for next level', { fontSize: 18, color: '#ffd54f' }).setOrigin(0.5);
    } else {
      this.add.text(w / 2, 280, 'All 5 levels complete!', { fontSize: 18, color: '#a0a0b0' }).setOrigin(0.5);
      this.add.text(w / 2, h - 50, 'Press SPACE to finish', { fontSize: 18, color: '#ffd54f' }).setOrigin(0.5);
    }
    this.input.keyboard.once('keydown-SPACE', () => {
      if (nextLevelIndex >= LEVEL_COUNT) {
        this.scene.start('GameOver', { score: this.totalScore, playerName: this.playerName });
      } else {
        const nextBlock = (this.blockIndex + 1) % this.blocksConfig.length;
        this.scene.start('Main', {
          blockIndex: nextBlock,
          blocksConfig: this.blocksConfig,
          totalScore: this.totalScore,
          levelIndex: nextLevelIndex,
          playerName: this.playerName
        });
      }
    });
  }
}

// ─── Victory (legacy / unused now; kept for reference) ──────────────────────
class VictoryScene extends Phaser.Scene {
  constructor() { super({ key: 'Victory' }); }

  init(data) {
    this.score = data.score ?? 0;
    this.blockIndex = data.blockIndex ?? 0;
    this.totalBlocks = data.totalBlocks ?? 1;
    this.totalScore = data.totalScore ?? data.score ?? 0;
    this.blocksConfig = data.blocksConfig ?? [];
    this.playerName = data.playerName ?? 'Player';
  }

  create() {
    const w = this.cameras.main.width, h = this.cameras.main.height;
    this.add.rectangle(0, 0, w, h, 0x0d0d18).setOrigin(0);
    this.add.text(w / 2, 90, 'All pellets collected!', { fontSize: 26, color: '#ffd54f' }).setOrigin(0.5);
    this.add.text(w / 2, 140, 'Block complete', { fontSize: 18, color: '#b0b0c0' }).setOrigin(0.5);
    this.add.text(w / 2, 200, 'Score: ' + this.score, { fontSize: 24, color: '#ffd54f' }).setOrigin(0.5);
    this.add.text(w / 2, 280, 'Press SPACE to continue', { fontSize: 18, color: '#a0a0b0' }).setOrigin(0.5);
    this.input.keyboard.once('keydown-SPACE', () => {
      if (this.blockIndex < this.totalBlocks - 1)
        this.scene.start('Main', { blockIndex: this.blockIndex + 1, blocksConfig: this.blocksConfig, totalScore: this.totalScore });
      else
        this.scene.start('GameOver', { score: this.totalScore, playerName: this.playerName });
    });
  }
}

// ─── Game Over ────────────────────────────────────────────────────────────
class GameOverScene extends Phaser.Scene {
  constructor() { super({ key: 'GameOver' }); }

  init(data) {
    this.score = data.score ?? 0;
    this.playerName = data.playerName ?? 'Player';
  }

  create() {
    const w = this.cameras.main.width, h = this.cameras.main.height;
    this.add.rectangle(0, 0, w, h, 0x0d0d18).setOrigin(0);
    this.add.text(w / 2, 100, 'Session complete', { fontSize: 26, color: '#e0e0e0' }).setOrigin(0.5);
    this.add.text(w / 2, 145, this.playerName + '!', { fontSize: 22, color: '#b0b0c0' }).setOrigin(0.5);
    this.add.text(w / 2, 195, 'Total score: ' + this.score, { fontSize: 24, color: '#ffd54f' }).setOrigin(0.5);
    this.add.text(w / 2, 280, 'Close window to exit', { fontSize: 16, color: '#808090' }).setOrigin(0.5);

    // Flush session log to CSV and trigger download
    const events = this.registry.get('gameLogEvents');
    const sessionId = this.registry.get('gameLogSessionId');
    const playerName = this.registry.get('gameLogPlayerName') ?? this.playerName;
    if (events && Array.isArray(events)) {
      gameLogEvent(this.registry, {
        event_type: 'session_end',
        timestamp_iso: new Date().toISOString(),
        session_id: sessionId,
        player_name: playerName,
        total_score: this.score
      });
      const csv = buildSessionCsv(events);
      const now = new Date();
      const pad = (n) => (n < 10 ? '0' : '') + n;
      const dateStr = now.getFullYear() + pad(now.getMonth() + 1) + pad(now.getDate()) + '_' + pad(now.getHours()) + pad(now.getMinutes()) + pad(now.getSeconds());
      const filename = 'session_' + (sessionId || 'unknown') + '_' + dateStr + '.csv';
      downloadCsv(csv, filename);
    }
    this.registry.remove('gameLogSessionId');
    this.registry.remove('gameLogPlayerName');
    this.registry.remove('gameLogEvents');
  }
}

// ─── Config & Launch ──────────────────────────────────────────────────────
const config = {
  type: Phaser.AUTO,
  width: COLS * CELL_SIZE,
  height: ROWS * CELL_SIZE + HUD_OFFSET_Y,
  parent: 'game-container',
  backgroundColor: 0x0d0d18,
  scale: {
    mode: Phaser.Scale.NONE,
    width: COLS * CELL_SIZE,
    height: ROWS * CELL_SIZE + HUD_OFFSET_Y
  },
  dom: { createContainer: true },
  scene: [BootScene, InstructionsScene, MainScene, FreezeOverlayScene, DeathScene, LevelCompleteScene, VictoryScene, GameOverScene]
};
new Phaser.Game(config);
