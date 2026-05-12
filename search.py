"""search.py - Pathfinding algorithms (BFS, Greedy, A*, Minimax)"""

import heapq
import csv
import os
import time
import copy
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from constants import (
    GRID_ROWS, GRID_COLS, TILE_COST, INF,
    EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE,
    UP, DOWN, LEFT, RIGHT, DIRS, DIR_DELTA,
    MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, SHOOT, IDLE,
    DIR_TO_MOVE, ACTION_TO_DIR, DIR_OPPOSITE,
    MINIMAX_LOG_FILE, get_boss_depth,
    BULLET_MOVE_DELAY,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _in_bounds(r: int, c: int) -> bool:
    return 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS


def _manhattan(a: tuple, b: tuple) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _reconstruct(came_from: dict, current: tuple) -> list:
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path   # does NOT include start; includes goal


# ─────────────────────────────────────────────────────────────────────────────
# BFS — Shortest-hop (BasicTank)
# ─────────────────────────────────────────────────────────────────────────────

def bfs(grid: list, start: tuple, goal: tuple,
        treat_brick_passable: bool = True) -> list:
    """
    Breadth-first search on the 26×26 grid.

    Parameters
    ----------
    grid                : 2-D list of tile ints.
    start, goal         : (row, col) tuples.
    treat_brick_passable: If True, BRICK counts as passable (tank will shoot
                          through it); STEEL and WATER are always blocked.

    Returns
    -------
    List of (row, col) cells from start (exclusive) to goal (inclusive).
    Empty list if no path found.
    """
    if start == goal:
        return []

    def passable(r, c):
        t = grid[r][c]
        if t in (STEEL, WATER):
            return False
        if t == BRICK and not treat_brick_passable:
            return False
        return True

    visited = {start}
    came_from = {}
    q = deque([start])

    while q:
        pos = q.popleft()
        for d in DIRS:
            dr, dc = DIR_DELTA[d]
            nr, nc = pos[0] + dr, pos[1] + dc
            if not _in_bounds(nr, nc):
                continue
            nxt = (nr, nc)
            if nxt in visited:
                continue
            if nxt == goal or passable(nr, nc):
                visited.add(nxt)
                came_from[nxt] = pos
                if nxt == goal:
                    return _reconstruct(came_from, goal)
                q.append(nxt)

    return []   # unreachable


# ─────────────────────────────────────────────────────────────────────────────
# Greedy Best-First Search — Manhattan heuristic (FastTank)
# ─────────────────────────────────────────────────────────────────────────────

def greedy(grid: list, start: tuple, goal: tuple) -> list:
    """
    Greedy best-first search; priority = Manhattan distance to goal.
    Ignores tile costs and player position — just charges toward the Eagle.

    Returns path list same format as bfs().
    """
    if start == goal:
        return []

    def passable(r, c):
        return grid[r][c] not in (STEEL, WATER)

    came_from = {}
    visited = {start}
    # heap: (heuristic, (row, col))
    heap = [(_manhattan(start, goal), start)]

    while heap:
        _, pos = heapq.heappop(heap)
        if pos == goal:
            return _reconstruct(came_from, goal)
        for d in DIRS:
            dr, dc = DIR_DELTA[d]
            nr, nc = pos[0] + dr, pos[1] + dc
            if not _in_bounds(nr, nc):
                continue
            nxt = (nr, nc)
            if nxt in visited:
                continue
            if nxt == goal or passable(nr, nc):
                visited.add(nxt)
                came_from[nxt] = pos
                h = _manhattan(nxt, goal)
                heapq.heappush(heap, (h, nxt))

    return []


# ─────────────────────────────────────────────────────────────────────────────
# A* — Cost-optimal navigation (ArmorTank)
# ─────────────────────────────────────────────────────────────────────────────

def astar(grid: list, start: tuple, goal: tuple,
          custom_cost=None) -> list:
    """
    A* search with TILE_COST table (BRICK=3, STEEL/WATER=INF).

    Parameters
    ----------
    grid        : 2-D tile grid.
    start, goal : (row, col).
    custom_cost : Optional callable(tile_int) -> float to override TILE_COST.

    Returns path list same format as bfs().
    """
    if start == goal:
        return []

    cost_fn = custom_cost if custom_cost else lambda t: TILE_COST.get(t, INF)

    g_score = {start: 0.0}
    came_from = {}
    # heap: (f, g, pos)
    heap = [(_manhattan(start, goal), 0.0, start)]

    while heap:
        f, g, pos = heapq.heappop(heap)
        if pos == goal:
            return _reconstruct(came_from, goal)
        if g > g_score.get(pos, INF):
            continue   # stale entry

        for d in DIRS:
            dr, dc = DIR_DELTA[d]
            nr, nc = pos[0] + dr, pos[1] + dc
            if not _in_bounds(nr, nc):
                continue
            nxt = (nr, nc)
            tile = grid[nr][nc]
            if nxt == goal:
                step_cost = 0.0
            else:
                step_cost = cost_fn(tile)
            if step_cost == INF:
                continue
            ng = g + step_cost
            if ng < g_score.get(nxt, INF):
                g_score[nxt] = ng
                came_from[nxt] = pos
                h = _manhattan(nxt, goal)
                heapq.heappush(heap, (ng + h, ng, nxt))

    return []


def find_nearest_steel(grid: list, start: tuple) -> Optional[tuple]:
    """
    BFS scan to find the nearest STEEL cell (safe cover for ArmorTank retreat).
    Returns (row, col) or None.
    """
    visited = {start}
    q = deque([start])
    while q:
        r, c = q.popleft()
        for d in DIRS:
            dr, dc = DIR_DELTA[d]
            nr, nc = r + dr, c + dc
            if not _in_bounds(nr, nc) or (nr, nc) in visited:
                continue
            visited.add((nr, nc))
            if grid[nr][nc] == STEEL:
                # Return cell adjacent to steel (can't stand on steel)
                return (r, c)
            if grid[nr][nc] not in (WATER,):
                q.append((nr, nc))
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Minimax + Alpha-Beta Pruning (BossTank)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MinimaxState:
    """
    Lightweight game snapshot for minimax tree search.
    Only includes data that changes during tree expansion.
    """
    boss_pos:   tuple
    boss_dir:   str
    boss_hp:    int
    player_pos: tuple
    player_dir: str
    player_hp:  int
    eagle_pos:  tuple
    # Bullets: list of dicts {pos, dir, owner ('boss'|'player')}
    bullets:    list = field(default_factory=list)
    # Destroyed bricks as frozenset so state is hashable
    destroyed:  frozenset = field(default_factory=frozenset)

    def clone(self):
        return MinimaxState(
            boss_pos=self.boss_pos,
            boss_dir=self.boss_dir,
            boss_hp=self.boss_hp,
            player_pos=self.player_pos,
            player_dir=self.player_dir,
            player_hp=self.player_hp,
            eagle_pos=self.eagle_pos,
            bullets=[dict(b) for b in self.bullets],
            destroyed=self.destroyed,
        )


class MinimaxLogger:
    """
    Records minimax benchmarking data per call and writes to CSV.

    Columns: tick, depth, nodes_ab, nodes_full, speedup, elapsed_ms
    """
    _HEADER = ['tick', 'depth', 'nodes_with_ab', 'nodes_without_ab',
               'speedup_ratio', 'elapsed_ms']

    def __init__(self, filepath: str = MINIMAX_LOG_FILE):
        self.filepath = filepath
        self.records = []
        self._ensure_header()

    def _ensure_header(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w', newline='') as f:
                csv.writer(f).writerow(self._HEADER)

    def record(self, tick: int, depth: int,
               nodes_ab: int, nodes_full: int, elapsed_ms: float):
        speedup = round(nodes_full / nodes_ab, 3) if nodes_ab > 0 else 0.0
        row = [tick, depth, nodes_ab, nodes_full, speedup, round(elapsed_ms, 2)]
        self.records.append(row)
        with open(self.filepath, 'a', newline='') as f:
            csv.writer(f).writerow(row)

    def last_speedup(self) -> float:
        if self.records:
            return self.records[-1][4]
        return 0.0

    def last_nodes_ab(self) -> int:
        if self.records:
            return self.records[-1][2]
        return 0


# ── State simulation helpers for minimax ─────────────────────────────────────

_BOSS_ACTIONS   = [MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, SHOOT]
_PLAYER_ACTIONS = [MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, SHOOT, IDLE]


def _apply_move(pos: tuple, action: str, grid: list,
                destroyed: frozenset) -> tuple:
    """Return new position after a move action; stays put if blocked."""
    if action not in ACTION_TO_DIR:
        return pos
    d = ACTION_TO_DIR[action]
    dr, dc = DIR_DELTA[d]
    nr, nc = pos[0] + dr, pos[1] + dc
    if not _in_bounds(nr, nc):
        return pos
    tile = grid[nr][nc]
    if tile in (STEEL, WATER, EAGLE):
        return pos
    if tile == BRICK and (nr, nc) not in destroyed:
        return pos   # blocked by intact brick
    return (nr, nc)


def _simulate_step(state: MinimaxState, grid: list,
                   boss_action: str, player_action: str) -> MinimaxState:
    """
    Advance state by one minimax half-ply (boss acts, then player acts,
    then bullets move one step). Simplified physics for tree search.
    """
    s = state.clone()
    destroyed = set(s.destroyed)

    # Boss move / shoot
    if boss_action == SHOOT:
        bullet = {'pos': s.boss_pos, 'dir': s.boss_dir, 'owner': 'boss'}
        s.bullets.append(bullet)
    elif boss_action in ACTION_TO_DIR:
        s.boss_dir = ACTION_TO_DIR[boss_action]
        s.boss_pos = _apply_move(s.boss_pos, boss_action, grid, s.destroyed)

    # Player move / shoot
    if player_action == SHOOT:
        bullet = {'pos': s.player_pos, 'dir': s.player_dir, 'owner': 'player'}
        s.bullets.append(bullet)
    elif player_action in ACTION_TO_DIR:
        s.player_dir = ACTION_TO_DIR[player_action]
        s.player_pos = _apply_move(s.player_pos, player_action, grid, s.destroyed)

    # Advance bullets one step
    surviving = []
    for b in s.bullets:
        dr, dc = DIR_DELTA[b['dir']]
        br, bc = b['pos']
        nr, nc = br + dr, bc + dc
        if not _in_bounds(nr, nc):
            continue
        t = grid[nr][nc]
        if t == BRICK and (nr, nc) not in destroyed:
            destroyed.add((nr, nc))   # destroy brick
            continue
        if t in (STEEL, WATER):
            continue
        # Check hits
        if b['owner'] == 'player' and (nr, nc) == s.boss_pos:
            s.boss_hp = max(0, s.boss_hp - 1)
            continue
        if b['owner'] == 'boss' and (nr, nc) == s.player_pos:
            s.player_hp = max(0, s.player_hp - 1)
            continue
        if (nr, nc) == s.eagle_pos:
            s.player_hp = 0   # Eagle destroyed = player loses
            continue
        b['pos'] = (nr, nc)
        surviving.append(b)

    # Bullet-bullet collision
    positions = {}
    final = []
    for b in surviving:
        p = b['pos']
        if p in positions:
            positions[p] = None   # mark collision
        else:
            positions[p] = b
    s.bullets = [b for b in positions.values() if b is not None]
    s.destroyed = frozenset(destroyed)
    return s


def _evaluate(state: MinimaxState, grid: list) -> float:
    """
    Heuristic evaluation from the BOSS (maximiser) perspective.
    Positive = good for boss.

    Uses the exact weights from the AL2002 project guide:
        Player within 3 tiles     → +60
        Player in line-of-sight   → +50
        Boss adjacent to steel    → +30
        Player HP missing (per HP)→ +20
        Boss HP missing (per HP)  → -40
        Player in forest tile     → -20
    """
    if state.boss_hp <= 0:
        return -10000.0
    if state.player_hp <= 0:
        return +10000.0

    score = 0.0

    br, bc = state.boss_pos
    pr, pc = state.player_pos
    er, ec = state.eagle_pos

    # Continuous progress incentives so the boss keeps closing distance
    # instead of hovering on locally equivalent edge states.
    player_dist = _manhattan(state.boss_pos, state.player_pos)
    eagle_dist = _manhattan(state.boss_pos, state.eagle_pos)
    score -= player_dist * 5.0
    score -= eagle_dist * 2.0

    # Player within 3 tiles: +60
    if player_dist <= 3:
        score += 60.0

    # Player in line-of-sight (same row or column): +50
    if br == pr or bc == pc:
        score += 50.0

    # Boss adjacent to steel wall: +30  (any of 4 neighbours)
    for d in DIRS:
        dr, dc = DIR_DELTA[d]
        nr, nc = br + dr, bc + dc
        if _in_bounds(nr, nc) and grid[nr][nc] == STEEL:
            score += 30.0
            break   # count once only

    # Player HP missing (per HP): +20 each
    PLAYER_MAX_HP = 3
    missing_player_hp = max(0, PLAYER_MAX_HP - state.player_hp)
    score += missing_player_hp * 20.0

    # Boss HP missing (per HP): -40 each
    BOSS_MAX_HP = 10
    missing_boss_hp = max(0, BOSS_MAX_HP - state.boss_hp)
    score += missing_boss_hp * (-40.0)

    # Player in forest tile: -20
    if _in_bounds(pr, pc) and grid[pr][pc] == FOREST:
        score -= 20.0

    return score


def _minimax_ab(state: MinimaxState, grid: list,
                depth: int, alpha: float, beta: float,
                maximising: bool, counter: list) -> tuple:
    """
    Minimax with alpha-beta pruning.
    counter[0] is incremented for each node visited.
    Returns (score, best_action).
    """
    counter[0] += 1

    if depth == 0 or state.boss_hp <= 0 or state.player_hp <= 0:
        return _evaluate(state, grid), IDLE

    if maximising:
        best_val = -float('inf')
        best_act = IDLE
        for act in _BOSS_ACTIONS:
            child = _simulate_step(state, grid, act, IDLE)
            val, _ = _minimax_ab(child, grid, depth-1, alpha, beta, False, counter)
            if val > best_val:
                best_val, best_act = val, act
            alpha = max(alpha, val)
            if beta <= alpha:
                break   # β cut-off
        return best_val, best_act
    else:
        best_val = float('inf')
        best_act = IDLE
        for act in _PLAYER_ACTIONS:
            child = _simulate_step(state, grid, IDLE, act)
            val, _ = _minimax_ab(child, grid, depth-1, alpha, beta, True, counter)
            if val < best_val:
                best_val, best_act = val, act
            beta = min(beta, val)
            if beta <= alpha:
                break   # α cut-off
        return best_val, best_act


def _minimax_noab(state: MinimaxState, grid: list,
                  depth: int, maximising: bool, counter: list) -> tuple:
    """
    Pure minimax WITHOUT alpha-beta pruning (benchmark only).
    Capped at depth ≤ 2 to prevent tick-level freeze during play.
    """
    counter[0] += 1

    if depth == 0 or state.boss_hp <= 0 or state.player_hp <= 0:
        return _evaluate(state, grid), IDLE

    if maximising:
        best_val, best_act = -float('inf'), IDLE
        for act in _BOSS_ACTIONS:
            child = _simulate_step(state, grid, act, IDLE)
            val, _ = _minimax_noab(child, grid, depth-1, False, counter)
            if val > best_val:
                best_val, best_act = val, act
        return best_val, best_act
    else:
        best_val, best_act = float('inf'), IDLE
        for act in _PLAYER_ACTIONS:
            child = _simulate_step(state, grid, IDLE, act)
            val, _ = _minimax_noab(child, grid, depth-1, True, counter)
            if val < best_val:
                best_val, best_act = val, act
        return best_val, best_act


def minimax(state: MinimaxState, grid: list,
            tick: int = 0,
            logger: Optional[MinimaxLogger] = None) -> str:
    """
    Public minimax entry point for BossTank.

    Selects search depth from Boss HP, runs alpha-beta search,
    optionally benchmarks against non-pruned version and logs results.

    Parameters
    ----------
    state  : Current MinimaxState snapshot.
    grid   : 2-D tile grid (used for move simulation).
    tick   : Current game tick (for log metadata).
    logger : MinimaxLogger instance; if None, no benchmarking is done.

    Returns
    -------
    Best action string for the Boss to take this tick.
    """
    depth = get_boss_depth(state.boss_hp)

    t0 = time.perf_counter()

    # Alpha-beta search
    ab_counter = [0]
    _, best_action = _minimax_ab(
        state, grid, depth, -float('inf'), float('inf'), True, ab_counter
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if logger is not None:
        # Non-pruning benchmark: cap at depth 2 to avoid frame drop
        bench_depth = min(depth, 2)
        noab_counter = [0]
        _minimax_noab(state, grid, bench_depth, True, noab_counter)

        # Scale estimated full-depth nodes if bench_depth < depth
        scale = (len(_BOSS_ACTIONS) ** depth) / max(1, len(_BOSS_ACTIONS) ** bench_depth)
        estimated_full = int(noab_counter[0] * scale)

        logger.record(tick, depth, ab_counter[0], estimated_full, elapsed_ms)

    return best_action