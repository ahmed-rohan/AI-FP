"# Battle City AI

A strategic tank combat game engine featuring four distinct AI opponents powered by different pathfinding and decision-making algorithms: **BFS**, **Greedy Best-First Search**, **A\* Search**, and **Minimax with Alpha-Beta Pruning**.

---

## 🎮 Project Overview

**Battle City AI** is a 26×26 grid-based tank combat game inspired by the classic NES game *Tank Wars*. The player controls a tank and must survive enemy waves while protecting an Eagle base. Each enemy tank type uses a different algorithm for pathfinding and tactical decision-making, creating distinct playstyles and difficulty progression.

### Features

- **4 Distinct AI Tank Types**
  - **BasicTank**: BFS pathfinding (reliable, predictable)
  - **FastTank**: Greedy Best-First Search (aggressive, reckless)
  - **ArmorTank**: A* Search with terrain costs (tactical, efficient)
  - **BossTank**: Minimax with Alpha-Beta Pruning (strategic, formidable)

- **3 Difficulty Levels**: Progressive enemy encounters from basic to boss tank
- **CSP-based Map Generation**: Dynamically generated playable maps with constraints
- **Real-time Combat System**: Bullets, terrain interactions, and line-of-sight mechanics
- **Benchmark Mode**: Evaluate Minimax performance with detailed CSV logging

---

## 🚀 Quick Start

### Requirements

- Python 3.8+
- `pygame` (for graphics)
- `numpy` (for grid operations)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/BattleCity.git
cd BattleCity

# Install dependencies
pip install pygame numpy
```

### Running the Game

```bash
# Start at Level 1 with the fixed map
python main.py

# Advanced options
python main.py --level 3 --benchmark  # Boss level with Minimax logging
```

#### Command-line Flags

| Flag | Options | Description |
|------|---------|-------------|
| `--level` | 1, 2, 3 | Difficulty level (default: 1) |
| `--benchmark` | - | Enable Minimax benchmarking and CSV logging |

---

## 🧠 Algorithm Overview

### BasicTank — BFS (Breadth-First Search)
- Finds shortest path in terms of hops
- Time: O(rows × cols)
- Best for: Reliable navigation without cost optimization
- Playstyle: Steady and predictable

### FastTank — Greedy Best-First Search
- Always moves toward goal using Manhattan distance heuristic
- Ignores terrain costs—charges directly forward
- Time: O(rows × cols × log n)
- Best for: Speed over optimality
- Playstyle: Aggressive and reckless

### ArmorTank — A\* Search
- Optimizes movement considering terrain costs
- Brick walls cost 3 (requires shooting), steel/water are barriers
- Combines g-cost and heuristic: f(n) = g(n) + h(n)
- Time: O(rows × cols × log n)
- Best for: Tactical, cost-aware pathfinding
- Playstyle: Methodical and calculated

### BossTank — Minimax with Alpha-Beta Pruning
- Searches game tree to depth 6 (adaptive)
- Maximizes BossTank advantage while minimizing player advantage
- Alpha-beta pruning reduces node exploration by ~3x
- Evaluation function considers distance, health, cover, and threats
- Time: ~200ms per decision
- Best for: Strategic, forward-thinking gameplay
- Playstyle: Formidable and unpredictable

---

## 📁 Project Structure

```
BattleCity/
├── main.py              # Entry point with CLI argument parsing
├── engine.py            # GameEngine class (core game loop)
├── agents.py            # AI tank implementations (BasicTank, FastTank, ArmorTank, BossTank)
├── search.py            # Pathfinding algorithms (BFS, Greedy, A*, Minimax)
├── map_generator.py     # CSP-based map generation
├── constants.py         # Game constants (grid size, tile types, tank stats)
├── PROJECT_REPORT.md    # Detailed technical report
└── README.md            # This file
```

---

## 🎯 Game Mechanics

### Grid System
- **Size**: 26×26 cells
- **Terrain Types**: Empty, Brick (destructible), Steel (indestructible), Water, Forest, Eagle Base
- **Movement**: Tanks move one cell per tick; bullets travel instantly in straight lines

### Tank Types

| Type | Speed | Health | Algorithm | Difficulty |
|------|-------|--------|-----------|------------|
| BasicTank | Normal | 1 | BFS | Easy |
| FastTank | Fast | 1 | Greedy | Medium |
| ArmorTank | Normal | 2 | A* | Hard |
| BossTank | Slow | 3 | Minimax | Extreme |

### Combat
- Each tank can move or shoot per turn
- Bullets destroy brick walls on contact
- Steel walls and water are impassable
- Player wins by surviving all enemy waves and protecting the Eagle

---

## 📊 Algorithm Comparison

| Metric | BFS | Greedy | A* | Minimax |
|--------|-----|--------|-----|---------|
| Path Optimality | Hop-optimal | Suboptimal | Cost-optimal | Game-theoretic |
| Speed | Fast | Fast | Fast | ~200ms/decision |
| Considers Costs | ✗ | ✗ | ✓ | ✓ |
| Typical Nodes | 150–300 | 80–200 | 100–250 | 30–90k |
| Playstyle | Reliable | Aggressive | Tactical | Strategic |

---

## 🔧 Customization

### Adjusting Terrain Costs (in `search.py`)

```python
TERRAIN_COSTS = {
    'empty': 1,
    'forest': 1,
    'brick': 3,      # Change to increase/decrease brick wall preference
    'steel': float('inf'),
    'water': float('inf'),
}
```

### Tuning Minimax Depth (in `agents.py`)

```python
# BossTank adaptive depth
if player_distance < 3:
    search_depth = 6  # Increase to 7–8 for deeper analysis
else:
    search_depth = 5
```

### Level Definitions (in `main.py`)

```python
LEVELS = {
    1: [TANK_BASIC]*7 + [TANK_FAST]*5,
    2: [TANK_FAST]*4 + [TANK_ARMOR]*3,
    3: [TANK_BOSS],
}
```

---

## 📈 Performance & Benchmarking

Run with `--benchmark` flag to generate `minimax_log.csv`:

```bash
python main.py --level 3 --benchmark
```

Logs include:
- Nodes explored with/without alpha-beta pruning
- Search depth used
- Decision quality metrics
- Execution time per decision

---

## 📚 Detailed Documentation

For an in-depth technical analysis including:
- Algorithm implementation details
- Design trade-offs and decisions
- Comparative algorithm analysis
- Map generation constraints
- Evaluation and results

See [PROJECT_REPORT.md](PROJECT_REPORT.md).

---

## 🏆 Learning Outcomes

This project demonstrates:
- **Pathfinding Algorithms**: BFS, Greedy Search, A\* practical implementation
- **Game AI**: Minimax decision-making with alpha-beta pruning
- **Game Development**: Real-time rendering, collision detection, game state management
- **Optimization**: Terrain costs, heuristic design, adaptive search depth
- **Constraint Satisfaction**: Map generation under constraints

---

## 📝 License

This project is part of coursework for **AL2002: AI Search & Game Playing** (Spring 2026).

---

## 🤝 Contributing

For bug reports or suggestions, please open an issue or submit a pull request.

---

**Last Updated**: May 2026" 
