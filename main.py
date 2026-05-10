"""
main.py
Entry point cho game Bomberman.

Module này quản lý vòng lặp chính, trạng thái game, đầu vào người chơi,
cập nhật màn chơi và lưu/đọc checkpoint Campaign.
Hỗ trợ cả chế độ Campaign và PvP trong cùng một lớp Game.

Các CTDL & Giải thuật được sử dụng:
- Queue (deque)    : bom đếm ngược, chain explosion, lực đẩy băng chuyền.
- BFS              : AI kẻ địch tìm đường, thoát vùng nguy hiểm.
- Min-Heap (heapq) : quản lý thời hạn power-up (trong Player).
- Stack (list)     : quản lý khiên chồng nhau (trong Player).
- FSM              : điều phối các trạng thái game (menu, playing, gameover…).
"""

import pygame
import sys
import random
import json
import os
from collections import deque
from settings import *
from player import Player
from level_manager import LevelManager

# Hằng số FSM — trạng thái game

STATE_MENU       = 0
"""int: Màn hình menu chính."""

STATE_TRANSITION = 1
"""int: Màn hình chuyển cảnh giữa các level."""

STATE_PLAYING    = 2
"""int: Đang trong màn chơi."""

STATE_GAMEOVER   = 3
"""int: Người chơi đã chết (Campaign)."""

STATE_VICTORY    = 4
"""int: Hoàn thành campaign hoặc kết thúc ván PvP."""

MAX_LEVEL = 5
"""int: Số level tối đa của chế độ Campaign."""

SAVE_FILE = "savegame.json"
"""str: Đường dẫn file lưu checkpoint Campaign."""


class Game:
    """Quản lý vòng lặp chính và trạng thái game Bomberman.

    Game sử dụng một FSM (Finite State Machine) đơn giản để điều phối
    các chế độ: menu, chuyển cảnh, chơi, game over và victory.

    Lớp này chịu trách nhiệm:
    - Lưu/đọc checkpoint Campaign (JSON).
    - Khởi tạo level qua LevelManager.
    - Quản lý bomb_queue (Queue) và chuỗi nổ.
    - Xử lý môi trường: băng, băng chuyền, teleport.
    - Điều phối AI kẻ địch và va chạm.

    Attributes:
        screen (pygame.Surface): Cửa sổ hiển thị game.
        clock (pygame.time.Clock): Đồng hồ điều chỉnh FPS.
        show_visualization (bool): Bật/tắt hiển thị đường đi BFS của AI (phím V).
        state (int): Trạng thái FSM hiện tại (STATE_MENU, STATE_PLAYING, …).
        saved_level (int): Level đã lưu từ checkpoint, dùng khi Continue Campaign.
        saved_stats (dict): Chỉ số đã lưu từ checkpoint (speed, range, shields).
        level (int | str): Level hiện tại (1–MAX_LEVEL) hoặc ``"PvP"``.
        transition_timer (int): Thời điểm (ms) kết thúc màn chuyển cảnh.
        is_pvp (bool): ``True`` khi đang ở chế độ PvP.
        pvp_winner (int | None): Người thắng PvP (1, 2, 0=hòa, None=chưa xong).
        level_manager (LevelManager): Quản lý map, enemy, powerup, teleport, cửa.
        player1 (Player | None): Người chơi 1 (WASD + B để đặt bom).
        player2 (Player | None): Người chơi 2 (mũi tên + P để đặt bom), chỉ PvP.
        bomb_queue (deque): Queue chứa các bom đang đếm ngược — DSA: Queue FIFO.
        explosions (list[dict]): Danh sách các ô đang bốc lửa với thời gian hết hạn.
    """

    def __init__(self):
        """Khởi tạo Pygame, màn hình, đọc checkpoint và chuẩn bị FSM."""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bomberman DSA - Campaign & PvP")
        self.clock = pygame.time.Clock()
        self.show_visualization = False

        self.state = STATE_MENU

        # Đọc toàn bộ dữ liệu checkpoint từ JSON
        saved_data = self.load_progress()
        self.saved_level = saved_data.get("saved_level", 1)
        # Lưu trữ thông số từ checkpoint (mặc định nếu chưa có save)
        self.saved_stats = saved_data.get(
            "stats", {"speed": PLAYER_SPEED, "range": 2, "shields": []}
        )

        self.level = 1
        self.transition_timer = 0

        self.is_pvp = False
        self.pvp_winner = None  # 1 = P1 thắng, 2 = P2 thắng, 0 = hòa

        self.level_manager = LevelManager()
        self.player1 = None
        self.player2 = None

    # Checkpoint (Save / Load)

    def load_progress(self) -> dict:
        """Đọc file ``savegame.json`` và trả về dữ liệu checkpoint.

        Nếu file không tồn tại hoặc bị lỗi, trả về giá trị mặc định
        (level 1, chỉ số gốc).

        Returns:
            dict: Dữ liệu checkpoint với hai khóa:
                - ``"saved_level"`` (int): Level đã lưu.
                - ``"stats"`` (dict): speed, range, shields.
        """
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Lỗi đọc save: {e}")
        return {"saved_level": 1, "stats": {"speed": PLAYER_SPEED, "range": 2, "shields": []}}

    def save_progress(self) -> None:
        """Ghi đè checkpoint hiện tại (level + chỉ số) xuống ``savegame.json``.

        Được gọi khi người chơi đi qua cửa sang level tiếp theo,
        hoặc khi bắt đầu New Game (reset checkpoint).

        Side effects:
            Tạo / ghi đè file ``savegame.json``.
            In thông báo xác nhận hoặc lỗi ra console.
        """
        try:
            data = {
                "saved_level": self.saved_level,
                "stats": self.saved_stats,
            }
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f)
            print(f"Đã lưu checkpoint: Level {self.saved_level}")
        except Exception as e:
            print(f"Lỗi ghi save: {e}")

    # Khởi tạo màn chơi

    def load_level(self) -> None:
        """Khởi tạo màn chơi mới và sinh các đối tượng game cần thiết.

        - **PvP**: sinh map PvP, tạo player1 (WASD) và player2 (mũi tên),
          mỗi người 3 mạng.
        - **Campaign**: sinh map theo ``self.level``, tạo player1 với 1 mạng
          và khôi phục chỉ số từ checkpoint (speed, range, shields).

        Đặt lại ``bomb_queue`` (Queue rỗng) và ``explosions`` cho màn mới.
        """
        self.bomb_queue = deque()   # DSA: Queue — reset hàng đợi bom
        self.explosions = []

        if self.is_pvp:
            self.level_manager.generate_pvp_level()
            # P1 góc trái trên, P2 góc phải dưới
            # Mặc định player_model="Player_1"
            self.player1 = Player(TILE_SIZE + 5, TILE_SIZE + 5, lives=3)
            # Khởi tạo Player 2 với model riêng biệt
            self.player2 = Player(
                SCREEN_WIDTH - TILE_SIZE * 2 + 5,
                SCREEN_HEIGHT - TILE_SIZE * 2 + 5,
                lives=3,
                player_model="Player_2"
            )
            self.pvp_winner = None
        else:
            self.level_manager.generate_level(self.level)
            self.player1 = Player(TILE_SIZE + 5, TILE_SIZE + 5, lives=1)

            # Khôi phục thống số từ checkpoint cho Player 1
            self.player1.current_speed   = self.saved_stats.get("speed", PLAYER_SPEED)
            self.player1.explosion_range = self.saved_stats.get("range", 2)
            self.player1.shields         = self.saved_stats.get("shields", []).copy()

            self.player2 = None  # Campaign chỉ có 1 người

    def start_campaign(self, is_new_game: bool = False) -> None:
        """Bắt đầu chế độ Campaign và chuyển sang STATE_TRANSITION.

        Args:
            is_new_game (bool): Nếu ``True``, xóa checkpoint cũ và bắt đầu
                từ level 1. Nếu ``False``, tiếp tục từ ``saved_level``.
        """
        self.is_pvp = False
        if is_new_game:
            # Xóa checkpoint cũ nếu chọn chơi lại từ đầu
            self.saved_level = 1
            self.saved_stats = {"speed": PLAYER_SPEED, "range": 2, "shields": []}
            self.save_progress()

        self.level = self.saved_level
        self.state = STATE_TRANSITION
        self.transition_timer = pygame.time.get_ticks() + 2500

    def start_pvp(self) -> None:
        """Bắt đầu chế độ PvP và chuyển sang STATE_TRANSITION."""
        self.is_pvp = True
        self.level = "PvP"
        self.state = STATE_TRANSITION
        self.transition_timer = pygame.time.get_ticks() + 2000

    # Input

    def handle_input(self) -> None:
        """Xử lý đầu vào phím và cập nhật trạng thái game tương ứng.

        Điều hướng theo ``self.state``:

        - **STATE_MENU**: [1] PvP, [2] New Campaign, [3] Continue Campaign.
        - **STATE_GAMEOVER**: [R] chơi lại, [M] về menu.
        - **STATE_VICTORY**: [M] về menu, [R] chơi lại (PvP).
        - **STATE_PLAYING**:
            - [B] Player 1 đặt bom — đẩy vào ``bomb_queue`` (Queue).
            - [P] Player 2 đặt bom (chỉ PvP) — đẩy vào ``bomb_queue``.
            - [V] bật/tắt Visualization mode.
            - WASD: di chuyển Player 1.
            - Mũi tên: di chuyển Player 2.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.state == STATE_MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        self.start_pvp()
                    elif event.key == pygame.K_2:
                        self.start_campaign(is_new_game=True)
                    elif event.key == pygame.K_3 and self.saved_level > 1:
                        self.start_campaign(is_new_game=False)

            elif self.state == STATE_GAMEOVER:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        if self.is_pvp:
                            self.start_pvp()
                        else:
                            self.start_campaign(is_new_game=False)
                    elif event.key == pygame.K_m:
                        self.state = STATE_MENU

            elif self.state == STATE_VICTORY:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:
                        if not self.is_pvp:
                            # Reset checkpoint sau khi hoàn thành campaign
                            self.saved_level = 1
                            self.saved_stats = {"speed": PLAYER_SPEED, "range": 2, "shields": []}
                            self.save_progress()
                        self.state = STATE_MENU
                    elif event.key == pygame.K_r and self.is_pvp:
                        self.start_pvp()

            elif self.state == STATE_PLAYING:
                if event.type == pygame.KEYDOWN:
                    # Đặt bom Player 1 (phím B)
                    if event.key == pygame.K_b and not self.player1.is_dead:
                        gx = self.player1.rect.centerx // TILE_SIZE
                        gy = self.player1.rect.centery // TILE_SIZE
                        if all(not (b['x'] == gx and b['y'] == gy) for b in self.bomb_queue):
                            self.bomb_queue.append({
                                'x': gx, 'y': gy,
                                'timer': pygame.time.get_ticks() + 2000,
                                'range': self.player1.explosion_range,
                            })
                    # Đặt bom Player 2 (phím P) — chỉ PvP
                    elif self.is_pvp and event.key == pygame.K_p and not self.player2.is_dead:
                        gx = self.player2.rect.centerx // TILE_SIZE
                        gy = self.player2.rect.centery // TILE_SIZE
                        if all(not (b['x'] == gx and b['y'] == gy) for b in self.bomb_queue):
                            self.bomb_queue.append({
                                'x': gx, 'y': gy,
                                'timer': pygame.time.get_ticks() + 2000,
                                'range': self.player2.explosion_range,
                            })
                    elif event.key == pygame.K_v:
                        self.show_visualization = not self.show_visualization

        if self.state == STATE_PLAYING:
            keys = pygame.key.get_pressed()

            # Di chuyển Player 1 (WASD)
            if not self.player1.is_dead:
                dx1, dy1 = 0, 0
                if keys[pygame.K_a]: dx1 = -self.player1.current_speed
                if keys[pygame.K_d]: dx1 =  self.player1.current_speed
                if keys[pygame.K_w]: dy1 = -self.player1.current_speed
                if keys[pygame.K_s]: dy1 =  self.player1.current_speed
                if dx1 != 0 or dy1 != 0:
                    self.player1.last_dx, self.player1.last_dy = dx1, dy1
                self.player1.move(dx1, dy1, self.level_manager.map)

            # Di chuyển Player 2 (mũi tên) — chỉ PvP
            if self.is_pvp and not self.player2.is_dead:
                dx2, dy2 = 0, 0
                if keys[pygame.K_LEFT]:  dx2 = -self.player2.current_speed
                if keys[pygame.K_RIGHT]: dx2 =  self.player2.current_speed
                if keys[pygame.K_UP]:    dy2 = -self.player2.current_speed
                if keys[pygame.K_DOWN]:  dy2 =  self.player2.current_speed
                if dx2 != 0 or dy2 != 0:
                    self.player2.last_dx, self.player2.last_dy = dx2, dy2
                self.player2.move(dx2, dy2, self.level_manager.map)

    # Explosion

    def handle_explosion(self, start_x: int, start_y: int, exp_range: int) -> None:
        """Xử lý lan truyền vụ nổ và kích hoạt chuỗi bom (chain explosion).

        DSA — BFS Chain Explosion:
        Dùng ``explosion_queue`` (Queue) để lan truyền nổ theo BFS.
        Khi tia lửa chạm bom khác, bom đó bị xóa khỏi ``bomb_queue``
        và tọa độ của nó được đẩy vào ``explosion_queue`` để kích nổ tiếp.

        Quy tắc lan tia lửa:
        - Lan 4 hướng, tối đa ``exp_range`` ô.
        - Dừng khi gặp WALL (không phá được, không xuyên).
        - Dừng sau khi phá SOFT_WALL (phá được, không xuyên qua).
        - 20% xác suất rơi power-up khi phá SOFT_WALL.

        Args:
            start_x (int): Cột tâm bom trên lưới.
            start_y (int): Hàng tâm bom trên lưới.
            exp_range (int): Tầm nổ của bom này (lấy từ ``bomb['range']``).
        """
        now = pygame.time.get_ticks()
        explosion_queue = deque([(start_x, start_y)])  # DSA: Queue BFS chain explosion

        while explosion_queue:
            bx, by = explosion_queue.popleft()
            for dx, dy in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]:
                for i in range(0 if (dx, dy) == (0, 0) else 1, exp_range + 1):
                    nx, ny = bx + dx * i, by + dy * i
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        tile = self.level_manager.map[ny][nx]
                        if tile == WALL:
                            break

                        self.explosions.append({'x': nx, 'y': ny, 'expiry': now + 500})

                        # Chain explosion: bom trong tầm nổ bị kích ngay lập tức
                        for bomb in list(self.bomb_queue):
                            if bomb['x'] == nx and bomb['y'] == ny:
                                self.bomb_queue.remove(bomb)
                                explosion_queue.append((nx, ny))

                        if tile == SOFT_WALL:
                            self.level_manager.map[ny][nx] = EMPTY
                            if random.random() < 0.20:  # PvP: drop rate 20%
                                self.level_manager.powerups[(nx, ny)] = random.choice(
                                    ["SPEED", "RANGE", "SHIELD", "GHOST"]
                                )
                            break
                        if (dx, dy) == (0, 0):
                            break

    # Update

    def update(self) -> None:
        """Cập nhật toàn bộ trạng thái game mỗi khung hình.

        Bỏ qua nếu không ở STATE_PLAYING (hoặc xử lý transition timer).

        Thứ tự xử lý khi STATE_PLAYING:
        1. **Win/Loss check**: Campaign (player1 chết → GAMEOVER);
           PvP (cả hai chết → hòa, một chết → người còn lại thắng).
        2. **Bom hết hạn**: popleft() từ ``bomb_queue`` → ``handle_explosion()``.
        3. **Dọn explosion** đã hết hạn hiển thị.
        4. **Va chạm explosion**: player và enemy bị trừ máu / xóa.
        5. **Môi trường** (cho từng player còn sống):
            - Ô băng (TRAP_ICE): tiếp tục trượt theo đà khi buông phím.
            - Băng chuyền: đẩy vào ``forced_move_queue`` rồi áp dụng.
            - Power-up: ``update_items()`` reset hiệu ứng hết hạn; nhặt item mới.
            - Teleport: dịch chuyển và đặt cooldown 1 giây.
        6. **Cửa qua màn** (Campaign): mở khi hết enemy, player bước vào → lưu checkpoint.
        7. **AI kẻ địch**: xử lý băng chuyền, BFS tìm đường, di chuyển, va chạm player1.
        """
        now = pygame.time.get_ticks()

        if self.state == STATE_TRANSITION:
            if now >= self.transition_timer:
                self.load_level()
                self.state = STATE_PLAYING
            return
        if self.state != STATE_PLAYING:
            return

        # 1. Win / Loss
        if not self.is_pvp and self.player1.is_dead:
            self.state = STATE_GAMEOVER
            return

        if self.is_pvp:
            if self.player1.is_dead and self.player2.is_dead:
                self.pvp_winner = 0   # Hòa
                self.state = STATE_VICTORY
                return
            elif self.player1.is_dead:
                self.pvp_winner = 2   # P2 thắng
                self.state = STATE_VICTORY
                return
            elif self.player2.is_dead:
                self.pvp_winner = 1   # P1 thắng
                self.state = STATE_VICTORY
                return

        # 2. Bom hết hạn → nổ (DSA: Queue popleft)
        while self.bomb_queue and now >= self.bomb_queue[0]['timer']:
            b = self.bomb_queue.popleft()
            self.handle_explosion(b['x'], b['y'], b['range'])
        self.explosions = [e for e in self.explosions if e['expiry'] > now]

        # 3. Va chạm explosion với player và enemy
        for e in self.explosions:
            exp_rect = pygame.Rect(e['x'] * TILE_SIZE, e['y'] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if not self.player1.is_dead and self.player1.rect.colliderect(exp_rect):
                self.player1.take_damage(now)
            if self.is_pvp and not self.player2.is_dead and self.player2.rect.colliderect(exp_rect):
                self.player2.take_damage(now)
            for enemy in self.level_manager.enemies[:]:
                if enemy.rect.colliderect(exp_rect):
                    self.level_manager.enemies.remove(enemy)

        # 4. Xử lý môi trường cho từng player
        players = [self.player1]
        if self.is_pvp:
            players.append(self.player2)

        keys = pygame.key.get_pressed()  # Dùng để kiểm tra trượt băng

        for p in players:
            if p.is_dead:
                continue
            px_grid = p.rect.centerx // TILE_SIZE
            py_grid = p.rect.centery // TILE_SIZE
            current_tile = self.level_manager.map[py_grid][px_grid]

            # Ô Băng (TRAP_ICE): trượt theo đà khi buông phím
            on_ice = False
            for r in range(max(0, py_grid - 1), min(GRID_HEIGHT, py_grid + 2)):
                for c in range(max(0, px_grid - 1), min(GRID_WIDTH, px_grid + 2)):
                    if self.level_manager.map[r][c] == TRAP_ICE:
                        ice_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        if p.rect.colliderect(ice_rect):
                            on_ice = True
                            break
                if on_ice:
                    break

            if on_ice:
                is_moving = False
                if p == self.player1:
                    is_moving = any(keys[k] for k in [pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s])
                elif p == self.player2:
                    is_moving = any(keys[k] for k in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN])

                if not is_moving:
                    # Duy trì tốc độ trượt bằng current_speed theo hướng cuối cùng
                    slide_x = p.current_speed if p.last_dx > 0 else (-p.current_speed if p.last_dx < 0 else 0)
                    slide_y = p.current_speed if p.last_dy > 0 else (-p.current_speed if p.last_dy < 0 else 0)
                    p.move(slide_x, slide_y, self.level_manager.map)

            # Băng chuyền: đẩy lực vào Queue rồi áp dụng ngay trong frame này
            if current_tile == CONVEYOR_LEFT:
                p.forced_move_queue.append((-2, 0))
            elif current_tile == CONVEYOR_RIGHT:
                p.forced_move_queue.append((2, 0))
            while p.forced_move_queue:
                fdx, fdy = p.forced_move_queue.popleft()
                p.move(fdx, fdy, self.level_manager.map)

            # Power-up: reset hiệu ứng hết hạn (Min-Heap) và nhặt item mới
            p.update_items(now, current_tile)
            if (px_grid, py_grid) in self.level_manager.powerups:
                p_type = self.level_manager.powerups.pop((px_grid, py_grid))
                p.pick_up_item(p_type, now)

            # Teleport
            teleports = self.level_manager.teleports
            if teleports and now > p.teleport_cooldown and (px_grid, py_grid) in teleports:
                other = (teleports[1] if (px_grid, py_grid) == teleports[0] else teleports[0])
                p.rect.center = (
                    other[0] * TILE_SIZE + TILE_SIZE // 2,
                    other[1] * TILE_SIZE + TILE_SIZE // 2,
                )
                p.teleport_cooldown = now + 1000

        # 5. Cửa qua màn (Campaign)
        if not self.is_pvp:
            px = self.player1.rect.centerx // TILE_SIZE
            py = self.player1.rect.centery // TILE_SIZE
            door = self.level_manager.door_pos
            door_open = (
                door
                and self.level_manager.map[door[1]][door[0]] == EMPTY
                and len(self.level_manager.enemies) == 0
                and (px, py) == door
            )
            if door_open:
                if self.level >= MAX_LEVEL:
                    self.state = STATE_VICTORY
                else:
                    self.saved_level += 1

                    # Lưu checkpoint: tạo snapshot chỉ số player hiện tại
                    self.saved_stats = {
                        "speed":   self.player1.current_speed,
                        "range":   self.player1.explosion_range,
                        "shields": self.player1.shields.copy(),
                    }
                    self.save_progress()
                    self.start_campaign(is_new_game=False)
                return

        # 6. AI kẻ địch (Campaign)
        for enemy in self.level_manager.enemies:
            ex = enemy.rect.centerx // TILE_SIZE
            ey = enemy.rect.centery // TILE_SIZE
            if 0 <= ex < GRID_WIDTH and 0 <= ey < GRID_HEIGHT:
                e_tile = self.level_manager.map[ey][ex]
                # Băng chuyền tác động lên enemy: đẩy ngang, xóa path BFS hiện tại
                if e_tile == CONVEYOR_LEFT:
                    enemy.rect.x -= 2
                    if enemy.check_collision(self.level_manager.map):
                        enemy.rect.x += 2
                    enemy.path = []
                elif e_tile == CONVEYOR_RIGHT:
                    enemy.rect.x += 2
                    if enemy.check_collision(self.level_manager.map):
                        enemy.rect.x -= 2
                    enemy.path = []

            px = self.player1.rect.centerx // TILE_SIZE
            py = self.player1.rect.centery // TILE_SIZE
            # BFS tìm đường mỗi frame
            path = enemy.find_path(
                px, py, self.level_manager.map,
                self.bomb_queue, self.player1.explosion_range, now,
            )
            if path:
                enemy.move(self.level_manager.map)
            if self.player1.rect.colliderect(enemy.rect):
                self.player1.take_damage(now)

    # Draw

    def draw(self) -> None:
        """Render toàn bộ nội dung game lên màn hình mỗi frame.

        Vẽ theo ``self.state``:

        - **STATE_MENU**: tiêu đề và các lựa chọn ([1] PvP, [2] New, [3] Continue).
        - **STATE_TRANSITION**: tên level hoặc "PVP BATTLE".
        - **STATE_PLAYING / GAMEOVER / VICTORY**:
            1. Map (WALL, SOFT_WALL, trap tiles, cửa qua màn).
            2. Visualization mode: vòng tròn vàng dọc đường đi BFS của enemy.
            3. Power-up, explosion (lửa), bom.
            4. Enemy (vẽ thông qua hàm draw riêng để hiện sprite).
            5. Player 1 (vẽ qua draw riêng); Player 2 nếu PvP.
            6. HUD: HP và Level / chế độ.
            7. Overlay mờ + text GAME OVER hoặc VICTORY.
        """
        self.screen.fill(BLACK)

        if self.state == STATE_MENU:
            font_title = pygame.font.SysFont("Arial", 64, bold=True)
            font_opt   = pygame.font.SysFont("Arial", 32)

            title = font_title.render("BOMBERMAN DSA", True, WHITE)
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120)))

            opt1 = font_opt.render("[1] PvP Mode (2 Players)", True, RED)
            opt2 = font_opt.render("[2] New Campaign", True, WHITE)
            self.screen.blit(opt1, opt1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
            self.screen.blit(opt2, opt2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))

            if self.saved_level > 1:
                opt3 = font_opt.render(
                    f"[3] Continue Campaign (Level {self.saved_level})", True, YELLOW
                )
                self.screen.blit(opt3, opt3.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80)))

        elif self.state == STATE_TRANSITION:
            font_level = pygame.font.SysFont("Arial", 72, bold=True)
            label = "PVP BATTLE" if self.is_pvp else f"LEVEL {self.level}"
            lvl_txt = font_level.render(label, True, WHITE)
            self.screen.blit(lvl_txt, lvl_txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))

        elif self.state in [STATE_PLAYING, STATE_GAMEOVER, STATE_VICTORY]:

            # Kiểm tra có player nào đang Ghost mode không (để đổi màu tường mềm)
            any_ghost = (
                (self.player1 and not self.player1.is_dead and self.player1.is_ghost)
                or (self.is_pvp and self.player2 and not self.player2.is_dead and self.player2.is_ghost)
            )

            # Vẽ Map
            for r in range(GRID_HEIGHT):
                for c in range(GRID_WIDTH):
                    rect = (c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    tile = self.level_manager.map[r][c]

                    if tile == WALL:
                        pygame.draw.rect(self.screen, GRAY, rect)
                    elif tile == SOFT_WALL:
                        # Tường mềm tối hơn khi có người dùng Ghost (visual hint)
                        wall_color = (100, 50, 10) if any_ghost else (139, 69, 19)
                        pygame.draw.rect(self.screen, wall_color, rect)
                    elif tile == TRAP_ICE:
                        pygame.draw.rect(self.screen, LIGHT_BLUE_ICE, rect)
                    elif tile in [CONVEYOR_LEFT, CONVEYOR_RIGHT]:
                        pygame.draw.rect(self.screen, (50, 50, 50), rect)
                        arrow = "<" if tile == CONVEYOR_LEFT else ">"
                        font_arrow = pygame.font.SysFont("Arial", 20, bold=True)
                        self.screen.blit(
                            font_arrow.render(arrow, True, WHITE),
                            (c * TILE_SIZE + 15, r * TILE_SIZE + 8),
                        )
                    elif tile == TRAP_TELEPORT:
                        pygame.draw.circle(
                            self.screen, MAGENTA,
                            (c * TILE_SIZE + 20, r * TILE_SIZE + 20), 12, 4,
                        )

            # Cửa qua màn (Campaign) — chỉ hiển thị khi map đã mở (EMPTY)
            if (not self.is_pvp
                    and self.level_manager.door_pos
                    and self.level_manager.map[self.level_manager.door_pos[1]]
                                              [self.level_manager.door_pos[0]] == EMPTY):
                pygame.draw.rect(
                    self.screen, GOLD,
                    (
                        self.level_manager.door_pos[0] * TILE_SIZE,
                        self.level_manager.door_pos[1] * TILE_SIZE,
                        TILE_SIZE, TILE_SIZE,
                    ),
                )

            # Visualization mode: hiển thị đường đi BFS của enemy (phím V)
            if self.show_visualization:
                for enemy in self.level_manager.enemies:
                    for step in enemy.path:
                        pygame.draw.circle(
                            self.screen, YELLOW,
                            (step[0] * TILE_SIZE + 20, step[1] * TILE_SIZE + 20), 6,
                        )

            # Power-up, Lửa, Bom
            for (gx, gy), p_type in self.level_manager.powerups.items():
                color = (LIGHT_BLUE if p_type == "SPEED" else
                         YELLOW     if p_type == "RANGE"  else
                         CYAN       if p_type == "SHIELD" else PURPLE)
                pygame.draw.rect(self.screen, color, (gx * TILE_SIZE + 12, gy * TILE_SIZE + 12, 16, 16))

            for e in self.explosions:
                pygame.draw.rect(self.screen, ORANGE,
                                 (e['x'] * TILE_SIZE, e['y'] * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            for b in self.bomb_queue:
                pygame.draw.circle(self.screen, RED,
                                   (b['x'] * TILE_SIZE + 20, b['y'] * TILE_SIZE + 20), 15)
            
            # Vẽ Enemy bằng cơ chế hoạt ảnh (Animation)
            current_time = pygame.time.get_ticks()
            for enemy in self.level_manager.enemies:
                enemy.draw(self.screen, current_time)

            # Player 1
            if self.player1 and not self.player1.is_dead:
                self.player1.draw(self.screen, current_time)

            # Player 2 (PvP)
            if self.is_pvp and self.player2 and not self.player2.is_dead:
                self.player2.draw(self.screen, current_time)

            # HUD: HP và Level / chế độ
            font = pygame.font.SysFont("Arial", 22, bold=True)
            if self.player1:
                self.screen.blit(font.render(f"P1 HP: {self.player1.lives}", True, BLUE), (10, 10))

            if self.is_pvp:
                self.screen.blit(font.render("PvP Mode", True, WHITE), (SCREEN_WIDTH - 120, 10))
                if self.player2:
                    self.screen.blit(
                        font.render(f"P2 HP: {self.player2.lives}", True, RED),
                        (SCREEN_WIDTH - 150, 40),
                    )
            else:
                self.screen.blit(
                    font.render(f"Level: {self.level}", True, WHITE),
                    (SCREEN_WIDTH - 100, 10),
                )

            # Overlay GAME OVER
            if self.state == STATE_GAMEOVER:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.screen.blit(overlay, (0, 0))
                self.screen.blit(
                    font.render("GAME OVER - Press R to Restart or M for Menu", True, RED),
                    (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2),
                )

            # Overlay VICTORY
            elif self.state == STATE_VICTORY:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.screen.blit(overlay, (0, 0))

                if self.is_pvp:
                    txt   = "DRAW!" if self.pvp_winner == 0 else f"PLAYER {self.pvp_winner} WINS!"
                    color = YELLOW if self.pvp_winner == 0 else (BLUE if self.pvp_winner == 1 else RED)
                else:
                    txt, color = "VICTORY! CAMPAIGN COMPLETED!", GOLD

                font_vic = pygame.font.SysFont("Arial", 72, bold=True)
                vic = font_vic.render(txt, True, color)
                self.screen.blit(vic, vic.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)))
                self.screen.blit(
                    font.render("Press R to play again or M for Menu", True, WHITE),
                    (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 + 50),
                )

        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_input()
        game.update()
        game.draw()
        game.clock.tick(FPS)