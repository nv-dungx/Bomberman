import pygame
import sys
import random
import heapq
from collections import deque
from settings import *

class Enemy:
    def __init__(self, x, y):
        self.grid_x = x
        self.grid_y = y
        self.rect = pygame.Rect(x * TILE_SIZE + 5, y * TILE_SIZE + 5, 30, 30)
        self.path = []

    def find_path(self, target_gx, target_gy, game_map):
        """DSA: Thuật toán BFS tìm đường ngắn nhất"""
        start = (self.grid_x, self.grid_y)
        target = (target_gx, target_gy)
        if start == target: return []
        
        queue = deque([start])
        parent_map = {start: None}
        
        while queue:
            current = queue.popleft()
            if current == target: break
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = current[0] + dx, current[1] + dy
                if (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and
                    game_map[ny][nx] == EMPTY and (nx, ny) not in parent_map):
                    parent_map[(nx, ny)] = current
                    queue.append((nx, ny))
        
        path = []
        curr = target
        while curr in parent_map and curr != start:
            path.append(curr)
            curr = parent_map[curr]
        self.path = path[::-1]
        return self.path

    def move(self):
        if not self.path: return
        target_node = self.path[0]
        tx, ty = target_node[0] * TILE_SIZE + 5, target_node[1] * TILE_SIZE + 5
        if self.rect.x < tx: self.rect.x += ENEMY_SPEED
        elif self.rect.x > tx: self.rect.x -= ENEMY_SPEED
        if self.rect.y < ty: self.rect.y += ENEMY_SPEED
        elif self.rect.y > ty: self.rect.y -= ENEMY_SPEED
        if abs(self.rect.x - tx) < ENEMY_SPEED and abs(self.rect.y - ty) < ENEMY_SPEED:
            self.grid_x, self.grid_y = target_node

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bomberman DSA - Week 2 Final")
        self.clock = pygame.time.Clock()
        
        self.player_rect = pygame.Rect(TILE_SIZE + 5, TILE_SIZE + 5, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.player_current_speed = PLAYER_SPEED
        
        self.bomb_queue = deque()
        self.explosions = []
        self.powerups = {}        
        self.active_effects = []   # DSA: Min-Heap
        self.explosion_range = 2
        
        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.setup_walls()
        
        # Khởi tạo 3 Enemy ở các góc xa
        self.enemies = [
            Enemy(GRID_WIDTH - 2, GRID_HEIGHT - 2),
            Enemy(GRID_WIDTH - 2, 1),
            Enemy(1, GRID_HEIGHT - 2)
        ]

    def setup_walls(self):
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if r == 0 or r == GRID_HEIGHT-1 or c == 0 or c == GRID_WIDTH-1:
                    self.map[r][c] = WALL
                elif r % 2 == 0 and c % 2 == 0:
                    self.map[r][c] = WALL
                else:
                    if r <= 2 and c <= 2: continue
                    # Mật độ thưa hơn: 30%
                    if random.random() < 0.3: 
                        self.map[r][c] = SOFT_WALL

    def handle_input(self):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:  dx = -self.player_current_speed
        if keys[pygame.K_RIGHT]: dx = self.player_current_speed
        if keys[pygame.K_UP]:    dy = -self.player_current_speed
        if keys[pygame.K_DOWN]:  dy = self.player_current_speed

        self.player_rect.x += dx
        if self.check_collision(): self.player_rect.x -= dx
        self.player_rect.y += dy
        if self.check_collision(): self.player_rect.y -= dy

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                gx, gy = self.player_rect.centerx // TILE_SIZE, self.player_rect.centery // TILE_SIZE
                self.bomb_queue.append({'x': gx, 'y': gy, 'timer': pygame.time.get_ticks() + 2000})

    def check_collision(self):
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if self.map[r][c] in [WALL, SOFT_WALL]:
                    if self.player_rect.colliderect(pygame.Rect(c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)):
                        return True
        return False

    def handle_explosion(self, bx, by):
        now = pygame.time.get_ticks()
        directions = [(0,0), (0,1), (0,-1), (1,0), (-1,0)]
        
        for dx, dy in directions:
            for i in range(0 if (dx,dy)==(0,0) else 1, self.explosion_range + 1):
                nx, ny = bx + dx*i, by + dy*i
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    tile = self.map[ny][nx]
                    if tile == WALL: break
                    
                    self.explosions.append({'x': nx, 'y': ny, 'expiry': now + 500})
                    
                    # DIỆT QUÁI
                    for enemy in self.enemies[:]:
                        if enemy.grid_x == nx and enemy.grid_y == ny:
                            self.enemies.remove(enemy)

                    # PHÁ TƯỜNG & RƠI ITEM (Thưa hơn: 15%)
                    if tile == SOFT_WALL:
                        self.map[ny][nx] = EMPTY
                        if random.random() < 0.15:
                            self.powerups[(nx, ny)] = random.choice(["SPEED", "RANGE"])
                        break
                    
                    if (dx, dy) == (0,0): break

    def update(self):
        now = pygame.time.get_ticks()
        
        # 1. Quản lý Bom và Tia lửa
        while self.bomb_queue and now >= self.bomb_queue[0]['timer']:
            b = self.bomb_queue.popleft()
            self.handle_explosion(b['x'], b['y'])
        self.explosions = [e for e in self.explosions if e['expiry'] > now]

        # 2. DSA: Min-Heap quản lý hiệu ứng
        while self.active_effects and self.active_effects[0][0] <= now:
            _, effect = heapq.heappop(self.active_effects)
            if effect == "RESET_SPEED": self.player_current_speed = PLAYER_SPEED
            if effect == "RESET_RANGE": self.explosion_range = 2

        # 3. Nhặt Item
        px, py = self.player_rect.centerx // TILE_SIZE, self.player_rect.centery // TILE_SIZE
        if (px, py) in self.powerups:
            p_type = self.powerups.pop((px, py))
            if p_type == "SPEED":
                self.player_current_speed = 5
                heapq.heappush(self.active_effects, (now + 5000, "RESET_SPEED"))
            elif p_type == "RANGE":
                self.explosion_range = 4
                heapq.heappush(self.active_effects, (now + 7000, "RESET_RANGE"))

        # 4. Enemy AI & Va chạm Player
        for enemy in self.enemies:
            path = enemy.find_path(px, py, self.map)
            if path: enemy.move()
            if self.player_rect.colliderect(enemy.rect): 
                print("💥 GAME OVER!")

    def draw(self):
        self.screen.fill(BLACK)
        # Vẽ Map
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                rect = (c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if self.map[r][c] == WALL: pygame.draw.rect(self.screen, GRAY, rect)
                elif self.map[r][c] == SOFT_WALL: pygame.draw.rect(self.screen, BROWN, rect)
        
        # Vẽ Item
        for (gx, gy), p_type in self.powerups.items():
            color = LIGHT_BLUE if p_type == "SPEED" else YELLOW
            pygame.draw.rect(self.screen, color, (gx*TILE_SIZE+12, gy*TILE_SIZE+12, 16, 16))

        # Vẽ Tia lửa
        for e in self.explosions:
            pygame.draw.rect(self.screen, ORANGE, (e['x']*TILE_SIZE, e['y']*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        # Vẽ Bom
        for b in self.bomb_queue:
            pygame.draw.circle(self.screen, RED, (b['x']*TILE_SIZE + 20, b['y']*TILE_SIZE + 20), 15)

        # Vẽ Player & Enemy
        pygame.draw.rect(self.screen, BLUE, self.player_rect)
        for enemy in self.enemies:
            pygame.draw.rect(self.screen, GREEN, enemy.rect)
            
        pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_input(); game.update(); game.draw()
        game.clock.tick(FPS)