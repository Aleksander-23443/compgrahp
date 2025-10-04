import cv2
import os
from ultralytics import YOLO
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
model = YOLO("yolov8n.pt")


def process_video(input_path, output_path, min_width=50, max_width=1000,
                  min_height=50, max_height=1000, visualize=False,
                  tolerance=5, smoothing_window=5):

    cap = cv2.VideoCapture(input_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if fps == 0:
        fps = 30

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    removed_folder = "static/removed_videos"
    os.makedirs(removed_folder, exist_ok=True)

    frame_idx = 0
    removed_frames = []
    confidences = []
    temp_removed = []
    no_human_counter = 0  # счётчик кадров без человека

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, device=device, verbose=False, conf=0.2)[0]
        humans = [box for box in results.boxes if int(box.cls[0]) == 0]
        humans = [
            h for h in humans
            if min_width <= (h.xyxy[0][2] - h.xyxy[0][0]) <= max_width
               and min_height <= (h.xyxy[0][3] - h.xyxy[0][1]) <= max_height
        ]

        if humans:
            no_human_counter = 0
            out.write(frame)
            max_conf = max(float(h.conf[0]) for h in humans)
            confidences.append(max_conf)
            print(f"[Кадр {frame_idx}] Человек найден (уверенность={max_conf:.2f})")

            # Если был временный фрагмент без человека — сохраняем его
            if temp_removed:
                removed_video_path = os.path.join(removed_folder, f"removed_{frame_idx}.mp4")
                writer = cv2.VideoWriter(removed_video_path, fourcc, fps, (width, height))
                for f in temp_removed:
                    writer.write(f)
                writer.release()
                removed_frames.append(os.path.basename(removed_video_path))
                temp_removed = []

        else:
            no_human_counter += 1
            if no_human_counter <= tolerance:
                # допускаем несколько кадров подряд без детекции
                out.write(frame)
                confidences.append(0.0)
                print(f"[Кадр {frame_idx}] Пропуск: человек не найден, но в пределах tolerance ({no_human_counter})")
            else:
                temp_removed.append(frame)
                confidences.append(0.0)
                print(f"[Кадр {frame_idx}] Человек не найден (за пределами tolerance)")

        frame_idx += 1

    # Сохраняем последний фрагмент без человека
    if temp_removed:
        removed_video_path = os.path.join(removed_folder, f"removed_last.mp4")
        writer = cv2.VideoWriter(removed_video_path, fourcc, fps, (width, height))
        for f in temp_removed:
            writer.write(f)
        writer.release()
        removed_frames.append(os.path.basename(removed_video_path))

    cap.release()
    out.release()

    # --- Сглаживание уверенности ---
    if len(confidences) > 1:
        smoothed = []
        for i in range(len(confidences)):
            start = max(0, i - smoothing_window + 1)
            avg = sum(confidences[start:i+1]) / (i - start + 1)
            smoothed.append(round(avg, 3))
        confidences = smoothed

    return removed_frames, confidences

