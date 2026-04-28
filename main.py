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
                # 👾 DSA: AI nhận diện tất cả bẫy là đường đi được
                if (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and
                    game_map[ny][nx] in [EMPTY, TRAP_TELEPORT, TRAP_ICE, CONVEYOR_LEFT, CONVEYOR_RIGHT] and 
                    (nx, ny) not in parent_map):
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
        pygame.display.set_caption("Bomberman DSA - Traps & Physics")
        self.clock = pygame.time.Clock()
        
        self.player_rect = pygame.Rect(TILE_SIZE + 5, TILE_SIZE + 5, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.player_current_speed = PLAYER_SPEED
        self.last_dx, self.last_dy = 0, 0 # Lưu hướng di chuyển để xử lý trượt băng
        self.is_dead = False
        
        # 🛡️ Quản lý Buff
        self.shields = []             
        self.invulnerable_until = 0   
        self.is_ghost = False          
        
        self.bomb_queue = deque()
        self.forced_move_queue = deque() # ➡️ DSA: Queue xử lý push event của Băng chuyền
        self.explosions = []
        self.powerups = {}        
        self.active_effects = []
        self.explosion_range = 2
        self.show_visualization = False 
        
        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.teleports = []            
        self.teleport_cooldown = 0     
        
        self.setup_walls()
        
        self.enemies = [
            Enemy(GRID_WIDTH - 2, GRID_HEIGHT - 2),
            Enemy(GRID_WIDTH - 2, 1),
            Enemy(1, GRID_HEIGHT - 2)
        ]

    def setup_walls(self):
        empty_spaces = []
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if r == 0 or r == GRID_HEIGHT-1 or c == 0 or c == GRID_WIDTH-1:
                    self.map[r][c] = WALL
                elif r % 2 == 0 and c % 2 == 0:
                    self.map[r][c] = WALL
                else:
                    if r <= 2 and c <= 2: continue
                    
                    # Phân bổ xác suất sinh Bẫy và Tường mềm
                    rand = random.random()
                    if rand < 0.3: 
                        self.map[r][c] = SOFT_WALL
                    elif rand < 0.35: 
                        self.map[r][c] = TRAP_ICE
                    elif rand < 0.37: 
                        self.map[r][c] = CONVEYOR_LEFT
                    elif rand < 0.39: 
                        self.map[r][c] = CONVEYOR_RIGHT
                    else:
                        empty_spaces.append((c, r)) 
                        
        # 🌀 Sinh ra 2 cổng Teleport
        if len(empty_spaces) >= 2:
            self.teleports = random.sample(empty_spaces, 2)
            for tx, ty in self.teleports:
                self.map[ty][tx] = TRAP_TELEPORT

    def move_player(self, dx, dy):
        """Hàm helper xử lý di chuyển và va chạm"""
        self.player_rect.x += dx
        if self.check_collision(): self.player_rect.x -= dx
        self.player_rect.y += dy
        if self.check_collision(): self.player_rect.y -= dy

    def handle_input(self):
        if self.is_dead: return 
        
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:  dx = -self.player_current_speed
        if keys[pygame.K_RIGHT]: dx = self.player_current_speed
        if keys[pygame.K_UP]:    dy = -self.player_current_speed
        if keys[pygame.K_DOWN]:  dy = self.player_current_speed

        # Lưu lại hướng đi cuối cùng nếu có bấm phím (Dùng cho Ô Băng)
        if dx != 0 or dy != 0:
            self.last_dx, self.last_dy = dx, dy

        self.move_player(dx, dy)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    gx, gy = self.player_rect.centerx // TILE_SIZE, self.player_rect.centery // TILE_SIZE
                    can_place = True
                    for bomb in self.bomb_queue:
                        if bomb['x'] == gx and bomb['y'] == gy: can_place = False
                    if can_place:
                        self.bomb_queue.append({'x': gx, 'y': gy, 'timer': pygame.time.get_ticks() + 2000})
                
                elif event.key == pygame.K_v:
                    self.show_visualization = not self.show_visualization

    def check_collision(self):
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                tile = self.map[r][c]
                if tile == WALL or (tile == SOFT_WALL and not self.is_ghost):
                    if self.player_rect.colliderect(pygame.Rect(c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)):
                        return True
        return False

    def handle_explosion(self, start_x, start_y):
        now = pygame.time.get_ticks()
        explosion_queue = deque([(start_x, start_y)])
        
        while explosion_queue:
            bx, by = explosion_queue.popleft()
            for dx, dy in [(0,0), (0,1), (0,-1), (1,0), (-1,0)]:
                for i in range(0 if (dx,dy)==(0,0) else 1, self.explosion_range + 1):
                    nx, ny = bx + dx*i, by + dy*i
                    
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        tile = self.map[ny][nx]
                        if tile == WALL: break
                        
                        self.explosions.append({'x': nx, 'y': ny, 'expiry': now + 500})
                        
                        for enemy in self.enemies[:]:
                            if enemy.grid_x == nx and enemy.grid_y == ny:
                                self.enemies.remove(enemy)

                        for bomb in list(self.bomb_queue):
                            if bomb['x'] == nx and bomb['y'] == ny:
                                self.bomb_queue.remove(bomb)       
                                explosion_queue.append((nx, ny))   

                        if tile == SOFT_WALL:
                            self.map[ny][nx] = EMPTY
                            if random.random() < 0.15:
                                self.powerups[(nx, ny)] = random.choice(["SPEED", "RANGE", "SHIELD", "GHOST"])
                            break 
                        if (dx, dy) == (0,0): break 

    def take_damage(self, now):
        if now < self.invulnerable_until: return 
            
        if self.shields:
            self.shields.pop() 
            self.invulnerable_until = now + 1500 
            print(f"🛡️ Bể Khiên! Còn {len(self.shields)} lớp.")
        else:
            self.is_dead = True
            print("💥 BẠN ĐÃ CHẾT!")

    def update(self):
        if self.is_dead: return 
        now = pygame.time.get_ticks()
        
        while self.bomb_queue and now >= self.bomb_queue[0]['timer']:
            b = self.bomb_queue.popleft()
            self.handle_explosion(b['x'], b['y'])
            
        self.explosions = [e for e in self.explosions if e['expiry'] > now]

        # 💥 [ĐÃ FIX]: Player chết nếu dẫm vào lửa bom
        for e in self.explosions:
            exp_rect = pygame.Rect(e['x'] * TILE_SIZE, e['y'] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if self.player_rect.colliderect(exp_rect):
                self.take_damage(now)

        # 🧊 & ➡️ XỬ LÝ BẪY TRÊN BẢN ĐỒ
        px_grid, py_grid = self.player_rect.centerx // TILE_SIZE, self.player_rect.centery // TILE_SIZE
        current_tile = self.map[py_grid][px_grid]
        keys = pygame.key.get_pressed()

        # Logic Ô Băng: Trượt tiếp nếu không bấm phím
        if current_tile == TRAP_ICE:
            if not (keys[pygame.K_LEFT] or keys[pygame.K_RIGHT] or keys[pygame.K_UP] or keys[pygame.K_DOWN]):
                self.move_player(self.last_dx * 0.8, self.last_dy * 0.8)

        # Logic Băng Chuyền: Đưa lực đẩy vào Queue
        if current_tile == CONVEYOR_LEFT:
            self.forced_move_queue.append((-2, 0))
        elif current_tile == CONVEYOR_RIGHT:
            self.forced_move_queue.append((2, 0))

        # Áp dụng lực đẩy từ Queue
        while self.forced_move_queue:
            fdx, fdy = self.forced_move_queue.popleft()
            self.move_player(fdx, fdy)

        # 🌀 LOGIC TELEPORT
        if self.teleports and now > self.teleport_cooldown:
            if (px_grid, py_grid) in self.teleports:
                other_portal = self.teleports[1] if (px_grid, py_grid) == self.teleports[0] else self.teleports[0]
                self.player_rect.x = other_portal[0] * TILE_SIZE + 5
                self.player_rect.y = other_portal[1] * TILE_SIZE + 5
                self.teleport_cooldown = now + 1000 
                print("🌀 Dịch chuyển tức thời!")

        # DSA: Min-Heap
        while self.active_effects and self.active_effects[0][0] <= now:
            _, effect = heapq.heappop(self.active_effects)
            if effect == "RESET_SPEED": self.player_current_speed = PLAYER_SPEED
            if effect == "RESET_RANGE": self.explosion_range = 2
            if effect == "RESET_GHOST": 
                self.is_ghost = False
                print("👻 Hết chế độ GHOST!")
                if self.map[py_grid][px_grid] == SOFT_WALL:
                    self.invulnerable_until = 0 
                    self.take_damage(now)
                    print("💀 Bị kẹt chết trong tường!")

        # 🎁 NHẶT ITEM
        if (px_grid, py_grid) in self.powerups:
            p_type = self.powerups.pop((px_grid, py_grid))
            if p_type == "SPEED":
                self.player_current_speed = 5
                heapq.heappush(self.active_effects, (now + 5000, "RESET_SPEED"))
            elif p_type == "RANGE":
                self.explosion_range = 4
                heapq.heappush(self.active_effects, (now + 7000, "RESET_RANGE"))
            elif p_type == "SHIELD":
                self.shields.append("SHIELD_LAYER")
            elif p_type == "GHOST":
                self.is_ghost = True
                heapq.heappush(self.active_effects, (now + 8000, "RESET_GHOST"))
                print("👻 Chế độ GHOST (8 giây)!")

        # 👾 ENEMY AI & VA CHẠM
        for enemy in self.enemies:
            path = enemy.find_path(px_grid, py_grid, self.map)
            if path: enemy.move()
            if self.player_rect.colliderect(enemy.rect): 
                self.take_damage(now)

    def draw(self):
        self.screen.fill(BLACK)
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                rect = (c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                tile = self.map[r][c]
                
                if tile == WALL: 
                    pygame.draw.rect(self.screen, GRAY, rect)
                elif tile == SOFT_WALL: 
                    color = (139, 69, 19) if not self.is_ghost else (100, 50, 10)
                    pygame.draw.rect(self.screen, color, rect)
                elif tile == TRAP_ICE:
                    pygame.draw.rect(self.screen, LIGHT_BLUE_ICE, rect)
                elif tile in [CONVEYOR_LEFT, CONVEYOR_RIGHT]:
                    pygame.draw.rect(self.screen, DARK_GRAY, rect)
                    # Vẽ mũi tên định hướng cho Băng chuyền
                    arrow = "<" if tile == CONVEYOR_LEFT else ">"
                    font = pygame.font.SysFont("Arial", 20, bold=True)
                    text = font.render(arrow, True, WHITE)
                    self.screen.blit(text, (c*TILE_SIZE + 15, r*TILE_SIZE + 8))
                elif tile == TRAP_TELEPORT:
                    pygame.draw.circle(self.screen, MAGENTA, (c*TILE_SIZE + 20, r*TILE_SIZE + 20), 12, 4)
        
        if self.show_visualization:
            for enemy in self.enemies:
                for step in enemy.path:
                    center_x = step[0] * TILE_SIZE + TILE_SIZE // 2
                    center_y = step[1] * TILE_SIZE + TILE_SIZE // 2
                    pygame.draw.circle(self.screen, YELLOW, (center_x, center_y), 6)

        for (gx, gy), p_type in self.powerups.items():
            if p_type == "SPEED": color = LIGHT_BLUE
            elif p_type == "RANGE": color = YELLOW
            elif p_type == "SHIELD": color = CYAN 
            else: color = PURPLE 
            pygame.draw.rect(self.screen, color, (gx*TILE_SIZE+12, gy*TILE_SIZE+12, 16, 16))

        for e in self.explosions:
            pygame.draw.rect(self.screen, ORANGE, (e['x']*TILE_SIZE, e['y']*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        for b in self.bomb_queue:
            pygame.draw.circle(self.screen, RED, (b['x']*TILE_SIZE + 20, b['y']*TILE_SIZE + 20), 15)

        now = pygame.time.get_ticks()
        is_invulnerable = now < self.invulnerable_until
        
        if not self.is_dead:
            if not is_invulnerable or (now // 100) % 2 == 0:
                player_color = PURPLE if self.is_ghost else BLUE
                pygame.draw.rect(self.screen, player_color, self.player_rect)
            
            if self.shields:
                thickness = len(self.shields) * 2
                pygame.draw.circle(self.screen, CYAN, self.player_rect.center, TILE_SIZE//2 + 4, thickness)

        for enemy in self.enemies:
            pygame.draw.rect(self.screen, GREEN, enemy.rect)
            
        if self.is_dead:
            font = pygame.font.SysFont("Arial", 72, bold=True)
            text = font.render("GAME OVER", True, RED)
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(text, text_rect)
            
        pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_input(); game.update(); game.draw()
        game.clock.tick(FPS)