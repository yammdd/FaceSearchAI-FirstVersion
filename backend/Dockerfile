# Sử dụng image Python 3.9 slim làm base
FROM python:3.9-slim

# Đặt thư mục làm việc
WORKDIR /app

# Cập nhật danh sách gói và cài đặt các thư viện hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    g++ \
    make \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgtk2.0-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    # <<< THÊM FFMPEG >>>
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Sao chép file requirements.txt
COPY requirements.txt requirements.txt

# Cài đặt các thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép file app.py (và các file khác nếu có)
COPY app.py .
# Hoặc COPY . . nếu có nhiều file python

# Chỉ định cổng
EXPOSE 5000

# Chạy file app.py
CMD ["python", "app.py"]
