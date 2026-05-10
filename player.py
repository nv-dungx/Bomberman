"""
player.py
Module định nghĩa thực thể người chơi trong game Bomberman.

Player xử lý di chuyển, va chạm, quản lý mạng, khiên, hiệu ứng item, và
trạng thái ma (ghost) khi đi xuyên tường mềm. Phiên bản này đã tích hợp
hệ thống nạp ảnh (Sprites) và hoạt ảnh (Animation).

Các cấu trúc dữ liệu được sử dụng:
- ``list``   — ngăn xếp khiên ``shields`` (Stack, dùng ``pop()``).
- ``heapq``  — hàng đợi ưu tiên thời gian hết hạn item (Min-Heap).
- ``deque``  — hàng đợi lực đẩy từ băng chuyền (Queue).
"""
import pygame
import heapq
from collections import deque
from settings import *
from asset_loader import AssetLoader


class Player:
    """Đại diện người chơi trong Bomberman.

    Player quản lý trạng thái di chuyển, sinh tồn và hiệu ứng item:
    tốc độ, tầm nổ bom, khiên, bất tử tạm thời và trạng thái ghost.

    Attributes:
        rect (pygame.Rect): Hình chữ nhật va chạm của người chơi (pixel).
        current_speed (int): Tốc độ di chuyển hiện tại (pixel/frame).
        last_dx (int): Hướng di chuyển ngang cuối cùng, dùng cho trượt băng.
        last_dy (int): Hướng di chuyển dọc cuối cùng.
        is_dead (bool): ``True`` khi người chơi hết mạng hoàn toàn.
        lives (int): Số mạng còn lại.
        shields (list[str]): Stack các lớp khiên.
        invulnerable_until (int): Thời điểm kết thúc i-frame (ms).
        is_ghost (bool): ``True`` khi có thể đi xuyên qua ``SOFT_WALL``.
        explosion_range (int): Tầm nổ của bom hiện tại.
        active_effects (list): Min-Heap quản lý thời gian hết hạn item.
        forced_move_queue (deque): Queue lực đẩy từ băng chuyền.
        teleport_cooldown (int): Thời điểm có thể dùng cổng teleport tiếp theo.
        direction (str): Hướng nhìn hiện tại ("up", "down", "left", "right").
        frame_index (int): Chỉ số frame hoạt ảnh hiện tại (0, 1, 2).
        animation_timer (int): Bộ đếm thời gian để chuyển đổi frame.
        is_moving (bool): Trạng thái xác định nhân vật có đang di chuyển hay không.
    """

    def __init__(self, x: int, y: int, lives: int = 1, player_model: str = "Player_1"):
        """Khởi tạo người chơi và nạp Spritesheet hoạt ảnh.

        Args:
            x (int): Tọa độ X ban đầu (pixel).
            y (int): Tọa độ Y ban đầu (pixel).
            lives (int): Số mạng khởi đầu. Mặc định là 1.
            player_model (str): Tên file ảnh (không bao gồm đuôi .png) trong assets/images/.
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

        # --- Hệ thống hoạt ảnh ---
        self.direction = "down"
        self.frame_index = 0
        self.animation_timer = 0
        self.is_moving = False

        # Nạp và cắt dải ảnh 9 frames (30x30 mỗi frame)
        frames = AssetLoader.load_sprite_sheet(f"{player_model}.png", 30, 30, 9)
        
        if frames and len(frames) >= 9:
            self.frames_down = frames[0:3]
            self.frames_right = frames[3:6]
            self.frames_up = frames[6:9]
            # Tạo hướng trái bằng cách lật ngược hướng phải
            self.frames_left = [pygame.transform.flip(f, True, False) for f in self.frames_right]
        else:
            # Fallback nếu không load được ảnh
            surf = pygame.Surface((30, 30))
            surf.fill(BLUE)
            self.frames_down = self.frames_up = self.frames_left = self.frames_right = [surf] * 3

    def move(self, dx: float, dy: float, game_map: list[list[int]]) -> None:
        """Di chuyển người chơi, kiểm tra va chạm và cập nhật trạng thái hoạt ảnh.

        Args:
            dx (float): Độ dịch chuyển theo trục X.
            dy (float): Độ dịch chuyển theo trục Y.
            game_map (list[list[int]]): Bản đồ 2D.
        """
        self.is_moving = (dx != 0 or dy != 0)
        
        if dx > 0: self.direction = "right"
        elif dx < 0: self.direction = "left"
        elif dy > 0: self.direction = "down"
        elif dy < 0: self.direction = "up"

        self.rect.x += dx
        if self.check_collision(game_map):
            self.rect.x -= dx

        self.rect.y += dy
        if self.check_collision(game_map):
            self.rect.y -= dy

    def check_collision(self, game_map: list[list[int]]) -> bool:
        """Kiểm tra va chạm với các ô tường trên bản đồ."""
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                tile = game_map[r][c]
                if tile == WALL or (tile == SOFT_WALL and not self.is_ghost):
                    tile_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.rect.colliderect(tile_rect):
                        return True
        return False

    def take_damage(self, now: int) -> None:
        """Áp dụng sát thương và xử lý i-frame, khiên, mạng sống."""
        if now < self.invulnerable_until:
            return

        if self.shields:
            self.shields.pop()
            self.invulnerable_until = now + 1500
        else:
            self.lives -= 1
            if self.lives <= 0:
                self.is_dead = True
            else:
                self.invulnerable_until = now + 1500

    def update_items(self, now: int, current_tile: int) -> None:
        """Hủy các hiệu ứng item đã hết hạn bằng Min-Heap."""
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
        """Áp dụng hiệu ứng item khi nhặt được."""
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
        """Vẽ Sprite nhân vật kèm hoạt ảnh và các hiệu ứng trực quan.

        Xử lý hoạt ảnh bước đi dựa trên ``is_moving`` và hướng ``direction``.
        Tích hợp chớp tắt khi bất tử và làm mờ ảnh khi ở trạng thái Ghost.
        """
        if self.is_dead:
            return

        # 1. Cập nhật frame hoạt ảnh
        if self.is_moving:
            if now - self.animation_timer > 100:  # Chuyển frame mỗi 100ms
                self.frame_index = (self.frame_index + 1) % 3
                self.animation_timer = now
        else:
            self.frame_index = 0  # Đứng im thì dùng frame đầu tiên

        # 2. Chọn bộ ảnh theo hướng
        if self.direction == "down": frameset = self.frames_down
        elif self.direction == "up": frameset = self.frames_up
        elif self.direction == "right": frameset = self.frames_right
        else: frameset = self.frames_left
        
        current_image = frameset[self.frame_index].copy()

        # 3. Hiệu ứng hiển thị (Bất tử & Ghost)
        is_invulnerable = now < self.invulnerable_until
        if not is_invulnerable or (now // 100) % 2 == 0:
            if self.is_ghost:
                current_image.set_alpha(150)  # Làm mờ khi đi xuyên tường
            screen.blit(current_image, self.rect)

        # 4. Vẽ vòng khiên bảo vệ
        if self.shields:
            pygame.draw.circle(
                screen, CYAN,
                self.rect.center,
                TILE_SIZE // 2 + 4, len(self.shields) * 2,
            )