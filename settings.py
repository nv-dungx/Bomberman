# settings.py

# 1. Cấu hình hệ thống lưới
TILE_SIZE = 40
GRID_WIDTH = 21   # Số ô ngang (nên chọn số lẻ để tường bao quanh đẹp)
GRID_HEIGHT = 15  # Số ô dọc
SCREEN_WIDTH = TILE_SIZE * GRID_WIDTH
SCREEN_HEIGHT = TILE_SIZE * GRID_HEIGHT
FPS = 60

# 2. Định nghĩa màu sắc (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)  # Màu tường cứng
RED = (255, 0, 0)       # Màu bom
BLUE = (0, 0, 255)      # Màu nhân vật
YELLOW = (255, 255, 0)  # Màu hiệu ứng nổ (tạm thời)

# 3. Định nghĩa các loại ô (Map Tiles)
EMPTY = 0
WALL = 1
SOFT_WALL = 2

# 4. Cấu hình Nhân vật
PLAYER_SPEED = 3  # Tốc độ di chuyển theo đơn vị ô lưới
PLAYER_WIDTH = 30
PLAYER_HEIGHT = 30
PLAYER_SIZE_RATIO = 0.7  # Nhân vật chiếm 70% kích thước ô để tránh kẹt
PLAYER_SIZE = int(TILE_SIZE * PLAYER_SIZE_RATIO)
# Phần bù để vẽ nhân vật vào chính giữa ô
PLAYER_OFFSET = (TILE_SIZE - PLAYER_SIZE) // 2