"""
player.py
---------
Quản lý thực thể người chơi: di chuyển, xử lý va chạm, nhặt item, và quản lý máu/khiên.
"""
import pygame
import heapq
from collections import deque
from settings import *

class Player:
    def __init__(self, x, y, lives = 1):
        self.rect = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.current_speed = PLAYER_SPEED
        self.last_dx, self.last_dy = 0, 0
        self.is_dead = False
        self.lives = lives  # 💖 Khởi tạo 3 mạng
        self.shields = []
        self.invulnerable_until = 0
        self.is_ghost = False
        self.explosion_range = 2
        self.active_effects = []
        self.forced_move_queue = deque()
        self.teleport_cooldown = 0
        
    def move(self, dx, dy, game_map):
        self.rect.x += dx
        if self.check_collision(game_map): self.rect.x -= dx
        self.rect.y += dy
        if self.check_collision(game_map): self.rect.y -= dy

    def check_collision(self, game_map):
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                tile = game_map[r][c]
                if tile == WALL or (tile == SOFT_WALL and not self.is_ghost):
                    tile_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.rect.colliderect(tile_rect): return True
        return False
        
    def take_damage(self, now):
        """Xử lý trừ máu, vỡ khiên hoặc chết."""
        if now < self.invulnerable_until:
            return # Đang trong thời gian bất tử thì không nhận sát thương
            
        if self.shields:
            self.shields.pop()
            self.invulnerable_until = now + 1500 # Bất tử 1.5s sau khi vỡ khiên
            print(f"🛡️ Bể Khiên! Còn {len(self.shields)} lớp.")
        else:
            self.lives -= 1
            if self.lives <= 0:
                self.is_dead = True
                print("💥 BẠN ĐÃ CHẾT!")
            else:
                self.invulnerable_until = now + 1500 # Nhấp nháy bất tử 1.5s để chạy trốn
                print(f"💔 Trúng bom! Còn {self.lives} mạng.")

    def update_items(self, now, current_tile):
        while self.active_effects and self.active_effects[0][0] <= now:
            _, effect = heapq.heappop(self.active_effects)
            if effect == "RESET_SPEED": self.current_speed = PLAYER_SPEED
            elif effect == "RESET_RANGE": self.explosion_range = 2
            elif effect == "RESET_GHOST":
                self.is_ghost = False
                if current_tile == SOFT_WALL: self.take_damage(now)

    def pick_up_item(self, p_type, now):
        if p_type == "SPEED":
            self.current_speed = 5
            heapq.heappush(self.active_effects, (now + 5000, "RESET_SPEED"))
        elif p_type == "RANGE":
            self.explosion_range = 4
            heapq.heappush(self.active_effects, (now + 7000, "RESET_RANGE"))
        elif p_type == "SHIELD":
            self.shields.append("L")
        elif p_type == "GHOST":
            self.is_ghost = True
            heapq.heappush(self.active_effects, (now + 8000, "RESET_GHOST"))

    def draw(self, screen, now):
        if self.is_dead: return
        is_invulnerable = now < self.invulnerable_until
        
        # Nhấp nháy khi đang vô địch (i-frame) sau khi trúng bom
        if not is_invulnerable or (now // 100) % 2 == 0:
            color = PURPLE if self.is_ghost else BLUE
            pygame.draw.rect(screen, color, self.rect)
        if self.shields:
            pygame.draw.circle(screen, CYAN, self.rect.center, TILE_SIZE // 2 + 4, len(self.shields) * 2)