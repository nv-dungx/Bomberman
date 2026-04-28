# settings.py

# 1. Cấu hình lưới (Grid) - Mở rộng chiều ngang sang phải
TILE_SIZE = 40
GRID_WIDTH = 31   
GRID_HEIGHT = 15
SCREEN_WIDTH = TILE_SIZE * GRID_WIDTH
SCREEN_HEIGHT = TILE_SIZE * GRID_HEIGHT
FPS = 60

# 2. Màu sắc (RGB)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)  # Tường cứng
BROWN = (139, 69, 19)   # Tường mềm
RED = (255, 0, 0)       # Bom
BLUE = (0, 0, 255)      # Player
ORANGE = (255, 165, 0)  # Hiệu ứng nổ
GREEN = (0, 255, 0)     # Enemy
LIGHT_BLUE = (173, 216, 230) # Item Tốc độ
YELLOW = (255, 255, 0)       # Item Tầm nổ
CYAN = (0, 255, 255)         # Item Shield
PURPLE = (160, 32, 240)      # Item Ghost
MAGENTA = (255, 0, 255)      # Teleport
LIGHT_BLUE_ICE = (173, 216, 230)
DARK_GRAY = (50, 50, 50)     # Sliding
WHITE = (255, 255, 255)

# 3. Định nghĩa Tiles
EMPTY = 0
WALL = 1
SOFT_WALL = 2
TRAP_TELEPORT = 3
TRAP_ICE = 4
CONVEYOR_LEFT = 5
CONVEYOR_RIGHT = 5

# 4. Thông số thực thể
PLAYER_SPEED = 3 
PLAYER_WIDTH = 30
PLAYER_HEIGHT = 30
ENEMY_SPEED = 2