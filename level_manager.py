"""
level_manager.py
----------------
Module quản lý sinh bản đồ và thực thể cho từng màn chơi trong game Bomberman.

Module này cung cấp lớp :class:`LevelManager` với hai chế độ sinh màn:

- **Campaign** (:meth:`LevelManager.generate_level`): Bản đồ ngẫu nhiên với
  độ khó tăng dần theo ``level_num``; bao gồm tường, băng chuyền, bẫy băng,
  cổng teleport, cửa thoát màn và kẻ địch phân cấp.
- **PvP** (:meth:`LevelManager.generate_pvp_level`): Bản đồ đối kháng hai
  người; không có quái, không có cửa, hai góc đối xứng được giữ trống cho
  mỗi người chơi.
"""
import random
from settings import *
from enemy import DumbEnemy, SmartEnemy, EliteEnemy


class LevelManager:
    """Quản lý trạng thái và sinh khung cảnh cho mỗi màn chơi.

    Lớp này chịu trách nhiệm khởi tạo bản đồ, spawn kẻ địch và vật phẩm.
    Sau khi gọi :meth:`generate_level` hoặc :meth:`generate_pvp_level`, các
    thuộc tính ``map``, ``enemies``, ``teleports``, ``door_pos`` và
    ``powerups`` sẵn sàng để module khác (Game loop) đọc và sử dụng.

    Attributes:
        map (list[list[int]]): Bản đồ 2D dùng hằng số tile từ ``settings``.
            Kích thước ``GRID_HEIGHT × GRID_WIDTH``. Rỗng cho đến khi gọi
            một trong hai phương thức generate.
        door_pos (tuple[int, int] | None): Tọa độ lưới ``(gx, gy)`` của cửa
            thoát màn, ẩn sau một ``SOFT_WALL``. ``None`` trong chế độ PvP.
        teleports (list[tuple[int, int]]): Danh sách đúng 2 cổng teleport
            ``[(gx1, gy1), (gx2, gy2)]``. Rỗng nếu không đủ ô trống.
        enemies (list[Enemy]): Danh sách kẻ địch được spawn, kiểu phụ thuộc
            vào ``level_num``. Rỗng trong chế độ PvP.
        powerups (dict[tuple[int, int], str]): Ánh xạ tọa độ lưới đến loại
            item. Ban đầu rỗng; được Game loop điền vào khi tường mềm bị phá.
    """

    def __init__(self):
        """Khởi tạo LevelManager với các cấu trúc dữ liệu rỗng.

        Các thuộc tính sẽ được điền khi gọi :meth:`generate_level` hoặc
        :meth:`generate_pvp_level`.
        """
        self.map: list[list[int]] = []
        self.door_pos: tuple[int, int] | None = None
        self.teleports: list[tuple[int, int]] = []
        self.enemies: list = []
        self.powerups: dict[tuple[int, int], str] = {}

    def generate_level(self, level_num: int) -> None:
        """Sinh toàn bộ cấu trúc màn Campaign theo số thứ tự màn.

        Thuật toán sinh bản đồ theo 4 bước tuần tự:

        **Bước 1 — Tường & Băng chuyền:**
        Viền ngoài và các ô chẵn-chẵn luôn là ``WALL``. Góc 3×3 trên-trái
        giữ ``EMPTY`` để tránh spawn kill người chơi. Các ô còn lại được
        phân bổ xác suất: 25% ``SOFT_WALL``, 3% ``CONVEYOR_LEFT``, 3%
        ``CONVEYOR_RIGHT``, còn lại ``EMPTY``.

        **Bước 2 — Cụm băng (TRAP_ICE):**
        Sinh ``min(level_num + 1, 6)`` cụm băng liên tiếp, mỗi cụm dài 2–4
        ô theo hướng ngẫu nhiên (ngang hoặc dọc). Cụm chỉ được đặt trên ô
        ``EMPTY`` đã có và không chồng lên góc an toàn.

        **Bước 3 — Cổng Teleport:**
        Chọn ngẫu nhiên 2 ô ``EMPTY`` còn lại và đặt ``TRAP_TELEPORT``.

        **Bước 4 — Cửa thoát màn & Spawn kẻ địch:**
        Cửa ẩn sau một ``SOFT_WALL`` ngẫu nhiên. Số kẻ địch là
        ``2 + level_num``; spawn tại các ô cách vị trí người chơi ≥ 8 bước
        Manhattan (chống spawn kill). Tier kẻ địch theo level:

        - Level 1–2: toàn ``DumbEnemy``.
        - Level 3–4: xen kẽ ``SmartEnemy`` và ``DumbEnemy``.
        - Level ≥ 5: xen kẽ ``EliteEnemy`` và ``SmartEnemy``.

        Args:
            level_num (int): Số thứ tự màn chơi (bắt đầu từ 1). Ảnh hưởng
                đến số lượng cụm băng, số kẻ địch và tier kẻ địch.

        Side effects:
            Ghi đè toàn bộ ``self.map``, ``self.enemies``, ``self.teleports``,
            ``self.door_pos`` và ``self.powerups``.
        """
        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.teleports = []
        self.door_pos = None
        self.enemies = []
        self.powerups = {}

        empty_spaces: list[tuple[int, int]] = []
        soft_walls_list: list[tuple[int, int]] = []

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
            if not empty_spaces:
                break
            length = random.choice([2, 3, 4])
            dx, dy = random.choice([(1, 0), (0, 1)])
            random.shuffle(empty_spaces)

            for start_x, start_y in empty_spaces:
                valid_cluster = True
                cluster_cells: list[tuple[int, int]] = []
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

        # 4. Giấu Cửa & Sinh Quái theo cấp độ (Có chống Spawn Kill)
        if soft_walls_list:
            self.door_pos = random.choice(soft_walls_list)

        num_enemies = 2 + level_num
        safe_spawn_spaces = [
            (x, y) for (x, y) in empty_spaces
            if abs(x - 1) + abs(y - 1) >= 8
        ]
        target_spaces = safe_spawn_spaces if len(safe_spawn_spaces) >= num_enemies else empty_spaces

        if len(target_spaces) >= num_enemies:
            enemy_spawns = random.sample(target_spaces, num_enemies)
            for i, (ex, ey) in enumerate(enemy_spawns):
                # Level 1-2: Quái Ngu. Level 3-4: Trộn Ngu và Khôn. Level 5+: Toàn Tinh Anh.
                if level_num <= 2:
                    self.enemies.append(DumbEnemy(ex, ey))
                elif level_num <= 4:
                    if i % 2 == 0:
                        self.enemies.append(SmartEnemy(ex, ey))
                    else:
                        self.enemies.append(DumbEnemy(ex, ey))
                else:
                    if i % 2 == 0:
                        self.enemies.append(EliteEnemy(ex, ey))
                    else:
                        self.enemies.append(SmartEnemy(ex, ey))

    def generate_pvp_level(self) -> None:
        """Sinh bản đồ đối kháng PvP: đối xứng, không quái, không cửa thoát.

        Bản đồ tuân theo cùng quy tắc tường cứng của Campaign (viền + ô
        chẵn-chẵn), nhưng có hai điểm khác biệt chính:

        - **Hai vùng an toàn đối xứng**: góc trên-trái (``r ≤ 2, c ≤ 2``)
          dành cho Player 1, góc dưới-phải (``r ≥ GRID_HEIGHT-3, c ≥ GRID_WIDTH-3``)
          dành cho Player 2 — cả hai vùng luôn là ``EMPTY``.
        - **Mật độ tường mềm cao hơn** (40% thay vì 25%) để tạo nhiều vật
          cản, khuyến khích chiến thuật đào hầm và đặt bẫy.
        - Không sinh băng chuyền, bẫy băng, teleport, cửa thoát hay kẻ địch.

        Side effects:
            Ghi đè toàn bộ ``self.map``, ``self.enemies``, ``self.teleports``,
            ``self.door_pos`` và ``self.powerups`` về trạng thái ban đầu.
        """
        self.map = [[EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.teleports = []
        self.door_pos = None
        self.enemies = []
        self.powerups = {}

        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if r == 0 or r == GRID_HEIGHT - 1 or c == 0 or c == GRID_WIDTH - 1:
                    self.map[r][c] = WALL
                elif r % 2 == 0 and c % 2 == 0:
                    self.map[r][c] = WALL
                else:
                    # Vùng an toàn cho Player 1 (Góc trên trái)
                    if r <= 2 and c <= 2:
                        continue
                    # Vùng an toàn cho Player 2 (Góc dưới phải)
                    if r >= GRID_HEIGHT - 3 and c >= GRID_WIDTH - 3:
                        continue

                    rand = random.random()
                    if rand < 0.40:  # Rải nhiều tường mềm hơn Campaign để anh em đào hầm
                        self.map[r][c] = SOFT_WALL