# Đồ án: Trò chơi Bomberman

Đồ án môn **Cấu trúc Dữ liệu và Thuật toán (DSA)**: Tái hiện tựa game Bomberman với **chế độ Campaign (Vượt ải)** và **chế độ PvP (Đối kháng 2 người)**.

---

## Tính năng Nổi bật

* **Chế độ chơi đa dạng**:
	+ **Campaign**: Sinh tồn qua 5 cấp độ với độ khó tăng dần, tiêu diệt quái vật để mở cửa qua màn.
	+ **PvP Mode**: Đối kháng cục bộ (Local Multiplayer) cực gắt, hỗ trợ 2 người chơi cùng lúc trên một bàn phím.
* **Hệ thống AI và Môi trường tương tác cao**:
	+ Quái vật thông minh biết tự tìm đường ngắn nhất để truy đuổi người chơi, đồng thời né các vùng bom sắp nổ.
	+ Bản đồ có các cạm bẫy vật lý như Ô băng (trượt không phanh), Băng chuyền (đẩy lùi) và Cổng dịch chuyển (Teleport).
* **Giao diện & Character Selection**: 
	+ Màn hình chọn nhân vật (FSM) hỗ trợ tự động quét file (Dynamic Load). Người chơi có thể tự do thêm file ảnh `.png` vào thư mục để game tự nhận diện mà không cần sửa code.
    + Giao diện tách biệt HUD hiển thị HP và Level chuyên nghiệp, kết hợp hiệu ứng âm thanh (SFX) & nhạc nền (BGM) đa dạng.

---

## Áp dụng DSA & Cấu trúc Dữ liệu

1. **`Queue` (Hàng đợi - Deque) cho hệ thống Bom và Nổ**:
	* Quản lý bom đếm ngược theo cơ chế FIFO (First In, First Out).
	* **Phân tích độ phức tạp**: Thuật toán Vụ nổ dây chuyền (Chain Explosion) dùng Queue để lan truyền tia lửa theo chiều rộng. Việc `pop`/`append` tọa độ tốn $\mathcal{O}(1)$, đảm bảo game không bị giật lag dù nổ hàng loạt bom cùng lúc.

2. **Thuật toán `BFS` (Breadth-First Search) cho AI Quái vật**:
	* Xử lý dò đường (Pathfinding) trên lưới 2D (Mảng 2 chiều). Khác với BFS thông thường, thuật toán được nâng cấp để coi các tia lửa và bom sắp nổ là "vật cản tạm thời", giúp AI biết quay đầu bỏ chạy.
	* Độ phức tạp duy trì ở mức an toàn $\mathcal{O}(V + E)$ (với V là số ô trên bản đồ), hoạt động mượt mà mỗi khung hình.

3. **`Min-Heap` (Hàng đợi ưu tiên) và `Stack` (Ngăn xếp) cho Player**:
	* `Min-Heap` (`heapq`): Dùng để theo dõi thời gian hết hạn của các hiệu ứng Power-up (Speed, Range, Ghost). Giúp truy xuất hiệu ứng nào sắp hết hạn nhanh nhất với $\mathcal{O}(1)$ và cập nhật với $\mathcal{O}(\log n)$.
	* `Stack` (`list`): Quản lý cơ chế cộng dồn khiên bảo vệ (Shield). Khi bị sát thương sẽ `pop` dần khiên ra để bảo vệ mạng sống.

4. **Máy trạng thái hữu hạn `FSM` (Finite State Machine)**:
	* Điều phối mượt mà các luồng trạng thái: `MENU` ➔ `CHARACTER_SELECT` ➔ `TRANSITION` ➔ `PLAYING` ➔ `VICTORY`/`GAMEOVER` với chỉ một vòng lặp sự kiện (event loop) duy nhất.

---

## Cài đặt & Sử dụng

Yêu cầu môi trường: **Python 3.8+**

```bash
# Cài đặt thư viện yêu cầu (pygame-ce)
pip install -r requirements.txt

# Chạy game
python main.py
```

---

## Tổ chức Mã nguồn

* `main.py`: Entry point, chứa vòng lặp chính, máy trạng thái FSM và xử lý kết xuất (render) bề mặt (Surface/HUD).
* `player.py`: Định nghĩa lớp Player, xử lý di chuyển, va chạm vật lý, nhặt vật phẩm và logic cộng dồn hiệu ứng.
* `level_manager.py`: Sinh bản đồ ngẫu nhiên (Campaign & PvP), quản lý danh sách quái vật, sinh power-up và bẫy rập.
* `sound_manager.py`: Tích hợp `pygame.mixer` load nhạc nền và SFX, có cơ chế dự phòng (fallback) chống crash nếu máy không có thiết bị âm thanh.
* `asset_loader.py`: Hỗ trợ load, cắt (subsurface) và chia tỷ lệ các dải ảnh (Sprite Sheet).

---

## Bản quyền & Tham khảo (Citations)

Dự án này là sản phẩm đồ án môn học. Toàn bộ kiến trúc game và các thuật toán cốt lõi (BFS tìm đường, Queue nổ bom, FSM...) đều do sinh viên tự triển khai từ đầu.

**Các thư viện UI và tài nguyên đã sử dụng:**
1. **`pygame-ce`**: Phiên bản Community Edition của Pygame, cung cấp vòng lặp game, dựng hình 2D và xử lý sự kiện hệ thống.
2. **Tài nguyên Hình ảnh & Âm thanh**: Đồ họa Pixel và âm thanh 8-bit được thiết kế riêng/sưu tầm từ nguồn mã nguồn mở (Creative Commons 0) không dính bản quyền (https://freesound.org/).

---

## Sinh viên thực hiện
* **Nguyễn Văn Dũng**
