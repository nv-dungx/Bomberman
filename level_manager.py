"""
level_manager.py
----------------
Quản lý việc sinh bản đồ, bẫy vật lý, vật phẩm rớt ra và tọa độ kẻ địch theo Level.
"""
import random
from settings import *
from enemy import DumbEnemy, SmartEnemy, EliteEnemy

class LevelManager:
    def __init__(self):
        self.map = []
        self.door_pos = None
        self.teleports = []
        self.enemies = []
        self.powerups = {}
        
    def generate_level(self, level_num):
        """Thuật toán tạo toàn bộ cấu trúc màn chơi."""
        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.teleports = []
        self.door_pos = None
        self.enemies = []
        self.powerups = {}
        
        empty_spaces = []
        soft_walls_list = []

        # 1. Sinh Tường & Băng Chuyền
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if r == 0 or r == GRID_HEIGHT - 1 or c == 0 or c == GRID_WIDTH - 1:
                    self.map[r][c] = WALL
                elif r % 2 == 0 and c % 2 == 0:
                    self.map[r][c] = WALL
                else:
                    # Chừa một góc nhỏ (3x3) để tuyệt đối không sinh tường/bẫy đè lên người chơi
                    if r <= 2 and c <= 2:
                        continue
                    
                    rand = random.random()
                    if rand < 0.25:
                        self.map[r][c] = SOFT_WALL
                        soft_walls_list.append((c, r))
                    elif rand < 0.28:
                        self.map[r][c] = CONVEYOR_LEFT
                    elif rand < 0.31:
                        self.map[r][c] = CONVEYOR_RIGHT
                    else:
                        empty_spaces.append((c, r))

        # 2. Sinh đường trượt băng (Cụm liên tiếp)
        num_ice_clusters = min(level_num + 1, 6)
        for _ in range(num_ice_clusters):
            if not empty_spaces: break
            length = random.choice([2, 3, 4])
            dx, dy = random.choice([(1, 0), (0, 1)])
            random.shuffle(empty_spaces) 
            
            for start_x, start_y in empty_spaces:
                valid_cluster = True
                cluster_cells = []
                for i in range(length):
                    nx, ny = start_x + dx * i, start_y + dy * i
                    if (nx, ny) in empty_spaces and not (nx <= 2 and ny <= 2):
                        cluster_cells.append((nx, ny))
                    else:
                        valid_cluster = False
                        break
                        
                if valid_cluster:
                    for cx, cy in cluster_cells:
                        self.map[cy][cx] = TRAP_ICE
                        empty_spaces.remove((cx, cy))
                    break

        # 3. Sinh Cổng Teleport
        if len(empty_spaces) >= 2:
            self.teleports = random.sample(empty_spaces, 2)
            for tx, ty in self.teleports:
                self.map[ty][tx] = TRAP_TELEPORT
                empty_spaces.remove((tx, ty))

        # 4. Giấu Cửa & Sinh Quái theo cấp độ (Có chống Spawn Kill)
        if soft_walls_list:
            self.door_pos = random.choice(soft_walls_list)

        num_enemies = 2 + level_num
        safe_spawn_spaces = [
            (x, y) for (x, y) in empty_spaces 
            if abs(x - 1) + abs(y - 1) >= 8
        ]
        target_spaces = safe_spawn_spaces if len(safe_spawn_spaces) >= num_enemies else empty_spaces

        if len(target_spaces) >= num_enemies:
            enemy_spawns = random.sample(target_spaces, num_enemies)
            for i, (ex, ey) in enumerate(enemy_spawns):
                # Level 1-2: Quái Ngu. Level 3-4: Trộn Ngu và Khôn. Level 5: Toàn Tinh Anh.
                if level_num <= 2:
                    self.enemies.append(DumbEnemy(ex, ey))
                elif level_num <= 4:
                    if i % 2 == 0: self.enemies.append(SmartEnemy(ex, ey))
                    else: self.enemies.append(DumbEnemy(ex, ey))
                else:
                    if i % 2 == 0: self.enemies.append(EliteEnemy(ex, ey))
                    else: self.enemies.append(SmartEnemy(ex, ey))
    def generate_pvp_level(self):
        """Tạo bản đồ đối kháng: Không quái, không cửa, 2 vùng an toàn đối xứng."""
        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.teleports = []
        self.door_pos = None
        self.enemies = []
        self.powerups = {}
        
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if r == 0 or r == GRID_HEIGHT - 1 or c == 0 or c == GRID_WIDTH - 1:
                    self.map[r][c] = WALL
                elif r % 2 == 0 and c % 2 == 0:
                    self.map[r][c] = WALL
                else:
                    # Vùng an toàn cho Player 1 (Góc trên trái)
                    if r <= 2 and c <= 2:
                        continue
                    # Vùng an toàn cho Player 2 (Góc dưới phải)
                    if r >= GRID_HEIGHT - 3 and c >= GRID_WIDTH - 3:
                        continue
                    
                    rand = random.random()
                    if rand < 0.40: # Rải nhiều tường mềm hơn Campaign để anh em đào hầm
                        self.map[r][c] = SOFT_WALL
