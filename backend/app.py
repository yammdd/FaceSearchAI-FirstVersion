# -*- coding: utf-8 -*-
# File: app.py
from flask import Flask, request, jsonify, send_from_directory, Response, abort
import os
import cv2
from deepface import DeepFace # Sử dụng DeepFace
import numpy as np
import io
from PIL import Image
import base64
import time
import subprocess
import traceback # Để log lỗi chi tiết
import threading # Để tải model nền

UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'static/results' # Thư mục chứa video kết quả

app = Flask(__name__) # Flask tự tìm thư mục static cùng cấp

model_ready = False # Cờ báo model đã sẵn sàng

upload_dir_path = os.path.join(app.root_path, UPLOAD_FOLDER)
result_dir_path = os.path.join(app.root_path, RESULT_FOLDER)
os.makedirs(upload_dir_path, exist_ok=True)
os.makedirs(result_dir_path, exist_ok=True)

# Các định dạng file cho phép
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

# Cấu hình DeepFace
DEEPFACE_MODEL = "ArcFace" # Model chính xác cao
DETECTOR_BACKEND = "yunet" # Bộ phát hiện nhanh
print(f"Using DeepFace Model: {DEEPFACE_MODEL}, Detector: {DETECTOR_BACKEND}")

query_image_path_or_array = None # Lưu ảnh query dạng numpy array

def allowed_file(filename, allowed_extensions):
    """Kiểm tra đuôi file hợp lệ."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/ready', methods=['GET'])
def ready_check():
    """Endpoint kiểm tra trạng thái sẵn sàng của model."""
    global model_ready
    if model_ready:
        return jsonify({"status": "ready"})
    else:
        return jsonify({"status": "loading", "message": "Model is loading, please wait..."}), 503

@app.route('/set_query', methods=['POST'])
def set_query():
    """Nhận và lưu ảnh query."""
    global query_image_path_or_array, model_ready
    if not model_ready: return jsonify({"error": "Model is not ready yet. Please wait."}), 503
    if 'query' not in request.files: return jsonify({"error": "No query image uploaded"}), 400
    file = request.files['query']
    if not file or file.filename == '': return jsonify({"error": "No selected file"}), 400
    if not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS): return jsonify({"error": "Unsupported image format"}), 400
    try:
        img_bytes = file.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_np is None: return jsonify({"error": "Could not decode image"}), 400
        # Kiểm tra có khuôn mặt trong ảnh query không
        try:
            _ = DeepFace.extract_faces(img_path=img_np, detector_backend=DETECTOR_BACKEND, enforce_detection=True)
        except ValueError as ve:
             print(f"DeepFace could not detect a face in the query image: {ve}")
             return jsonify({"error": "No face found in query image."}), 400
        query_image_path_or_array = img_np
        print("Query image stored successfully.")
        return jsonify({"status": "Query set successfully"})
    except Exception as e:
        print(f"Error processing query image: {e}"); traceback.print_exc()
        return jsonify({"error": f"Error processing query image: {str(e)}"}), 500

@app.route('/search', methods=['POST'])
def search():
    """Xử lý video: Tìm khuôn mặt, so sánh, vẽ hộp/chữ, chuyển đổi FFmpeg."""
    global query_image_path_or_array, model_ready
    if not model_ready: return jsonify({"error": "Model is not ready yet. Please wait."}), 503
    if query_image_path_or_array is None: return jsonify({"error": "Query face not set yet."}), 400
    if 'video' not in request.files: return jsonify({"error": "No video file uploaded"}), 400
    video_file = request.files['video']
    if not video_file or video_file.filename == '': return jsonify({"error": "No selected video file"}), 400
    if not allowed_file(video_file.filename, ALLOWED_VIDEO_EXTENSIONS): return jsonify({"error": "Unsupported video format"}), 400

    # Chuẩn bị đường dẫn file
    safe_filename = "".join(c for c in video_file.filename if c.isalnum() or c in ['.', '_']).rstrip()
    video_path = os.path.join(upload_dir_path, safe_filename)
    video_file.save(video_path)
    print(f"Video saved to (inside container): {video_path}")

    timestamp = int(time.time())
    temp_output_filename = f"temp_output_{os.path.splitext(safe_filename)[0]}_{timestamp}.mp4"
    temp_out_path = os.path.join(result_dir_path, temp_output_filename)
    final_output_filename = f"output_{os.path.splitext(safe_filename)[0]}_{timestamp}_h264.mp4"
    final_out_path = os.path.join(result_dir_path, final_output_filename)
    print(f"Temporary OpenCV output: {temp_out_path}")
    print(f"Final FFmpeg output (web compatible): {final_out_path}")

    cap = None
    out = None
    try:
        # Mở video input
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened(): raise IOError(f"Could not open video file {video_path}")

        # Lấy thông số video
        fps = int(cap.get(cv2.CAP_PROP_FPS)); fps = 30 if fps <= 0 else fps
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Video properties: {width}x{height} @ {fps}fps")

        # Chuẩn bị video output tạm thời bằng OpenCV
        fourcc_str = 'mp4v'; fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
        out = cv2.VideoWriter(temp_out_path, fourcc, fps, (width, height))
        if not out.isOpened(): raise IOError(f"Could not open OpenCV video writer for {temp_out_path} with codec '{fourcc_str}'.")

        frame_count = 0; matches_found_this_run = 0; process_every_n_frames = 15 # Xử lý cách frame
        last_matched_boxes = [] # Lưu box khớp từ frame trước để làm mượt

        # Vòng lặp xử lý từng frame
        while True:
            ret, frame = cap.read()
            if not ret: break # Hết video
            frame_count += 1
            current_frame_matched_boxes = [] # Box khớp trong frame này
            processed_frame_flag = False # Đánh dấu frame có được xử lý DeepFace không

            # Chỉ xử lý DeepFace trên một số frame
            if frame_count % process_every_n_frames == 0:
                processed_frame_flag = True
                print(f"--- Processing frame {frame_count} ---")
                try:
                    start_time = time.time()
                    # 1. Tìm tất cả khuôn mặt trong frame
                    detected_faces = DeepFace.extract_faces(
                        img_path=frame, detector_backend=DETECTOR_BACKEND,
                        enforce_detection=False, align=True
                    )
                    detection_time = time.time()
                    print(f"DeepFace.extract_faces found {len(detected_faces)} face(s) in {detection_time - start_time:.2f}s")

                    # 2. Verify từng khuôn mặt tìm được với ảnh query
                    for face_data in detected_faces:
                        face_img_array = face_data['face']
                        facial_area = face_data['facial_area']
                        try:
                            verify_start_time = time.time()
                            # So sánh khuôn mặt đã align với ảnh query
                            verification_result = DeepFace.verify(
                                img1_path = query_image_path_or_array, img2_path = face_img_array,
                                model_name = DEEPFACE_MODEL, enforce_detection = False,
                                detector_backend = 'skip', align = False, silent=True
                            )
                            verify_end_time = time.time()
                            distance = verification_result.get('distance')
                            threshold = verification_result.get('threshold')
                            verified = verification_result.get("verified", False)
                            print(f"  Verify face: Verified={verified}, Distance={distance:.4f}, Threshold={threshold:.4f} (took {verify_end_time - verify_start_time:.2f}s)")

                            # 3. Nếu khớp, lưu tọa độ và vẽ lên frame
                            if verified:
                                x = facial_area['x']; y = facial_area['y']
                                w = facial_area['w']; h = facial_area['h']
                                box_coords = (x, y, w, h)
                                current_frame_matched_boxes.append(box_coords) # Lưu lại box khớp

                                # Vẽ hộp và chữ màu xanh đậm
                                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                                label = "Matched"; label_y = y - 10 if y - 10 > 10 else y + 20
                                cv2.putText(frame, label, (x, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                                matches_found_this_run += 1

                        except Exception as verify_err: print(f"!!!!! ERROR during DeepFace.verify: {verify_err}")
                except Exception as frame_proc_error: print(f"!!!!! ERROR processing frame {frame_count}: {frame_proc_error}"); traceback.print_exc()

                # Cập nhật danh sách box khớp cuối cùng
                last_matched_boxes = current_frame_matched_boxes
                print(f"--- Finished processing frame {frame_count}, {len(last_matched_boxes)} matches found ---")

            else:
                # Frame trung gian: Vẽ lại các box từ lần xử lý trước (màu nhạt, không chữ)
                faded_color = (144, 238, 144) # LightGreen
                for (x, y, w, h) in last_matched_boxes:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), faded_color, 1)

            # Ghi frame (đã vẽ hoặc chưa) vào video tạm
            out.write(frame)

        # Kết thúc vòng lặp video
        print(f"OpenCV loop finished. Total matches drawn instances: {matches_found_this_run}.")
        out.release(); out = None; print("OpenCV Video writer released.")

        # Chuyển đổi video tạm sang H.264 bằng FFmpeg
        if not os.path.exists(temp_out_path) or os.path.getsize(temp_out_path) == 0:
            raise ValueError(f"Temporary OpenCV video file is missing or empty: {temp_out_path}")
        print(f"Starting FFmpeg conversion from {temp_out_path} to {final_out_path}")
        ffmpeg_command = ['ffmpeg','-i', temp_out_path,'-c:v', 'libx264','-preset', 'fast','-crf', '23','-c:a', 'aac','-strict', 'experimental','-y',final_out_path]
        try:
            result = subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
            print("FFmpeg conversion successful!")
            if not os.path.exists(final_out_path) or os.path.getsize(final_out_path) == 0:
                 raise IOError("FFmpeg ran but failed to create a valid output file.")
            # Xóa file tạm sau khi thành công
            if os.path.exists(temp_out_path): os.remove(temp_out_path); print(f"Removed temporary file: {temp_out_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error during FFmpeg conversion (code: {e.returncode}): {e.stderr}")
            raise RuntimeError("FFmpeg conversion failed.")
        except FileNotFoundError:
            print("Error: 'ffmpeg' command not found.")
            raise RuntimeError("FFmpeg command not found on the server.")

        # Trả về URL của video cuối cùng
        video_url = f"/static/results/{final_output_filename}"
        return jsonify({"video_url": video_url})

    except Exception as e:
        # Xử lý lỗi chung
        print(f"Unhandled error processing video '{safe_filename}': {e}"); traceback.print_exc()
        # Dọn dẹp file nếu có lỗi
        if cap and cap.isOpened(): cap.release()
        if out and out.isOpened(): out.release()
        if os.path.exists(video_path): os.remove(video_path)
        if os.path.exists(temp_out_path):
             try: os.remove(temp_out_path)
             except OSError: pass
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
    finally:
        # Đảm bảo giải phóng tài nguyên
        if cap and cap.isOpened(): cap.release(); print("Video capture released.")
        # Xóa video gốc đã upload
        if os.path.exists(video_path):
            try: os.remove(video_path); print(f"Removed uploaded video: {video_path}")
            except OSError as e: print(f"Error removing uploaded video file {video_path}: {e}")

@app.route('/process_live_frame', methods=['POST'])
def process_live_frame():
    """Xử lý frame từ webcam."""
    global query_image_path_or_array, model_ready
    if not model_ready: return jsonify({"error": "Model not ready yet."}), 503
    if query_image_path_or_array is None: return jsonify({"matches": []})
    data = request.get_json()
    if not data or 'image' not in data: return jsonify({"error": "No image data received"}), 400
    try:
        image_data = data['image']
        if ',' in image_data: header, encoded_data = image_data.split(',', 1)
        else: encoded_data = image_data
        image_bytes = base64.b64decode(encoded_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None: return jsonify({"error": "Could not decode image data"}), 400
        results = []
        try:
            # Dùng verify để so sánh frame với ảnh query
            verification_result = DeepFace.verify(
                img1_path = query_image_path_or_array, img2_path = frame,
                model_name = DEEPFACE_MODEL, detector_backend = DETECTOR_BACKEND,
                enforce_detection = False, align=True, silent=True
            )
            # Nếu khớp, lấy tọa độ và trả về
            if verification_result.get("verified", False):
                facial_area = verification_result.get("facial_areas", {}).get("img2", None)
                if facial_area:
                    x = facial_area['x']; y = facial_area['y']; w = facial_area['w']; h = facial_area['h']
                    results.append({"box": [x, y, x+w, y+h]})
                else: print("Warning: DeepFace.verify matched but did not return facial area for img2.")
        except ValueError as ve: print(f"ValueError during DeepFace.verify: {ve}"); # Bỏ qua nếu không tìm thấy mặt
        except Exception as verify_err: print(f"Error during DeepFace.verify: {verify_err}"); traceback.print_exc()
        return jsonify({"matches": results}) # Trả về danh sách box khớp (có thể rỗng)
    except (base64.binascii.Error, ValueError, TypeError) as decode_error: print(f"Error decoding base64: {decode_error}"); return jsonify({"error": "Invalid image data"}), 400
    except Exception as e: print(f"Error processing live frame: {e}"); traceback.print_exc(); return jsonify({"error": f"Error processing frame: {str(e)}"}), 500

@app.route('/static/results/<path:path>')
def send_result(path):
    """Phục vụ file kết quả (video hoặc ảnh)."""
    result_dir = os.path.join(app.root_path, RESULT_FOLDER)
    file_path = os.path.join(result_dir, path)
    print(f"Attempting to serve result file: {file_path}")
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        print(f"Error: File not found at {file_path}"); abort(404)
    try:
        return send_from_directory(result_dir, path, as_attachment=False)
    except Exception as e:
        print(f"Error serving file {path}: {e}"); abort(500)

def preload_model():
    """Tải trước model DeepFace trong một luồng riêng."""
    global model_ready
    try:
        print(f"Pre-loading DeepFace model ({DEEPFACE_MODEL}) and detector ({DETECTOR_BACKEND})...")
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        _ = DeepFace.represent(dummy_img, model_name=DEEPFACE_MODEL, detector_backend=DETECTOR_BACKEND, enforce_detection=False)
        model_ready = True # Đặt cờ True khi xong
        print("DeepFace model and detector loaded. Backend is ready.")
    except Exception as load_err:
        print(f"ERROR: Could not pre-load DeepFace components: {load_err}")
        traceback.print_exc()
        # Giữ model_ready = False nếu lỗi

if __name__ == '__main__':
    # Khởi chạy luồng tải model
    preload_thread = threading.Thread(target=preload_model, daemon=True) # daemon=True để thread tự thoát khi app chính thoát
    preload_thread.start()
    # Chạy Flask app (tắt debug và reloader khi dùng thread)
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
