import pygame
import sys
from collections import deque
from settings import *

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        
        # Vị trí tính bằng PIXEL (Bắt đầu ở ô 1,1 -> 40,40)
        # Cộng thêm 5 pixel để nhân vật nằm giữa ô trống ban đầu
        self.player_rect = pygame.Rect(TILE_SIZE + 5, TILE_SIZE + 5, PLAYER_WIDTH, PLAYER_HEIGHT)
        
        self.bomb_queue = deque()
        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.setup_walls()

    def setup_walls(self):
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if r == 0 or r == GRID_HEIGHT-1 or c == 0 or c == GRID_WIDTH-1:
                    self.map[r][c] = WALL
                elif r % 2 == 0 and c % 2 == 0:
                    self.map[r][c] = WALL

    def handle_input(self):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        
        if keys[pygame.K_LEFT]:  dx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT]: dx = PLAYER_SPEED
        if keys[pygame.K_UP]:    dy = -PLAYER_SPEED
        if keys[pygame.K_DOWN]:  dy = PLAYER_SPEED

        # Di chuyển theo trục X và check va chạm
        self.player_rect.x += dx
        if self.check_wall_collision():
            self.player_rect.x -= dx # Nếu chạm thì lùi lại

        # Di chuyển theo trục Y và check va chạm
        self.player_rect.y += dy
        if self.check_wall_collision():
            self.player_rect.y -= dy # Nếu chạm thì lùi lại

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Tính ô lưới dựa trên tâm của Player
                    grid_x = self.player_rect.centerx // TILE_SIZE
                    grid_y = self.player_rect.centery // TILE_SIZE
                    now = pygame.time.get_ticks()
                    self.bomb_queue.append({'x': grid_x, 'y': grid_y, 'timer': now + 2000})

    def check_wall_collision(self):
        """Duyệt qua các ô tường và check va chạm với Player Rect"""
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if self.map[r][c] == WALL:
                    wall_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.player_rect.colliderect(wall_rect):
                        return True
        return False

    def draw(self):
        self.screen.fill(BLACK)
        
        # 1. Vẽ Tường
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if self.map[r][c] == WALL:
                    pygame.draw.rect(self.screen, GRAY, (c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        # 2. Vẽ Bom
        for b in self.bomb_queue:
            pygame.draw.circle(self.screen, RED, (b['x']*TILE_SIZE + 20, b['y']*TILE_SIZE + 20), 15)

        # 3. Vẽ Player (Blue)
        pygame.draw.rect(self.screen, BLUE, self.player_rect)
        
        pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_input()
        game.draw()
        game.clock.tick(FPS)