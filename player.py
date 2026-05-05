"""
player.py
Module định nghĩa thực thể người chơi trong game Bomberman.

Player xử lý di chuyển, va chạm, quản lý mạng, khiên, hiệu ứng item, và
trạng thái ma (ghost) khi đi xuyên tường mềm.

Các cấu trúc dữ liệu được sử dụng:
- ``list``   — ngăn xếp khiên ``shields`` (Stack, dùng ``pop()``).
- ``heapq``  — hàng đợi ưu tiên thời gian hết hạn item (Min-Heap).
- ``deque``  — hàng đợi lực đẩy từ băng chuyền (Queue).
"""
import pygame
import heapq
from collections import deque
from settings import *


class Player:
    """Đại diện người chơi trong Bomberman.

    Player quản lý trạng thái di chuyển, sinh tồn và hiệu ứng item:
    tốc độ, tầm nổ bom, khiên, bất tử tạm thời và trạng thái ghost.

    Attributes:
        rect (pygame.Rect): Hình chữ nhật va chạm của người chơi (pixel).
        current_speed (int): Tốc độ di chuyển hiện tại (pixel/frame).
            Bị thay đổi khi nhặt item ``SPEED``; reset về ``PLAYER_SPEED`` sau 5 giây.
        last_dx (int): Hướng di chuyển cuối cùng theo trục X, dùng để tính
            trượt trên ô băng (TRAP_ICE).
        last_dy (int): Hướng di chuyển cuối cùng theo trục Y.
        is_dead (bool): ``True`` khi người chơi hết mạng hoàn toàn.
        lives (int): Số mạng còn lại. Mặc định là 1.
        shields (list[str]): Stack các lớp khiên. Mỗi phần tử là ``"L"``
            (một lớp); ``pop()`` tiêu thụ lớp ngoài cùng khi nhận sát thương.
        invulnerable_until (int): Thời điểm (ms) kết thúc trạng thái bất tử
            (i-frame) sau khi mất khiên hoặc mất mạng.
        is_ghost (bool): ``True`` khi item Ghost đang hoạt động; người chơi
            đi xuyên qua ``SOFT_WALL`` mà không bị cản.
        explosion_range (int): Số ô tối đa sóng nổ lan ra theo mỗi hướng.
            Bị tăng khi nhặt item ``RANGE``; reset về 2 sau 7 giây.
        active_effects (list): Min-Heap lưu ``(expiry_ms, effect_name)`` để
            xác định thời điểm hủy từng hiệu ứng item.
        forced_move_queue (deque[tuple[int, int]]): Queue lực đẩy từ băng
            chuyền. Mỗi phần tử là ``(dx, dy)`` pixel sẽ được áp dụng cuối frame.
        teleport_cooldown (int): Thời điểm (ms) người chơi có thể dùng
            cổng teleport tiếp theo; tránh bị dịch chuyển liên tục.
    """

    def __init__(self, x: int, y: int, lives: int = 1):
        """Khởi tạo người chơi tại tọa độ pixel (x, y).

        Args:
            x (int): Tọa độ X ban đầu (pixel, góc trên-trái của rect).
            y (int): Tọa độ Y ban đầu (pixel).
            lives (int): Số mạng khởi đầu. Mặc định là 1.
        """
        self.rect = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.current_speed = PLAYER_SPEED
        self.last_dx, self.last_dy = 0, 0
        self.is_dead = False
        self.lives = lives
        self.shields = []
        self.invulnerable_until = 0
        self.is_ghost = False
        self.explosion_range = 2
        self.active_effects = []
        self.forced_move_queue = deque()
        self.teleport_cooldown = 0

    def move(self, dx: float, dy: float, game_map: list[list[int]]) -> None:
        """Di chuyển người chơi và kiểm tra va chạm với bản đồ.

        Áp dụng di chuyển theo từng trục riêng lẻ (trục X trước, trục Y sau)
        để tránh bị kẹt vào góc tường khi di chuyển chéo.

        Args:
            dx (float): Độ dịch chuyển theo trục X (pixel). Có thể là số thực
                khi tính toán trượt băng (nhân với hệ số 0.8).
            dy (float): Độ dịch chuyển theo trục Y (pixel).
            game_map (list[list[int]]): Bản đồ 2D dùng để kiểm tra va chạm.
        """
        self.rect.x += dx
        if self.check_collision(game_map):
            self.rect.x -= dx

        self.rect.y += dy
        if self.check_collision(game_map):
            self.rect.y -= dy

    def check_collision(self, game_map: list[list[int]]) -> bool:
        """Kiểm tra xem ``rect`` có đang đè lên ô tường không.

        Duyệt toàn bộ bản đồ và kiểm tra va chạm pixel-perfect giữa
        ``rect`` và từng ô ``WALL`` / ``SOFT_WALL``. Khi ``is_ghost`` là
        ``True``, ``SOFT_WALL`` bị bỏ qua hoàn toàn.

        Args:
            game_map (list[list[int]]): Bản đồ 2D dùng hằng số tile từ ``settings``.

        Returns:
            bool: ``True`` nếu ``rect`` đang chồng lên ô tường, ``False`` nếu không.
        """
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                tile = game_map[r][c]
                if tile == WALL or (tile == SOFT_WALL and not self.is_ghost):
                    tile_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.rect.colliderect(tile_rect):
                        return True
        return False

    def take_damage(self, now: int) -> None:
        """Áp dụng sát thương lên người chơi.

        Xử lý theo thứ tự ưu tiên:
        1. Nếu đang trong i-frame (``invulnerable_until``), bỏ qua hoàn toàn.
        2. Nếu còn khiên, tiêu thụ một lớp (Stack ``pop``) và kích hoạt
           i-frame 1.5 giây.
        3. Nếu không còn khiên, trừ 1 mạng. Nếu hết mạng, đặt ``is_dead = True``;
           ngược lại kích hoạt i-frame 1.5 giây.

        Args:
            now (int): Thời điểm hiện tại (ms), thường là ``pygame.time.get_ticks()``.

        Side effects:
            - Có thể đặt ``self.is_dead = True``.
            - Có thể cập nhật ``self.invulnerable_until``.
            - In thông báo trạng thái ra console.
        """
        if now < self.invulnerable_until:
            return

        if self.shields:
            self.shields.pop()
            self.invulnerable_until = now + 1500
            print(f"Khiên bị vỡ. Còn {len(self.shields)} lớp.")
        else:
            self.lives -= 1
            if self.lives <= 0:
                self.is_dead = True
                print("Người chơi đã chết.")
            else:
                self.invulnerable_until = now + 1500
                print(f"Người chơi trúng bom. Còn {self.lives} mạng.")

    def update_items(self, now: int, current_tile: int) -> None:
        """Hủy các hiệu ứng item đã hết hạn và reset chỉ số về mặc định.

        Lấy liên tục từ Min-Heap ``active_effects`` các hiệu ứng có thời điểm
        hết hạn ``≤ now`` và áp dụng thao tác reset tương ứng.

        Trường hợp đặc biệt với ``RESET_GHOST``: nếu người chơi đang đứng
        trên ``SOFT_WALL`` khi ghost hết hạn, :meth:`take_damage` được gọi
        ngay lập tức (người chơi bị nhốt trong tường).

        Args:
            now (int): Thời điểm hiện tại (ms).
            current_tile (int): Tile mà người chơi đang đứng, dùng để kiểm
                tra tình huống ghost hết hạn trên tường mềm.
        """
        while self.active_effects and self.active_effects[0][0] <= now:
            _, effect = heapq.heappop(self.active_effects)
            if effect == "RESET_SPEED":
                self.current_speed = PLAYER_SPEED
            elif effect == "RESET_RANGE":
                self.explosion_range = 2
            elif effect == "RESET_GHOST":
                self.is_ghost = False
                if current_tile == SOFT_WALL:
                    self.take_damage(now)

    def pick_up_item(self, p_type: str, now: int) -> None:
        """Áp dụng hiệu ứng item và đặt lịch hủy vào Min-Heap nếu cần.

        Với các item có thời hạn (``SPEED``, ``RANGE``, ``GHOST``), thời điểm
        reset được đẩy vào ``active_effects`` để :meth:`update_items` xử lý
        tự động. Item ``SHIELD`` không có thời hạn — chỉ bị tiêu thụ khi
        nhận sát thương.

        Args:
            p_type (str): Loại item, một trong ``"SPEED"``, ``"RANGE"``,
                ``"SHIELD"``, ``"GHOST"``.
            now (int): Thời điểm nhặt item (ms), dùng làm gốc tính thời hạn.
        """
        if p_type == "SPEED":
            self.current_speed = 5
            heapq.heappush(self.active_effects, (now + 5000, "RESET_SPEED"))
        elif p_type == "RANGE":
            self.explosion_range = 4
            heapq.heappush(self.active_effects, (now + 7000, "RESET_RANGE"))
        elif p_type == "SHIELD":
            self.shields.append("L")
        elif p_type == "GHOST":
            self.is_ghost = True
            heapq.heappush(self.active_effects, (now + 8000, "RESET_GHOST"))

    def draw(self, screen: pygame.Surface, now: int) -> None:
        """Vẽ người chơi lên màn hình với các hiệu ứng trực quan.

        Hiệu ứng được áp dụng theo thứ tự:
        - **Bất tử (i-frame)**: nhân vật chớp tắt mỗi 100 ms (ẩn/hiện xen kẽ).
        - **Ghost**: tô màu tím (``PURPLE``) thay vì xanh dương (``BLUE``).
        - **Khiên**: vẽ vòng tròn ``CYAN`` bao quanh; độ dày tăng theo số lớp.

        Không vẽ gì nếu ``is_dead`` là ``True``.

        Args:
            screen (pygame.Surface): Bề mặt Pygame để vẽ lên.
            now (int): Thời điểm hiện tại (ms), dùng để tính nhịp chớp tắt.
        """
        if self.is_dead:
            return

        is_invulnerable = now < self.invulnerable_until

        if not is_invulnerable or (now // 100) % 2 == 0:
            color = PURPLE if self.is_ghost else BLUE
            pygame.draw.rect(screen, color, self.rect)

        if self.shields:
            pygame.draw.circle(
                screen, CYAN,
                self.rect.center,
                TILE_SIZE // 2 + 4, len(self.shields) * 2,
            )