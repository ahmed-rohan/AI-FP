"""constants.py - Battle City AI Configuration"""

# ── Grid ──────────────────────────────────────────────────────────────────────
GRID_ROWS = 26
GRID_COLS = 26
CELL_SIZE  = 24          # pixels per grid cell

# ── Window ────────────────────────────────────────────────────────────────────
PANEL_WIDTH = 220        # right-side HUD panel width (px)
WIN_W = GRID_COLS * CELL_SIZE + PANEL_WIDTH   # 844
WIN_H = GRID_ROWS * CELL_SIZE                 # 624
FPS   = 60

# ── Tile Types ────────────────────────────────────────────────────────────────
EMPTY  = 0
BRICK  = 1
STEEL  = 2
WATER  = 3
FOREST = 4
EAGLE  = 5

# ── A* Traversal Costs ────────────────────────────────────────────────────────
INF = float('inf')
TILE_COST = {
    EMPTY:  1,
    FOREST: 1,
    BRICK:  3,      # shoot-through + wait penalty
    STEEL:  INF,
    WATER:  INF,
    EAGLE:  INF,
}

# ── Colours (RGB) ────────────────────────────────────────────────────────────

# ── Directions ────────────────────────────────────────────────────────────────
UP    = 'UP'
DOWN  = 'DOWN'
LEFT  = 'LEFT'
RIGHT = 'RIGHT'
DIRS  = [UP, DOWN, LEFT, RIGHT]
DIR_DELTA    = {UP: (-1, 0), DOWN: (1, 0), LEFT: (0, -1), RIGHT: (0, 1)}
DIR_OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

# ── Actions ───────────────────────────────────────────────────────────────────
MOVE_UP    = 'MOVE_UP'
MOVE_DOWN  = 'MOVE_DOWN'
MOVE_LEFT  = 'MOVE_LEFT'
MOVE_RIGHT = 'MOVE_RIGHT'
SHOOT      = 'SHOOT'
IDLE       = 'IDLE'

ACTION_TO_DIR = {
    MOVE_UP: UP, MOVE_DOWN: DOWN,
    MOVE_LEFT: LEFT, MOVE_RIGHT: RIGHT,
}
DIR_TO_MOVE = {
    UP: MOVE_UP, DOWN: MOVE_DOWN,
    LEFT: MOVE_LEFT, RIGHT: MOVE_RIGHT,
}

# ── Tank Stats ────────────────────────────────────────────────────────────────
BASIC_HP  = 1
FAST_HP   = 1
ARMOR_HP  = 4
BOSS_HP   = 10

# Move delay = ticks between position updates (lower = faster)
PLAYER_MOVE_DELAY = 7
BASIC_MOVE_DELAY  = 18   # ~3.3 moves/sec
FAST_MOVE_DELAY   = 9    # ~6.7 moves/sec
ARMOR_MOVE_DELAY  = 15   # ~4.0 moves/sec
BOSS_MOVE_DELAY   = 12   # ~5.0 moves/sec
BULLET_MOVE_DELAY = 4    # ~15 moves/sec (≈2× player speed)

PLAYER_SHOOT_CD = 30     # ticks between player shots
ENEMY_SHOOT_CD  = 60     # ticks between enemy shots

# ── Map Layout ────────────────────────────────────────────────────────────────
EAGLE_POS    = (24, 13)
PLAYER_SPAWN = (25, 0)
ENEMY_SPAWNS = [(0, 0), (0, 13), (0, 25)]

# 8-neighbours of Eagle cell that form the protection ring
EAGLE_RING_OFFSETS = [
    (-1, -1), (-1, 0), (-1, 1),
    ( 0, -1),           ( 0, 1),
    ( 1, -1), ( 1, 0), ( 1, 1),
]

# ── CSP Constraints ───────────────────────────────────────────────────────────
MAX_WALL_DENSITY = 0.40   # fraction of total cells
MIN_SPAWN_DIST   = 10     # Manhattan dist: enemy spawn → player spawn
MAX_ENEMIES_ALIVE = 4     # max simultaneous enemies on field

# ── AI Timers ─────────────────────────────────────────────────────────────────
BFS_RECOMPUTE_TICKS = 300    # 5 s at 60 FPS
ARMOR_RETREAT_HITS  = 3      # hits before ArmorTank retreats
ARMOR_RETREAT_TICKS = 120    # 2 s in cover before resuming (guide spec)

# ── Minimax Depth Schedule ────────────────────────────────────────────────────
def get_boss_depth(hp: int) -> int:
    """Return minimax search depth based on Boss current HP."""
    if hp >= 7:   return 2   # HP 10-7
    elif hp >= 3: return 3   # HP  6-3
    else:         return 4   # HP  2-1

# ── Scoring ───────────────────────────────────────────────────────────────────
SCORE_BASIC = 100
SCORE_FAST  = 200
SCORE_ARMOR = 400
SCORE_BOSS  = 1000

# ── Files ─────────────────────────────────────────────────────────────────────
MINIMAX_LOG_FILE = 'minimax_log.csv'

# ── Tank type identifiers ─────────────────────────────────────────────────────
TANK_PLAYER = 'player'
TANK_BASIC  = 'basic'
TANK_FAST   = 'fast'
TANK_ARMOR  = 'armor'
TANK_BOSS   = 'boss'
