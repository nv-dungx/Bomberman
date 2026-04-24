import pygame
import sys
import random
import heapq
from collections import deque
from settings import *

class Enemy:
    def __init__(self, x, y):
        # Tọa độ lưới (Grid)
        self.grid_x = x
        self.grid_y = y
        # Rect để di chuyển Pixel-perfect
        self.rect = pygame.Rect(x * TILE_SIZE + 5, y * TILE_SIZE + 5, 30, 30)
        self.path = [] # Lưu đường đi tìm được từ BFS

    def find_path(self, target_gx, target_gy, game_map):
        """DSA: Thuật toán BFS tìm đường ngắn nhất trên đồ thị lưới"""
        start = (self.grid_x, self.grid_y)
        target = (target_gx, target_gy)
        
        if start == target: return []

        queue = deque([start])
        parent_map = {start: None}
        
        while queue:
            current = queue.popleft()
            if current == target: break
                
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_node = (current[0] + dx, current[1] + dy)
                
                # Điều kiện đi: Trong map + Không phải tường + Chưa duyệt
                if (0 <= next_node[0] < GRID_WIDTH and 
                    0 <= next_node[1] < GRID_HEIGHT and
                    game_map[next_node[1]][next_node[0]] == EMPTY and
                    next_node not in parent_map):
                    
                    parent_map[next_node] = current
                    queue.append(next_node)
        
        # Truy ngược đường đi
        path = []
        curr = target
        while curr in parent_map and curr != start:
            path.append(curr)
            curr = parent_map[curr]
        
        self.path = path[::-1] # Đảo ngược lại để có thứ tự từ start -> target
        return self.path

    def move(self):
        """Di chuyển Enemy dựa trên node đầu tiên của path"""
        if not self.path: return

        target_node = self.path[0]
        target_px = target_node[0] * TILE_SIZE + 5
        target_py = target_node[1] * TILE_SIZE + 5

        # Di chuyển dần dần về phía target pixel
        if self.rect.x < target_px: self.rect.x += ENEMY_SPEED
        elif self.rect.x > target_px: self.rect.x -= ENEMY_SPEED
        
        if self.rect.y < target_py: self.rect.y += ENEMY_SPEED
        elif self.rect.y > target_py: self.rect.y -= ENEMY_SPEED

        # Nếu đã đến sát ô mục tiêu, cập nhật lại grid_x, grid_y
        if abs(self.rect.x - target_px) < ENEMY_SPEED and abs(self.rect.y - target_py) < ENEMY_SPEED:
            self.grid_x, self.grid_y = target_node

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bomberman DSA - AI Enemy BFS")
        self.clock = pygame.time.Clock()
        
        self.player_rect = pygame.Rect(TILE_SIZE + 5, TILE_SIZE + 5, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.bomb_queue = deque()
        self.explosions = []
        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        
        self.setup_walls()
        # Khởi tạo Enemy ở góc dưới bên phải
        self.enemies = [Enemy(GRID_WIDTH - 2, GRID_HEIGHT - 2)]

    def setup_walls(self):
        """Khởi tạo tường với mật độ thưa hơn"""
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                # 1. Tường cứng bao quanh và cột trụ
                if r == 0 or r == GRID_HEIGHT-1 or c == 0 or c == GRID_WIDTH-1:
                    self.map[r][c] = WALL
                elif r % 2 == 0 and c % 2 == 0:
                    self.map[r][c] = WALL
                # 2. Sinh tường mềm ngẫu nhiên
                else:
                    # Chừa trống góc 3x3 cho người chơi xuất phát
                    if r <= 2 and c <= 2:
                        continue
                    
                    # GIẢM MẬT ĐỘ: Thay vì 0.6, dùng 0.35 để tường thưa hơn
                    if random.random() < 0.35: 
                        self.map[r][c] = SOFT_WALL

    def handle_input(self):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:  dx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT]: dx = PLAYER_SPEED
        if keys[pygame.K_UP]:    dy = -PLAYER_SPEED
        if keys[pygame.K_DOWN]:  dy = PLAYER_SPEED

        self.player_rect.x += dx
        if self.check_wall_collision(): self.player_rect.x -= dx
        self.player_rect.y += dy
        if self.check_wall_collision(): self.player_rect.y -= dy

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                gx, gy = self.player_rect.centerx // TILE_SIZE, self.player_rect.centery // TILE_SIZE
                self.bomb_queue.append({'x': gx, 'y': gy, 'timer': pygame.time.get_ticks() + 2000})

    def check_wall_collision(self):
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if self.map[r][c] in [WALL, SOFT_WALL]:
                    if self.player_rect.colliderect(pygame.Rect(c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)):
                        return True
        return False

    def handle_explosion(self, bx, by):
        now = pygame.time.get_ticks()
        for dx, dy in [(0,0), (0,1), (0,-1), (1,0), (-1,0)]:
            for i in range(0 if (dx,dy)==(0,0) else 1, 3):
                nx, ny = bx + dx*i, by + dy*i
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    if self.map[ny][nx] == WALL: break
                    self.explosions.append({'x': nx, 'y': ny, 'expiry': now + 500})
                    if self.map[ny][nx] == SOFT_WALL:
                        self.map[ny][nx] = EMPTY
                        break

    def update(self):
        now = pygame.time.get_ticks()
        while self.bomb_queue and now >= self.bomb_queue[0]['timer']:
            b = self.bomb_queue.popleft()
            self.handle_explosion(b['x'], b['y'])
        self.explosions = [e for e in self.explosions if e['expiry'] > now]

        # Update Enemy AI
        px, py = self.player_rect.centerx // TILE_SIZE, self.player_rect.centery // TILE_SIZE
        for enemy in self.enemies:
            enemy.find_path(px, py, self.map)
            enemy.move()
            if self.player_rect.colliderect(enemy.rect):
                print("GAME OVER - CHẠM PHẢI QUÁI!")

    def draw(self):
        self.screen.fill(BLACK)
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                rect = (c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if self.map[r][c] == WALL: pygame.draw.rect(self.screen, GRAY, rect)
                elif self.map[r][c] == SOFT_WALL: pygame.draw.rect(self.screen, BROWN, rect)
        
        # Visualization: Vẽ đường đi của Enemy
        for enemy in self.enemies:
            for step in enemy.path:
                vis_rect = (step[0]*TILE_SIZE + 10, step[1]*TILE_SIZE + 10, 20, 20)
                pygame.draw.rect(self.screen, (100, 100, 0), vis_rect) # Màu vàng tối

        for e in self.explosions:
            pygame.draw.rect(self.screen, ORANGE, (e['x']*TILE_SIZE, e['y']*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        for b in self.bomb_queue:
            pygame.draw.circle(self.screen, RED, (b['x']*TILE_SIZE + 20, b['y']*TILE_SIZE + 20), 15)

        pygame.draw.rect(self.screen, BLUE, self.player_rect)
        for enemy in self.enemies:
            pygame.draw.rect(self.screen, (0, 255, 0), enemy.rect)
            
        pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_input(); game.update(); game.draw()
        game.clock.tick(FPS)