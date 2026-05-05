"""
enemy.py
--------
Quản lý AI của kẻ địch với 3 cấp độ (Tiers) sử dụng tính Kế thừa (Inheritance) trong OOP.
- DumbEnemy (Tier 1): Dùng BFS thuần, không biết né bom.
- SmartEnemy (Tier 2): Dùng BFS + Flood-fill để né bom.
- EliteEnemy (Tier 3): Dùng A* + Flood-fill + Tính toán trọng số địa hình.
"""
import pygame
import heapq
from collections import deque
from settings import *

class Enemy:
    """Class Cha (Base Class) chứa các thuộc tính và kỹ năng sinh tồn cơ bản."""
    def __init__(self, grid_x, grid_y, speed, color):
        self.rect = pygame.Rect(grid_x * TILE_SIZE + 5, grid_y * TILE_SIZE + 5, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.speed = speed
        self.color = color
        self.path = []
        self.reaction_delay = 1200

    def check_collision(self, game_map):
        """Kiểm tra va chạm vật lý với tường cứng và tường mềm."""
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if game_map[r][c] in [WALL, SOFT_WALL]:
                    tile_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.rect.colliderect(tile_rect):
                        return True
        return False

    def move(self, game_map):
        """Di chuyển có check va chạm (Hitbox) để không bị xuyên tường khi cắt góc."""
        if not self.path: return
        next_step = self.path[0]
        target_x = next_step[0] * TILE_SIZE + (TILE_SIZE - PLAYER_WIDTH) // 2
        target_y = next_step[1] * TILE_SIZE + (TILE_SIZE - PLAYER_HEIGHT) // 2

        dx = target_x - self.rect.x
        dy = target_y - self.rect.y

        # Tách riêng X và Y để check va chạm độc lập (Giúp quái trượt dọc theo tường)
        if dx != 0:
            step_x = min(self.speed, abs(dx)) if dx > 0 else -min(self.speed, abs(dx))
            self.rect.x += step_x
            if self.check_collision(game_map):
                self.rect.x -= step_x # Đụng tường thì dội lại
        
        if dy != 0:
            step_y = min(self.speed, abs(dy)) if dy > 0 else -min(self.speed, abs(dy))
            self.rect.y += step_y
            if self.check_collision(game_map):
                self.rect.y -= step_y # Đụng tường thì dội lại

        # Nếu đã lọt vào tâm lưới (cho phép sai số nhỏ để tránh kẹt pixel)
        if abs(self.rect.x - target_x) <= self.speed and abs(self.rect.y - target_y) <= self.speed:
            self.rect.x = target_x
            self.rect.y = target_y
            self.path.pop(0)

    def get_danger_zones(self, bomb_queue, explosion_range, now, game_map):
        """Flood-fill: Tính toán các ô sẽ bị nổ để né tránh."""
        danger_zones = set()
        for b in bomb_queue:
            time_left = b['timer'] - now
            if time_left < self.reaction_delay:
                danger_zones.add((b['x'], b['y']))
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    for i in range(1, explosion_range + 1):
                        nx, ny = b['x'] + dx * i, b['y'] + dy * i
                        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                            if game_map[ny][nx] == WALL: break
                            danger_zones.add((nx, ny))
                            if game_map[ny][nx] == SOFT_WALL: break
        return danger_zones

    def bfs_to_safety(self, start, game_map, danger_zones):
        """BFS: Tìm ô an toàn GẦN NHẤT khi đang kẹt trong vùng nguy hiểm."""
        queue = deque([(start[0], start[1], [])])
        visited = {start}
        while queue:
            cx, cy, path = queue.popleft()
            if (cx, cy) not in danger_zones:
                return path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and (nx, ny) not in visited:
                    if game_map[ny][nx] not in [WALL, SOFT_WALL]:
                        visited.add((nx, ny))
                        queue.append((nx, ny, path + [(nx, ny)]))
        return []

    def find_path(self, player_x, player_y, game_map, bomb_queue, explosion_range, now):
        """Hàm ảo (Virtual function) sẽ được ghi đè bởi các class con."""
        raise NotImplementedError("Phải ghi đè hàm này ở class con")


class DumbEnemy(Enemy):
    """Tier 1: Quái Ngu. Chỉ biết lao đầu vào người chơi, đạp lên cả bom."""
    def __init__(self, grid_x, grid_y):
        # Tốc độ 1 (chậm), Màu Xanh Lá
        super().__init__(grid_x, grid_y, speed=1, color=(0, 255, 0))

    def find_path(self, player_x, player_y, game_map, bomb_queue, explosion_range, now):
        start = (self.rect.centerx // TILE_SIZE, self.rect.centery // TILE_SIZE)
        goal = (player_x, player_y)
        queue = deque([(start[0], start[1], [])])
        visited = {start}

        while queue:
            cx, cy, path = queue.popleft()
            if (cx, cy) == goal:
                self.path = path
                return self.path

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and (nx, ny) not in visited:
                    if game_map[ny][nx] not in [WALL, SOFT_WALL]:
                        visited.add((nx, ny))
                        queue.append((nx, ny, path + [(nx, ny)]))
        self.path = []
        return self.path


class SmartEnemy(Enemy):
    """Tier 2: Quái Tầm Trung. Biết né bom bằng Flood-fill nhưng không hiểu địa hình."""
    def __init__(self, grid_x, grid_y):
        # Tốc độ 2, Màu Cam
        super().__init__(grid_x, grid_y, speed=2, color=(255, 165, 0))

    def find_path(self, player_x, player_y, game_map, bomb_queue, explosion_range, now):
        start = (self.rect.centerx // TILE_SIZE, self.rect.centery // TILE_SIZE)
        goal = (player_x, player_y)
        danger_zones = self.get_danger_zones(bomb_queue, explosion_range, now, game_map)

        if start in danger_zones:
            self.path = self.bfs_to_safety(start, game_map, danger_zones)
            return self.path

        queue = deque([(start[0], start[1], [])])
        visited = {start}
        while queue:
            cx, cy, path = queue.popleft()
            if (cx, cy) == goal:
                self.path = path
                return self.path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and (nx, ny) not in visited:
                    # Né Tường và Né Vùng Bom Nổ
                    if game_map[ny][nx] not in [WALL, SOFT_WALL] and (nx, ny) not in danger_zones:
                        visited.add((nx, ny))
                        queue.append((nx, ny, path + [(nx, ny)]))
        self.path = []
        return self.path


class EliteEnemy(Enemy):
    """Tier 3: Quái Tinh Anh (Trùm). Dùng A* tính toán chi phí để đi đường khôn nhất."""
    def __init__(self, grid_x, grid_y):
        # Tốc độ 2, Màu Đỏ Thẫm, Phản xạ nhận diện bom cực nhanh (1500ms)
        super().__init__(grid_x, grid_y, speed=2, color=(200, 0, 0))
        self.reaction_delay = 1500

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_tile_weight(self, tile):
        if tile == EMPTY or tile == TRAP_TELEPORT: return 1
        elif tile == TRAP_ICE: return 2
        elif tile in [CONVEYOR_LEFT, CONVEYOR_RIGHT]: return 5
        return float('inf')

    def a_star_hunt(self, start, goal, game_map, danger_zones):
        open_set = []
        heapq.heappush(open_set, (0, 0, start))
        came_from = {}
        g_score = {start: 0}

        while open_set:
            _, current_g, current = heapq.heappop(open_set)

            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = current[0] + dx, current[1] + dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    tile = game_map[ny][nx]
                    weight = self.get_tile_weight(tile)

                    if weight == float('inf') or (nx, ny) in danger_zones:
                        continue

                    tentative_g_score = current_g + weight
                    if (nx, ny) not in g_score or tentative_g_score < g_score[(nx, ny)]:
                        came_from[(nx, ny)] = current
                        g_score[(nx, ny)] = tentative_g_score
                        f_score = tentative_g_score + self.heuristic((nx, ny), goal)
                        heapq.heappush(open_set, (f_score, tentative_g_score, (nx, ny)))
        return []

    def find_path(self, player_x, player_y, game_map, bomb_queue, explosion_range, now):
        start = (self.rect.centerx // TILE_SIZE, self.rect.centery // TILE_SIZE)
        goal = (player_x, player_y)
        danger_zones = self.get_danger_zones(bomb_queue, explosion_range, now, game_map)

        if start in danger_zones:
            self.path = self.bfs_to_safety(start, game_map, danger_zones)
        else:
            self.path = self.a_star_hunt(start, goal, game_map, danger_zones)
        return self.path