"""agents.py - AI tank agents (Basic, Fast, Armor, Boss)"""

import random
from constants import (
    UP, DOWN, LEFT, RIGHT, DIRS, DIR_DELTA, DIR_TO_MOVE, DIR_OPPOSITE,
    MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, SHOOT, IDLE,
    ACTION_TO_DIR, EAGLE_POS, PLAYER_SPAWN, ENEMY_SPAWNS,
    BASIC_HP, FAST_HP, ARMOR_HP, BOSS_HP,
    BASIC_MOVE_DELAY, FAST_MOVE_DELAY, ARMOR_MOVE_DELAY, BOSS_MOVE_DELAY,
    BFS_RECOMPUTE_TICKS, ARMOR_RETREAT_HITS, ARMOR_RETREAT_TICKS,
    TANK_BASIC, TANK_FAST, TANK_ARMOR, TANK_BOSS,
    GRID_ROWS, GRID_COLS, BRICK, STEEL, WATER, FOREST, EMPTY, EAGLE,
    get_boss_depth, MINIMAX_LOG_FILE,
)
from search import (
    bfs, greedy, astar, minimax,
    find_nearest_steel, MinimaxState, MinimaxLogger,
)


def _in_bounds(r: int, c: int) -> bool:
    return 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS


def _manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _facing_direction(pos: tuple, nxt: tuple) -> str:
    """Return the direction needed to move from pos to nxt."""
    dr = nxt[0] - pos[0]
    dc = nxt[1] - pos[1]
    for d, (ddr, ddc) in DIR_DELTA.items():
        if ddr == dr and ddc == dc:
            return d
    return DOWN


def _direction_to_action(current_dir: str, target_dir: str,
                          pos: tuple, nxt_pos: tuple) -> str:
    """Return MOVE_* action that steers the tank toward nxt_pos."""
    _ = current_dir   # could be used for turning-delay logic
    return DIR_TO_MOVE[target_dir]


def _wall_in_direction(grid: list, pos: tuple, direction: str) -> int:
    """Return tile type of the cell directly ahead, or -1 if out-of-bounds."""
    dr, dc = DIR_DELTA[direction]
    nr, nc = pos[0] + dr, pos[1] + dc
    if _in_bounds(nr, nc):
        return grid[nr][nc]
    return -1


# ─────────────────────────────────────────────────────────────────────────────
# Base Agent
# ─────────────────────────────────────────────────────────────────────────────

class Agent:
    """Abstract base class for all AI tank agents."""

    tank_type: str = 'base'
    max_hp:    int = 1

    def __init__(self, spawn_pos: tuple):
        self.pos       = spawn_pos
        self.direction = DOWN
        self.hp        = self.max_hp
        self._path: list = []

    # ── Public interface ──────────────────────────────────────────────────────

    def decide(self, percepts: dict) -> str:
        """
        Choose an action for this tick.

        percepts keys
        -------------
        pos         (row, col)      Tank's current position
        direction   str             Current facing direction
        hp          int             Current HP
        grid        list[list[int]] Current map state
        player_pos  (row, col)      Human player position
        player_hp   int
        eagle_pos   (row, col)
        bullets     list[dict]      Active bullets {pos, dir, owner}
        enemies     list[Agent]     Other enemy agents still alive
        tick        int             Current game tick
        logger      MinimaxLogger | None
        """
        raise NotImplementedError

    def update(self, event: str, **kwargs) -> None:
        """
        Receive an event notification from the engine.
        Events: 'hit', 'blocked', 'enemy_destroyed', 'brick_destroyed'
        """
        pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _next_path_action(self, grid: list, target: tuple) -> str:
        """
        Return MOVE_* for the next step along self._path toward target.
        Re-plans if path is empty or stale.
        """
        if not self._path or self._path[0] not in self._reachable_neighbours(grid):
            self._plan(grid, target)

        if not self._path:
            return self._wander()

        nxt = self._path[0]
        d   = _facing_direction(self.pos, nxt)
        self.direction = d
        return DIR_TO_MOVE[d]

    def _plan(self, grid: list, target: tuple) -> None:
        """Compute a new path using BFS; subclasses override for other algos."""
        self._path = bfs(grid, self.pos, target)

    def _advance_path(self) -> None:
        """Pop the front of the path after a successful move."""
        if self._path:
            self._path.pop(0)

    def _reachable_neighbours(self, grid: list) -> set:
        s = set()
        for d in DIRS:
            dr, dc = DIR_DELTA[d]
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if _in_bounds(nr, nc) and grid[nr][nc] not in (STEEL, WATER):
                s.add((nr, nc))
        return s

    def _wander(self) -> str:
        """Random movement fallback when no path found."""
        return random.choice([MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT])

    def _should_shoot(self, grid: list, target: tuple) -> bool:
        """
        True if the tank faces a BRICK wall that lies between it and target,
        or if target is directly in the line of fire.
        """
        dr, dc = DIR_DELTA[self.direction]
        r, c = self.pos
        for _ in range(26):
            r += dr; c += dc
            if not _in_bounds(r, c):
                break
            t = grid[r][c]
            if (r, c) == target:
                return True
            if t == BRICK:
                return True
            if t in (STEEL, WATER):
                break
        return False

    def _player_in_line_of_fire(self, grid: list, player_pos: tuple) -> bool:
        """Check if player is visible in the current facing direction."""
        dr, dc = DIR_DELTA[self.direction]
        r, c = self.pos
        for _ in range(26):
            r += dr; c += dc
            if not _in_bounds(r, c):
                break
            if (r, c) == player_pos:
                return True
            t = grid[r][c]
            if t in (STEEL, WATER):
                break
        return False

    def _shoot_eagle_if_adjacent(self, eagle_pos: tuple) -> str:
        """If eagle is adjacent, rotate to face it and shoot. Else return IDLE."""
        for direction in DIRS:
            dr, dc = DIR_DELTA[direction]
            nr, nc = self.pos[0] + dr, self.pos[1] + dc
            if (nr, nc) == eagle_pos:
                self.direction = direction
                return SHOOT
        return IDLE


# ─────────────────────────────────────────────────────────────────────────────
# 1. BasicTank — Simple Reflex Agent (BFS)
# ─────────────────────────────────────────────────────────────────────────────

class BasicTank(Agent):
    """
    Simple Reflex Agent.

    Percept  →  Action rule table:
        Path available  →  follow BFS path step
        Brick ahead     →  SHOOT
        No path         →  random wander

    Path recomputed on:  spawn / path blocked / every BFS_RECOMPUTE_TICKS

    BFS treats ONLY Empty and Forest as passable (cost = 1).
    Bricks are NOT passable — BasicTank takes detours, never plans through walls.
    """

    tank_type = TANK_BASIC
    max_hp    = BASIC_HP

    def __init__(self, spawn_pos: tuple):
        super().__init__(spawn_pos)
        self._last_plan_tick = -BFS_RECOMPUTE_TICKS  # force plan on first tick
        self._blocked_count  = 0

    def _plan(self, grid: list, target: tuple) -> None:
        """BFS with bricks treated as impassable (shortest-hop open path)."""
        self._path = bfs(grid, self.pos, target, treat_brick_passable=False)

    def decide(self, percepts: dict) -> str:
        grid      = percepts['grid']
        tick      = percepts['tick']
        eagle_pos = percepts['eagle_pos']
        player_pos = percepts['player_pos']

        # Sync position
        self.pos       = percepts['pos']
        self.direction = percepts['direction']

        # Try to shoot eagle if adjacent
        eagle_shot = self._shoot_eagle_if_adjacent(eagle_pos)
        if eagle_shot == SHOOT:
            return SHOOT

        # Shoot at player if visible (30% chance)
        if self._player_in_line_of_fire(grid, player_pos) and random.random() < 0.3:
            return SHOOT

        # Replan trigger: every 5s OR path empty OR repeated blocks
        replan = (
            not self._path or
            tick - self._last_plan_tick >= BFS_RECOMPUTE_TICKS or
            self._blocked_count >= 3
        )
        if replan:
            self._plan(grid, eagle_pos)
            self._last_plan_tick = tick
            self._blocked_count  = 0

        # Check brick directly ahead on current path
        if self._path:
            nxt  = self._path[0]
            d    = _facing_direction(self.pos, nxt)
            self.direction = d
            ahead = _wall_in_direction(grid, self.pos, d)
            if ahead == BRICK:
                return SHOOT

            if nxt == self.pos:
                self._advance_path()

            if self._path:
                nxt = self._path[0]
                d   = _facing_direction(self.pos, nxt)
                self.direction = d
                return DIR_TO_MOVE[d]

        return self._wander()

    def update(self, event: str, **kwargs) -> None:
        if event == 'blocked':
            self._blocked_count += 1
        elif event == 'moved':
            self._advance_path()
            self._blocked_count = 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. FastTank — Goal-Based Agent (Greedy Best-First)
# ─────────────────────────────────────────────────────────────────────────────

class FastTank(Agent):
    """
    Goal-Based Agent.

    Single goal: reach and destroy the Eagle as fast as possible.
    Uses Greedy Best-First search; ignores player entirely.
    Recomputes path every tick (always has freshest heuristic estimate).
    """

    tank_type = TANK_FAST
    max_hp    = FAST_HP

    def __init__(self, spawn_pos: tuple):
        super().__init__(spawn_pos)

    def _plan(self, grid: list, target: tuple) -> None:
        self._path = greedy(grid, self.pos, target)

    def decide(self, percepts: dict) -> str:
        grid      = percepts['grid']
        eagle_pos = percepts['eagle_pos']
        player_pos = percepts['player_pos']

        self.pos       = percepts['pos']
        self.direction = percepts['direction']

        # Try to shoot eagle if adjacent
        eagle_shot = self._shoot_eagle_if_adjacent(eagle_pos)
        if eagle_shot == SHOOT:
            return SHOOT

        # Shoot at player if visible (20% chance)
        if self._player_in_line_of_fire(grid, player_pos) and random.random() < 0.2:
            return SHOOT

        # Replan every tick for up-to-date greedy path
        self._plan(grid, eagle_pos)

        if self._path:
            nxt = self._path[0]
            if nxt == self.pos:
                self._advance_path()
                if not self._path:
                    return IDLE

            nxt = self._path[0]
            d   = _facing_direction(self.pos, nxt)
            self.direction = d

            ahead = _wall_in_direction(grid, self.pos, d)
            if ahead == BRICK:
                return SHOOT

            return DIR_TO_MOVE[d]

        return self._wander()

    def update(self, event: str, **kwargs) -> None:
        if event == 'moved':
            self._advance_path()


# ─────────────────────────────────────────────────────────────────────────────
# 3. ArmorTank — Model-Based Reflex Agent (A*)
# ─────────────────────────────────────────────────────────────────────────────

class ArmorTank(Agent):
    """
    Model-Based Reflex Agent.

    Internal state model
    --------------------
    hits_taken    : int   — cumulative damage received
    known_steel   : set   — (r,c) of confirmed steel cells seen
    mode          : str   — 'ATTACK' | 'RETREAT' | 'COVER'
    retreat_ticks : int   — countdown while hiding in cover

    Behaviour
    ---------
    ATTACK   : A* path to Eagle; shoot bricks in the way.
    RETREAT  : On 3rd hit → A* to nearest steel cell (cover).
    COVER    : Wait ARMOR_RETREAT_TICKS, then resume ATTACK.
    """

    tank_type = TANK_ARMOR
    max_hp    = ARMOR_HP

    _MODE_ATTACK  = 'ATTACK'
    _MODE_RETREAT = 'RETREAT'
    _MODE_COVER   = 'COVER'

    def __init__(self, spawn_pos: tuple):
        super().__init__(spawn_pos)
        self.hits_taken    = 0
        self.known_steel   = set()
        self.mode          = self._MODE_ATTACK
        self.retreat_ticks = 0
        self._cover_pos    = None

    def _plan(self, grid: list, target: tuple) -> None:
        self._path = astar(grid, self.pos, target)

    def _plan_retreat(self, grid: list) -> None:
        cover = find_nearest_steel(grid, self.pos)
        if cover is None:
            # No steel nearby — just retreat toward a map edge
            cover = (0, self.pos[1])
        self._cover_pos = cover
        self._path      = astar(grid, self.pos, cover)

    def decide(self, percepts: dict) -> str:
        grid      = percepts['grid']
        tick      = percepts['tick']
        eagle_pos = percepts['eagle_pos']
        player_pos = percepts['player_pos']

        self.pos       = percepts['pos']
        self.direction = percepts['direction']

        # Try to shoot eagle if adjacent
        eagle_shot = self._shoot_eagle_if_adjacent(eagle_pos)
        if eagle_shot == SHOOT:
            return SHOOT

        # Shoot at player if visible (35% chance - more aggressive)
        if self._player_in_line_of_fire(grid, player_pos) and random.random() < 0.35:
            return SHOOT

        # Update steel knowledge from visible surroundings (4-neighbours)
        for d in DIRS:
            dr, dc = DIR_DELTA[d]
            nr, nc = self.pos[0]+dr, self.pos[1]+dc
            if _in_bounds(nr, nc) and grid[nr][nc] == STEEL:
                self.known_steel.add((nr, nc))

        # ── COVER mode ────────────────────────────────────────────────────────
        if self.mode == self._MODE_COVER:
            self.retreat_ticks -= 1
            if self.retreat_ticks <= 0:
                self.mode  = self._MODE_ATTACK
                self._path = []
            return IDLE

        # ── RETREAT mode ─────────────────────────────────────────────────────
        if self.mode == self._MODE_RETREAT:
            if not self._path:
                self._plan_retreat(grid)
            if not self._path or self.pos == self._cover_pos:
                self.mode          = self._MODE_COVER
                self.retreat_ticks = ARMOR_RETREAT_TICKS
                return IDLE
            nxt = self._path[0]
            if nxt == self.pos:
                self._advance_path()
                return IDLE
            d = _facing_direction(self.pos, nxt)
            self.direction = d
            return DIR_TO_MOVE[d]

        # ── ATTACK mode ───────────────────────────────────────────────────────
        if not self._path:
            self._plan(grid, eagle_pos)

        if not self._path:
            return self._wander()

        nxt = self._path[0]
        if nxt == self.pos:
            self._advance_path()
            if not self._path:
                return IDLE
            nxt = self._path[0]

        d = _facing_direction(self.pos, nxt)
        self.direction = d
        ahead = _wall_in_direction(grid, self.pos, d)

        if ahead == BRICK:
            return SHOOT

        return DIR_TO_MOVE[d]

    def update(self, event: str, **kwargs) -> None:
        if event == 'hit':
            self.hits_taken += 1
            if (self.hits_taken % ARMOR_RETREAT_HITS == 0 and
                    self.mode == self._MODE_ATTACK):
                self.mode  = self._MODE_RETREAT
                self._path = []
        elif event == 'moved':
            self._advance_path()
        elif event == 'blocked':
            self._path = []   # force replan


# ─────────────────────────────────────────────────────────────────────────────
# 4. BossTank — Adversarial Agent (Minimax + Alpha-Beta)
# ─────────────────────────────────────────────────────────────────────────────

class BossTank(Agent):
    """
    Adversarial Agent.

    Phases (determined by HP)
    -------------------------
    HP 10-7  → Minimax depth 2  (fast scan, aggressive)
    HP  6-3  → Minimax depth 3  (deeper threat assessment)
    HP  2-1  → Minimax depth 4  (desperate, maximum lookahead)

    The agent builds a MinimaxState snapshot each tick, calls minimax(),
    and executes the returned best action.
    Benchmarking data is written to minimax_log.csv when a logger is provided.
    """

    tank_type = TANK_BOSS
    max_hp    = BOSS_HP

    def __init__(self, spawn_pos: tuple, enable_benchmark: bool = False):
        super().__init__(spawn_pos)
        self._shoot_cooldown = 0
        self.logger = MinimaxLogger() if enable_benchmark else None

    # ── state snapshot builder ────────────────────────────────────────────────

    def _build_state(self, percepts: dict) -> MinimaxState:
        bullets_snapshot = [
            {'pos': b['pos'], 'dir': b['dir'], 'owner': b['owner']}
            for b in percepts.get('bullets', [])
        ]
        destroyed = frozenset(percepts.get('destroyed_bricks', set()))
        return MinimaxState(
            boss_pos   = self.pos,
            boss_dir   = self.direction,
            boss_hp    = self.hp,
            player_pos = percepts['player_pos'],
            player_dir = percepts.get('player_dir', DOWN),
            player_hp  = percepts['player_hp'],
            eagle_pos  = percepts['eagle_pos'],
            bullets    = bullets_snapshot,
            destroyed  = destroyed,
        )

    def decide(self, percepts: dict) -> str:
        self.pos       = percepts['pos']
        self.direction = percepts['direction']
        self.hp        = percepts['hp']

        grid  = percepts['grid']
        tick  = percepts['tick']

        state = self._build_state(percepts)

        # Minimax returns the best action for the Boss
        action = minimax(state, grid, tick=tick, logger=self.logger)

        # Throttle shooting
        if action == SHOOT:
            if self._shoot_cooldown > 0:
                action = IDLE
            else:
                self._shoot_cooldown = 45

        if self._shoot_cooldown > 0:
            self._shoot_cooldown -= 1

        # Sync direction from move action
        if action in ACTION_TO_DIR:
            self.direction = ACTION_TO_DIR[action]

        return action

    def update(self, event: str, **kwargs) -> None:
        if event == 'hit':
            self.hp = max(0, self.hp - 1)
