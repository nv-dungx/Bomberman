"""
level_manager.py
----------------
Quản lý việc sinh bản đồ, bẫy vật lý, vật phẩm rớt ra và tọa độ kẻ địch theo Level.
"""
import random
from settings import *
from enemy import Enemy

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

        # 4. Giấu Cửa & Sinh Quái (Có chống Spawn Kill)
        if soft_walls_list:
            self.door_pos = random.choice(soft_walls_list)

        num_enemies = 2 + level_num
        
        # Lọc ra các ô trống thỏa mãn Khoảng cách Manhattan >= 6 so với ô (1, 1)
        safe_spawn_spaces = [
            (x, y) for (x, y) in empty_spaces 
            if abs(x - 1) + abs(y - 1) >= 6
        ]
        
        # Nếu vì lý do nào đó map quá kẹt không đủ ô an toàn, fallback về dùng mọi ô trống
        target_spaces = safe_spawn_spaces if len(safe_spawn_spaces) >= num_enemies else empty_spaces

        if len(target_spaces) >= num_enemies:
            enemy_spawns = random.sample(target_spaces, num_enemies)
            for ex, ey in enemy_spawns:
                self.enemies.append(Enemy(ex, ey))