import pygame
from collections import deque
from settings import *

class Enemy:
    def __init__(self, x, y):
        self.grid_x = x
        self.grid_y = y
        self.rect = pygame.Rect(x * TILE_SIZE + 5, y * TILE_SIZE + 5, 30, 30)
        self.path = []

    def get_danger_zones(self, bomb_queue, explosion_range, game_map, now):
        """DSA: Flood-fill nhưng có thêm logic 'Phản xạ chậm'"""
        danger_zones = set()
        for bomb in bomb_queue:
            # 🧠 CƠ CHẾ NERF AI: Chỉ sợ bom khi thời gian nổ còn dưới 1200ms (1.2 giây)
            # Bom mới đặt (còn 2000ms) thì quái vẫn thản nhiên đi qua!
            if bomb['timer'] - now > 1200:
                continue

            bx, by = bomb['x'], bomb['y']
            danger_zones.add((bx, by))
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                for i in range(1, explosion_range + 1):
                    nx, ny = bx + dx * i, by + dy * i
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        if game_map[ny][nx] == WALL: break 
                        danger_zones.add((nx, ny))
                        if game_map[ny][nx] == SOFT_WALL: break 
        return danger_zones

    def find_path(self, target_gx, target_gy, game_map, bomb_queue, explosion_range, now):
        start = (self.grid_x, self.grid_y)
        # Bổ sung biến 'now' vào đây để tính toán
        danger_zones = self.get_danger_zones(bomb_queue, explosion_range, game_map, now)
        
        if start in danger_zones:
            return self.bfs_to_safety(start, danger_zones, game_map)
        
        return self.bfs_standard(start, (target_gx, target_gy), game_map, danger_zones)

    def bfs_to_safety(self, start, danger_zones, game_map):
        queue = deque([start])
        parent_map = {start: None}
        
        while queue:
            curr = queue.popleft()
            if curr not in danger_zones: 
                return self.reconstruct_path(parent_map, curr, start)
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = curr[0] + dx, curr[1] + dy
                if (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and
                    game_map[ny][nx] in [EMPTY, TRAP_TELEPORT, TRAP_ICE, CONVEYOR_LEFT, CONVEYOR_RIGHT] and 
                    (nx, ny) not in parent_map):
                    parent_map[(nx, ny)] = curr
                    queue.append((nx, ny))
        return []

    def bfs_standard(self, start, target, game_map, danger_zones):
        queue = deque([start])
        parent_map = {start: None}
        
        while queue:
            curr = queue.popleft()
            if curr == target:
                return self.reconstruct_path(parent_map, curr, start)
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = curr[0] + dx, curr[1] + dy
                if (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and
                    game_map[ny][nx] in [EMPTY, TRAP_TELEPORT, TRAP_ICE, CONVEYOR_LEFT, CONVEYOR_RIGHT] and 
                    (nx, ny) not in parent_map and (nx, ny) not in danger_zones): 
                    parent_map[(nx, ny)] = curr
                    queue.append((nx, ny))
        return []

    def reconstruct_path(self, parent_map, curr, start):
        path = []
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