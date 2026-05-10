"""map_generator.py - CSP-based procedural map generation"""

import random
import copy
from collections import deque
from constants import (
    GRID_ROWS, GRID_COLS, EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE,
    EAGLE_POS, PLAYER_SPAWN, ENEMY_SPAWNS,
    EAGLE_RING_OFFSETS, MAX_WALL_DENSITY, MIN_SPAWN_DIST,
)

# Tiles that cannot be walked through (walls for BFS)
_IMPASSABLE = {STEEL, WATER}
_WALL_TILES  = {BRICK, STEEL, WATER}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _in_bounds(r: int, c: int) -> bool:
    return 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS


def _manhattan(a: tuple, b: tuple) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _bfs_reachable(grid: list, start: tuple, goal: tuple) -> bool:
    """Return True if a path exists from start to goal through EMPTY/FOREST/BRICK cells."""
    passable = lambda t: t not in (STEEL, WATER)
    visited = set()
    q = deque([start])
    visited.add(start)
    while q:
        r, c = q.popleft()
        if (r, c) == goal:
            return True
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if _in_bounds(nr, nc) and (nr, nc) not in visited:
                if passable(grid[nr][nc]) or (nr, nc) == goal:
                    visited.add((nr, nc))
                    q.append((nr, nc))
    return False


def _count_walls(grid: list) -> int:
    return sum(1 for r in range(GRID_ROWS) for c in range(GRID_COLS)
               if grid[r][c] in _WALL_TILES)


# ── Fixed-cell builders ───────────────────────────────────────────────────────

def _init_grid() -> list:
    """Create a blank grid with fixed structural cells placed."""
    grid = [[EMPTY] * GRID_COLS for _ in range(GRID_ROWS)]

    # Eagle
    er, ec = EAGLE_POS
    grid[er][ec] = EAGLE

    # Eagle protection ring — C1
    for dr, dc in EAGLE_RING_OFFSETS:
        nr, nc = er + dr, ec + dc
        if _in_bounds(nr, nc):
            grid[nr][nc] = BRICK  # initially all brick; CSP may reinforce to STEEL

    # Player spawn — must stay EMPTY
    grid[PLAYER_SPAWN[0]][PLAYER_SPAWN[1]] = EMPTY

    # Enemy spawns — C3: already MIN_SPAWN_DIST away by definition of spawn coords
    for sr, sc in ENEMY_SPAWNS:
        if _in_bounds(sr, sc):
            grid[sr][sc] = EMPTY

    return grid


def _fixed_cells(grid: list) -> set:
    """Return set of (r,c) that must not be reassigned."""
    fixed = set()
    er, ec = EAGLE_POS
    fixed.add((er, ec))
    for dr, dc in EAGLE_RING_OFFSETS:
        nr, nc = er + dr, ec + dc
        if _in_bounds(nr, nc):
            fixed.add((nr, nc))
    fixed.add(PLAYER_SPAWN)
    for sp in ENEMY_SPAWNS:
        fixed.add(sp)
    return fixed


# ── CSP: backtracking + forward checking ─────────────────────────────────────

class _CSPSolver:
    """
    Variable  : each free (r,c) cell on the grid.
    Domain    : {EMPTY, BRICK, STEEL, WATER, FOREST}
    Constraints checked via forward checking at each assignment:
        - C4: wall density budget not exceeded.
        - C3: cells within MIN_SPAWN_DIST of player spawn cannot be walls.
    After full assignment C1+C2 are verified; repair applied if needed.
    """

    # Probability weights for tile selection (makes maps interesting)
    _TILE_WEIGHTS = [
        (EMPTY,  45),
        (BRICK,  30),
        (STEEL,   8),
        (WATER,   7),
        (FOREST, 10),
    ]

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.max_walls = int(MAX_WALL_DENSITY * GRID_ROWS * GRID_COLS)

    # ── forward-checking predicates ───────────────────────────────────────────

    def _fc_density(self, tile: int, wall_count: int) -> bool:
        """C4: assigning a wall tile must not exceed budget."""
        if tile in _WALL_TILES:
            return wall_count < self.max_walls
        return True

    def _fc_spawn_safe(self, r: int, c: int, tile: int) -> bool:
        """C3: cells near player/enemy spawns must stay EMPTY/FOREST."""
        if tile in _WALL_TILES:
            # Protect player spawn
            if _manhattan((r, c), PLAYER_SPAWN) < MIN_SPAWN_DIST:
                return False
            # Protect enemy spawns
            for enemy_sp in ENEMY_SPAWNS:
                if _manhattan((r, c), enemy_sp) < MIN_SPAWN_DIST:
                    return False
        return True

    # ── weighted random domain ordering ───────────────────────────────────────

    def _sample_domain(self) -> list:
        tiles, weights = zip(*self._TILE_WEIGHTS)
        return self.rng.choices(tiles, weights=weights, k=len(tiles))

    # ── recursive backtracking ────────────────────────────────────────────────

    def solve(self, grid: list, cells: list) -> bool:
        """
        Assign tiles to free cells with forward checking.
        Returns True on success; grid is modified in-place.
        """
        wall_count = _count_walls(grid)
        return self._bt(grid, cells, 0, wall_count)

    def _bt(self, grid: list, cells: list, idx: int, wall_count: int) -> bool:
        if idx == len(cells):
            return True

        r, c = cells[idx]

        # Build feasible domain for this cell
        seen = set()
        domain = []
        for tile in self._sample_domain():
            if tile in seen:
                continue
            seen.add(tile)
            if (self._fc_density(tile, wall_count) and
                    self._fc_spawn_safe(r, c, tile)):
                domain.append(tile)

        for tile in domain:
            is_wall = tile in _WALL_TILES
            grid[r][c] = tile
            new_wc = wall_count + (1 if is_wall else 0)

            if self._bt(grid, cells, idx + 1, new_wc):
                return True

            # Backtrack
            grid[r][c] = EMPTY

        return False   # triggers backtrack in parent frame


# ── Reachability repair ───────────────────────────────────────────────────────

def _repair_reachability(grid: list, rng: random.Random) -> None:
    """
    C2: Ensure BFS path from every spawn to Eagle.
    Strategy: for each failing spawn, run BFS to find the nearest blocking
    wall cluster and clear one cell at a time until path is open.
    """
    eagle = EAGLE_POS
    all_spawns = [PLAYER_SPAWN] + ENEMY_SPAWNS

    for spawn in all_spawns:
        for _ in range(200):          # safety iteration limit
            if _bfs_reachable(grid, spawn, eagle):
                break
            # BFS to find the first blocking (steel/water) cell to remove
            visited = {spawn}
            q = deque([(spawn, [])])
            cleared = False
            while q and not cleared:
                pos, path = q.popleft()
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = pos[0]+dr, pos[1]+dc
                    if not _in_bounds(nr, nc) or (nr,nc) in visited:
                        continue
                    if (nr, nc) == eagle:
                        cleared = True
                        break
                    t = grid[nr][nc]
                    if t in (STEEL, WATER):
                        # Clear this blocking cell
                        grid[nr][nc] = EMPTY
                        cleared = True
                        break
                    visited.add((nr, nc))
                    q.append(((nr, nc), path + [(nr, nc)]))
            if not cleared:
                break   # path already open or unreachable due to map edge


# ── Public API ────────────────────────────────────────────────────────────────

def generate_map(seed: int = None) -> list:
    """
    Generate and return a valid 26×26 Battle City map (list of lists of ints).

    Parameters
    ----------
    seed : int or None
        Random seed for reproducible generation.

    Returns
    -------
    grid : list[list[int]]
        26×26 grid; each cell is one of EMPTY(0)..EAGLE(5).
    """
    rng = random.Random(seed)

    for attempt in range(50):
        grid = _init_grid()
        fixed = _fixed_cells(grid)

        # Collect assignable cells; shuffle for randomness
        free_cells = [
            (r, c)
            for r in range(GRID_ROWS)
            for c in range(GRID_COLS)
            if (r, c) not in fixed
        ]
        rng.shuffle(free_cells)

        solver = _CSPSolver(rng)
        success = solver.solve(grid, free_cells)

        if not success:
            continue   # rare; retry with new shuffle

        # Enforce C2: BFS reachability repair
        _repair_reachability(grid, rng)

        # Validate all constraints
        if _validate(grid):
            return grid

    # Fallback: guaranteed safe hand-crafted map
    return _fallback_map()


def _validate(grid: list) -> bool:
    """Check all four CSP constraints on a completed grid."""
    # C1 — Eagle ring
    er, ec = EAGLE_POS
    for dr, dc in EAGLE_RING_OFFSETS:
        nr, nc = er + dr, ec + dc
        if _in_bounds(nr, nc) and grid[nr][nc] not in (BRICK, STEEL):
            return False

    # C2 — Reachability
    for spawn in [PLAYER_SPAWN] + ENEMY_SPAWNS:
        if not _bfs_reachable(grid, spawn, EAGLE_POS):
            return False

    # C3 — Spawn safety (enemy spawns already hard-coded far from player)
    for sp in ENEMY_SPAWNS:
        if _manhattan(sp, PLAYER_SPAWN) < MIN_SPAWN_DIST:
            return False

    # C4 — Wall density
    if _count_walls(grid) > MAX_WALL_DENSITY * GRID_ROWS * GRID_COLS:
        return False

    return True


def _fallback_map() -> list:
    """
    Hand-crafted minimal valid map used if CSP fails after 50 attempts.
    Guaranteed to satisfy all four constraints.
    """
    grid = _init_grid()

    # Scatter some brick walls in the middle area (avoid spawn zones)
    brick_positions = [
        (12, 5), (12, 6), (13, 5),      # left middle
        (12, 20), (12, 21), (13, 20),   # right middle
        (15, 8), (15, 9), (15, 10),     # lower left
        (15, 15), (15, 16), (15, 17),   # lower center
        (20, 5), (20, 6), (20, 7),      # bottom left
        (20, 18), (20, 19), (20, 20),   # bottom right
    ]
    for r, c in brick_positions:
        if _in_bounds(r, c) and (r, c) not in _fixed_cells(grid):
            grid[r][c] = BRICK

    steel_positions = [
        (10, 3), (10, 22),
        (18, 3), (18, 22),
    ]
    for r, c in steel_positions:
        if _in_bounds(r, c) and (r, c) not in _fixed_cells(grid):
            grid[r][c] = STEEL

    water_positions = [
        (14, 12), (14, 13), (14, 14),
    ]
    for r, c in water_positions:
        if _in_bounds(r, c) and (r, c) not in _fixed_cells(grid):
            grid[r][c] = WATER

    forest_positions = [
        (8, 8), (8, 9), (9, 8),         # center area
        (8, 16), (8, 17), (9, 17),      # center right
    ]
    for r, c in forest_positions:
        if _in_bounds(r, c) and (r, c) not in _fixed_cells(grid):
            grid[r][c] = FOREST

    return grid


def print_map(grid: list) -> None:
    """Debug helper — ASCII render of the grid."""
    symbols = {EMPTY: '.', BRICK: 'B', STEEL: 'S',
               WATER: 'W', FOREST: 'F', EAGLE: 'E'}
    for row in grid:
        print(''.join(symbols.get(t, '?') for t in row))
