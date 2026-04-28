"""
settings.py
-----------
Module cấu hình toàn cục cho game Bomberman.

Định nghĩa tất cả các hằng số dùng chung giữa các module:
màn hình, lưới, màu sắc, loại ô (tile), và thông số nhân vật.
"""

# ---------------------------------------------------------------------------
# 1. Cấu hình lưới (Grid) - Mở rộng chiều ngang sang phải
# ---------------------------------------------------------------------------

TILE_SIZE: int = 40
"""Kích thước mỗi ô lưới (pixel)."""

GRID_WIDTH: int = 31
"""Số cột của lưới bản đồ."""

GRID_HEIGHT: int = 15
"""Số hàng của lưới bản đồ."""

SCREEN_WIDTH: int = TILE_SIZE * GRID_WIDTH
"""Chiều rộng cửa sổ game (pixel), bằng TILE_SIZE × GRID_WIDTH."""

SCREEN_HEIGHT: int = TILE_SIZE * GRID_HEIGHT
"""Chiều cao cửa sổ game (pixel), bằng TILE_SIZE × GRID_HEIGHT."""

FPS: int = 60
"""Số khung hình tối đa mỗi giây."""

# ---------------------------------------------------------------------------
# 2. Màu sắc (RGB)
# ---------------------------------------------------------------------------

BLACK = (0, 0, 0)
"""Màu đen — nền mặc định."""

GRAY = (100, 100, 100)
"""Màu xám — tường cứng (không phá được)."""

BROWN = (139, 69, 19)
"""Màu nâu — tường mềm (có thể phá bằng bom)."""

RED = (255, 0, 0)
"""Màu đỏ — đại diện cho bom."""

BLUE = (0, 0, 255)
"""Màu xanh dương — đại diện cho người chơi (Player)."""

ORANGE = (255, 165, 0)
"""Màu cam — hiệu ứng vụ nổ."""

GREEN = (0, 255, 0)
"""Màu xanh lá — đại diện cho kẻ địch (Enemy)."""

LIGHT_BLUE = (173, 216, 230)
"""Màu xanh nhạt — item tăng tốc độ."""

YELLOW = (255, 255, 0)
"""Màu vàng — item tăng tầm nổ."""

CYAN = (0, 255, 255)
"""Màu xanh cyan — item Shield (khiên)."""

PURPLE = (160, 32, 240)
"""Màu tím — item Ghost (đi xuyên tường)."""

MAGENTA = (255, 0, 255)
"""Màu hồng — bẫy / ô dịch chuyển (Teleport)."""

LIGHT_BLUE_ICE = (173, 216, 230)
"""Màu xanh băng — bẫy trơn trượt (Ice trap)."""

DARK_GRAY = (50, 50, 50)
"""Màu xám tối — hiệu ứng trượt (Sliding)."""

WHITE = (255, 255, 255)
"""Màu trắng — dùng chung cho UI / văn bản."""

# ---------------------------------------------------------------------------
# 3. Định nghĩa Tiles
# ---------------------------------------------------------------------------

EMPTY: int = 0
"""Ô trống — nhân vật có thể đi qua tự do."""

WALL: int = 1
"""Tường cứng — không thể phá hủy, chặn nổ và di chuyển."""

SOFT_WALL: int = 2
"""Tường mềm — bị phá hủy khi bị sóng nổ chạm vào."""

TRAP_TELEPORT: int = 3
"""Bẫy dịch chuyển — đưa nhân vật tới vị trí ngẫu nhiên khác."""

TRAP_ICE: int = 4
"""Bẫy băng — khiến nhân vật trượt và mất kiểm soát tạm thời."""

CONVEYOR_LEFT: int = 5
"""Băng tải trái — đẩy nhân vật sang trái."""

CONVEYOR_RIGHT: int = 5
"""Băng tải phải — đẩy nhân vật sang phải.

Note:
    Hiện tại CONVEYOR_LEFT và CONVEYOR_RIGHT dùng chung giá trị ``5``.
    Cần phân biệt thành hai giá trị riêng nếu muốn xử lý hai chiều độc lập.
"""

# ---------------------------------------------------------------------------
# 4. Thông số thực thể
# ---------------------------------------------------------------------------

PLAYER_SPEED: int = 3
"""Tốc độ di chuyển của người chơi (pixel/frame)."""

PLAYER_WIDTH: int = 30
"""Chiều rộng sprite người chơi (pixel)."""

PLAYER_HEIGHT: int = 30
"""Chiều cao sprite người chơi (pixel)."""

ENEMY_SPEED: int = 2
"""Tốc độ di chuyển của kẻ địch (pixel/frame)."""
