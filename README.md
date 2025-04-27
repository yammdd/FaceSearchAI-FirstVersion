# Ứng dụng Tìm kiếm Khuôn mặt bằng AI

## Mô tả

Đây là một ứng dụng web cho phép người dùng tìm kiếm sự xuất hiện của một khuôn mặt cụ thể (từ ảnh chân dung) trong các video hoặc thông qua luồng webcam trực tiếp. Ứng dụng sử dụng thư viện DeepFace với mô hình nhận diện khuôn mặt tiên tiến (ArcFace) để đạt độ chính xác cao.

## Tính năng

* **Đặt ảnh Query:** Tải lên ảnh chân dung của người cần tìm kiếm.
* **Tìm kiếm trong Video:** Tải lên một file video (MP4, MKV, AVI, MOV) và ứng dụng sẽ xử lý video, đánh dấu các khung hình chứa khuôn mặt khớp với ảnh query. Video kết quả (đã xử lý) sẽ được hiển thị trên web.
* **Tìm kiếm Live Webcam:** Bật webcam của bạn và ứng dụng sẽ nhận diện khuôn mặt khớp với ảnh query trong thời gian thực, vẽ hộp và chữ "Matched" trực tiếp trên luồng video.
* **Giao diện Web:** Giao diện người dùng thân thiện được xây dựng bằng HTML, Tailwind CSS và JavaScript.
* **Backend Mạnh mẽ:** Backend được xây dựng bằng Flask (Python), sử dụng DeepFace (với model ArcFace) để nhận diện và OpenCV để xử lý video/ảnh.
* **Đóng gói Docker:** Toàn bộ ứng dụng (frontend và backend) được đóng gói bằng Docker và Docker Compose để dễ dàng triển khai và chạy.
* **Xử lý Video Nâng cao:** Sử dụng FFmpeg để chuyển đổi video kết quả sang định dạng H.264 tương thích với trình duyệt web.
* **Thông báo tải mô hình:** Hiển thị lớp phủ loading khi backend đang tải mô hình AI trong lần khởi động đầu tiên.

## Công nghệ sử dụng

* **Backend:**
    * Python 3.9
    * Flask
    * DeepFace (Model: ArcFace, Detector: yunet)
    * OpenCV (cv2)
    * NumPy
    * Pillow
    * FFmpeg (thông qua `subprocess`)
* **Frontend:**
    * HTML5
    * Tailwind CSS
    * JavaScript (Fetch API, MediaDevices API)
* **Deployment:**
    * Docker
    * Docker Compose
    * Nginx (làm reverse proxy và phục vụ frontend)

## Điều kiện tiên quyết

* **Docker:** Đã cài đặt Docker Engine và Docker Compose trên máy của bạn. (Xem [hướng dẫn cài đặt Docker](https://docs.docker.com/engine/install/))

## Cài đặt và Chạy ứng dụng

1.  **Clone Repository (Nếu có):**
    ```bash
    git clone <URL_repository_cua_ban>
    cd AI_system_development
    ```
    Hoặc đảm bảo bạn có đầy đủ các file và thư mục (`backend/`, `frontend/`, `docker-compose.yml`, `nginx.conf`) trong một thư mục gốc.

2.  **Kiểm tra cấu trúc thư mục:** Đảm bảo cấu trúc thư mục giống như sau:
    ```
    AI_system_development/
    ├── backend/
    │   ├── app.py
    │   ├── requirements.txt
    │   └── Dockerfile
    ├── frontend/
    │   ├── index.html
    │   └── Dockerfile
    ├── docker-compose.yml
    └── nginx.conf
    ```

3.  **Build và Chạy bằng Docker Compose:**
    Mở terminal hoặc command prompt trong thư mục gốc (`AI_system_development/`) và chạy lệnh:
    ```bash
    docker-compose up -d --build
    ```
    * `up`: Khởi tạo và chạy các container.
    * `-d`: Chạy ở chế độ detached (chạy nền).
    * `--build`: Buộc Docker Compose build lại các image (quan trọng trong lần chạy đầu hoặc khi có thay đổi code/Dockerfile).

4.  **Chờ tải mô hình (Lần đầu):** Lần đầu tiên chạy, backend sẽ cần tải về các file của mô hình DeepFace (ArcFace và yunet). Quá trình này có thể mất vài phút. Bạn có thể theo dõi log backend bằng lệnh:
    ```bash
    docker-compose logs -f backend
    ```
    Khi thấy dòng **"DeepFace model and detector loaded. Backend is ready."** là backend đã sẵn sàng.

5.  **Truy cập ứng dụng:** Mở trình duyệt web và truy cập vào địa chỉ: `http://localhost:8080` (nếu bạn không thay đổi cổng trong `docker-compose.yml`).

## Hướng dẫn sử dụng

Khi bạn truy cập `http://localhost:8080`, bạn sẽ thấy giao diện ứng dụng.

**Quan trọng:** Trong lần đầu tiên truy cập sau khi khởi động backend, bạn sẽ thấy một **lớp phủ loading** ("Đang tải mô hình AI...") che màn hình. Vui lòng **chờ cho đến khi lớp phủ này biến mất** và giao diện người dùng được kích hoạt hoàn toàn trước khi thực hiện các bước tiếp theo.

1.  **Bước 1: Đặt ảnh Query**
    * Trong phần "Bước 1: Tải ảnh chân dung cần tìm":
        * Nhấp vào nút "Choose File" (hoặc tương tự) để chọn một file ảnh (.png, .jpg, .jpeg, ...) chứa khuôn mặt của người bạn muốn tìm kiếm.
        * Ảnh bạn chọn sẽ được hiển thị preview bên dưới.
        * Nhấp vào nút **"Đặt ảnh tìm kiếm"**.
        * Chờ thông báo "Ảnh tìm kiếm đã được đặt thành công!" xuất hiện. Nếu có lỗi (ví dụ: không tìm thấy khuôn mặt trong ảnh), thông báo lỗi sẽ hiển thị.

2.  **Bước 2: Chọn chế độ tìm kiếm**
    Ứng dụng có 2 tab chính: "Tìm kiếm trong Video" và "Tìm kiếm Live Webcam". Tab **"Tìm kiếm Live Webcam"** được chọn làm mặc định.

    * **Chế độ Tìm kiếm trong Video:**
        * Chuyển sang tab "Tìm kiếm trong Video".
        * Trong phần "Bước 2: Tải video để tìm kiếm":
            * Nhấp "Choose File" để chọn file video (.mp4, .mkv, .avi, .mov) bạn muốn tìm kiếm.
            * Nhấp nút **"Tìm kiếm Video"**.
            * Quá trình xử lý video sẽ bắt đầu (có thể mất thời gian tùy thuộc vào độ dài video và cấu hình máy). Bạn sẽ thấy thông báo "Đang xử lý video...".
            * Khi xử lý xong, video kết quả (với các hộp màu xanh lá và chữ "Matched" vẽ trên các khuôn mặt khớp) sẽ được hiển thị trong khung video bên dưới. Nếu không tìm thấy khuôn mặt nào khớp, video gốc sẽ được hiển thị.
            * Bạn có thể sử dụng các nút điều khiển của trình phát video để xem kết quả.

    * **Chế độ Tìm kiếm Live Webcam (Mặc định):**
        * Trong phần "Bước 2: Tìm kiếm bằng Webcam":
            * Nhấp nút **"Bắt đầu Webcam"**. Trình duyệt có thể sẽ hỏi quyền truy cập webcam, hãy cho phép.
            * Luồng video từ webcam của bạn sẽ hiển thị trong khung.
            * Ứng dụng sẽ liên tục phân tích các frame từ webcam. Nếu phát hiện khuôn mặt khớp với ảnh query đã đặt, một hộp màu xanh lá và chữ "Matched" sẽ được vẽ trực tiếp lên khuôn mặt đó trên màn hình.
            * Nhấp nút **"Dừng Webcam"** để tắt luồng video và dừng quá trình nhận diện.

**Lưu ý:**

* Bạn phải **đặt ảnh query thành công** trước khi có thể sử dụng chức năng tìm kiếm video hoặc live webcam.
* Quá trình xử lý video có thể tốn nhiều tài nguyên CPU và thời gian.
* Độ chính xác của nhận diện phụ thuộc vào chất lượng ảnh query, chất lượng video/webcam, điều kiện ánh sáng, góc mặt,...

## Ghi chú

* Model DeepFace "ArcFace" được sử dụng để tối ưu độ chính xác, nhưng có thể chậm trên các máy không có GPU mạnh. Bạn có thể thử các model khác (như "Facenet", "SFace") bằng cách thay đổi biến `DEEPFACE_MODEL` trong `app.py` nếu cần hiệu năng tốt hơn.
* Bộ phát hiện "yunet" được chọn vì tốc độ. Bạn có thể thử các bộ phát hiện khác được DeepFace hỗ trợ.
* Video kết quả được chuyển đổi sang H.264 bằng FFmpeg để đảm bảo tương thích tốt nhất với trình duyệt.
