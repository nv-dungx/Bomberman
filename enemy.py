"""
enemy.py
Module định nghĩa các lớp AI kẻ địch cho game Bomberman.

Module cung cấp lớp nền :class:`Enemy` và ba tier con:

- :class:`DumbEnemy`  — Tier 1: BFS thuần, không né bom.
- :class:`SmartEnemy` — Tier 2: BFS + flood-fill né bom.
- :class:`EliteEnemy` — Tier 3: A* có trọng số + flood-fill né bom nhanh hơn.

Hệ thống phân cấp cho phép mở rộng thêm tier mới bằng cách kế thừa
:class:`Enemy` và ghi đè :meth:`Enemy.find_path`.
"""
import pygame
import random
import heapq
from collections import deque
from settings import *
from asset_loader import AssetLoader


class Enemy:
    """Lớp nền đại diện cho kẻ địch trong game Bomberman.

    Cung cấp các hành vi chung: di chuyển có va chạm, tính vùng nguy hiểm
    (flood-fill), thoát vùng nguy hiểm (BFS an toàn). Các lớp con phải
    ghi đè :meth:`find_path` để triển khai thuật toán tìm đường riêng.

    Attributes:
        rect (pygame.Rect): Hình chữ nhật va chạm trong không gian pixel.
        speed (int): Số pixel di chuyển tối đa mỗi frame.
        color (tuple[int, int, int]): Màu RGB dùng khi vẽ kẻ địch.
        path (list[tuple[int, int]]): Danh sách ô lưới ``(grid_x, grid_y)``
            tạo thành đường đi hiện tại; ô đầu tiên là bước kế tiếp.
        reaction_delay (int): Ngưỡng thời gian còn lại của bom (ms) để kẻ
            địch bắt đầu coi bom là nguy hiểm. Mặc định là 1200 ms (cơ chế
            "phản xạ chậm" để cân bằng độ khó).
    """

    def __init__(self, grid_x: int, grid_y: int, speed: int, color: tuple, enemy_model: str = "enemy_dumb"):
        """Khởi tạo kẻ địch tại ô lưới (grid_x, grid_y) và nạp hoạt ảnh.

        Args:
            grid_x (int): Tọa độ cột trên lưới.
            grid_y (int): Tọa độ hàng trên lưới.
            speed (int): Tốc độ di chuyển (pixel/frame).
            color (tuple[int, int, int]): Màu RGB để vẽ (dùng làm fallback).
            enemy_model (str): Tên file spritesheet trong assets/images/.
        """
        self.rect = pygame.Rect(
            grid_x * TILE_SIZE + 5,
            grid_y * TILE_SIZE + 5,
            PLAYER_WIDTH, PLAYER_HEIGHT,
        )
        self.speed = speed
        self.color = color
        self.path: list[tuple[int, int]] = []
        self.reaction_delay = 1200

        # --- Hệ thống hoạt ảnh ---
        self.direction = "down"
        self.frame_index = 0
        self.animation_timer = 0
        self.is_moving = False
        
        # Lưu tọa độ cũ để tự động suy ra hướng đi
        self.last_x = self.rect.x
        self.last_y = self.rect.y
        self.slide_dx = 0
        self.slide_dy = 0
        self.move_frac_x = 0
        self.move_frac_y = 0
        self.teleport_cooldown = 0
        self.post_explosion_wait_until = 0

        # Nạp dải ảnh 9 frames
        frames = AssetLoader.load_sprite_sheet(f"{enemy_model}.png", 30, 30, 9)
        if frames and len(frames) >= 9:
            self.frames_down = frames[0:3]
            self.frames_right = frames[3:6]
            self.frames_up = frames[6:9]
            self.frames_left = [pygame.transform.flip(f, True, False) for f in self.frames_right]
        else:
            # Fallback nếu lỗi ảnh
            surf = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT))
            surf.fill(self.color)
            self.frames_down = self.frames_up = self.frames_left = self.frames_right = [surf] * 3

    def check_collision(self, game_map: list[list[int]]) -> bool:
        """Kiểm tra va chạm pixel-perfect giữa ``rect`` và tường.

        Duyệt toàn bộ bản đồ; kẻ địch bị chặn bởi cả ``WALL`` lẫn
        ``SOFT_WALL`` (không có khả năng xuyên tường mềm).

        Args:
            game_map (list[list[int]]): Bản đồ 2D dùng hằng số tile.

        Returns:
            bool: ``True`` nếu ``rect`` đang chồng lên ô tường.
        """
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if game_map[r][c] in [WALL, SOFT_WALL]:
                    tile_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.rect.colliderect(tile_rect):
                        return True
        return False

    def on_explosion_started(self, now: int) -> None:
        """Hook cho enemy phản ứng khi một vụ nổ vừa bắt đầu."""
        pass

    def can_move(self, now: int) -> bool:
        """True nếu enemy được phép di chuyển trong frame hiện tại."""
        return now >= self.post_explosion_wait_until

    def consume_subpixel_step(self, axis: str, delta: float) -> int:
        """Tích lũy phần lẻ để tốc độ float như 1.2 không bị pygame.Rect cắt mất."""
        attr = "move_frac_x" if axis == "x" else "move_frac_y"
        total = getattr(self, attr) + delta
        step = int(total)
        setattr(self, attr, total - step)
        return step

    def move(self, game_map: list[list[int]], speed_multiplier: float = 1.0) -> tuple[float, float]:
        """Di chuyển kẻ địch từng bước theo ``self.path``, có kiểm tra va chạm.

        Mỗi frame, kẻ địch tiến đến tọa độ pixel của ô đầu tiên trong
        ``self.path`` với tốc độ ``speed``. Trục X và Y được xử lý độc lập
        để kẻ địch có thể "trượt dọc theo tường" thay vì bị kẹt cứng.

        Khi ``rect`` đến đủ gần tâm ô đích (sai số ≤ ``speed``), tọa độ
        được snap vào đúng tâm và ô đó bị xóa khỏi ``self.path``.

        Không làm gì nếu ``self.path`` rỗng.

        Args:
            game_map (list[list[int]]): Bản đồ 2D dùng để kiểm tra va chạm.
        """
        if not self.path:
            return (0, 0)
        next_step = self.path[0]
        target_x = next_step[0] * TILE_SIZE + (TILE_SIZE - PLAYER_WIDTH) // 2
        target_y = next_step[1] * TILE_SIZE + (TILE_SIZE - PLAYER_HEIGHT) // 2
        move_speed = max(1, self.speed * speed_multiplier)
        moved_x = 0
        moved_y = 0

        dx = target_x - self.rect.x
        dy = target_y - self.rect.y

        if dx != 0:
            desired_x = min(move_speed, abs(dx)) if dx > 0 else -min(move_speed, abs(dx))
            step_x = self.consume_subpixel_step("x", desired_x)
            self.rect.x += step_x
            if self.check_collision(game_map):
                self.rect.x -= step_x
                self.move_frac_x = 0
            else:
                moved_x = desired_x if step_x else 0

        if dy != 0:
            desired_y = min(move_speed, abs(dy)) if dy > 0 else -min(move_speed, abs(dy))
            step_y = self.consume_subpixel_step("y", desired_y)
            self.rect.y += step_y
            if self.check_collision(game_map):
                self.rect.y -= step_y
                self.move_frac_y = 0
            else:
                moved_y = desired_y if step_y else 0

        if abs(self.rect.x - target_x) <= move_speed and abs(self.rect.y - target_y) <= move_speed:
            self.rect.x = target_x
            self.rect.y = target_y
            self.path.pop(0)
            moved_x = 0
            moved_y = 0

        return (moved_x, moved_y)

    def draw(self, screen: pygame.Surface, now: int) -> None:
        """Tính toán hướng đi và vẽ hoạt ảnh kẻ địch lên màn hình."""
        # 1. Tính độ chênh lệch tọa độ để biết đang đi hướng nào
        dx = self.rect.x - self.last_x
        dy = self.rect.y - self.last_y
        
        if dx != 0 or dy != 0:
            self.is_moving = True
            if dx > 0: self.direction = "right"
            elif dx < 0: self.direction = "left"
            elif dy > 0: self.direction = "down"
            elif dy < 0: self.direction = "up"
        else:
            self.is_moving = False

        # Cập nhật lại tọa độ cũ cho frame tiếp theo
        self.last_x = self.rect.x
        self.last_y = self.rect.y

        # 2. Cập nhật frame hoạt ảnh
        if self.is_moving:
            if now - self.animation_timer > 100:  # Đổi frame mỗi 100ms
                self.frame_index = (self.frame_index + 1) % 3
                self.animation_timer = now
        else:
            self.frame_index = 0  # Đứng im dùng frame số 0

        # 3. Lấy ảnh theo hướng và vẽ
        if self.direction == "down": frameset = self.frames_down
        elif self.direction == "up": frameset = self.frames_up
        elif self.direction == "right": frameset = self.frames_right
        else: frameset = self.frames_left
        
        screen.blit(frameset[self.frame_index], self.rect)

    def get_danger_zones(
        self,
        bomb_queue: list[dict],
        explosion_range: int,
        now: int,
        game_map: list[list[int]],
    ) -> set[tuple[int, int]]:
        """Tính tập hợp ô lưới nằm trong vùng nguy hiểm của bom (flood-fill).

        Chỉ tính những quả bom có thời gian còn lại nhỏ hơn ``reaction_delay``
        (cơ chế phản xạ chậm). Sóng nổ dừng tại ``WALL`` và ``SOFT_WALL``
        giống logic nổ thực tế.

        Args:
            bomb_queue (list[dict]): Danh sách bom đang hoạt động. Mỗi phần
                tử là dict với key ``'x'``, ``'y'``, ``'timer'`` (ms nổ).
            explosion_range (int): Tầm nổ tối đa (số ô mỗi hướng).
            now (int): Thời điểm hiện tại (ms).
            game_map (list[list[int]]): Bản đồ 2D.

        Returns:
            set[tuple[int, int]]: Tập hợp tọa độ ``(grid_x, grid_y)`` nguy hiểm.
        """
        danger_zones: set[tuple[int, int]] = set()
        for b in bomb_queue:
            time_left = b['timer'] - now
            if time_left < self.reaction_delay:
                danger_zones.add((b['x'], b['y']))
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    for i in range(1, explosion_range + 1):
                        nx, ny = b['x'] + dx * i, b['y'] + dy * i
                        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                            if game_map[ny][nx] == WALL:
                                break
                            danger_zones.add((nx, ny))
                            if game_map[ny][nx] == SOFT_WALL:
                                break
        return danger_zones

    def rect_at_grid(self, grid_x: int, grid_y: int) -> pygame.Rect:
        """Tạo hitbox enemy khi đứng gọn ở một ô grid."""
        return pygame.Rect(
            grid_x * TILE_SIZE + (TILE_SIZE - PLAYER_WIDTH) // 2,
            grid_y * TILE_SIZE + (TILE_SIZE - PLAYER_HEIGHT) // 2,
            PLAYER_WIDTH,
            PLAYER_HEIGHT,
        )

    def rect_intersects_danger(
        self,
        rect: pygame.Rect,
        danger_zones: set[tuple[int, int]],
    ) -> bool:
        """Kiểm tra toàn bộ thân enemy có chạm vùng nổ không."""
        for danger_x, danger_y in danger_zones:
            danger_rect = pygame.Rect(
                danger_x * TILE_SIZE,
                danger_y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE,
            )
            if rect.colliderect(danger_rect):
                return True
        return False

    def body_in_danger(self, danger_zones: set[tuple[int, int]]) -> bool:
        """True nếu hitbox hiện tại của enemy còn dính vùng nổ."""
        return self.rect_intersects_danger(self.rect, danger_zones)

    def grid_body_safe(
        self,
        grid_pos: tuple[int, int],
        danger_zones: set[tuple[int, int]],
    ) -> bool:
        """True nếu enemy đứng ở ô này thì toàn bộ thân nằm ngoài vùng nổ."""
        return not self.rect_intersects_danger(
            self.rect_at_grid(grid_pos[0], grid_pos[1]),
            danger_zones,
        )

    def bfs_to_safety(
        self,
        start: tuple[int, int],
        game_map: list[list[int]],
        danger_zones: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        """Tìm đường đến ô an toàn gần nhất bằng BFS.

        Duyệt BFS từ ``start`` theo 4 hướng cho đến khi tìm được ô đầu tiên
        nằm ngoài ``danger_zones``. Chỉ đi qua các ô không phải ``WALL``
        hoặc ``SOFT_WALL``.

        Args:
            start (tuple[int, int]): Vị trí xuất phát ``(grid_x, grid_y)``.
            game_map (list[list[int]]): Bản đồ 2D.
            danger_zones (set[tuple[int, int]]): Tập hợp ô cần thoát khỏi.

        Returns:
            list[tuple[int, int]]: Danh sách ô lưới từ bước kế tiếp đến ô
            an toàn đầu tiên. Trả về ``[]`` nếu không tìm được lối thoát.
        """
        if self.body_in_danger(danger_zones) and self.grid_body_safe(start, danger_zones):
            return [start]

        queue: deque = deque([(start[0], start[1], [])])
        visited: set[tuple[int, int]] = {start}
        while queue:
            cx, cy, path = queue.popleft()
            if self.grid_body_safe((cx, cy), danger_zones):
                return path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT
                        and (nx, ny) not in visited
                        and game_map[ny][nx] not in [WALL, SOFT_WALL]):
                    visited.add((nx, ny))
                    queue.append((nx, ny, path + [(nx, ny)]))
        return []

    def find_path(
        self,
        player_x: int,
        player_y: int,
        game_map: list[list[int]],
        bomb_queue: list[dict],
        explosion_range: int,
        now: int,
    ) -> list[tuple[int, int]]:
        """Tính đường đi đến người chơi — phương thức ảo, bắt buộc ghi đè.

        Lớp con phải triển khai thuật toán tìm đường phù hợp với tier của
        mình (BFS, BFS + né bom, A* …) và cập nhật ``self.path``.

        Args:
            player_x (int): Tọa độ cột người chơi trên lưới.
            player_y (int): Tọa độ hàng người chơi trên lưới.
            game_map (list[list[int]]): Bản đồ 2D.
            bomb_queue (list[dict]): Danh sách bom đang hoạt động.
            explosion_range (int): Tầm nổ tối đa.
            now (int): Thời điểm hiện tại (ms).

        Raises:
            NotImplementedError: Luôn raise nếu không được ghi đè.
        """
        raise NotImplementedError("Phải ghi đè hàm này ở class con")


class DumbEnemy(Enemy):
    """Tier 1 — Quái Ngu: BFS thuần, lao thẳng vào người chơi, không né bom.

    Tốc độ thấp nhất (1 pixel/frame). Phù hợp cho các màn đầu (level 1–2)
    khi người chơi cần làm quen với cơ chế.
    """

    def __init__(self, grid_x: int, grid_y: int):
        """Khởi tạo DumbEnemy tại ô lưới (grid_x, grid_y)."""
        super().__init__(grid_x, grid_y, speed=1, color=(0, 255, 0), enemy_model="enemy_dumb")

    def find_path(
        self,
        player_x: int,
        player_y: int,
        game_map: list[list[int]],
        bomb_queue: list[dict],
        explosion_range: int,
        now: int,
    ) -> list[tuple[int, int]]:
        """Tìm đường ngắn nhất đến người chơi bằng BFS, bỏ qua hoàn toàn bom."""
        start = (self.rect.centerx // TILE_SIZE, self.rect.centery // TILE_SIZE)
        goal = (player_x, player_y)
        queue: deque = deque([(start[0], start[1], [])])
        visited: set[tuple[int, int]] = {start}

        while queue:
            cx, cy, path = queue.popleft()
            if (cx, cy) == goal:
                self.path = path
                return self.path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT
                        and (nx, ny) not in visited
                        and game_map[ny][nx] not in [WALL, SOFT_WALL]):
                    visited.add((nx, ny))
                    queue.append((nx, ny, path + [(nx, ny)]))
        self.path = []
        return self.path


class SmartEnemy(Enemy):
    """Tier 2 — Quái Khôn: BFS + flood-fill né bom, không tính trọng số địa hình.

    Tốc độ trung bình (2 pixel/frame). Khi đứng trong vùng nguy hiểm, ưu tiên
    thoát ra trước khi tiếp tục truy đuổi. Phù hợp cho level 3–4.
    """

    def __init__(self, grid_x: int, grid_y: int):
        """Khởi tạo SmartEnemy tại ô lưới (grid_x, grid_y)."""
        super().__init__(grid_x, grid_y, speed=2, color=(255, 165, 0), enemy_model="enemy_smart")

    def find_path(
        self,
        player_x: int,
        player_y: int,
        game_map: list[list[int]],
        bomb_queue: list[dict],
        explosion_range: int,
        now: int,
    ) -> list[tuple[int, int]]:
        """Tìm đường đến người chơi bằng BFS, né vùng nguy hiểm khi truy đuổi."""
        start = (self.rect.centerx // TILE_SIZE, self.rect.centery // TILE_SIZE)
        goal = (player_x, player_y)
        danger_zones = self.get_danger_zones(bomb_queue, explosion_range, now, game_map)

        if self.body_in_danger(danger_zones):
            self.path = self.bfs_to_safety(start, game_map, danger_zones)
            return self.path

        queue: deque = deque([(start[0], start[1], [])])
        visited: set[tuple[int, int]] = {start}
        while queue:
            cx, cy, path = queue.popleft()
            if (cx, cy) == goal:
                self.path = path
                return self.path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT
                        and (nx, ny) not in visited
                        and game_map[ny][nx] not in [WALL, SOFT_WALL]
                        and self.grid_body_safe((nx, ny), danger_zones)):
                    visited.add((nx, ny))
                    queue.append((nx, ny, path + [(nx, ny)]))
        self.path = []
        return self.path


class EliteEnemy(Enemy):
    """Tier 3 — Quái Tinh Anh (Trùm): A* có trọng số địa hình + phản xạ bom nhanh hơn.

    Tốc độ 2 pixel/frame, ``reaction_delay`` tăng lên 1500 ms (phản xạ sớm hơn
    SmartEnemy). Sử dụng A* để chọn đường có tổng chi phí thấp nhất.

    Trọng số ô:
    - ``EMPTY`` / ``TRAP_TELEPORT``: 1 (ưu tiên cao nhất).
    - ``TRAP_ICE``: 2 (hơi tránh vì mất kiểm soát).
    - ``CONVEYOR_LEFT`` / ``CONVEYOR_RIGHT``: 5 (tránh vì bị đẩy).
    - Các ô khác (tường): ``inf`` (không đi qua).
    """

    def __init__(self, grid_x: int, grid_y: int):
        """Khởi tạo EliteEnemy tại ô lưới (grid_x, grid_y)."""
        super().__init__(grid_x, grid_y, speed=2, color=(200, 0, 0), enemy_model="enemy_elite")
        self.reaction_delay = 1500
        self.post_explosion_delay = random.randint(50, 400)

    def on_explosion_started(self, now: int) -> None:
        """EliteEnemy đứng chờ một nhịp để vụ nổ kết thúc rồi mới đi tiếp."""
        self.post_explosion_wait_until = max(
            self.post_explosion_wait_until,
            now + self.post_explosion_delay,
        )
        self.path = []
        self.slide_dx = 0
        self.slide_dy = 0
        self.move_frac_x = 0
        self.move_frac_y = 0

    def heuristic(self, a: tuple[int, int], b: tuple[int, int]) -> int:
        """Hàm heuristic Manhattan distance cho thuật toán A*."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_tile_weight(self, tile: int) -> float:
        """Trả về chi phí di chuyển qua một loại ô cho A*.

        Args:
            tile (int): Loại ô từ settings.py (EMPTY, WALL, etc.).

        Returns:
            float: Chi phí di chuyển (1 cho ô trống, cao hơn cho ô nguy hiểm).
        """
        if tile in (EMPTY, TRAP_TELEPORT):
            return 1
        elif tile == TRAP_ICE:
            return 2
        elif tile in (CONVEYOR_LEFT, CONVEYOR_RIGHT):
            return 5
        return float('inf')

    def a_star_hunt(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
        game_map: list[list[int]],
        danger_zones: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        """Tìm đường đến ``goal`` bằng A* có trọng số, tránh vùng nguy hiểm.

        Args:
            start (tuple[int, int]): Vị trí xuất phát ``(grid_x, grid_y)``.
            goal (tuple[int, int]): Vị trí đích ``(grid_x, grid_y)``.
            game_map (list[list[int]]): Bản đồ 2D.
            danger_zones (set[tuple[int, int]]): Tập hợp ô nguy hiểm.

        Returns:
            list[tuple[int, int]]: Danh sách ô lưới từ ``start`` đến ``goal``.
        """
        open_set: list = []
        heapq.heappush(open_set, (0, 0, start))
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score: dict[tuple[int, int], float] = {start: 0}

        while open_set:
            _, current_g, current = heapq.heappop(open_set)

            if current == goal:
                path: list[tuple[int, int]] = []
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
                    if weight == float('inf') or not self.grid_body_safe((nx, ny), danger_zones):
                        continue
                    tentative_g = current_g + weight
                    if (nx, ny) not in g_score or tentative_g < g_score[(nx, ny)]:
                        came_from[(nx, ny)] = current
                        g_score[(nx, ny)] = tentative_g
                        f_score = tentative_g + self.heuristic((nx, ny), goal)
                        heapq.heappush(open_set, (f_score, tentative_g, (nx, ny)))
        return []

    def find_path(
        self,
        player_x: int,
        player_y: int,
        game_map: list[list[int]],
        bomb_queue: list[dict],
        explosion_range: int,
        now: int,
    ) -> list[tuple[int, int]]:
        """Tìm đường đến người chơi bằng A*, thoát vùng nguy hiểm nếu cần."""
        start = (self.rect.centerx // TILE_SIZE, self.rect.centery // TILE_SIZE)
        goal = (player_x, player_y)
        danger_zones = self.get_danger_zones(bomb_queue, explosion_range, now, game_map)

        if self.body_in_danger(danger_zones):
            self.path = self.bfs_to_safety(start, game_map, danger_zones)
        else:
            self.path = self.a_star_hunt(start, goal, game_map, danger_zones)
        return self.path
