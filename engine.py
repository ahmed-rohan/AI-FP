"""engine.py - Battle City AI Game Engine"""

import pygame, sys, random
from constants import *
from agents import BasicTank, FastTank, ArmorTank, BossTank

# ── Layout ────────────────────────────────────────────────────────────────────
BORDER   = 16
GAME_X   = BORDER
GAME_Y   = BORDER
PANEL_W  = 180
WIN_W    = GAME_X + GRID_COLS * CELL_SIZE + BORDER + PANEL_W
WIN_H    = GAME_Y + GRID_ROWS * CELL_SIZE + BORDER

# ── NES Palette ───────────────────────────────────────────────────────────────
NES_BLACK  = (  0,   0,   0)
NES_GRAY   = (104, 104, 104)
NES_LGRAY  = (188, 188, 188)
NES_BRICK  = (200,  68,   0)
NES_MORTAR = (104,   0,   0)
NES_STEELW = (252, 252, 252)
NES_STEELG = ( 80,  80,  80)
NES_GREEN  = (  0, 120,   0)
NES_LGREEN = (  0, 200,   0)
NES_WATER1 = ( 24,  24, 200)
NES_WATER2 = ( 60,  60, 252)
NES_EAGLE  = (200, 120,   0)
NES_WHITE  = (252, 252, 252)
NES_YELLOW = (252, 200,   0)
NES_ORANGE = (252, 120,   0)
NES_RED    = (220,   0,   0)

TANK_COLORS = {
    TANK_PLAYER: (200, 200,   0),
    TANK_BASIC:  (188, 188, 188),
    TANK_FAST:   (248, 248,   0),
    TANK_ARMOR:  (  0, 200, 200),
    TANK_BOSS:   (220,   0,   0),
}

# ── Tile cache ────────────────────────────────────────────────────────────────
_TILE_CACHE = {}

def _make_brick():
    s = CELL_SIZE; surf = pygame.Surface((s, s))
    surf.fill(NES_BLACK)
    # Top brick row (y 0..10)
    pygame.draw.rect(surf, NES_BRICK, (0,  0, 11, 11))
    pygame.draw.rect(surf, NES_BRICK, (13, 0, s-13, 11))
    # Bottom brick row offset (y 12..s)
    pygame.draw.rect(surf, NES_BRICK, (0,  13, 5, s-13))
    pygame.draw.rect(surf, NES_BRICK, (7,  13, 10, s-13))
    pygame.draw.rect(surf, NES_BRICK, (19, 13, s-19, s-13))
    return surf

def _make_steel():
    s = CELL_SIZE; surf = pygame.Surface((s, s))
    surf.fill(NES_STEELG)
    h = s // 2
    for rx, ry in [(1,1),(h+1,1),(1,h+1),(h+1,h+1)]:
        pygame.draw.rect(surf, NES_STEELW, (rx, ry, h-2, h-2))
        pygame.draw.rect(surf, NES_STEELG, (rx, ry, h-2, h-2), 1)
        # highlight
        pygame.draw.line(surf, (220,220,220), (rx,ry), (rx+h-3, ry))
        pygame.draw.line(surf, (220,220,220), (rx,ry), (rx, ry+h-3))
    return surf

def _make_water(phase=0):
    s = CELL_SIZE; surf = pygame.Surface((s, s))
    surf.fill(NES_WATER1)
    for y in range(0, s, 4):
        ox = (phase * 3 + y) % 8
        pygame.draw.line(surf, NES_WATER2, (ox, y), (s, y))
        if ox > 0:
            pygame.draw.line(surf, NES_WATER2, (0, y), (ox-2, y))
    return surf

def _make_forest():
    s = CELL_SIZE; surf = pygame.Surface((s, s))
    surf.fill(NES_GREEN)
    for (x,y) in [(4,2),(12,2),(8,6),(2,10),(14,10),(6,14),(12,14)]:
        if x+4 <= s and y+4 <= s:
            pygame.draw.rect(surf, NES_LGREEN, (x, y, 4, 4))
    return surf

def _make_eagle(alive=True):
    s = CELL_SIZE; surf = pygame.Surface((s, s))
    surf.fill(NES_BLACK)
    col = NES_EAGLE if alive else NES_GRAY
    cx, cy = s//2, s//2
    # Phoenix body
    pygame.draw.rect(surf, col, (cx-3, cy-4, 6, 8))
    # Wings
    for sx in [-1, 1]:
        pts = [(cx, cy-2),
               (cx + sx*10, cy-6),
               (cx + sx*10, cy+2),
               (cx + sx*3, cy+4)]
        pygame.draw.polygon(surf, col, pts)
    # Head
    pygame.draw.circle(surf, col, (cx, cy-5), 3)
    return surf

def _get_tile(tile, water_phase=0):
    key = (tile, water_phase if tile == WATER else 0)
    if key not in _TILE_CACHE:
        if tile == BRICK:  _TILE_CACHE[key] = _make_brick()
        elif tile == STEEL: _TILE_CACHE[key] = _make_steel()
        elif tile == WATER: _TILE_CACHE[key] = _make_water(water_phase)
        elif tile == FOREST: _TILE_CACHE[key] = _make_forest()
        elif tile == EAGLE: _TILE_CACHE[key] = _make_eagle(True)
        else:
            s = CELL_SIZE; surf = pygame.Surface((s,s)); surf.fill(NES_BLACK)
            _TILE_CACHE[key] = surf
    return _TILE_CACHE[key]

# ── Tank sprite ───────────────────────────────────────────────────────────────
def _draw_tank(surf, r, c, direction, color, hp_max, hp_cur, ox, oy):
    x = ox + c * CELL_SIZE
    y = oy + r * CELL_SIZE
    s = CELL_SIZE
    col  = color
    dark = tuple(max(0, v - 60) for v in col)

    # Tracks (sides)
    pygame.draw.rect(surf, dark,    (x+1,   y+3, 4, s-6))
    pygame.draw.rect(surf, dark,    (x+s-5, y+3, 4, s-6))
    for i in range(4, s-4, 5):
        pygame.draw.line(surf, NES_BLACK, (x+1, y+i), (x+4,   y+i), 1)
        pygame.draw.line(surf, NES_BLACK, (x+s-5,y+i),(x+s-2, y+i), 1)

    # Body
    pygame.draw.rect(surf, col, (x+5, y+4, s-10, s-8))

    # Turret
    pygame.draw.rect(surf, col,     (x+s//2-3, y+s//2-3, 7, 7))
    pygame.draw.rect(surf, NES_BLACK,(x+s//2-3,y+s//2-3, 7, 7), 1)

    # Barrel
    bw, bl = 4, 8
    if   direction == UP:    pygame.draw.rect(surf, col, (x+s//2-2, y,       bw, bl))
    elif direction == DOWN:  pygame.draw.rect(surf, col, (x+s//2-2, y+s-bl,  bw, bl))
    elif direction == LEFT:  pygame.draw.rect(surf, col, (x,         y+s//2-2, bl, bw))
    else:                    pygame.draw.rect(surf, col, (x+s-bl,   y+s//2-2, bl, bw))

    # HP dots
    for i in range(hp_cur):
        pygame.draw.circle(surf, NES_WHITE, (x+4+i*4, y+1), 2)

def _draw_mini_tank(surf, x, y, col):
    """12×14 enemy icon for HUD."""
    pygame.draw.rect(surf, col, (x+2, y+2,  8, 10))
    pygame.draw.rect(surf, col, (x,   y+4,  2,  6))
    pygame.draw.rect(surf, col, (x+10,y+4,  2,  6))
    pygame.draw.rect(surf, col, (x+4, y,    4,  4))

def _draw_bullet(surf, r, c, owner, ox, oy):
    x = ox + c * CELL_SIZE + CELL_SIZE//2
    y = oy + r * CELL_SIZE + CELL_SIZE//2
    col = NES_WHITE if owner == 'player' else NES_ORANGE
    pygame.draw.circle(surf, col,      (x, y), 4)
    pygame.draw.circle(surf, NES_YELLOW,(x, y), 2)

# ── Game objects ──────────────────────────────────────────────────────────────
class Bullet:
    __slots__ = ('pos','direction','owner','move_timer')
    def __init__(self, pos, direction, owner):
        self.pos = list(pos); self.direction = direction
        self.owner = owner;   self.move_timer = 0

class TankEntity:
    def __init__(self, agent, color):
        self.agent      = agent
        self.color      = color
        self.pos        = list(agent.pos)
        self.direction  = agent.direction
        self.hp         = agent.hp
        self.max_hp     = agent.hp
        self.alive      = True
        self.move_timer = 0
        self.shoot_cd   = 0
        self.score_val  = {TANK_BASIC:SCORE_BASIC,TANK_FAST:SCORE_FAST,
                           TANK_ARMOR:SCORE_ARMOR,TANK_BOSS:SCORE_BOSS}.get(agent.tank_type,100)

# ── GameEngine ────────────────────────────────────────────────────────────────
class GameEngine:
    def __init__(self, grid, enemy_queue, benchmark=False):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Battle City AI  —  AL2002")
        self.clock  = pygame.time.Clock()
        self._font  = pygame.font.SysFont('consolas', 14, bold=True)
        self._fsm   = pygame.font.SysFont('consolas', 12)

        self.grid       = grid
        self.destroyed  = set()
        self.tick       = 0
        self.score      = 0
        self.game_over  = False
        self.won        = False
        self.benchmark  = benchmark
        self._water_ph  = 0

        # Player entity via duck-typed object
        class _P:
            pos=PLAYER_SPAWN; direction=UP; hp=3; tank_type=TANK_PLAYER
        self.player        = TankEntity(_P(), TANK_COLORS[TANK_PLAYER])
        self.player.max_hp = 3
        self.player_lives  = 3

        self._enemy_queue   = list(enemy_queue)
        self._enemies       = []
        self._bullets       = []
        self._total_enemies = len(self._enemy_queue)
        self._try_spawn_enemies()

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            self.tick += 1
            act = self._step1_input()
            if act is None: pygame.quit(); sys.exit()
            agent_acts = self._step2_agent_decisions()
            self._step3_move(act, agent_acts)
            self._step4_shoot(act, agent_acts)
            self._step5_bullet_update()
            self._step6_collision()
            self._step7_state_update()
            self._step8_spawn_check()
            self._step9_render()
            res = self._step10_win_lose()
            if res: return res
            self.clock.tick(FPS)

    # ── Step 1: Input ─────────────────────────────────────────────────────────
    def _step1_input(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return None
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return None
        if self.game_over: return IDLE
        k = pygame.key.get_pressed()
        if k[pygame.K_w] or k[pygame.K_UP]:    return MOVE_UP
        if k[pygame.K_s] or k[pygame.K_DOWN]:  return MOVE_DOWN
        if k[pygame.K_a] or k[pygame.K_LEFT]:  return MOVE_LEFT
        if k[pygame.K_d] or k[pygame.K_RIGHT]: return MOVE_RIGHT
        if k[pygame.K_SPACE]:                  return SHOOT
        return IDLE

    # ── Step 2: Agent Decisions ───────────────────────────────────────────────
    def _step2_agent_decisions(self):
        acts = {}
        for ent in self._enemies:
            if not ent.alive: continue
            acts[id(ent)] = ent.agent.decide(self._build_percepts(ent))
        return acts

    def _build_percepts(self, ent):
        return {'pos': tuple(ent.pos), 'direction': ent.direction,
                'hp': ent.hp, 'grid': self.grid,
                'player_pos': tuple(self.player.pos),
                'player_dir': self.player.direction,
                'player_hp': self.player.hp, 'eagle_pos': EAGLE_POS,
                'bullets': [{'pos':tuple(b.pos),'dir':b.direction,'owner':b.owner}
                             for b in self._bullets],
                'enemies': self._enemies, 'tick': self.tick,
                'destroyed_bricks': self.destroyed,
                'logger': getattr(ent.agent,'logger',None)}

    # ── Step 3: Move ──────────────────────────────────────────────────────────
    def _step3_move(self, player_action, agent_actions):
        self.player.move_timer += 1
        if self.player.move_timer >= PLAYER_MOVE_DELAY:
            self.player.move_timer = 0
            if player_action in ACTION_TO_DIR:
                d = ACTION_TO_DIR[player_action]
                self.player.direction = d
                self._try_move(self.player, d)

        delays = {TANK_BASIC:BASIC_MOVE_DELAY, TANK_FAST:FAST_MOVE_DELAY,
                  TANK_ARMOR:ARMOR_MOVE_DELAY, TANK_BOSS:BOSS_MOVE_DELAY}
        for ent in self._enemies:
            if not ent.alive: continue
            ent.move_timer += 1
            if ent.move_timer >= delays.get(ent.agent.tank_type, BASIC_MOVE_DELAY):
                ent.move_timer = 0
                act = agent_actions.get(id(ent), IDLE)
                if act in ACTION_TO_DIR:
                    d = ACTION_TO_DIR[act]
                    ent.direction = d
                    moved = self._try_move(ent, d)
                    ent.agent.update('moved' if moved else 'blocked')

    def _try_move(self, ent, direction):
        dr, dc = DIR_DELTA[direction]
        nr, nc = ent.pos[0]+dr, ent.pos[1]+dc
        if not (0<=nr<GRID_ROWS and 0<=nc<GRID_COLS): return False
        t = self.grid[nr][nc]
        if t in (STEEL, WATER, EAGLE): return False
        if t == BRICK and (nr,nc) not in self.destroyed: return False
        occ = {tuple(self.player.pos)} | {tuple(e.pos) for e in self._enemies if e.alive}
        if (nr,nc) in occ: return False
        ent.pos = [nr, nc]
        ent.agent.pos = (nr, nc)
        return True

    # ── Step 4: Shoot ─────────────────────────────────────────────────────────
    def _step4_shoot(self, player_action, agent_actions):
        if player_action == SHOOT and self.player.shoot_cd <= 0:
            self._bullets.append(Bullet(list(self.player.pos), self.player.direction, 'player'))
            self.player.shoot_cd = PLAYER_SHOOT_CD
        if self.player.shoot_cd > 0: self.player.shoot_cd -= 1

        for ent in self._enemies:
            if not ent.alive: continue
            act = agent_actions.get(id(ent), IDLE)
            if act == SHOOT and ent.shoot_cd <= 0:
                self._bullets.append(Bullet(list(ent.pos), ent.direction, ent.agent.tank_type))
                ent.shoot_cd = ENEMY_SHOOT_CD
            if ent.shoot_cd > 0: ent.shoot_cd -= 1

    # ── Step 5: Bullet Update ─────────────────────────────────────────────────
    def _step5_bullet_update(self):
        for b in self._bullets:
            b.move_timer += 1
            if b.move_timer >= BULLET_MOVE_DELAY:
                b.move_timer = 0
                dr, dc = DIR_DELTA[b.direction]
                b.pos[0] += dr; b.pos[1] += dc

    # ── Step 6: Collision ─────────────────────────────────────────────────────
    def _step6_collision(self):
        rm = set()
        for i, b in enumerate(self._bullets):
            r, c = b.pos
            if not (0<=r<GRID_ROWS and 0<=c<GRID_COLS): rm.add(i); continue
            t = self.grid[r][c]
            if t == BRICK and (r,c) not in self.destroyed:
                self.destroyed.add((r,c)); rm.add(i); continue
            if t in (STEEL, WATER): rm.add(i); continue
            if t == EAGLE or (r,c) == EAGLE_POS:
                self.game_over = True; self.won = False; rm.add(i); continue
            if b.owner != 'player' and [r,c] == self.player.pos:
                self.player.hp -= 1; rm.add(i)
                if self.player.hp <= 0:
                    self.player_lives -= 1
                    if self.player_lives <= 0: self.game_over = True; self.won = False
                    else: self.player.pos = list(PLAYER_SPAWN); self.player.hp = 3
                continue
            if b.owner == 'player':
                for ent in self._enemies:
                    if ent.alive and [r,c] == ent.pos:
                        ent.hp -= 1; ent.agent.update('hit'); rm.add(i)
                        if ent.hp <= 0: ent.alive = False; self.score += ent.score_val
                        break
        # bullet-bullet
        pos_map = {}
        for i, b in enumerate(self._bullets):
            if i in rm: continue
            key = (b.pos[0], b.pos[1])
            if key in pos_map: rm.add(i); rm.add(pos_map[key])
            else: pos_map[key] = i
        self._bullets = [b for i,b in enumerate(self._bullets) if i not in rm]

    # ── Step 7: State Update ──────────────────────────────────────────────────
    def _step7_state_update(self):
        self._enemies = [e for e in self._enemies if e.alive]
        for r,c in self.destroyed:
            if self.grid[r][c] == BRICK: self.grid[r][c] = EMPTY

    # ── Step 8: Spawn ─────────────────────────────────────────────────────────
    def _step8_spawn_check(self):
        if len(self._enemies) < MAX_ENEMIES_ALIVE and self._enemy_queue:
            self._try_spawn_enemies()

    def _try_spawn_enemies(self):
        spts = ENEMY_SPAWNS[:]
        random.shuffle(spts)
        occ = {tuple(self.player.pos)} | {tuple(e.pos) for e in self._enemies}
        cls_map = {TANK_BASIC:BasicTank,TANK_FAST:FastTank,
                   TANK_ARMOR:ArmorTank,TANK_BOSS:BossTank}
        while len(self._enemies) < MAX_ENEMIES_ALIVE and self._enemy_queue:
            if not spts: break
            sp = spts.pop(0)
            if sp in occ: continue
            tt = self._enemy_queue.pop(0)
            kw = {'enable_benchmark': self.benchmark} if tt == TANK_BOSS else {}
            ag = cls_map.get(tt, BasicTank)(sp, **kw)
            ent = TankEntity(ag, TANK_COLORS.get(tt, TANK_COLORS[TANK_BASIC]))
            ent.pos = list(sp); ent.hp = ag.hp; ent.max_hp = ag.hp
            self._enemies.append(ent); occ.add(sp)

    # ── Step 9: Render ────────────────────────────────────────────────────────
    def _step9_render(self):
        self._water_ph = (self._water_ph + 1) % 16
        surf = self.screen

        # Gray surround
        surf.fill(NES_GRAY)

        # Black game field
        gw = GRID_COLS * CELL_SIZE
        gh = GRID_ROWS * CELL_SIZE
        pygame.draw.rect(surf, NES_BLACK, (GAME_X, GAME_Y, gw, gh))

        # Tiles
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                t = self.grid[r][c]
                if t == EMPTY: continue
                ts = _get_tile(t, self._water_ph // 4)
                surf.blit(ts, (GAME_X + c*CELL_SIZE, GAME_Y + r*CELL_SIZE))

        # Forest drawn OVER tanks (transparency trick: drawn again after tanks)
        # Bullets
        for b in self._bullets:
            _draw_bullet(surf, b.pos[0], b.pos[1], b.owner, GAME_X, GAME_Y)

        # Enemies
        for ent in self._enemies:
            if ent.alive:
                _draw_tank(surf, ent.pos[0], ent.pos[1],
                           ent.direction, ent.color,
                           ent.max_hp, ent.hp, GAME_X, GAME_Y)

        # Player
        _draw_tank(surf, self.player.pos[0], self.player.pos[1],
                   self.player.direction, self.player.color,
                   self.player.max_hp, self.player.hp, GAME_X, GAME_Y)

        # Draw forest tiles again on top (NES hides tanks in forest)
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] == FOREST:
                    ts = _get_tile(FOREST)
                    surf.blit(ts, (GAME_X + c*CELL_SIZE, GAME_Y + r*CELL_SIZE))

        # HUD
        self._render_hud(surf)

        # Overlay
        if self.game_over:
            self._render_overlay(surf)

        pygame.display.flip()

    def _render_hud(self, surf):
        px = GAME_X + GRID_COLS * CELL_SIZE + BORDER + 4
        py = GAME_Y

        # Enemy icons grid (2 columns)
        remaining = len(self._enemy_queue) + len(self._enemies)
        col_idx = 0
        ix, iy = px, py
        for i in range(remaining):
            _draw_mini_tank(surf, ix + col_idx*16, iy, NES_LGRAY)
            col_idx += 1
            if col_idx >= 2:
                col_idx = 0; iy += 18

        # Separator
        sep_y = py + 10 * 18 + 6
        pygame.draw.line(surf, NES_LGRAY, (px, sep_y), (px+36, sep_y), 2)

        # Player icon + lives
        _draw_mini_tank(surf, px, sep_y+8, TANK_COLORS[TANK_PLAYER])
        lbl = self._font.render(f"x{self.player_lives}", True, NES_WHITE)
        surf.blit(lbl, (px+16, sep_y+8))

        # Stage
        pygame.draw.line(surf, NES_ORANGE, (px+2, sep_y+34), (px+2, sep_y+46), 3)
        pygame.draw.polygon(surf, NES_ORANGE,
            [(px+3,sep_y+34),(px+14,sep_y+39),(px+3,sep_y+44)])
        stg = self._fsm.render("1", True, NES_WHITE)
        surf.blit(stg, (px+16, sep_y+36))

        # Score
        sc_y = sep_y + 60
        s1 = self._fsm.render("SCORE", True, NES_ORANGE)
        s2 = self._font.render(str(self.score), True, NES_WHITE)
        surf.blit(s1, (px, sc_y))
        surf.blit(s2, (px, sc_y+14))

        # Boss HP + minimax info
        boss = next((e for e in self._enemies
                     if e.agent.tank_type==TANK_BOSS and e.alive), None)
        if boss:
            by = sc_y + 40
            bt = self._fsm.render("BOSS", True, NES_RED)
            surf.blit(bt, (px, by))
            bar_w = max(1, int((boss.hp / BOSS_HP) * 36))
            pygame.draw.rect(surf, NES_RED,   (px, by+14, bar_w, 6))
            pygame.draw.rect(surf, NES_STEELG,(px, by+14, 36,    6), 1)
            dp = self._fsm.render(f"D:{get_boss_depth(boss.hp)}", True, NES_YELLOW)
            surf.blit(dp, (px, by+24))
            lgr = getattr(boss.agent,'logger',None)
            if lgr and lgr.records:
                sp = self._fsm.render(f"x{lgr.last_speedup():.1f}AB", True, NES_LGREEN)
                surf.blit(sp, (px, by+38))

    def _render_overlay(self, surf):
        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((0,0,0,160))
        surf.blit(ov,(0,0))
        msg = "STAGE CLEAR!" if self.won else "GAME OVER"
        col = NES_YELLOW if self.won else NES_RED
        img = self._font.render(msg, True, col)
        cx = WIN_W//2 - img.get_width()//2
        cy = WIN_H//2 - img.get_height()//2
        # black shadow
        shadow = self._font.render(msg, True, NES_BLACK)
        surf.blit(shadow, (cx+2, cy+2))
        surf.blit(img, (cx, cy))
        sc = self._fsm.render(f"Score: {self.score}", True, NES_WHITE)
        surf.blit(sc, (WIN_W//2 - sc.get_width()//2, cy+24))

    # ── Step 10: Win/Lose ─────────────────────────────────────────────────────
    def _step10_win_lose(self):
        if self.game_over:
            return 'win' if self.won else 'lose'
        if not self._enemy_queue and not self._enemies:
            self.game_over = True; self.won = True; return 'win'
        return None
