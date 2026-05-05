"""
main.py
-------
Điểm khởi chạy chính.
Tích hợp FSM, Save JSON, và Chế độ PvP (2 Người chơi WASD/B và Arrows/P).
"""
import pygame
import sys
import random
import json
import os
from collections import deque
from settings import *
from player import Player
from level_manager import LevelManager

STATE_MENU = 0
STATE_TRANSITION = 1
STATE_PLAYING = 2
STATE_GAMEOVER = 3
STATE_VICTORY = 4

MAX_LEVEL = 5
SAVE_FILE = "savegame.json"

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bomberman DSA - Campaign & PvP")
        self.clock = pygame.time.Clock()
        self.show_visualization = False 
        
        self.state = STATE_MENU
        self.saved_level = self.load_progress()  
        self.level = 1
        self.transition_timer = 0
        
        self.is_pvp = False
        self.pvp_winner = None # Lưu xem ai thắng (1, 2, hoặc 0 nếu hòa)
        
        self.level_manager = LevelManager()
        self.player1 = None
        self.player2 = None

    def load_progress(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("saved_level", 1)
            except: pass
        return 1

    def save_progress(self):
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump({"saved_level": self.saved_level}, f)
        except: pass

    def load_level(self):
        self.bomb_queue = deque()         
        self.explosions = []
        
        if self.is_pvp:
            self.level_manager.generate_pvp_level()
            # P1 ở góc trái trên, P2 ở góc phải dưới
            self.player1 = Player(TILE_SIZE + 5, TILE_SIZE + 5, lives = 3)
            self.player2 = Player(SCREEN_WIDTH - TILE_SIZE * 2 + 5, SCREEN_HEIGHT - TILE_SIZE * 2 + 5)
            self.pvp_winner = None
        else:
            self.level_manager.generate_level(self.level)
            self.player1 = Player(TILE_SIZE + 5, TILE_SIZE + 5)
            self.player2 = None # Campaign chỉ có 1 người

    def start_campaign(self, is_new_game=False):
        self.is_pvp = False
        if is_new_game:
            self.saved_level = 1
            self.save_progress()
        self.level = self.saved_level
        self.state = STATE_TRANSITION
        self.transition_timer = pygame.time.get_ticks() + 2500
        
    def start_pvp(self):
        self.is_pvp = True
        self.level = "PvP"
        self.state = STATE_TRANSITION
        self.transition_timer = pygame.time.get_ticks() + 2000

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if self.state == STATE_MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1: self.start_pvp()
                    elif event.key == pygame.K_2: self.start_campaign(is_new_game=True)  
                    elif event.key == pygame.K_3 and self.saved_level > 1: self.start_campaign(is_new_game=False) 

            elif self.state == STATE_GAMEOVER:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        if self.is_pvp: self.start_pvp()
                        else: self.start_campaign(is_new_game=False)
                    elif event.key == pygame.K_m:
                        self.state = STATE_MENU

            elif self.state == STATE_VICTORY:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:
                        if not self.is_pvp: 
                            self.saved_level = 1
                            self.save_progress()
                        self.state = STATE_MENU
                    elif event.key == pygame.K_r and self.is_pvp:
                        self.start_pvp() # Chơi lại ván PvP
                    
            elif self.state == STATE_PLAYING:
                if event.type == pygame.KEYDOWN:
                    # ĐẶT BOM PLAYER 1 (Phím B)
                    if event.key == pygame.K_b and not self.player1.is_dead:
                        gx, gy = self.player1.rect.centerx // TILE_SIZE, self.player1.rect.centery // TILE_SIZE
                        if all(not (b['x'] == gx and b['y'] == gy) for b in self.bomb_queue):
                            self.bomb_queue.append({'x': gx, 'y': gy, 'timer': pygame.time.get_ticks() + 2000, 'range': self.player1.explosion_range})

                    # ĐẶT BOM PLAYER 2 (Phím P) - Chỉ PvP
                    elif self.is_pvp and event.key == pygame.K_p and not self.player2.is_dead:
                        gx, gy = self.player2.rect.centerx // TILE_SIZE, self.player2.rect.centery // TILE_SIZE
                        if all(not (b['x'] == gx and b['y'] == gy) for b in self.bomb_queue):
                            self.bomb_queue.append({'x': gx, 'y': gy, 'timer': pygame.time.get_ticks() + 2000, 'range': self.player2.explosion_range})
                            
                    elif event.key == pygame.K_v:
                        self.show_visualization = not self.show_visualization

        if self.state == STATE_PLAYING:
            keys = pygame.key.get_pressed()
            
            # DI CHUYỂN PLAYER 1 (WASD)
            if not self.player1.is_dead:
                dx1, dy1 = 0, 0
                if keys[pygame.K_a]: dx1 = -self.player1.current_speed
                if keys[pygame.K_d]: dx1 = self.player1.current_speed
                if keys[pygame.K_w]: dy1 = -self.player1.current_speed
                if keys[pygame.K_s]: dy1 = self.player1.current_speed
                if dx1 != 0 or dy1 != 0: self.player1.last_dx, self.player1.last_dy = dx1, dy1
                self.player1.move(dx1, dy1, self.level_manager.map)

            # DI CHUYỂN PLAYER 2 (MŨI TÊN)
            if self.is_pvp and not self.player2.is_dead:
                dx2, dy2 = 0, 0
                if keys[pygame.K_LEFT]: dx2 = -self.player2.current_speed
                if keys[pygame.K_RIGHT]: dx2 = self.player2.current_speed
                if keys[pygame.K_UP]: dy2 = -self.player2.current_speed
                if keys[pygame.K_DOWN]: dy2 = self.player2.current_speed
                if dx2 != 0 or dy2 != 0: self.player2.last_dx, self.player2.last_dy = dx2, dy2
                self.player2.move(dx2, dy2, self.level_manager.map)

    def handle_explosion(self, start_x, start_y, exp_range):
        now = pygame.time.get_ticks()
        explosion_queue = deque([(start_x, start_y)])

        while explosion_queue:
            bx, by = explosion_queue.popleft()
            for dx, dy in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]:
                for i in range(0 if (dx, dy) == (0, 0) else 1, exp_range + 1):
                    nx, ny = bx + dx * i, by + dy * i
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        tile = self.level_manager.map[ny][nx]
                        if tile == WALL: break

                        self.explosions.append({'x': nx, 'y': ny, 'expiry': now + 500})

                        for bomb in list(self.bomb_queue):
                            if bomb['x'] == nx and bomb['y'] == ny:
                                self.bomb_queue.remove(bomb)
                                explosion_queue.append((nx, ny))

                        if tile == SOFT_WALL:
                            self.level_manager.map[ny][nx] = EMPTY
                            if random.random() < 0.20: # PvP rớt đồ rate cao hơn chút (20%)
                                self.level_manager.powerups[(nx, ny)] = random.choice(["SPEED", "RANGE", "SHIELD", "GHOST"])
                            break
                        if (dx, dy) == (0, 0): break

    def update(self):
        now = pygame.time.get_ticks()
        
        if self.state == STATE_TRANSITION:
            if now >= self.transition_timer:
                self.load_level()
                self.state = STATE_PLAYING
            return
        if self.state != STATE_PLAYING: return

        # Xử lý Win/Loss Campaign
        if not self.is_pvp and self.player1.is_dead:
            self.state = STATE_GAMEOVER
            return
            
        # Xử lý Win/Loss PvP
        if self.is_pvp:
            if self.player1.is_dead and self.player2.is_dead:
                self.pvp_winner = 0 # Hòa
                self.state = STATE_VICTORY
                return
            elif self.player1.is_dead:
                self.pvp_winner = 2 # P2 Thắng
                self.state = STATE_VICTORY
                return
            elif self.player2.is_dead:
                self.pvp_winner = 1 # P1 Thắng
                self.state = STATE_VICTORY
                return

        # Lửa & Bom
        while self.bomb_queue and now >= self.bomb_queue[0]['timer']:
            b = self.bomb_queue.popleft()
            self.handle_explosion(b['x'], b['y'], b['range'])
        self.explosions = [e for e in self.explosions if e['expiry'] > now]

        for e in self.explosions:
            exp_rect = pygame.Rect(e['x'] * TILE_SIZE, e['y'] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if not self.player1.is_dead and self.player1.rect.colliderect(exp_rect): self.player1.take_damage(now)
            if self.is_pvp and not self.player2.is_dead and self.player2.rect.colliderect(exp_rect): self.player2.take_damage(now)
            
            for enemy in self.level_manager.enemies[:]:
                if enemy.rect.colliderect(exp_rect): self.level_manager.enemies.remove(enemy)

        # Môi trường, Bẫy, Quái, Qua màn... (Gộp xử lý cho các players hiện có)
        players = [self.player1]
        if self.is_pvp: players.append(self.player2)
        
        for p in players:
            if p.is_dead: continue
            px_grid, py_grid = p.rect.centerx // TILE_SIZE, p.rect.centery // TILE_SIZE
            current_tile = self.level_manager.map[py_grid][px_grid]
            
            # Băng chuyền & Trượt
            if current_tile == CONVEYOR_LEFT: p.forced_move_queue.append((-2, 0))
            elif current_tile == CONVEYOR_RIGHT: p.forced_move_queue.append((2, 0))
            while p.forced_move_queue:
                fdx, fdy = p.forced_move_queue.popleft()
                p.move(fdx, fdy, self.level_manager.map)

            # Item
            p.update_items(now, current_tile)
            if (px_grid, py_grid) in self.level_manager.powerups:
                p_type = self.level_manager.powerups.pop((px_grid, py_grid))
                p.pick_up_item(p_type, now)
            
            # Teleport
            teleports = self.level_manager.teleports
            if teleports and now > p.teleport_cooldown and (px_grid, py_grid) in teleports:
                other = (teleports[1] if (px_grid, py_grid) == teleports[0] else teleports[0])
                p.rect.center = (other[0] * TILE_SIZE + TILE_SIZE // 2, other[1] * TILE_SIZE + TILE_SIZE // 2)
                p.teleport_cooldown = now + 1000

        # Cửa qua màn (Chỉ Campaign)
        if not self.is_pvp:
            px, py = self.player1.rect.centerx // TILE_SIZE, self.player1.rect.centery // TILE_SIZE
            door = self.level_manager.door_pos
            if door and self.level_manager.map[door[1]][door[0]] == EMPTY and len(self.level_manager.enemies) == 0 and (px, py) == door:
                if self.level >= MAX_LEVEL: self.state = STATE_VICTORY
                else:
                    self.saved_level += 1 
                    self.save_progress()
                    self.start_campaign(is_new_game=False)
                return

        # AI Kẻ địch (Campaign)
        for enemy in self.level_manager.enemies:
            ex, ey = enemy.rect.centerx // TILE_SIZE, enemy.rect.centery // TILE_SIZE
            if 0 <= ex < GRID_WIDTH and 0 <= ey < GRID_HEIGHT:
                e_tile = self.level_manager.map[ey][ex]
                if e_tile == CONVEYOR_LEFT:
                    enemy.rect.x -= 2
                    if enemy.check_collision(self.level_manager.map): enemy.rect.x += 2 
                    enemy.path = [] 
                elif e_tile == CONVEYOR_RIGHT:
                    enemy.rect.x += 2
                    if enemy.check_collision(self.level_manager.map): enemy.rect.x -= 2 
                    enemy.path = [] 
            
            px, py = self.player1.rect.centerx // TILE_SIZE, self.player1.rect.centery // TILE_SIZE
            path = enemy.find_path(px, py, self.level_manager.map, self.bomb_queue, self.player1.explosion_range, now)
            if path: enemy.move(self.level_manager.map)
            if self.player1.rect.colliderect(enemy.rect): self.player1.take_damage(now)

    def draw(self):
        self.screen.fill(BLACK)
        
        if self.state == STATE_MENU:
            font_title = pygame.font.SysFont("Arial", 64, bold=True)
            font_opt = pygame.font.SysFont("Arial", 32)
            
            title = font_title.render("BOMBERMAN DSA", True, WHITE)
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120)))
            
            opt1 = font_opt.render("[1] PvP Mode (2 Players)", True, RED)
            opt2 = font_opt.render("[2] New Campaign", True, WHITE)
            self.screen.blit(opt1, opt1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
            self.screen.blit(opt2, opt2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))
            
            if self.saved_level > 1:
                opt3 = font_opt.render(f"[3] Continue Campaign (Level {self.saved_level})", True, YELLOW)
                self.screen.blit(opt3, opt3.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80)))
            
        elif self.state == STATE_TRANSITION:
            font_level = pygame.font.SysFont("Arial", 72, bold=True)
            lvl_txt = font_level.render(f"PVP BATTLE" if self.is_pvp else f"LEVEL {self.level}", True, WHITE)
            self.screen.blit(lvl_txt, lvl_txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))

        elif self.state in [STATE_PLAYING, STATE_GAMEOVER, STATE_VICTORY]:
            
            # Kiểm tra xem có người chơi nào đang ở trạng thái xuyên tường không
            any_ghost = False
            if self.player1 and not self.player1.is_dead and self.player1.is_ghost: any_ghost = True
            if self.is_pvp and self.player2 and not self.player2.is_dead and self.player2.is_ghost: any_ghost = True

            # Vẽ Map
            for r in range(GRID_HEIGHT):
                for c in range(GRID_WIDTH):
                    rect = (c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    tile = self.level_manager.map[r][c]
                    
                    if tile == WALL: 
                        pygame.draw.rect(self.screen, GRAY, rect)
                    elif tile == SOFT_WALL: 
                        # Phục hồi logic: Tường chuyển màu nâu tối nếu có người ăn item Ghost
                        wall_color = (100, 50, 10) if any_ghost else (139, 69, 19)
                        pygame.draw.rect(self.screen, wall_color, rect)
                    elif tile == TRAP_ICE: 
                        pygame.draw.rect(self.screen, LIGHT_BLUE_ICE, rect)
                    elif tile in [CONVEYOR_LEFT, CONVEYOR_RIGHT]: 
                        pygame.draw.rect(self.screen, (50, 50, 50), rect)
                        arrow = "<" if tile == CONVEYOR_LEFT else ">"
                        font_arrow = pygame.font.SysFont("Arial", 20, bold=True)
                        self.screen.blit(font_arrow.render(arrow, True, WHITE), (c * TILE_SIZE + 15, r * TILE_SIZE + 8))
                    elif tile == TRAP_TELEPORT:
                        pygame.draw.circle(self.screen, MAGENTA, (c * TILE_SIZE + 20, r * TILE_SIZE + 20), 12, 4)

            # Vẽ Cửa (Nếu có)
            if not self.is_pvp and self.level_manager.door_pos and self.level_manager.map[self.level_manager.door_pos[1]][self.level_manager.door_pos[0]] == EMPTY:
                pygame.draw.rect(self.screen, GOLD, (self.level_manager.door_pos[0] * TILE_SIZE, self.level_manager.door_pos[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))

            if self.show_visualization:
                for enemy in self.level_manager.enemies:
                    for step in enemy.path:
                        pygame.draw.circle(self.screen, YELLOW, (step[0] * TILE_SIZE + 20, step[1] * TILE_SIZE + 20), 6)

            # 3. Vẽ Items (Đã phục hồi đúng 4 màu), Lửa, Bom, Quái
            for (gx, gy), p_type in self.level_manager.powerups.items():
                if p_type == "SPEED": color = LIGHT_BLUE
                elif p_type == "RANGE": color = YELLOW
                elif p_type == "SHIELD": color = CYAN
                else: color = PURPLE # GHOST
                pygame.draw.rect(self.screen, color, (gx * TILE_SIZE + 12, gy * TILE_SIZE + 12, 16, 16))
                
            for e in self.explosions: pygame.draw.rect(self.screen, ORANGE, (e['x'] * TILE_SIZE, e['y'] * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            for b in self.bomb_queue: pygame.draw.circle(self.screen, RED, (b['x'] * TILE_SIZE + 20, b['y'] * TILE_SIZE + 20), 15)
            for enemy in self.level_manager.enemies: pygame.draw.rect(self.screen, enemy.color, enemy.rect)
                
            if self.player1 and not self.player1.is_dead:
                self.player1.draw(self.screen, pygame.time.get_ticks()) 
            if self.is_pvp and self.player2 and not self.player2.is_dead:
                color2 = PURPLE if self.player2.is_ghost else RED
                pygame.draw.rect(self.screen, color2, self.player2.rect)
                if self.player2.shields: pygame.draw.circle(self.screen, CYAN, self.player2.rect.center, TILE_SIZE // 2 + 4, len(self.player2.shields) * 2)

            # --- PHẦN UI MỚI: HIỂN THỊ MẠNG (HP) VÀ LEVEL ---
            font = pygame.font.SysFont("Arial", 22, bold=True)
            
            # HP Player 1 (Góc trái trên)
            if self.player1:
                hp_text1 = f"P1 HP: {'❤ ' * self.player1.lives}"
                self.screen.blit(font.render(hp_text1, True, BLUE), (10, 10))
            
            # Cụm UI bên phải
            if self.is_pvp:
                # Mode báo PvP và HP Player 2
                self.screen.blit(font.render("PvP Mode", True, WHITE), (SCREEN_WIDTH - 120, 10))
                if self.player2:
                    hp_text2 = f"P2 HP: {'❤ ' * self.player2.lives}"
                    self.screen.blit(font.render(hp_text2, True, RED), (SCREEN_WIDTH - 150, 40))
            else:
                self.screen.blit(font.render(f"Level: {self.level}", True, WHITE), (SCREEN_WIDTH - 100, 10))

            # Overlays Game Over & Victory
            if self.state == STATE_GAMEOVER:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.screen.blit(overlay, (0, 0))
                self.screen.blit(font.render("GAME OVER - Press R to Restart or M for Menu", True, RED), (SCREEN_WIDTH//2 - 250, SCREEN_HEIGHT//2))
                
            elif self.state == STATE_VICTORY:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.screen.blit(overlay, (0, 0))
                
                if self.is_pvp:
                    txt = "DRAW!" if self.pvp_winner == 0 else f"PLAYER {self.pvp_winner} WINS!"
                    color = YELLOW if self.pvp_winner == 0 else (BLUE if self.pvp_winner == 1 else RED)
                else:
                    txt, color = "VICTORY! CAMPAIGN COMPLETED!", GOLD
                    
                font_vic = pygame.font.SysFont("Arial", 72, bold=True)
                vic = font_vic.render(txt, True, color)
                self.screen.blit(vic, vic.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)))
                self.screen.blit(font.render("Press R to play again or M for Menu", True, WHITE), (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 + 50))

        pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_input()
        game.update()
        game.draw()
        game.clock.tick(FPS)