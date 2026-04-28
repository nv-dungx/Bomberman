"""
main.py
-------
Điểm khởi chạy và vòng lặp chính của game Bomberman DSA.

Module này định nghĩa lớp :class:`Game` — trung tâm điều phối toàn bộ
trạng thái game, bao gồm:

- Khởi tạo màn hình, bản đồ và các thực thể (người chơi, kẻ địch, bom).
- Xử lý đầu vào bàn phím.
- Cập nhật logic mỗi frame (bom, nổ, bẫy, item, AI kẻ địch).
- Vẽ toàn bộ màn hình.

Các cấu trúc dữ liệu được sử dụng:
- ``deque``  — hàng đợi bom và lực đẩy băng chuyền (Queue).
- ``list``   — ngăn xếp khiên ``shields`` (Stack).
- ``heapq``  — hàng đợi ưu tiên thời gian hết hạn item (Min-Heap).
- ``dict``   — tra cứu O(1) vị trí item trên bản đồ.
"""

import pygame
import sys
import random
import heapq
from collections import deque
from settings import *
from enemy import Enemy


class Game:
    """Lớp quản lý toàn bộ vòng lặp game Bomberman.

    Chịu trách nhiệm khởi tạo Pygame, duy trì trạng thái game và điều
    phối ba giai đoạn mỗi frame: xử lý đầu vào → cập nhật logic → vẽ.

    Attributes:
        screen (pygame.Surface): Bề mặt hiển thị chính.
        clock (pygame.time.Clock): Đồng hồ điều khiển FPS.
        player_rect (pygame.Rect): Hình chữ nhật va chạm của người chơi.
        player_current_speed (int): Tốc độ di chuyển hiện tại (pixel/frame),
            có thể thay đổi khi nhặt item SPEED.
        last_dx (int): Độ dịch chuyển ngang cuối cùng, dùng cho hiệu ứng trượt băng.
        last_dy (int): Độ dịch chuyển dọc cuối cùng, dùng cho hiệu ứng trượt băng.
        is_dead (bool): ``True`` nếu người chơi đã chết.
        shields (list[str]): Stack các lớp khiên. Mỗi phần tử là ``"L"``
            đại diện cho một lớp; ``pop()`` tiêu thụ lớp ngoài cùng khi nhận sát thương.
        invulnerable_until (int): Thời điểm hết i-frame sau khi mất khiên (ms).
        is_ghost (bool): ``True`` khi item Ghost đang hoạt động; người chơi
            có thể đi xuyên tường mềm.
        bomb_queue (deque[dict]): Queue các quả bom đang đếm ngược. Mỗi phần
            tử là dict ``{'x': int, 'y': int, 'timer': int}``.
        forced_move_queue (deque[tuple[int, int]]): Queue các lực đẩy từ băng
            chuyền, xử lý cuối mỗi frame.
        explosions (list[dict]): Danh sách các ô đang bốc lửa. Mỗi phần tử là
            dict ``{'x': int, 'y': int, 'expiry': int}``.
        powerups (dict[tuple[int, int], str]): Ánh xạ tọa độ lưới ``(gx, gy)``
            đến loại item (``"SPEED"``, ``"RANGE"``, ``"SHIELD"``, ``"GHOST"``).
        active_effects (list): Min-Heap lưu ``(expiry_ms, effect_name)`` để
            biết khi nào cần hủy hiệu ứng item.
        explosion_range (int): Tầm nổ tối đa (số ô) của bom hiện tại.
        show_visualization (bool): Nếu ``True``, vẽ đường đi BFS của kẻ địch.
        map (list[list[int]]): Bản đồ 2D dùng hằng số tile từ ``settings``.
        teleports (list[tuple[int, int]]): Danh sách đúng 2 cổng teleport
            ``[(gx1, gy1), (gx2, gy2)]``.
        teleport_cooldown (int): Thời điểm (ms) người chơi có thể dùng teleport
            tiếp theo; tránh bị teleport liên tục.
        enemies (list[Enemy]): Danh sách kẻ địch đang còn sống.
    """

    def __init__(self):
        """Khởi tạo game: Pygame, cửa sổ, trạng thái người chơi, bản đồ và kẻ địch."""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bomberman DSA - AI Nerf & Pixel-Perfect Collision")
        self.clock = pygame.time.Clock()

        self.player_rect = pygame.Rect(TILE_SIZE + 5, TILE_SIZE + 5, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.player_current_speed = PLAYER_SPEED
        self.last_dx, self.last_dy = 0, 0
        self.is_dead = False

        # 🛡️ DSA Structures
        self.shields = []                 # Stack quản lý Khiên
        self.invulnerable_until = 0
        self.is_ghost = False
        self.bomb_queue = deque()         # Queue xử lý thời gian nổ
        self.forced_move_queue = deque()  # Queue xử lý lực đẩy của Băng chuyền
        self.explosions = []
        self.powerups = {}
        self.active_effects = []          # Min-Heap quản lý thời gian Item
        self.explosion_range = 2
        self.show_visualization = False

        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.teleports = []
        self.teleport_cooldown = 0
        self.setup_map()

        self.enemies = [
            Enemy(GRID_WIDTH - 2, GRID_HEIGHT - 2),
            Enemy(GRID_WIDTH - 2, 1),
            Enemy(1, GRID_HEIGHT - 2),
        ]

    def setup_map(self) -> None:
        """Sinh ngẫu nhiên bản đồ và đặt hai cổng teleport.

        Quy tắc sinh bản đồ:

        - Viền ngoài và các ô chẵn-chẵn ``(r%2==0, c%2==0)`` luôn là ``WALL``.
        - Vùng 3×3 góc trên-trái được giữ trống để người chơi spawn an toàn.
        - Các ô còn lại có xác suất ngẫu nhiên trở thành ``SOFT_WALL``,
          ``TRAP_ICE``, ``CONVEYOR_LEFT``, ``CONVEYOR_RIGHT`` hoặc ``EMPTY``.
        - Sau khi sinh xong, chọn ngẫu nhiên 2 ô trống và đặt cổng ``TRAP_TELEPORT``.
        """
        empty_spaces = []
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if r == 0 or r == GRID_HEIGHT - 1 or c == 0 or c == GRID_WIDTH - 1:
                    self.map[r][c] = WALL
                elif r % 2 == 0 and c % 2 == 0:
                    self.map[r][c] = WALL
                else:
                    if r <= 2 and c <= 2:
                        continue
                    rand = random.random()
                    if rand < 0.25:
                        self.map[r][c] = SOFT_WALL
                    elif rand < 0.30:
                        self.map[r][c] = TRAP_ICE
                    elif rand < 0.32:
                        self.map[r][c] = CONVEYOR_LEFT
                    elif rand < 0.34:
                        self.map[r][c] = CONVEYOR_RIGHT
                    else:
                        empty_spaces.append((c, r))

        # 🌀 Sinh cổng Teleport
        if len(empty_spaces) >= 2:
            self.teleports = random.sample(empty_spaces, 2)
            for tx, ty in self.teleports:
                self.map[ty][tx] = TRAP_TELEPORT

    def move_player(self, dx: float, dy: float) -> None:
        """Di chuyển người chơi theo (dx, dy) pixel, có kiểm tra va chạm.

        Áp dụng di chuyển theo từng trục riêng lẻ (trục X trước, trục Y sau)
        để tránh bị kẹt vào góc tường.

        Args:
            dx (float): Độ dịch chuyển theo trục X (pixel). Có thể là số thực
                khi tính toán trượt băng.
            dy (float): Độ dịch chuyển theo trục Y (pixel).
        """
        self.player_rect.x += dx
        if self.check_collision():
            self.player_rect.x -= dx
        self.player_rect.y += dy
        if self.check_collision():
            self.player_rect.y -= dy

    def handle_input(self) -> None:
        """Đọc đầu vào bàn phím và xử lý di chuyển, đặt bom, bật/tắt debug.

        Được gọi mỗi frame trước :meth:`update`.

        - Phím mũi tên: di chuyển người chơi.
        - ``SPACE``: đặt bom tại ô hiện tại (tối đa 1 bom/ô).
        - ``V``: bật/tắt hiển thị đường đi BFS của kẻ địch.
        - Đóng cửa sổ (``QUIT``): thoát game.

        Không làm gì nếu người chơi đã chết (``self.is_dead``).
        """
        if self.is_dead:
            return
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:  dx = -self.player_current_speed
        if keys[pygame.K_RIGHT]: dx = self.player_current_speed
        if keys[pygame.K_UP]:    dy = -self.player_current_speed
        if keys[pygame.K_DOWN]:  dy = self.player_current_speed

        if dx != 0 or dy != 0:
            self.last_dx, self.last_dy = dx, dy
        self.move_player(dx, dy)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    gx = self.player_rect.centerx // TILE_SIZE
                    gy = self.player_rect.centery // TILE_SIZE
                    can_place = all(not (b['x'] == gx and b['y'] == gy) for b in self.bomb_queue)
                    if can_place:
                        self.bomb_queue.append({
                            'x': gx, 'y': gy,
                            'timer': pygame.time.get_ticks() + 2000,
                        })
                elif event.key == pygame.K_v:
                    self.show_visualization = not self.show_visualization

    def check_collision(self) -> bool:
        """Kiểm tra xem ``player_rect`` có đang đè lên ô tường không.

        Duyệt toàn bộ bản đồ và kiểm tra va chạm pixel-perfect giữa
        ``player_rect`` và từng ô ``WALL`` / ``SOFT_WALL``. Khi ``is_ghost``
        là ``True``, ``SOFT_WALL`` được bỏ qua.

        Returns:
            bool: ``True`` nếu có va chạm với tường, ``False`` nếu không.
        """
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                tile = self.map[r][c]
                if tile == WALL or (tile == SOFT_WALL and not self.is_ghost):
                    tile_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.player_rect.colliderect(tile_rect):
                        return True
        return False

    def handle_explosion(self, start_x: int, start_y: int) -> None:
        """Xử lý vụ nổ từ một quả bom, bao gồm nổ dây chuyền.

        Lan sóng nổ theo 4 hướng và tâm bom, tối đa ``explosion_range`` ô
        mỗi hướng. Sóng nổ dừng lại khi gặp ``WALL`` (không phá được) hoặc
        ``SOFT_WALL`` (phá vỡ, có cơ hội rớt item, rồi dừng).

        Nếu sóng nổ chạm vào quả bom khác, quả bom đó bị kích nổ ngay lập
        tức (chain explosion) bằng cách thêm tọa độ của nó vào hàng đợi BFS
        nội bộ.

        Args:
            start_x (int): Tọa độ cột của bom trên lưới.
            start_y (int): Tọa độ hàng của bom trên lưới.

        Side effects:
            - Thêm các ô bị lửa vào ``self.explosions``.
            - Xóa bom bị kích nổ dây chuyền khỏi ``self.bomb_queue``.
            - Chuyển ``SOFT_WALL`` thành ``EMPTY`` và có thể thêm item vào
              ``self.powerups``.
        """
        now = pygame.time.get_ticks()
        explosion_queue = deque([(start_x, start_y)])

        while explosion_queue:
            bx, by = explosion_queue.popleft()
            for dx, dy in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]:
                for i in range(0 if (dx, dy) == (0, 0) else 1, self.explosion_range + 1):
                    nx, ny = bx + dx * i, by + dy * i
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        tile = self.map[ny][nx]
                        if tile == WALL:
                            break

                        self.explosions.append({'x': nx, 'y': ny, 'expiry': now + 500})

                        # Chain Explosion Logic
                        for bomb in list(self.bomb_queue):
                            if bomb['x'] == nx and bomb['y'] == ny:
                                self.bomb_queue.remove(bomb)
                                explosion_queue.append((nx, ny))

                        # Phá tường & rớt đồ
                        if tile == SOFT_WALL:
                            self.map[ny][nx] = EMPTY
                            if random.random() < 0.15:
                                self.powerups[(nx, ny)] = random.choice(
                                    ["SPEED", "RANGE", "SHIELD", "GHOST"]
                                )
                            break
                        if (dx, dy) == (0, 0):
                            break

    def take_damage(self, now: int) -> None:
        """Xử lý sát thương lên người chơi.

        Nếu đang trong thời gian bất tử (i-frame), bỏ qua hoàn toàn.
        Nếu còn khiên (``shields``), tiêu thụ một lớp (``pop``) và kích
        hoạt i-frame 1.5 giây. Nếu không còn khiên, người chơi chết.

        Args:
            now (int): Thời điểm hiện tại (ms), thường là ``pygame.time.get_ticks()``.

        Side effects:
            - Có thể đặt ``self.is_dead = True``.
            - Có thể cập nhật ``self.invulnerable_until``.
            - In thông báo ra console.
        """
        if now < self.invulnerable_until:
            return
        if self.shields:
            self.shields.pop()
            self.invulnerable_until = now + 1500
            print(f"🛡️ Bể Khiên! Còn {len(self.shields)} lớp.")
        else:
            self.is_dead = True
            print("💥 BẠN ĐÃ CHẾT!")

    def update(self) -> None:
        """Cập nhật toàn bộ trạng thái game cho một frame.

        Thứ tự xử lý:

        1. **Bom & Lửa**: Kích nổ các bom đã hết giờ; dọn lửa hết hạn.
        2. **Va chạm lửa**: Kiểm tra pixel-perfect giữa lửa với người chơi
           và kẻ địch; xử lý sát thương / tiêu diệt.
        3. **Bẫy môi trường**: Xử lý ô băng (trượt), băng chuyền (đẩy),
           và teleport (dịch chuyển).
        4. **Item hết hạn**: Lấy từ Min-Heap các hiệu ứng đã hết hạn và
           reset về trạng thái mặc định.
        5. **Nhặt item**: Nếu người chơi đứng trên ô có item, áp dụng hiệu
           ứng và đẩy thời gian hết hạn vào Min-Heap.
        6. **AI kẻ địch**: Tính đường BFS và di chuyển từng kẻ địch; kiểm
           tra va chạm vật lý với người chơi.

        Không làm gì nếu người chơi đã chết.
        """
        if self.is_dead:
            return
        now = pygame.time.get_ticks()

        # 1. Cập nhật bom & Lửa
        while self.bomb_queue and now >= self.bomb_queue[0]['timer']:
            b = self.bomb_queue.popleft()
            self.handle_explosion(b['x'], b['y'])
        self.explosions = [e for e in self.explosions if e['expiry'] > now]

        # 💥 2. XỬ LÝ VA CHẠM VỚI TIA LỬA (Pixel-perfect)
        for e in self.explosions:
            exp_rect = pygame.Rect(e['x'] * TILE_SIZE, e['y'] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if self.player_rect.colliderect(exp_rect):
                self.take_damage(now)
            for enemy in self.enemies[:]:
                if enemy.rect.colliderect(exp_rect):
                    self.enemies.remove(enemy)
                    print("🎯 Quái đã bị thui rụi!")

        # 3. Xử lý môi trường (Bẫy)
        px_grid = self.player_rect.centerx // TILE_SIZE
        py_grid = self.player_rect.centery // TILE_SIZE
        current_tile = self.map[py_grid][px_grid]
        keys = pygame.key.get_pressed()

        # 🧊 Ô Băng
        if current_tile == TRAP_ICE:
            if not any(keys[k] for k in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]):
                self.move_player(self.last_dx * 0.8, self.last_dy * 0.8)

        # ➡️ Băng Chuyền
        if current_tile == CONVEYOR_LEFT:
            self.forced_move_queue.append((-2, 0))
        elif current_tile == CONVEYOR_RIGHT:
            self.forced_move_queue.append((2, 0))

        while self.forced_move_queue:
            fdx, fdy = self.forced_move_queue.popleft()
            self.move_player(fdx, fdy)

        # 🌀 Teleport
        if (self.teleports
                and now > self.teleport_cooldown
                and (px_grid, py_grid) in self.teleports):
            other = (
                self.teleports[1]
                if (px_grid, py_grid) == self.teleports[0]
                else self.teleports[0]
            )
            self.player_rect.center = (
                other[0] * TILE_SIZE + TILE_SIZE // 2,
                other[1] * TILE_SIZE + TILE_SIZE // 2,
            )
            self.teleport_cooldown = now + 1000

        # 4. Item Min-Heap
        while self.active_effects and self.active_effects[0][0] <= now:
            _, effect = heapq.heappop(self.active_effects)
            if effect == "RESET_SPEED":
                self.player_current_speed = PLAYER_SPEED
            elif effect == "RESET_RANGE":
                self.explosion_range = 2
            elif effect == "RESET_GHOST":
                self.is_ghost = False
                if self.map[py_grid][px_grid] == SOFT_WALL:
                    self.take_damage(now)

        # 🎁 Nhặt Item
        if (px_grid, py_grid) in self.powerups:
            p_type = self.powerups.pop((px_grid, py_grid))
            if p_type == "SPEED":
                self.player_current_speed = 5
                heapq.heappush(self.active_effects, (now + 5000, "RESET_SPEED"))
            elif p_type == "RANGE":
                self.explosion_range = 4
                heapq.heappush(self.active_effects, (now + 7000, "RESET_RANGE"))
            elif p_type == "SHIELD":
                self.shields.append("L")
            elif p_type == "GHOST":
                self.is_ghost = True
                heapq.heappush(self.active_effects, (now + 8000, "RESET_GHOST"))

        # 👾 Enemy AI & Va chạm vật lý với người
        for enemy in self.enemies:
            path = enemy.find_path(px_grid, py_grid, self.map, self.bomb_queue, self.explosion_range, now)
            if path:
                enemy.move()
            if self.player_rect.colliderect(enemy.rect):
                self.take_damage(now)

    def draw(self) -> None:
        """Vẽ toàn bộ màn hình cho frame hiện tại.

        Thứ tự vẽ (painter's algorithm — lớp sau đè lên lớp trước):

        1. Nền đen.
        2. Các ô bản đồ (tường, tường mềm, băng, băng chuyền, teleport).
        3. *(Tùy chọn)* Đường đi BFS của kẻ địch (nếu ``show_visualization``).
        4. Item trên bản đồ.
        5. Lửa nổ và bom.
        6. Người chơi (chớp tắt khi i-frame; màu tím khi Ghost; viền khiên).
        7. Kẻ địch.
        8. Màn hình "GAME OVER" nếu người chơi đã chết.

        Cuối cùng gọi ``pygame.display.flip()`` để đẩy buffer lên màn hình.
        """
        self.screen.fill(BLACK)
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                rect = (c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                tile = self.map[r][c]

                if tile == WALL:
                    pygame.draw.rect(self.screen, GRAY, rect)
                elif tile == SOFT_WALL:
                    color = (100, 50, 10) if self.is_ghost else (139, 69, 19)
                    pygame.draw.rect(self.screen, color, rect)
                elif tile == TRAP_ICE:
                    pygame.draw.rect(self.screen, LIGHT_BLUE_ICE, rect)
                elif tile in [CONVEYOR_LEFT, CONVEYOR_RIGHT]:
                    pygame.draw.rect(self.screen, (50, 50, 50), rect)
                    arrow = "<" if tile == CONVEYOR_LEFT else ">"
                    font = pygame.font.SysFont("Arial", 20, bold=True)
                    self.screen.blit(
                        font.render(arrow, True, WHITE),
                        (c * TILE_SIZE + 15, r * TILE_SIZE + 8),
                    )
                elif tile == TRAP_TELEPORT:
                    pygame.draw.circle(
                        self.screen, MAGENTA,
                        (c * TILE_SIZE + 20, r * TILE_SIZE + 20), 12, 4,
                    )

        # Vẽ tia nhìn AI
        if self.show_visualization:
            for enemy in self.enemies:
                for step in enemy.path:
                    pygame.draw.circle(
                        self.screen, YELLOW,
                        (step[0] * TILE_SIZE + 20, step[1] * TILE_SIZE + 20), 6,
                    )

        # Vẽ Item
        for (gx, gy), p_type in self.powerups.items():
            color = (
                LIGHT_BLUE if p_type == "SPEED" else
                YELLOW     if p_type == "RANGE"  else
                CYAN       if p_type == "SHIELD" else
                PURPLE
            )
            pygame.draw.rect(self.screen, color, (gx * TILE_SIZE + 12, gy * TILE_SIZE + 12, 16, 16))

        # Vẽ Lửa & Bom
        for e in self.explosions:
            pygame.draw.rect(self.screen, ORANGE, (e['x'] * TILE_SIZE, e['y'] * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        for b in self.bomb_queue:
            pygame.draw.circle(self.screen, RED, (b['x'] * TILE_SIZE + 20, b['y'] * TILE_SIZE + 20), 15)

        # Vẽ Player (chớp tắt nếu I-frames)
        now = pygame.time.get_ticks()
        is_invulnerable = now < self.invulnerable_until

        if not self.is_dead:
            if not is_invulnerable or (now // 100) % 2 == 0:
                color = PURPLE if self.is_ghost else BLUE
                pygame.draw.rect(self.screen, color, self.player_rect)
            if self.shields:
                pygame.draw.circle(
                    self.screen, CYAN,
                    self.player_rect.center,
                    TILE_SIZE // 2 + 4, len(self.shields) * 2,
                )

        # Vẽ Quái
        for enemy in self.enemies:
            pygame.draw.rect(self.screen, GREEN, enemy.rect)

        # Vẽ Game Over
        if self.is_dead:
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