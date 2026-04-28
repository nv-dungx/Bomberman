"""
enemy.py
--------
Module định nghĩa lớp Enemy — kẻ địch trong game Bomberman.

Enemy sử dụng thuật toán BFS (Breadth-First Search) để tìm đường đến
người chơi, đồng thời có khả năng né tránh vùng nguy hiểm của bom.
Một cơ chế "phản xạ chậm" được tích hợp để cân bằng độ khó: kẻ địch
chỉ bắt đầu né bom khi thời gian nổ còn dưới ngưỡng nhất định.
"""

import pygame
from collections import deque
from settings import *


class Enemy:
    """Kẻ địch điều khiển bởi AI trong game Bomberman.

    AI hoạt động theo hai chế độ:
    - **Tấn công**: Dùng BFS tìm đường ngắn nhất đến người chơi, tránh
      các ô trong vùng nguy hiểm của bom.
    - **Né tránh**: Khi đang đứng trong vùng nguy hiểm, dùng BFS tìm ô
      an toàn gần nhất và di chuyển đến đó.

    Attributes:
        grid_x (int): Tọa độ cột hiện tại của kẻ địch trên lưới.
        grid_y (int): Tọa độ hàng hiện tại của kẻ địch trên lưới.
        rect (pygame.Rect): Hình chữ nhật va chạm, dùng để vẽ và kiểm tra
            collision trong không gian pixel.
        path (list[tuple[int, int]]): Danh sách các ô lưới (grid_x, grid_y)
            tạo thành đường đi hiện tại đến mục tiêu.
    """

    def __init__(self, x: int, y: int):
        """Khởi tạo kẻ địch tại vị trí lưới (x, y).

        Args:
            x (int): Tọa độ cột ban đầu trên lưới.
            y (int): Tọa độ hàng ban đầu trên lưới.
        """
        self.grid_x = x
        self.grid_y = y
        self.rect = pygame.Rect(x * TILE_SIZE + 5, y * TILE_SIZE + 5, 30, 30)
        self.path: list[tuple[int, int]] = []

    def get_danger_zones(
        self,
        bomb_queue: list[dict],
        explosion_range: int,
        game_map: list[list[int]],
        now: int,
    ) -> set[tuple[int, int]]:
        """Tính toán tập hợp các ô lưới nằm trong vùng nguy hiểm của bom.

        Sử dụng flood-fill theo 4 hướng cho mỗi quả bom. Áp dụng cơ chế
        "phản xạ chậm": kẻ địch chỉ coi một quả bom là nguy hiểm khi thời
        gian còn lại đến lúc nổ nhỏ hơn hoặc bằng 1200 ms. Bom mới đặt
        (còn ~2000 ms) bị bỏ qua, giúp AI bớt hoàn hảo và dễ chơi hơn.

        Args:
            bomb_queue (list[dict]): Danh sách bom đang hoạt động. Mỗi phần
                tử là dict với các key:
                - ``'x'`` (int): cột của bom trên lưới.
                - ``'y'`` (int): hàng của bom trên lưới.
                - ``'timer'`` (int): thời điểm nổ (ms, tính từ pygame.time.get_ticks).
            explosion_range (int): Số ô tối đa mà sóng nổ lan ra theo mỗi hướng.
            game_map (list[list[int]]): Bản đồ 2D, mỗi phần tử là hằng số tile
                (EMPTY, WALL, SOFT_WALL, …).
            now (int): Thời điểm hiện tại (ms), thường là pygame.time.get_ticks().

        Returns:
            set[tuple[int, int]]: Tập hợp các tọa độ (grid_x, grid_y) bị ảnh
            hưởng bởi bom đang đếm ngược.
        """
        danger_zones: set[tuple[int, int]] = set()
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
                        if game_map[ny][nx] == WALL:
                            break
                        danger_zones.add((nx, ny))
                        if game_map[ny][nx] == SOFT_WALL:
                            break
        return danger_zones

    def find_path(
        self,
        target_gx: int,
        target_gy: int,
        game_map: list[list[int]],
        bomb_queue: list[dict],
        explosion_range: int,
        now: int,
    ) -> list[tuple[int, int]]:
        """Xác định đường đi cho kẻ địch trong frame hiện tại.

        Nếu kẻ địch đang ở trong vùng nguy hiểm, ưu tiên tìm đường thoát an
        toàn (``bfs_to_safety``). Ngược lại, tìm đường ngắn nhất đến mục tiêu
        đồng thời tránh vùng nguy hiểm (``bfs_standard``).

        Args:
            target_gx (int): Tọa độ cột mục tiêu (thường là vị trí người chơi).
            target_gy (int): Tọa độ hàng mục tiêu.
            game_map (list[list[int]]): Bản đồ 2D.
            bomb_queue (list[dict]): Danh sách bom đang hoạt động.
            explosion_range (int): Tầm nổ tối đa.
            now (int): Thời điểm hiện tại (ms).

        Returns:
            list[tuple[int, int]]: Danh sách ô lưới tạo thành đường đi, không
            bao gồm ô xuất phát. Trả về danh sách rỗng nếu không tìm được đường.
        """
        start = (self.grid_x, self.grid_y)
        danger_zones = self.get_danger_zones(bomb_queue, explosion_range, game_map, now)

        if start in danger_zones:
            return self.bfs_to_safety(start, danger_zones, game_map)

        return self.bfs_standard(start, (target_gx, target_gy), game_map, danger_zones)

    def bfs_to_safety(
        self,
        start: tuple[int, int],
        danger_zones: set[tuple[int, int]],
        game_map: list[list[int]],
    ) -> list[tuple[int, int]]:
        """Tìm đường đến ô an toàn gần nhất bằng BFS.

        Duyệt BFS từ vị trí hiện tại theo 4 hướng cho đến khi gặp ô đầu tiên
        nằm ngoài ``danger_zones``. Chỉ đi qua các ô có thể bước lên được
        (EMPTY, TRAP_TELEPORT, TRAP_ICE, CONVEYOR_LEFT/RIGHT).

        Args:
            start (tuple[int, int]): Vị trí xuất phát (grid_x, grid_y).
            danger_zones (set[tuple[int, int]]): Tập hợp ô nguy hiểm.
            game_map (list[list[int]]): Bản đồ 2D.

        Returns:
            list[tuple[int, int]]: Đường đi từ ô kế tiếp đến ô an toàn đầu tiên.
            Trả về danh sách rỗng nếu không tìm được lối thoát.
        """
        queue = deque([start])
        parent_map: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

        while queue:
            curr = queue.popleft()
            if curr not in danger_zones:
                return self.reconstruct_path(parent_map, curr, start)

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = curr[0] + dx, curr[1] + dy
                if (
                    0 <= nx < GRID_WIDTH
                    and 0 <= ny < GRID_HEIGHT
                    and game_map[ny][nx] in [EMPTY, TRAP_TELEPORT, TRAP_ICE, CONVEYOR_LEFT, CONVEYOR_RIGHT]
                    and (nx, ny) not in parent_map
                ):
                    parent_map[(nx, ny)] = curr
                    queue.append((nx, ny))
        return []

    def bfs_standard(
        self,
        start: tuple[int, int],
        target: tuple[int, int],
        game_map: list[list[int]],
        danger_zones: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        """Tìm đường ngắn nhất đến mục tiêu bằng BFS, tránh vùng nguy hiểm.

        Duyệt BFS từ ``start`` đến ``target``. Các ô trong ``danger_zones`` bị
        loại khỏi không gian tìm kiếm để đảm bảo kẻ địch không đi vào vùng
        bom trong quá trình di chuyển bình thường.

        Args:
            start (tuple[int, int]): Vị trí xuất phát (grid_x, grid_y).
            target (tuple[int, int]): Vị trí đích cần đến.
            game_map (list[list[int]]): Bản đồ 2D.
            danger_zones (set[tuple[int, int]]): Tập hợp ô cần tránh.

        Returns:
            list[tuple[int, int]]: Đường đi từ ô kế tiếp đến ``target``.
            Trả về danh sách rỗng nếu không tìm được đường.
        """
        queue = deque([start])
        parent_map: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

        while queue:
            curr = queue.popleft()
            if curr == target:
                return self.reconstruct_path(parent_map, curr, start)

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = curr[0] + dx, curr[1] + dy
                if (
                    0 <= nx < GRID_WIDTH
                    and 0 <= ny < GRID_HEIGHT
                    and game_map[ny][nx] in [EMPTY, TRAP_TELEPORT, TRAP_ICE, CONVEYOR_LEFT, CONVEYOR_RIGHT]
                    and (nx, ny) not in parent_map
                    and (nx, ny) not in danger_zones
                ):
                    parent_map[(nx, ny)] = curr
                    queue.append((nx, ny))
        return []

    def reconstruct_path(
        self,
        parent_map: dict[tuple[int, int], tuple[int, int] | None],
        curr: tuple[int, int],
        start: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """Tái tạo đường đi từ bảng cha (parent map) của BFS.

        Truy ngược từ ``curr`` về ``start`` qua ``parent_map``, sau đó đảo
        thứ tự để thu được đường đi từ ô kế tiếp ``start`` đến ``curr``.
        Kết quả được lưu vào ``self.path`` và trả về.

        Args:
            parent_map (dict): Ánh xạ mỗi ô đến ô cha của nó trong BFS.
            curr (tuple[int, int]): Ô đích (cuối đường đi).
            start (tuple[int, int]): Ô xuất phát (không được đưa vào path).

        Returns:
            list[tuple[int, int]]: Danh sách ô lưới từ ô kế tiếp ``start``
            đến ``curr`` (không gồm ``start``).
        """
        path: list[tuple[int, int]] = []
        while curr in parent_map and curr != start:
            path.append(curr)
            curr = parent_map[curr]
        self.path = path[::-1]
        return self.path

    def move(self) -> None:
        """Di chuyển kẻ địch theo đường đi đã tính toán (``self.path``).

        Mỗi frame, kẻ địch dịch chuyển ``rect`` về phía ô lưới đầu tiên trong
        ``self.path`` với tốc độ ``ENEMY_SPEED`` pixel/frame. Khi ``rect`` đến
        đủ gần ô đích (sai số < ``ENEMY_SPEED``), tọa độ lưới được cập nhật và
        ô đó bị xóa khỏi ``self.path``.

        Không làm gì nếu ``self.path`` rỗng.
        """
        if not self.path:
            return
        target_node = self.path[0]
        tx, ty = target_node[0] * TILE_SIZE + 5, target_node[1] * TILE_SIZE + 5
        if self.rect.x < tx:
            self.rect.x += ENEMY_SPEED
        elif self.rect.x > tx:
            self.rect.x -= ENEMY_SPEED
        if self.rect.y < ty:
            self.rect.y += ENEMY_SPEED
        elif self.rect.y > ty:
            self.rect.y -= ENEMY_SPEED
        if abs(self.rect.x - tx) < ENEMY_SPEED and abs(self.rect.y - ty) < ENEMY_SPEED:
            self.grid_x, self.grid_y = target_node
            self.path.pop(0)
