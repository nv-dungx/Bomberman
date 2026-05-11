"""
sound_manager.py
Module quản lý toàn bộ nhạc nền (BGM) và hiệu ứng âm thanh (SFX) của game.

Sử dụng pygame.mixer để tải và phát âm thanh. Tích hợp cơ chế "an toàn" (fallback)
để game không bị crash nếu máy tính người chơi không có thiết bị âm thanh hoặc lỗi driver.
"""

import pygame
import os

class SoundManager:
    """Lớp quản lý âm thanh tập trung cho game Bomberman.

    Chịu trách nhiệm khởi tạo pygame.mixer, nạp trước các file hiệu ứng âm thanh (SFX)
    vào bộ nhớ để phát ngay lập tức, và cung cấp các phương thức để bật/tắt nhạc nền (BGM).

    Attributes:
        enabled (bool): Cờ đánh dấu hệ thống âm thanh có hoạt động hay không.
                        Nếu False (máy không có loa/lỗi driver), các hàm phát nhạc sẽ bị bỏ qua.
        sounds (dict): Từ điển lưu trữ các đối tượng pygame.mixer.Sound đã được nạp.
                       Key là tên hiệu ứng (str), Value là âm thanh đã giải mã.
        sound_path (str): Đường dẫn thư mục chứa các file âm thanh (mặc định là "assets/sounds").
    """

    def __init__(self):
        """Khởi tạo hệ thống âm thanh và nạp sẵn các file SFX."""
        # Cố gắng khởi tạo mixer, nếu máy tính không có thiết bị âm thanh thì chuyển sang chế độ im lặng
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            print("Cảnh báo: Không tìm thấy thiết bị âm thanh hoặc lỗi driver. Game sẽ chạy ở chế độ im lặng.")
            self.enabled = False

        self.sounds = {}
        self.sound_path = "assets/sounds"

        if self.enabled:
            # Nạp sẵn các hiệu ứng SFX (bắt buộc dùng file .wav để không bị delay)
            self.load_sfx("place_bomb", "sfx_place_bomb.wav")
            self.load_sfx("explosion", "sfx_explosion.wav")
            self.load_sfx("pickup", "sfx_pickup.wav")
            self.load_sfx("hurt", "sfx_hurt.wav")
            self.load_sfx("enemy_die", "sfx_enemy_die.wav")
            self.load_sfx("select", "sfx_menu_select.wav")

    def load_sfx(self, name: str, filename: str) -> None:
        """Đọc file âm thanh (.wav) từ ổ đĩa và lưu vào từ điển bộ nhớ.

        Chỉ nên dùng cho các hiệu ứng âm thanh ngắn (SFX) cần phát ngay lập tức
        mà không có độ trễ. Đặt âm lượng mặc định là 50%.

        Args:
            name (str): Tên định danh (key) để gọi âm thanh này sau này.
            filename (str): Tên file thực tế lưu trong thư mục `assets/sounds/`.
        """
        path = os.path.join(self.sound_path, filename)
        if os.path.exists(path):
            self.sounds[name] = pygame.mixer.Sound(path)
            self.sounds[name].set_volume(0.5)  # Chỉnh âm lượng SFX ở mức 50%
        else:
            print(f"Không tìm thấy file âm thanh SFX: {filename}")

    def play_sfx(self, name: str) -> None:
        """Phát một hiệu ứng âm thanh (SFX) đã được nạp từ trước.

        Sử dụng nhiều kênh (channel) tự động của Pygame để phát nhiều
        âm thanh cùng lúc mà không bị đè tiếng nhau.

        Args:
            name (str): Tên định danh của hiệu ứng cần phát (ví dụ: "explosion").
        """
        if self.enabled and name in self.sounds:
            self.sounds[name].play()