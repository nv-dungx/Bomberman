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
from asset_loader import AssetLoader
from sound_manager import SoundManager

# Hằng số FSM — trạng thái game
STATE_MENU             = 0
"""int: Màn hình menu chính."""

STATE_CHARACTER_SELECT = 1
"""int: Màn hình chọn nhân vật (hỗ trợ tránh trùng lặp trong PvP)."""

STATE_TRANSITION       = 2
"""int: Màn hình chuyển cảnh giữa các level."""

STATE_PLAYING          = 3
"""int: Đang trong màn chơi."""

STATE_GAMEOVER         = 4
"""int: Người chơi đã chết (Campaign)."""

STATE_VICTORY          = 5
"""int: Hoàn thành campaign hoặc kết thúc ván PvP."""

STATE_PAUSED           = 6
"""int: Màn hình tạm dừng khi đang trong màn chơi."""

MAX_LEVEL = 5
"""int: Số level tối đa của chế độ Campaign."""

SAVE_FILE = "savegame.json"
"""str: Đường dẫn file lưu checkpoint Campaign."""

HUD_HEIGHT = 40
"""int: Độ cao của thanh thông tin (HUD) hiển thị HP và Level."""

ICE_SPEED_MULTIPLIER = 1.2
"""float: Hệ số tăng tốc khi thực thể đang đi trên ô băng."""

ICE_FRICTION = 0.88
"""float: Hệ số giảm tốc trượt sau khi rời khỏi ô băng."""

ICE_MIN_SLIDE_SPEED = 0.25
"""float: Ngưỡng tốc độ đủ nhỏ để dừng trượt hoàn toàn."""


class Game:
    """Quản lý vòng lặp chính và trạng thái game Bomberman.

    Game sử dụng một FSM (Finite State Machine) đơn giản để điều phối
    các chế độ: menu, chọn tướng, chuyển cảnh, chơi, game over và victory.

    Lớp này chịu trách nhiệm:
    - Lưu/đọc checkpoint Campaign (JSON).
    - Quản lý logic chọn nhân vật động (tự động load từ folder).
    - Khởi tạo level qua LevelManager.
    - Quản lý bomb_queue (Queue) và chuỗi nổ.
    - Xử lý môi trường: băng, băng chuyền, teleport.
    - Điều phối AI kẻ địch và va chạm.
    - Quản lý bề mặt hiển thị phụ (game_surface) để tách biệt HUD.
    - Quản lý âm thanh (BGM và SFX) qua SoundManager.

    Attributes:
        screen (pygame.Surface): Cửa sổ hiển thị tổng (bao gồm cả HUD).
        game_surface (pygame.Surface): Bề mặt render nội dung game chính.
        clock (pygame.time.Clock): Đồng hồ điều chỉnh FPS.
        show_visualization (bool): Bật/tắt hiển thị đường đi BFS của AI (phím V).
        state (int): Trạng thái FSM hiện tại (STATE_MENU, STATE_PLAYING, …).
        saved_level (int): Level đã lưu từ checkpoint, dùng khi Continue Campaign.
        saved_stats (dict): Chỉ số đã lưu từ checkpoint (speed, range, shields).
        level (int | str): Level hiện tại (1–MAX_LEVEL) hoặc ``"PvP"``.
        transition_timer (int): Thời điểm (ms) kết thúc màn chuyển cảnh.
        is_pvp (bool): ``True`` khi đang ở chế độ PvP.
        pvp_winner (int | None): Người thắng PvP (1, 2, 0=hòa, None=chưa xong).
        available_models (list): Danh sách các file nhân vật (.png) hợp lệ.
        p1_model_idx (int): Chỉ mục nhân vật của Player 1.
        p2_model_idx (int): Chỉ mục nhân vật của Player 2.
        level_manager (LevelManager): Quản lý map, enemy, powerup, teleport, cửa.
        player1 (Player | None): Người chơi 1 (WASD + B để đặt bom).
        player2 (Player | None): Người chơi 2 (mũi tên + P để đặt bom), chỉ PvP.
        bomb_queue (deque): Queue chứa các bom đang đếm ngược — DSA: Queue FIFO.
        explosions (list[dict]): Danh sách các ô đang bốc lửa với thời gian hết hạn.
        sm (SoundManager): Quản lý nhạc nền và hiệu ứng âm thanh.
    """

    def __init__(self):
        """Khởi tạo Pygame, màn hình, đọc checkpoint và nạp hình ảnh/âm thanh."""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT + HUD_HEIGHT))
        self.game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        
        pygame.display.set_caption("Bomberman DSA - Campaign & PvP")
        self.clock = pygame.time.Clock()
        self.show_visualization = False

        self.sm = SoundManager()
        self.state = STATE_MENU
        self.paused_at = 0

        saved_data = self.load_progress()
        self.saved_level = saved_data.get("saved_level", 1)
        self.saved_stats = saved_data.get(
            "stats", {"speed": PLAYER_SPEED, "range": 2, "shields": []}
        )

        self.level = 1
        self.transition_timer = 0
        self.is_pvp = False
        self.pvp_winner = None
        self.level_manager = LevelManager()
        self.player1 = None
        self.player2 = None

        # --- QUẢN LÝ CHỌN NHÂN VẬT (TỰ ĐỘNG QUÉT FOLDER) ---
        self.available_models = []
        self.model_previews = {}
        img_dir = os.path.join("assets", "images")
        
        if os.path.exists(img_dir):
            for filename in os.listdir(img_dir):
                if filename.startswith("Player_") and filename.endswith(".png"):
                    model_name = filename[:-4] # Bỏ đuôi .png
                    self.available_models.append(model_name)
                    try:
                        # Tải file sprite sheet gốc
                        sheet_path = os.path.join(img_dir, filename)
                        sheet = pygame.image.load(sheet_path).convert_alpha()
                        # Cắt lấy frame đầu tiên (kích thước chuẩn của Player là 30x30)
                        preview = sheet.subsurface((0, 0, 30, 30))
                        # Phóng to gấp đôi (60x60) để hiển thị rực rỡ trên màn hình chọn tướng
                        scaled_preview = pygame.transform.scale(preview, (60, 60))
                        self.model_previews[model_name] = scaled_preview
                    except Exception as e:
                        print(f"Lỗi tải ảnh preview cho {model_name}: {e}")
        
        self.available_models.sort()
        
        # Fallback an toàn nếu lỡ xóa mất hết file ảnh nhân vật
        if not self.available_models:
            self.available_models = ["Player_1"]
            fallback_surf = pygame.Surface((60, 60))
            fallback_surf.fill(BLUE)
            self.model_previews["Player_1"] = fallback_surf

        self.p1_model_idx = 0
        self.p2_model_idx = 1 if len(self.available_models) > 1 else 0

        # --- NẠP TOÀN BỘ HÌNH ẢNH MÔI TRƯỜNG ---
        self.wall_img = AssetLoader.load_image("wall.png", TILE_SIZE, TILE_SIZE)
        self.soft_wall_img = AssetLoader.load_image("soft_wall.png", TILE_SIZE, TILE_SIZE)
        self.floor_img = AssetLoader.load_image("floor.png", TILE_SIZE, TILE_SIZE)
        self.door_img = AssetLoader.load_image("door.png", TILE_SIZE, TILE_SIZE)

        self.ice_img = AssetLoader.load_image("trap_ice.png", TILE_SIZE, TILE_SIZE)
        self.tele_frames = AssetLoader.load_sprite_sheet("trap_teleport.png", 40, 40, 3)
        if not self.tele_frames or len(self.tele_frames) < 3:
            s = pygame.Surface((40, 40))
            s.fill(MAGENTA)
            self.tele_frames = [s] * 3

        self.item_imgs = {
            "SPEED":  AssetLoader.load_image("item_speed.png", TILE_SIZE, TILE_SIZE),
            "RANGE":  AssetLoader.load_image("item_range.png", TILE_SIZE, TILE_SIZE),
            "SHIELD": AssetLoader.load_image("item_shield.png", TILE_SIZE, TILE_SIZE),
            "GHOST":  AssetLoader.load_image("item_ghost.png", TILE_SIZE, TILE_SIZE)
        }

        self.bomb_frames = AssetLoader.load_sprite_sheet("bomb.png", 40, 40, 3)
        if not self.bomb_frames or len(self.bomb_frames) < 3:
            s = pygame.Surface((40, 40))
            s.fill(RED)
            self.bomb_frames = [s] * 3

        self.exp_center = AssetLoader.load_image("exp_center.png", TILE_SIZE, TILE_SIZE)
        self.exp_body   = AssetLoader.load_image("exp_body.png", TILE_SIZE, TILE_SIZE)
        self.exp_end    = AssetLoader.load_image("exp_end.png", TILE_SIZE, TILE_SIZE)

    def load_progress(self) -> dict:
        """Đọc file ``savegame.json`` và trả về dữ liệu checkpoint."""
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Lỗi đọc save: {e}")
        return {"saved_level": 1, "stats": {"speed": PLAYER_SPEED, "range": 2, "shields": []}}

    def save_progress(self) -> None:
        """Ghi đè checkpoint hiện tại xuống ``savegame.json``."""
        try:
            data = {"saved_level": self.saved_level, "stats": self.saved_stats}
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f)
            print(f"Đã lưu checkpoint: Level {self.saved_level}")
        except Exception as e:
            print(f"Lỗi ghi save: {e}")

    def change_state(self, new_state: int) -> None:
        """Hàm phụ trợ để chuyển đổi trạng thái FSM."""
        self.state = new_state

    def pause_game(self) -> None:
        """Pause game and remember when the pause started."""
        self.paused_at = pygame.time.get_ticks()
        self.change_state(STATE_PAUSED)

    def resume_game(self) -> None:
        """Resume game without letting timers advance while paused."""
        pause_duration = pygame.time.get_ticks() - self.paused_at
        self.paused_at = 0

        for bomb in self.bomb_queue:
            bomb['timer'] += pause_duration

        for explosion in self.explosions:
            explosion['expiry'] += pause_duration

        for enemy in self.level_manager.enemies:
            enemy.animation_timer += pause_duration
            enemy.post_explosion_wait_until += pause_duration

        players = [self.player1]
        if self.is_pvp:
            players.append(self.player2)

        for player in players:
            if not player:
                continue
            player.invulnerable_until += pause_duration
            player.teleport_cooldown += pause_duration
            player.animation_timer += pause_duration
            player.active_effects = [
                (expiry + pause_duration, effect)
                for expiry, effect in player.active_effects
            ]

        self.change_state(STATE_PLAYING)

    def rect_overlaps_tile(self, rect: pygame.Rect, tile_type: int) -> bool:
        """Kiểm tra rect có đang chồng lên một loại tile cụ thể không."""
        grid_x = rect.centerx // TILE_SIZE
        grid_y = rect.centery // TILE_SIZE
        for r in range(max(0, grid_y - 1), min(GRID_HEIGHT, grid_y + 2)):
            for c in range(max(0, grid_x - 1), min(GRID_WIDTH, grid_x + 2)):
                if self.level_manager.map[r][c] != tile_type:
                    continue
                tile_rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if rect.colliderect(tile_rect):
                    return True
        return False

    def prepare_sliding(self, entity) -> None:
        """Khởi tạo dữ liệu trượt cho entity cũ chưa có thuộc tính này."""
        if not hasattr(entity, "slide_dx"):
            entity.slide_dx = 0
        if not hasattr(entity, "slide_dy"):
            entity.slide_dy = 0
        if not hasattr(entity, "move_frac_x"):
            entity.move_frac_x = 0
        if not hasattr(entity, "move_frac_y"):
            entity.move_frac_y = 0

    def consume_subpixel_step(self, entity, axis: str, delta: float) -> int:
        """Tích lũy phần lẻ để chuyển tốc độ float thành bước pixel ổn định."""
        attr = "move_frac_x" if axis == "x" else "move_frac_y"
        total = getattr(entity, attr) + delta
        step = int(total)
        setattr(entity, attr, total - step)
        return step

    def decay_slide(self, entity) -> None:
        """Giảm dần vận tốc trượt cho đến khi entity dừng hẳn."""
        entity.slide_dx *= ICE_FRICTION
        entity.slide_dy *= ICE_FRICTION
        if abs(entity.slide_dx) < ICE_MIN_SLIDE_SPEED:
            entity.slide_dx = 0
        if abs(entity.slide_dy) < ICE_MIN_SLIDE_SPEED:
            entity.slide_dy = 0

    def move_enemy_by_delta(self, enemy, dx: float, dy: float) -> tuple[float, float]:
        """Đẩy enemy theo vận tốc trượt, có kiểm tra va chạm từng trục."""
        moved_x = 0
        moved_y = 0

        if dx:
            dx = self.consume_subpixel_step(enemy, "x", dx)
            enemy.rect.x += dx
            if enemy.check_collision(self.level_manager.map):
                enemy.rect.x -= dx
                enemy.slide_dx = 0
                enemy.move_frac_x = 0
            else:
                moved_x = dx

        if dy:
            dy = self.consume_subpixel_step(enemy, "y", dy)
            enemy.rect.y += dy
            if enemy.check_collision(self.level_manager.map):
                enemy.rect.y -= dy
                enemy.slide_dy = 0
                enemy.move_frac_y = 0
            else:
                moved_y = dy

        return (moved_x, moved_y)

    def move_player_with_ice(self, player, dx: float, dy: float, animate: bool = False) -> None:
        """Di chuyển player, tăng tốc trên băng và trượt chậm dần khi rời băng."""
        self.prepare_sliding(player)
        on_ice = self.rect_overlaps_tile(player.rect, TRAP_ICE)

        if dx or dy:
            if on_ice:
                dx *= ICE_SPEED_MULTIPLIER
                dy *= ICE_SPEED_MULTIPLIER
            desired_dx = dx
            desired_dy = dy
            dx = self.consume_subpixel_step(player, "x", dx)
            dy = self.consume_subpixel_step(player, "y", dy)
            before = player.rect.topleft
            player.move(dx, dy, self.level_manager.map, animate=animate)
            moved_x = player.rect.x - before[0]
            moved_y = player.rect.y - before[1]
            player.slide_dx = desired_dx if on_ice and moved_x else 0
            player.slide_dy = desired_dy if on_ice and moved_y else 0
            return

        if player.slide_dx or player.slide_dy:
            slide_dx = self.consume_subpixel_step(player, "x", player.slide_dx)
            slide_dy = self.consume_subpixel_step(player, "y", player.slide_dy)
            before = player.rect.topleft
            player.move(slide_dx, slide_dy, self.level_manager.map)
            if player.rect.x == before[0]:
                player.slide_dx = 0
                player.move_frac_x = 0
            if player.rect.y == before[1]:
                player.slide_dy = 0
                player.move_frac_y = 0
            if not on_ice:
                self.decay_slide(player)
            return

        player.is_moving = False

    def handle_entity_teleport(self, entity, now: int) -> None:
        """Dịch chuyển player hoặc enemy khi đứng trên ô teleport."""
        if not hasattr(entity, "teleport_cooldown"):
            entity.teleport_cooldown = 0

        teleports = self.level_manager.teleports
        grid_pos = (entity.rect.centerx // TILE_SIZE, entity.rect.centery // TILE_SIZE)
        if not teleports or now <= entity.teleport_cooldown or grid_pos not in teleports:
            return

        other = teleports[1] if grid_pos == teleports[0] else teleports[0]
        entity.rect.center = (
            other[0] * TILE_SIZE + TILE_SIZE // 2,
            other[1] * TILE_SIZE + TILE_SIZE // 2,
        )
        entity.teleport_cooldown = now + 1000
        if hasattr(entity, "path"):
            entity.path = []

    def load_level(self) -> None:
        """Khởi tạo màn chơi mới và sinh các đối tượng game cần thiết."""
        self.bomb_queue = deque()
        self.explosions = []
        
        p1_model = self.available_models[self.p1_model_idx]
        p2_model = self.available_models[self.p2_model_idx]

        if self.is_pvp:
            self.level_manager.generate_pvp_level()
            self.player1 = Player(TILE_SIZE + 5, TILE_SIZE + 5, lives=3, player_model=p1_model)
            self.player2 = Player(
                SCREEN_WIDTH - TILE_SIZE * 2 + 5,
                SCREEN_HEIGHT - TILE_SIZE * 2 + 5,
                lives=3,
                player_model=p2_model
            )
            self.pvp_winner = None
        else:
            self.level_manager.generate_level(self.level)
            self.player1 = Player(TILE_SIZE + 5, TILE_SIZE + 5, lives=1, player_model=p1_model)
            self.player1.current_speed = self.saved_stats.get("speed", PLAYER_SPEED)
            self.player1.explosion_range = self.saved_stats.get("range", 2)
            self.player1.shields = self.saved_stats.get("shields", []).copy()
            self.player2 = None

    def start_campaign(self, is_new_game: bool = False) -> None:
        """Bắt đầu Campaign; chỉ chọn nhân vật khi chuẩn bị vào level 1."""
        self.sm.play_sfx("select")
        self.is_pvp = False
        if is_new_game:
            self.saved_level = 1
            self.saved_stats = {"speed": PLAYER_SPEED, "range": 2, "shields": []}
            self.save_progress()

        self.level = self.saved_level
        if self.level == 1:
            self.state = STATE_CHARACTER_SELECT
        else:
            self.state = STATE_TRANSITION
            self.transition_timer = pygame.time.get_ticks() + 2000

    def start_pvp(self) -> None:
        """Bắt đầu chế độ PvP và chuyển sang Character Selection."""
        self.sm.play_sfx("select")
        self.is_pvp = True
        self.p1_model_idx = 0
        self.p2_model_idx = 1 if len(self.available_models) > 1 else 0
        self.state = STATE_CHARACTER_SELECT

    def handle_input(self) -> None:
        """Xử lý đầu vào phím và cập nhật trạng thái game tương ứng."""
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
                        
            elif self.state == STATE_CHARACTER_SELECT:
                if event.type == pygame.KEYDOWN:
                    num_models = len(self.available_models)
                    
                    if event.key == pygame.K_a:
                        self.sm.play_sfx("select")
                        self.p1_model_idx = (self.p1_model_idx - 1) % num_models
                        if num_models > 1 and self.is_pvp and self.p1_model_idx == self.p2_model_idx:
                            self.p1_model_idx = (self.p1_model_idx - 1) % num_models
                    elif event.key == pygame.K_d:
                        self.sm.play_sfx("select")
                        self.p1_model_idx = (self.p1_model_idx + 1) % num_models
                        if num_models > 1 and self.is_pvp and self.p1_model_idx == self.p2_model_idx:
                            self.p1_model_idx = (self.p1_model_idx + 1) % num_models
                            
                    if self.is_pvp:
                        if event.key == pygame.K_LEFT:
                            self.sm.play_sfx("select")
                            self.p2_model_idx = (self.p2_model_idx - 1) % num_models
                            if num_models > 1 and self.p2_model_idx == self.p1_model_idx:
                                self.p2_model_idx = (self.p2_model_idx - 1) % num_models
                        elif event.key == pygame.K_RIGHT:
                            self.sm.play_sfx("select")
                            self.p2_model_idx = (self.p2_model_idx + 1) % num_models
                            if num_models > 1 and self.p2_model_idx == self.p1_model_idx:
                                self.p2_model_idx = (self.p2_model_idx + 1) % num_models
                                
                    if event.key == pygame.K_RETURN:
                        self.sm.play_sfx("select")
                        if self.is_pvp:
                            self.level = "PvP"
                        else:
                            self.level = self.saved_level
                        self.state = STATE_TRANSITION
                        self.transition_timer = pygame.time.get_ticks() + 2000

            elif self.state == STATE_GAMEOVER:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        if self.is_pvp:
                            self.start_pvp()
                        else:
                            self.start_campaign(is_new_game=False)
                    elif event.key == pygame.K_m:
                        self.change_state(STATE_MENU)

            elif self.state == STATE_VICTORY:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:
                        if not self.is_pvp:
                            self.saved_level = 1
                            self.saved_stats = {"speed": PLAYER_SPEED, "range": 2, "shields": []}
                            self.save_progress()
                        self.change_state(STATE_MENU)
                    elif event.key == pygame.K_r and self.is_pvp:
                        self.start_pvp()

            elif self.state == STATE_PAUSED:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                        self.sm.play_sfx("select")
                        self.resume_game()
                    elif event.key == pygame.K_m:
                        self.sm.play_sfx("select")
                        self.paused_at = 0
                        self.change_state(STATE_MENU)

            elif self.state == STATE_PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.sm.play_sfx("select")
                        self.pause_game()
                    elif event.key == pygame.K_b and not self.player1.is_dead:
                        self.place_bomb(self.player1)
                    elif self.is_pvp and event.key == pygame.K_p and not self.player2.is_dead:
                        self.place_bomb(self.player2)
                    elif event.key == pygame.K_v:
                        self.show_visualization = not self.show_visualization

        if self.state == STATE_PLAYING:
            keys = pygame.key.get_pressed()
            
            if not self.player1.is_dead:
                dx1, dy1 = 0, 0
                if keys[pygame.K_a]:
                    dx1 = -self.player1.current_speed
                if keys[pygame.K_d]:
                    dx1 = self.player1.current_speed
                if keys[pygame.K_w]:
                    dy1 = -self.player1.current_speed
                if keys[pygame.K_s]:
                    dy1 = self.player1.current_speed
                    
                if dx1 != 0 or dy1 != 0:
                    self.player1.last_dx = dx1
                    self.player1.last_dy = dy1
                self.player1.player_input_active = dx1 != 0 or dy1 != 0
                self.move_player_with_ice(self.player1, dx1, dy1, animate=self.player1.player_input_active)
            else:
                self.player1.player_input_active = False

            if self.is_pvp and not self.player2.is_dead:
                dx2, dy2 = 0, 0
                if keys[pygame.K_LEFT]:
                    dx2 = -self.player2.current_speed
                if keys[pygame.K_RIGHT]:
                    dx2 = self.player2.current_speed
                if keys[pygame.K_UP]:
                    dy2 = -self.player2.current_speed
                if keys[pygame.K_DOWN]:
                    dy2 = self.player2.current_speed
                    
                if dx2 != 0 or dy2 != 0:
                    self.player2.last_dx = dx2
                    self.player2.last_dy = dy2
                self.player2.player_input_active = dx2 != 0 or dy2 != 0
                self.move_player_with_ice(self.player2, dx2, dy2, animate=self.player2.player_input_active)
            elif self.is_pvp:
                self.player2.player_input_active = False

    def place_bomb(self, player) -> None:
        """Xử lý logic đặt bom cho người chơi."""
        gx = player.rect.centerx // TILE_SIZE
        gy = player.rect.centery // TILE_SIZE
        
        can_place = True
        for b in self.bomb_queue:
            if b['x'] == gx and b['y'] == gy:
                can_place = False
                break
                
        if can_place:
            self.bomb_queue.append({
                'x': gx,
                'y': gy,
                'timer': pygame.time.get_ticks() + 2000,
                'range': player.explosion_range,
            })
            self.sm.play_sfx("place_bomb")

    def handle_explosion(self, start_x: int, start_y: int, exp_range: int) -> None:
        """Xử lý lan truyền vụ nổ và kích hoạt chuỗi bom (chain explosion)."""
        now = pygame.time.get_ticks()
        explosion_queue = deque([(start_x, start_y)])
        for enemy in self.level_manager.enemies:
            enemy.on_explosion_started(now)
        
        self.sm.play_sfx("explosion")

        while explosion_queue:
            bx, by = explosion_queue.popleft()
            self.explosions.append({'x': bx, 'y': by, 'expiry': now + 500, 'type': 'center', 'angle': 0})

            # Kiểm tra softwall tại vị trí trung tâm bom
            center_tile = self.level_manager.map[by][bx]
            if center_tile == SOFT_WALL:
                self.level_manager.map[by][bx] = EMPTY
                if random.random() < 0.20:
                    self.level_manager.powerups[(bx, by)] = random.choice(
                        ["SPEED", "RANGE", "SHIELD", "GHOST"]
                    )

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                angle = 0
                if dx == 1:
                    angle = 0
                elif dx == -1:
                    angle = 180
                elif dy == -1:
                    angle = 90
                elif dy == 1:
                    angle = 270

                for i in range(1, exp_range + 1):
                    nx = bx + dx * i
                    ny = by + dy * i
                    
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        tile = self.level_manager.map[ny][nx]
                        if tile == WALL:
                            break

                        is_last = (i == exp_range)
                        if not is_last:
                            nnx = nx + dx
                            nny = ny + dy
                            if 0 <= nnx < GRID_WIDTH and 0 <= nny < GRID_HEIGHT:
                                if self.level_manager.map[nny][nnx] in [WALL, SOFT_WALL]:
                                    is_last = True

                        if is_last:
                            part_type = 'end'
                        else:
                            part_type = 'body'
                            
                        self.explosions.append({'x': nx, 'y': ny, 'expiry': now + 500, 'type': part_type, 'angle': angle})

                        for bomb in list(self.bomb_queue):
                            if bomb['x'] == nx and bomb['y'] == ny:
                                self.bomb_queue.remove(bomb)
                                explosion_queue.append((nx, ny))

                        if tile == SOFT_WALL:
                            self.level_manager.map[ny][nx] = EMPTY
                            if random.random() < 0.20:
                                self.level_manager.powerups[(nx, ny)] = random.choice(
                                    ["SPEED", "RANGE", "SHIELD", "GHOST"]
                                )
                            break

    def update(self) -> None:
        """Cập nhật toàn bộ trạng thái game mỗi khung hình."""
        now = pygame.time.get_ticks()

        if self.state == STATE_TRANSITION:
            if now >= self.transition_timer:
                self.load_level()
                self.change_state(STATE_PLAYING)
            return
            
        if self.state != STATE_PLAYING:
            return

        if not self.is_pvp and self.player1.is_dead:
            self.change_state(STATE_GAMEOVER)
            return

        if self.is_pvp:
            if self.player1.is_dead and self.player2.is_dead:
                self.pvp_winner = 0
                self.change_state(STATE_VICTORY)
                return
            elif self.player1.is_dead:
                self.pvp_winner = 2
                self.change_state(STATE_VICTORY)
                return
            elif self.player2.is_dead:
                self.pvp_winner = 1
                self.change_state(STATE_VICTORY)
                return

        while self.bomb_queue and now >= self.bomb_queue[0]['timer']:
            b = self.bomb_queue.popleft()
            self.handle_explosion(b['x'], b['y'], b['range'])
            
        # Lọc các vụ nổ đã hết hạn
        active_explosions = []
        for e in self.explosions:
            if e['expiry'] > now:
                active_explosions.append(e)
        self.explosions = active_explosions

        for e in self.explosions:
            exp_rect = pygame.Rect(e['x'] * TILE_SIZE, e['y'] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            
            if not self.player1.is_dead and self.player1.rect.colliderect(exp_rect):
                old_h = self.player1.lives
                self.player1.take_damage(now)
                if self.player1.lives < old_h:
                    self.sm.play_sfx("hurt")
                    
            if self.is_pvp and not self.player2.is_dead and self.player2.rect.colliderect(exp_rect):
                old_h = self.player2.lives
                self.player2.take_damage(now)
                if self.player2.lives < old_h:
                    self.sm.play_sfx("hurt")
                    
            for enemy in self.level_manager.enemies[:]:
                if enemy.rect.colliderect(exp_rect):
                    self.sm.play_sfx("enemy_die")
                    self.level_manager.enemies.remove(enemy)

        players = [self.player1]
        if self.is_pvp:
            players.append(self.player2)

        for p in players:
            if p.is_dead:
                continue
                
            px_grid = p.rect.centerx // TILE_SIZE
            py_grid = p.rect.centery // TILE_SIZE
            current_tile = self.level_manager.map[py_grid][px_grid]

            if current_tile == CONVEYOR_LEFT:
                p.forced_move_queue.append((-2, 0))
            elif current_tile == CONVEYOR_RIGHT:
                p.forced_move_queue.append((2, 0))
                
            while p.forced_move_queue:
                fdx, fdy = p.forced_move_queue.popleft()
                input_active = getattr(p, "player_input_active", False)
                p.move(
                    fdx,
                    fdy,
                    self.level_manager.map,
                    animate=input_active,
                    update_direction=not input_active,
                )

            p.update_items(now, current_tile)
            if (px_grid, py_grid) in self.level_manager.powerups:
                p_type = self.level_manager.powerups.pop((px_grid, py_grid))
                p.pick_up_item(p_type, now)
                self.sm.play_sfx("pickup")

            teleports = self.level_manager.teleports
            if teleports:
                self.handle_entity_teleport(p, now)

        if not self.is_pvp:
            px = self.player1.rect.centerx // TILE_SIZE
            py = self.player1.rect.centery // TILE_SIZE
            door = self.level_manager.door_pos
            door_open = False
            
            if door and self.level_manager.map[door[1]][door[0]] == EMPTY and len(self.level_manager.enemies) == 0 and (px, py) == door:
                door_open = True
                
            if door_open:
                if self.level >= MAX_LEVEL:
                    self.change_state(STATE_VICTORY)
                else:
                    self.saved_level += 1
                    self.level = self.saved_level
                    self.saved_stats = {
                        "speed": self.player1.current_speed,
                        "range": self.player1.explosion_range,
                        "shields": self.player1.shields.copy(),
                    }
                    self.save_progress()
                    self.state = STATE_TRANSITION
                    self.transition_timer = pygame.time.get_ticks() + 2000
                return

        for enemy in self.level_manager.enemies:
            self.prepare_sliding(enemy)
            enemy_on_ice = self.rect_overlaps_tile(enemy.rect, TRAP_ICE)

            if not enemy.can_move(now):
                enemy.path = []
                continue

            ex = enemy.rect.centerx // TILE_SIZE
            ey = enemy.rect.centery // TILE_SIZE
            if 0 <= ex < GRID_WIDTH and 0 <= ey < GRID_HEIGHT:
                e_tile = self.level_manager.map[ey][ex]
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

            self.handle_entity_teleport(enemy, now)

            if not enemy_on_ice and (enemy.slide_dx or enemy.slide_dy):
                self.move_enemy_by_delta(enemy, enemy.slide_dx, enemy.slide_dy)
                self.decay_slide(enemy)
                self.handle_entity_teleport(enemy, now)

                if self.player1.rect.colliderect(enemy.rect):
                    old_h = self.player1.lives
                    self.player1.take_damage(now)
                    if self.player1.lives < old_h:
                        self.sm.play_sfx("hurt")
                continue

            px = self.player1.rect.centerx // TILE_SIZE
            py = self.player1.rect.centery // TILE_SIZE
            path = enemy.find_path(
                px, py, self.level_manager.map,
                self.bomb_queue, self.player1.explosion_range, now,
            )
            
            moved_x, moved_y = 0, 0
            if path:
                speed_multiplier = ICE_SPEED_MULTIPLIER if enemy_on_ice else 1.0
                moved_x, moved_y = enemy.move(self.level_manager.map, speed_multiplier)
                if enemy_on_ice and (moved_x or moved_y):
                    enemy.slide_dx = moved_x
                    enemy.slide_dy = moved_y
            elif enemy.slide_dx or enemy.slide_dy:
                self.move_enemy_by_delta(enemy, enemy.slide_dx, enemy.slide_dy)
                if not enemy_on_ice:
                    self.decay_slide(enemy)

            self.handle_entity_teleport(enemy, now)
                
            if self.player1.rect.colliderect(enemy.rect):
                old_h = self.player1.lives
                self.player1.take_damage(now)
                if self.player1.lives < old_h:
                    self.sm.play_sfx("hurt")

    def draw(self) -> None:
        """Render toàn bộ nội dung game lên màn hình mỗi frame."""
        self.screen.fill((20, 20, 20))
        now = self.paused_at if self.state == STATE_PAUSED else pygame.time.get_ticks()
        font = pygame.font.SysFont("Arial", 24, bold=True)
        
        if self.state in [STATE_PLAYING, STATE_PAUSED, STATE_GAMEOVER, STATE_VICTORY]:
            p1_hp = font.render(f"P1 HP: {self.player1.lives}", True, BLUE)
            self.screen.blit(p1_hp, (20, 8))
            
            if self.is_pvp:
                p2_hp = font.render(f"P2 HP: {self.player2.lives}", True, RED)
                self.screen.blit(p2_hp, (SCREEN_WIDTH - 150, 8))
            
            if self.is_pvp:
                mode_label = "PVP MATCH"
            else:
                mode_label = f"CAMPAIGN - LEVEL {self.level}"
                
            mode_txt = font.render(mode_label, True, WHITE)
            self.screen.blit(mode_txt, (SCREEN_WIDTH // 2 - mode_txt.get_width() // 2, 8))

        self.game_surface.fill(BLACK)

        if self.state == STATE_MENU:
            font_title = pygame.font.SysFont("Arial", 64, bold=True)
            font_opt = pygame.font.SysFont("Arial", 32)
            
            title = font_title.render("BOMBERMAN", True, WHITE)
            self.game_surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120)))

            opt1 = font_opt.render("[1] PvP Mode (2 Players)", True, RED)
            opt2 = font_opt.render("[2] New Campaign", True, WHITE)
            
            self.game_surface.blit(opt1, opt1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
            self.game_surface.blit(opt2, opt2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))

            if self.saved_level > 1:
                opt3 = font_opt.render(f"[3] Continue Campaign (Level {self.saved_level})", True, YELLOW)
                self.game_surface.blit(opt3, opt3.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80)))

        elif self.state == STATE_CHARACTER_SELECT:
            f_title = pygame.font.SysFont("Arial", 48, True)
            f_hint = pygame.font.SysFont("Arial", 24)
            
            title = f_title.render("SELECT YOUR CHARACTER", True, YELLOW)
            self.game_surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

            # --- Hiển thị Player 1 ---
            p1_label = font.render("PLAYER 1 (A/D)", True, BLUE)
            self.game_surface.blit(p1_label, (150, 150))
            
            p1_model_name = self.available_models[self.p1_model_idx]
            if p1_model_name in self.model_previews:
                preview_img = self.model_previews[p1_model_name]
                # Canh giữa ảnh preview dưới dòng label
                preview_x = 150 + p1_label.get_width() // 2 - preview_img.get_width() // 2
                self.game_surface.blit(preview_img, (preview_x, 200))
                
            p1_name = font.render(p1_model_name, True, WHITE)
            # Canh giữa dòng text tên nhân vật
            text_x = 150 + p1_label.get_width() // 2 - p1_name.get_width() // 2
            self.game_surface.blit(p1_name, (text_x, 280))
            
            # --- Hiển thị Player 2 (Chỉ trong chế độ PvP) ---
            if self.is_pvp:
                p2_label = font.render("PLAYER 2 (LEFT/RIGHT)", True, RED)
                self.game_surface.blit(p2_label, (SCREEN_WIDTH - 350, 150))
                
                p2_model_name = self.available_models[self.p2_model_idx]
                if p2_model_name in self.model_previews:
                    preview_img = self.model_previews[p2_model_name]
                    # Canh giữa ảnh preview dưới dòng label
                    preview_x = SCREEN_WIDTH - 350 + p2_label.get_width() // 2 - preview_img.get_width() // 2
                    self.game_surface.blit(preview_img, (preview_x, 200))
                    
                p2_name = font.render(p2_model_name, True, WHITE)
                # Canh giữa dòng text tên nhân vật
                text_x = SCREEN_WIDTH - 350 + p2_label.get_width() // 2 - p2_name.get_width() // 2
                self.game_surface.blit(p2_name, (text_x, 280))

            hint = f_hint.render("Press ENTER to Start Game", True, GRAY)
            self.game_surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 450))

        elif self.state == STATE_TRANSITION:
            font_level = pygame.font.SysFont("Arial", 72, bold=True)
            if self.is_pvp:
                label = "PVP BATTLE"
            else:
                label = f"LEVEL {self.level}"
            lvl_txt = font_level.render(label, True, WHITE)
            self.game_surface.blit(lvl_txt, lvl_txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))

        elif self.state in [STATE_PLAYING, STATE_PAUSED, STATE_GAMEOVER, STATE_VICTORY]:
            
            any_ghost = False
            if self.player1 and not self.player1.is_dead and self.player1.is_ghost:
                any_ghost = True
            if self.is_pvp and self.player2 and not self.player2.is_dead and self.player2.is_ghost:
                any_ghost = True

            for r in range(GRID_HEIGHT):
                for c in range(GRID_WIDTH):
                    pos = (c * TILE_SIZE, r * TILE_SIZE)
                    self.game_surface.blit(self.floor_img, pos)
                    
                    tile = self.level_manager.map[r][c]
                    if tile == WALL:
                        self.game_surface.blit(self.wall_img, pos)
                    elif tile == SOFT_WALL:
                        if any_ghost:
                            ghost_wall = self.soft_wall_img.copy()
                            ghost_wall.fill((100, 100, 100), special_flags=pygame.BLEND_RGB_MULT)
                            self.game_surface.blit(ghost_wall, pos)
                        else:
                            self.game_surface.blit(self.soft_wall_img, pos)
                    elif tile == TRAP_ICE:
                        self.game_surface.blit(self.ice_img, pos)
                    elif tile in [CONVEYOR_LEFT, CONVEYOR_RIGHT]:
                        pygame.draw.rect(self.game_surface, (50, 50, 50), (pos[0], pos[1], TILE_SIZE, TILE_SIZE))
                        if tile == CONVEYOR_LEFT:
                            arrow = "<"
                        else:
                            arrow = ">"
                        font_arrow = pygame.font.SysFont("Arial", 20, bold=True)
                        self.game_surface.blit(
                            font_arrow.render(arrow, True, WHITE),
                            (c * TILE_SIZE + 15, r * TILE_SIZE + 8),
                        )
                    elif tile == TRAP_TELEPORT:
                        t_frame = (now // 150) % 3
                        self.game_surface.blit(self.tele_frames[t_frame], pos)

            if not self.is_pvp and self.level_manager.door_pos:
                door_col = self.level_manager.door_pos[0]
                door_row = self.level_manager.door_pos[1]
                if self.level_manager.map[door_row][door_col] == EMPTY:
                    door_x = door_col * TILE_SIZE
                    door_y = door_row * TILE_SIZE
                    self.game_surface.blit(self.door_img, (door_x, door_y))

            if self.show_visualization:
                for enemy in self.level_manager.enemies:
                    for step in enemy.path:
                        pygame.draw.circle(
                            self.game_surface, YELLOW,
                            (step[0] * TILE_SIZE + 20, step[1] * TILE_SIZE + 20), 6,
                        )

            for (gx, gy), p_type in self.level_manager.powerups.items():
                self.game_surface.blit(self.item_imgs[p_type], (gx * TILE_SIZE, gy * TILE_SIZE))

            for e in self.explosions:
                if e['type'] == 'center':
                    img = self.exp_center
                elif e['type'] == 'body':
                    img = pygame.transform.rotate(self.exp_body, e['angle'])
                else:
                    img = pygame.transform.rotate(self.exp_end, e['angle'])
                self.game_surface.blit(img, (e['x'] * TILE_SIZE, e['y'] * TILE_SIZE))

            b_frame = (now // 200) % 3
            for b in self.bomb_queue:
                self.game_surface.blit(
                    self.bomb_frames[b_frame], 
                    (b['x'] * TILE_SIZE, b['y'] * TILE_SIZE)
                )

            for enemy in self.level_manager.enemies:
                enemy.draw(self.game_surface, now)

            if self.player1 and not self.player1.is_dead:
                self.player1.draw(self.game_surface, now)

            if self.is_pvp and self.player2 and not self.player2.is_dead:
                self.player2.draw(self.game_surface, now)

            if self.state == STATE_GAMEOVER:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.game_surface.blit(overlay, (0, 0))
                
                game_over_txt = pygame.font.SysFont("Arial", 24, bold=True).render(
                    "GAME OVER - Press R to Restart or M for Menu", True, RED
                )
                self.game_surface.blit(game_over_txt, (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2))

            elif self.state == STATE_PAUSED:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 185))
                self.game_surface.blit(overlay, (0, 0))

                pause_font = pygame.font.SysFont("Arial", 72, bold=True)
                hint_font = pygame.font.SysFont("Arial", 28, bold=True)

                pause_txt = pause_font.render("PAUSED", True, YELLOW)
                self.game_surface.blit(
                    pause_txt,
                    pause_txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 45)),
                )

                hint_txt = hint_font.render("ENTER/ESC Resume   M Menu", True, WHITE)
                self.game_surface.blit(
                    hint_txt,
                    hint_txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 35)),
                )

            elif self.state == STATE_VICTORY:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.game_surface.blit(overlay, (0, 0))

                if self.is_pvp:
                    if self.pvp_winner == 0:
                        txt = "DRAW!"
                        color = YELLOW
                    elif self.pvp_winner == 1:
                        txt = "PLAYER 1 WINS!"
                        color = BLUE
                    else:
                        txt = "PLAYER 2 WINS!"
                        color = RED
                else:
                    txt = "VICTORY! CAMPAIGN COMPLETED!"
                    color = GOLD

                font_vic = pygame.font.SysFont("Arial", 72, bold=True)
                vic = font_vic.render(txt, True, color)
                self.game_surface.blit(vic, vic.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)))
                
                replay_txt = pygame.font.SysFont("Arial", 24, bold=True).render(
                    "Press R to play again or M for Menu", True, WHITE
                )
                self.game_surface.blit(replay_txt, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 + 50))

        self.screen.blit(self.game_surface, (0, HUD_HEIGHT))
        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_input()
        game.update()
        game.draw()
        game.clock.tick(FPS)
