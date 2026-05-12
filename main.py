"""
main.py - Battle City AI
Entry point with CLI flags.
"""

import argparse
import sys

from constants import (
    TANK_BASIC, TANK_FAST, TANK_ARMOR, TANK_BOSS,
)
from map_generator import _fallback_map
from engine import GameEngine


# ── Level definitions (enemy queue) ──────────────────────────────────────────
# Per manual: Level 1 (Brick Maze), Level 2 (Steel Fortress), Boss Level
LEVELS = {
    1: [TANK_BASIC]*7 + [TANK_FAST]*5,
    2: [TANK_FAST]*4 + [TANK_ARMOR]*3,
    3: [TANK_BOSS],
}


def build_enemy_queue(level: int, benchmark: bool) -> list:
    queue = list(LEVELS.get(level, LEVELS[1]))
    if benchmark:
        # Move Boss to front so benchmarking starts immediately
        queue = [t for t in queue if t == TANK_BOSS] + \
                [t for t in queue if t != TANK_BOSS]
        if TANK_BOSS not in queue:
            queue.insert(0, TANK_BOSS)
    return queue


def main():
    parser = argparse.ArgumentParser(
        description="Battle City AI  –  AL2002 Spring 2026"
    )
    parser.add_argument(
        '--level', type=int, choices=range(1, 4), default=1, metavar='1-3',
        help="Difficulty level 1-3 (default: 1)"
    )
    parser.add_argument(
        '--benchmark', action='store_true',
        help="Enable Minimax CSV benchmarking (forces Boss at turn 1)"
    )
    parser.add_argument(
        '--seed', type=int, default=None,
        help="Reserved for compatibility; fixed map does not use a seed"
    )
    args = parser.parse_args()

    # ── Generate map ──────────────────────────────────────────────────────────
    print(f"[Battle City AI]  map=fixed  level={args.level}"
          f"  benchmark={args.benchmark}")
    grid = _fallback_map()
    print("  Using hand-crafted fixed map.")

    # ── Build enemy queue ─────────────────────────────────────────────────────
    enemy_queue = build_enemy_queue(args.level, args.benchmark)
    print(f"  Enemy queue ({len(enemy_queue)}): "
          + ', '.join(enemy_queue))

    if args.benchmark:
        print(f"  Benchmark mode ON — minimax log → minimax_log.csv")

    # ── Launch engine ─────────────────────────────────────────────────────────
    engine = GameEngine(grid, enemy_queue, benchmark=args.benchmark)
    result = engine.run()
    print(f"\n[Result] {result.upper()}  |  Score: {engine.score}")

    if args.benchmark:
        print(f"  Minimax log saved to: minimax_log.csv")

    sys.exit(0)


if __name__ == '__main__':
    main()
