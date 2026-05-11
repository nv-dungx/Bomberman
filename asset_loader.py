"""
asset_loader.py
Module quản lý và nạp tài nguyên (hình ảnh, âm thanh) cho game Bomberman.
Sử dụng mẫu thiết kế (Pattern) Cache để đảm bảo mỗi ảnh chỉ được nạp từ ổ cứng đúng 1 lần.
"""
import pygame
import os
from settings import *

class AssetLoader:
    """Lớp quản lý nạp tài nguyên hình ảnh với cơ chế cache để tối ưu hiệu suất.

    Sử dụng mẫu thiết kế Singleton-like với static methods và dictionary cache
    để đảm bảo mỗi file ảnh chỉ được đọc từ ổ cứng một lần duy nhất.
    Hỗ trợ nạp ảnh đơn lẻ và spritesheet cho hoạt ảnh.

    Attributes:
        _cache (dict): Bộ nhớ cache lưu trữ các ảnh đã nạp, key là tên file.
    """
    _cache = {}  # Dictionary lưu trữ các ảnh đã nạp lên RAM

    @staticmethod
    def load_image(file_name: str, width: int = None, height: int = None) -> pygame.Surface:
        """Nạp một ảnh tĩnh đơn lẻ (Ví dụ: Tường, Bom, Item)."""
        if file_name in AssetLoader._cache:
            return AssetLoader._cache[file_name]

        path = os.path.join("assets", "images", file_name)
        try:
            # convert_alpha() giúp giữ lại nền trong suốt (transparent)
            image = pygame.image.load(path).convert_alpha()
            if width and height:
                image = pygame.transform.scale(image, (width, height))
            
            AssetLoader._cache[file_name] = image
            return image
        except Exception as e:
            print(f"Lỗi: Không thể tải ảnh {file_name}: {e}")
            # Nếu lỗi, trả về một khối màu tím (Magenta) để game không bị crash
            surf = pygame.Surface((width or TILE_SIZE, height or TILE_SIZE))
            surf.fill(MAGENTA)
            return surf

    @staticmethod
    def load_sprite_sheet(file_name: str, frame_width: int, frame_height: int, num_frames: int, scale_w: int = None, scale_h: int = None) -> list[pygame.Surface]:
        """
        Nạp một dải ảnh (spritesheet) ngang và cắt nó thành danh sách các frame.
        Dùng cho hoạt ảnh của Player, Enemy.
        """
        cache_key = f"{file_name}_sheet"
        if cache_key in AssetLoader._cache:
            return AssetLoader._cache[cache_key]

        path = os.path.join("assets", "images", file_name)
        frames = []
        try:
            sheet = pygame.image.load(path).convert_alpha()
            for i in range(num_frames):
                # Tạo một Surface trống có kích thước bằng 1 frame
                image = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA).convert_alpha()
                
                # Cắt frame thứ 'i' từ tấm ảnh dài sheet và dán vào image
                rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
                image.blit(sheet, (0, 0), rect)
                
                # Phóng to/thu nhỏ (Scale) nếu cần thiết
                if scale_w and scale_h:
                    image = pygame.transform.scale(image, (scale_w, scale_h))
                
                frames.append(image)
                
            AssetLoader._cache[cache_key] = frames
            return frames
        except Exception as e:
            print(f"Lỗi: Không thể tải spritesheet {file_name}: {e}")
            # Fallback nếu lỗi
            fallback_surf = pygame.Surface((frame_width, frame_height))
            fallback_surf.fill(MAGENTA)
            return [fallback_surf] * num_frames