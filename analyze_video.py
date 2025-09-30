import cv2
import os
from ultralytics import YOLO
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
model = YOLO("yolov8n.pt")


def process_video(input_path, output_path, min_size=50, max_size=1000, visualize=False):


    cap = cv2.VideoCapture(input_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    removed_folder = "static/removed_videos"
    os.makedirs(removed_folder, exist_ok=True)

    frame_idx = 0
    removed_frames = []
    confidences = []
    temp_removed = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, device=device, verbose=False)[0]
        humans = [box for box in results.boxes if int(box.cls[0]) == 0]
        humans = [h for h in humans if min_size <= (h.xyxy[0][2]-h.xyxy[0][0]) <= max_size]

        if humans:
            out.write(frame)
            max_conf = max(float(h.conf[0]) for h in humans)
            confidences.append(max_conf)
            print(f"[Кадр {frame_idx}] Человек найден (уверенность={max_conf:.2f})")

            # Если был временный фрагмент без человека, сохраняем его
            if temp_removed:
                removed_video_path = os.path.join(removed_folder, f"removed_{frame_idx}.mp4")
                writer = cv2.VideoWriter(removed_video_path, fourcc, fps, (width, height))
                for f in temp_removed:
                    writer.write(f)
                writer.release()
                removed_frames.append(os.path.basename(removed_video_path))
                temp_removed = []

        else:
            # не пишем кадры без человека в итоговое видео
            temp_removed.append(frame)
            confidences.append(0.0)
            print(f"[Кадр {frame_idx}] Человек не найден")

        frame_idx += 1

    # Сохраняем последний фрагмент без человека, если есть
    if temp_removed:
        removed_video_path = os.path.join(removed_folder, f"removed_last.mp4")
        writer = cv2.VideoWriter(removed_video_path, fourcc, fps, (width, height))
        for f in temp_removed:
            writer.write(f)
        writer.release()
        removed_frames.append(os.path.basename(removed_video_path))

    cap.release()
    out.release()
    return removed_frames, confidences
