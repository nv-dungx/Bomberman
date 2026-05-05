"""
main.py
-------
Điểm khởi chạy chính, quản lý Game Engine, vòng lặp sự kiện và điều phối các module.
"""
import pygame
import sys
import random
from collections import deque
from settings import *
from player import Player
from level_manager import LevelManager

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bomberman DSA - Module Refactored")
        self.clock = pygame.time.Clock()
        self.show_visualization = False 
        self.level = 1
        
        self.level_manager = LevelManager()
        self.load_level()

    def load_level(self):
        """Khởi tạo player và yêu cầu level_manager sinh map mới."""
        self.player = Player(TILE_SIZE + 5, TILE_SIZE + 5)
        self.bomb_queue = deque()         
        self.explosions = []
        self.level_manager.generate_level(self.level)

    def handle_input(self):
        """Bắt sự kiện phím điều hướng, đặt bom và xử lý Event Loop."""
        # 1. BẮT BUỘC PHẢI QUÉT EVENT CHO DÙ SỐNG HAY CHẾT
        for event in pygame.event.get():
            # Xử lý nút X đóng cửa sổ
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            # Xử lý khi đã Game Over (Bấm R để chơi lại)
            if self.player.is_dead:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    print("🔄 Chơi lại từ Level 1...")
                    self.level = 1
                    self.load_level()
                continue # Đã chết thì bỏ qua các nút bấm khác (SPACE, V...)

            # Xử lý các phím bấm 1 lần (SPACE, V) khi CÒN SỐNG
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    gx = self.player.rect.centerx // TILE_SIZE
                    gy = self.player.rect.centery // TILE_SIZE
                    can_place = all(not (b['x'] == gx and b['y'] == gy) for b in self.bomb_queue)
                    if can_place:
                        self.bomb_queue.append({
                            'x': gx, 'y': gy,
                            'timer': pygame.time.get_ticks() + 2000,
                        })
                elif event.key == pygame.K_v:
                    self.show_visualization = not self.show_visualization

        # 2. Xử lý phím đè (Di chuyển) - CHỈ CHẠY KHI CÒN SỐNG
        if self.player.is_dead: 
            return

        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:  dx = -self.player.current_speed
        if keys[pygame.K_RIGHT]: dx = self.player.current_speed
        if keys[pygame.K_UP]:    dy = -self.player.current_speed
        if keys[pygame.K_DOWN]:  dy = self.player.current_speed

        if dx != 0 or dy != 0:
            self.player.last_dx, self.player.last_dy = dx, dy
            
        self.player.move(dx, dy, self.level_manager.map)

    def handle_explosion(self, start_x, start_y):
        """Xử lý tính toán vùng nổ của bom."""
        now = pygame.time.get_ticks()
        explosion_queue = deque([(start_x, start_y)])

        while explosion_queue:
            bx, by = explosion_queue.popleft()
            for dx, dy in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]:
                for i in range(0 if (dx, dy) == (0, 0) else 1, self.player.explosion_range + 1):
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
                            if (nx, ny) != self.level_manager.door_pos and random.random() < 0.15:
                                self.level_manager.powerups[(nx, ny)] = random.choice(["SPEED", "RANGE", "SHIELD", "GHOST"])
                            break
                        if (dx, dy) == (0, 0): break

    def update(self):
        """Cập nhật frame game: bẫy, sát thương, logic quái."""
        if self.player.is_dead: return
        now = pygame.time.get_ticks()

        # 1. Update Lửa/Bom
        while self.bomb_queue and now >= self.bomb_queue[0]['timer']:
            b = self.bomb_queue.popleft()
            self.handle_explosion(b['x'], b['y'])
        self.explosions = [e for e in self.explosions if e['expiry'] > now]

        for e in self.explosions:
            exp_rect = pygame.Rect(e['x'] * TILE_SIZE, e['y'] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if self.player.rect.colliderect(exp_rect):
                self.player.take_damage(now)
            for enemy in self.level_manager.enemies[:]:
                if enemy.rect.colliderect(exp_rect):
                    self.level_manager.enemies.remove(enemy)

        # 2. Xử lý Môi trường vật lý
        px_grid = self.player.rect.centerx // TILE_SIZE
        py_grid = self.player.rect.centery // TILE_SIZE
        current_tile = self.level_manager.map[py_grid][px_grid]
        keys = pygame.key.get_pressed()

        # Trượt Băng
        on_ice = False
        for r in range(max(0, py_grid - 1), min(GRID_HEIGHT, py_grid + 2)):
            for c in range(max(0, px_grid - 1), min(GRID_WIDTH, px_grid + 2)):
                if self.level_manager.map[r][c] == TRAP_ICE:
                    ice_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.player.rect.colliderect(ice_rect):
                        on_ice = True
                        break
            if on_ice: break

        if on_ice and not any(keys[k] for k in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]):
            slide_x = self.player.current_speed if self.player.last_dx > 0 else (-self.player.current_speed if self.player.last_dx < 0 else 0)
            slide_y = self.player.current_speed if self.player.last_dy > 0 else (-self.player.current_speed if self.player.last_dy < 0 else 0)
            self.player.move(slide_x, slide_y, self.level_manager.map)

        # Băng chuyền
        if current_tile == CONVEYOR_LEFT:
            self.player.forced_move_queue.append((-2, 0))
        elif current_tile == CONVEYOR_RIGHT:
            self.player.forced_move_queue.append((2, 0))

        while self.player.forced_move_queue:
            fdx, fdy = self.player.forced_move_queue.popleft()
            self.player.move(fdx, fdy, self.level_manager.map)

        # Teleport
        teleports = self.level_manager.teleports
        if teleports and now > self.player.teleport_cooldown and (px_grid, py_grid) in teleports:
            other = (teleports[1] if (px_grid, py_grid) == teleports[0] else teleports[0])
            self.player.rect.center = (other[0] * TILE_SIZE + TILE_SIZE // 2, other[1] * TILE_SIZE + TILE_SIZE // 2)
            self.player.teleport_cooldown = now + 1000

        # 3. Điều kiện qua màn
        door_pos = self.level_manager.door_pos
        if door_pos and self.level_manager.map[door_pos[1]][door_pos[0]] == EMPTY:
            if len(self.level_manager.enemies) == 0 and (px_grid, py_grid) == door_pos:
                self.level += 1
                self.load_level()
                return

        # 4. Item
        self.player.update_items(now, current_tile)
        if (px_grid, py_grid) in self.level_manager.powerups:
            p_type = self.level_manager.powerups.pop((px_grid, py_grid))
            self.player.pick_up_item(p_type, now)

        # 5. AI Kẻ địch
        for enemy in self.level_manager.enemies:
            path = enemy.find_path(px_grid, py_grid, self.level_manager.map, self.bomb_queue, self.player.explosion_range, now)
            if path: enemy.move()
            if self.player.rect.colliderect(enemy.rect):
                self.player.take_damage(now)

    def draw(self):
        """Vẽ toàn bộ lên màn hình."""
        self.screen.fill(BLACK)
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                rect = (c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                tile = self.level_manager.map[r][c]

                if tile == WALL: pygame.draw.rect(self.screen, GRAY, rect)
                elif tile == SOFT_WALL:
                    color = (100, 50, 10) if self.player.is_ghost else (139, 69, 19)
                    pygame.draw.rect(self.screen, color, rect)
                elif tile == TRAP_ICE: pygame.draw.rect(self.screen, LIGHT_BLUE_ICE, rect)
                elif tile in [CONVEYOR_LEFT, CONVEYOR_RIGHT]:
                    pygame.draw.rect(self.screen, (50, 50, 50), rect)
                    arrow = "<" if tile == CONVEYOR_LEFT else ">"
                    font = pygame.font.SysFont("Arial", 20, bold=True)
                    self.screen.blit(font.render(arrow, True, WHITE), (c * TILE_SIZE + 15, r * TILE_SIZE + 8))
                elif tile == TRAP_TELEPORT:
                    pygame.draw.circle(self.screen, MAGENTA, (c * TILE_SIZE + 20, r * TILE_SIZE + 20), 12, 4)

        # Vẽ Cửa
        door_pos = self.level_manager.door_pos
        if door_pos and self.level_manager.map[door_pos[1]][door_pos[0]] == EMPTY:
            pygame.draw.rect(self.screen, GOLD, (door_pos[0] * TILE_SIZE, door_pos[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))

        # Hiển thị đường đi BFS (nếu bấm V)
        if self.show_visualization:
            for enemy in self.level_manager.enemies:
                for step in enemy.path:
                    pygame.draw.circle(self.screen, YELLOW, (step[0] * TILE_SIZE + 20, step[1] * TILE_SIZE + 20), 6)

        # Vẽ Vật phẩm
        for (gx, gy), p_type in self.level_manager.powerups.items():
            color = LIGHT_BLUE if p_type == "SPEED" else YELLOW if p_type == "RANGE" else CYAN if p_type == "SHIELD" else PURPLE
            pygame.draw.rect(self.screen, color, (gx * TILE_SIZE + 12, gy * TILE_SIZE + 12, 16, 16))

        # Vẽ Lửa và Bom
        for e in self.explosions:
            pygame.draw.rect(self.screen, ORANGE, (e['x'] * TILE_SIZE, e['y'] * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        for b in self.bomb_queue:
            pygame.draw.circle(self.screen, RED, (b['x'] * TILE_SIZE + 20, b['y'] * TILE_SIZE + 20), 15)

        # Vẽ Quái và Người chơi
        for enemy in self.level_manager.enemies:
            pygame.draw.rect(self.screen, GREEN, enemy.rect)
        self.player.draw(self.screen, pygame.time.get_ticks())

        # Vẽ UI
        font = pygame.font.SysFont("Arial", 24, bold=True)
        self.screen.blit(font.render(f"Level: {self.level}", True, WHITE), (SCREEN_WIDTH - 100, 10))

        if self.player.is_dead:
            font = pygame.font.SysFont("Arial", 72, bold=True)
            text = font.render("GAME OVER", True, RED)
            self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

        pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_input()
        game.update()
        game.draw()
        game.clock.tick(FPS)