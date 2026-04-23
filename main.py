import pygame
import sys
import random
from collections import deque
from settings import *

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bomberman DSA - IT003")
        self.clock = pygame.time.Clock()
        
        # Vị trí Pixel-perfect (Bắt đầu ở ô 1,1)
        self.player_rect = pygame.Rect(TILE_SIZE + 5, TILE_SIZE + 5, PLAYER_WIDTH, PLAYER_HEIGHT)
        
        # DSA Core: Queue quản lý bom
        self.bomb_queue = deque()
        
        # Khởi tạo Map
        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.setup_walls()

    def setup_walls(self):
        """Khởi tạo tường cứng và rải tường mềm ngẫu nhiên"""
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
                    if random.random() < 0.6: # 60% tỉ lệ có tường mềm
                        self.map[r][c] = SOFT_WALL

    def handle_input(self):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        
        if keys[pygame.K_LEFT]:  dx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT]: dx = PLAYER_SPEED
        if keys[pygame.K_UP]:    dy = -PLAYER_SPEED
        if keys[pygame.K_DOWN]:  dy = PLAYER_SPEED

        # Di chuyển X và check va chạm
        self.player_rect.x += dx
        if self.check_wall_collision():
            self.player_rect.x -= dx

        # Di chuyển Y và check va chạm
        self.player_rect.y += dy
        if self.check_wall_collision():
            self.player_rect.y -= dy

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Đặt bom tại ô lưới mà tâm Player đang đứng
                    gx = self.player_rect.centerx // TILE_SIZE
                    gy = self.player_rect.centery // TILE_SIZE
                    now = pygame.time.get_ticks()
                    self.bomb_queue.append({'x': gx, 'y': gy, 'timer': now + 2000})

    def check_wall_collision(self):
        """Kiểm tra va chạm với cả WALL và SOFT_WALL"""
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if self.map[r][c] in [WALL, SOFT_WALL]:
                    wall_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.player_rect.colliderect(wall_rect):
                        return True
        return False

    def handle_explosion(self, bx, by):
        """Xử lý phá tường khi bom nổ"""
        explosion_range = 2
        directions = [(0,1), (0,-1), (1,0), (-1,0)]
        
        # Check tâm bom
        self.check_player_hit(bx, by)

        for dx, dy in directions:
            for i in range(1, explosion_range + 1):
                nx, ny = bx + dx*i, by + dy*i
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    tile = self.map[ny][nx]
                    if tile == WALL: 
                        break # Tường cứng chặn lửa
                    
                    self.check_player_hit(nx, ny)
                    
                    if tile == SOFT_WALL:
                        self.map[ny][nx] = EMPTY # Phá tường mềm
                        break # Tường mềm chặn lửa sau khi bị phá

    def check_player_hit(self, gx, gy):
        """Kiểm tra xem lửa tại ô gx, gy có trúng Player không"""
        px = self.player_rect.centerx // TILE_SIZE
        py = self.player_rect.centery // TILE_SIZE
        if gx == px and gy == py:
            print("PLAYER DIED!")

    def update(self):
        now = pygame.time.get_ticks()
        # Duyệt Queue xem quả bom nào đến giờ nổ
        while self.bomb_queue and now >= self.bomb_queue[0]['timer']:
            b = self.bomb_queue.popleft()
            self.handle_explosion(b['x'], b['y'])

    def draw(self):
        self.screen.fill(BLACK)
        
        # Vẽ Map
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                rect = (c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if self.map[r][c] == WALL:
                    pygame.draw.rect(self.screen, GRAY, rect)
                elif self.map[r][c] == SOFT_WALL:
                    pygame.draw.rect(self.screen, BROWN, rect)
        
        # Vẽ Bom
        for b in self.bomb_queue:
            pygame.draw.circle(self.screen, RED, (b['x']*TILE_SIZE + 20, b['y']*TILE_SIZE + 20), 15)

        # Vẽ Player
        pygame.draw.rect(self.screen, BLUE, self.player_rect)
        
        pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_input()
        game.update()
        game.draw()
        game.clock.tick(FPS)