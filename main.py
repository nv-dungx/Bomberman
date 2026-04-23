import pygame
import sys
import heapq
from collections import deque
from settings import *

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bomberman DSA Project")
        self.clock = pygame.time.Clock()
        
        self.bomb_queue = deque()
        self.active_effects = [] 
        self.player_pos = [1, 1]

        # 1. Khởi tạo map toàn ô trống
        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

        # 2. Tạo tường bao quanh (Đóng kín 4 cạnh)
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if r == 0 or r == GRID_HEIGHT - 1 or c == 0 or c == GRID_WIDTH - 1:
                    self.map[r][c] = WALL
                
                # Bonus: Tạo các cột trụ cứng ở giữa (đặc trưng của Bomberman)
                elif r % 2 == 0 and c % 2 == 0:
                    self.map[r][c] = WALL

    def handle_input(self):
        keys = pygame.key.get_pressed()
        # Di chuyển cơ bản (Tuần 1)
        if keys[pygame.K_LEFT]: self.player_pos[0] -= 0.1
        if keys[pygame.K_RIGHT]: self.player_pos[0] += 0.1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Đặt bom: Đưa vào Queue
                    now = pygame.time.get_ticks()
                    self.bomb_queue.append({'x': round(self.player_pos[0]), 
                                          'y': round(self.player_pos[1]), 
                                          'timer': now + 2000})
                if event.key == pygame.K_p: # Giả lập ăn Power-up (Tuần 2)
                    now = pygame.time.get_ticks()
                    heapq.heappush(self.active_effects, (now + 5000, "SPEED_BOOST"))
                    print("Đã ăn Speed Boost! Hết hạn sau 5s.")

    def update(self):
        now = pygame.time.get_ticks()
        
        # DSA: Check bom nổ (Queue)
        while self.bomb_queue and now >= self.bomb_queue[0]['timer']:
            b = self.bomb_queue.popleft()
            print(f"BÙM tại {b['x']}, {b['y']}")

        # DSA: Check Power-up hết hạn (Min-Heap)
        while self.active_effects and self.active_effects[0][0] <= now:
            expiry, effect = heapq.heappop(self.active_effects)
            print(f"Hiệu ứng {effect} đã hết thời gian!")

    def draw(self):
        self.screen.fill(BLACK)
        # Vẽ tường
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if self.map[r][c] == WALL:
                    pygame.draw.rect(self.screen, GRAY, (c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        # Vẽ Bom
        for b in self.bomb_queue:
            pygame.draw.circle(self.screen, RED, (b['x']*TILE_SIZE + 20, b['y']*TILE_SIZE + 20), 15)
            
        # Vẽ Player
        pygame.draw.rect(self.screen, BLUE, (self.player_pos[0]*TILE_SIZE, self.player_pos[1]*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_input()
        game.update()
        game.draw()
        game.clock.tick(FPS)