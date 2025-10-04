import os
import subprocess
import atexit
import shutil
from flask import Flask, render_template, request, url_for
from werkzeug.utils import secure_filename
from analyze_video import process_video

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
OUTPUT_FOLDER = "static/processed"
REMOVED_FOLDER = "static/removed_videos"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(REMOVED_FOLDER, exist_ok=True)


def clear_folders():
    """Очистка всех рабочих папок (processed, removed_videos, uploads)."""
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, REMOVED_FOLDER]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                path = os.path.join(folder, f)
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)


# Очистка при завершении программы
atexit.register(clear_folders)


def convert_to_h264(input_path, output_path):
    temp_path = output_path.replace(".mp4", "_h264.mp4")
    if not os.path.exists(temp_path):
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart",
            temp_path
        ], check=True)
    return temp_path


def convert_removed_videos(removed_paths):
    final_files = []
    for path in removed_paths:
        input_path = os.path.join(REMOVED_FOLDER, path)
        filename = os.path.basename(path)
        output_path = os.path.join(REMOVED_FOLDER, filename.replace(".mp4", "_h264.mp4"))

        if not os.path.exists(output_path):
            subprocess.run([
                "ffmpeg", "-y", "-i", input_path,
                "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart",
                output_path
            ], check=True)

        final_files.append(os.path.basename(output_path))
    return final_files


@app.route("/", methods=["GET", "POST"])
def index():
    video_url = None
    removed_videos = []
    confidences = []
    message = None

    if request.method == "GET":
        # Очистка папок при обновлении страницы
        clear_folders()

    if request.method == "POST":
        file = request.files.get("video")
        if file and file.filename:
            filename = secure_filename(file.filename)
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)

            custom_filename = request.form.get("custom_filename", f"processed_{filename}")
            output_filename = custom_filename if custom_filename.endswith(".mp4") else custom_filename + ".mp4"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)

            try:
                min_width = int(request.form.get("min_width", 100))
                max_width = int(request.form.get("max_width", 1000))
                min_height = int(request.form.get("min_height", 100))
                max_height = int(request.form.get("max_height", 1000))
            except ValueError:
                min_width, max_width = 100, 1000
                min_height, max_height = 100, 1000

            min_width = max(1, min_width)
            max_width = min(max_width, 5000)
            if min_width > max_width:
                min_width, max_width = max_width, min_width

            min_height = max(1, min_height)
            max_height = min(max_height, 5000)
            if min_height > max_height:
                min_height, max_height = max_height, min_height

            visualize = "visualize" in request.form

            removed_frames, confidences = process_video(
                input_path, output_path,
                min_width, max_width,
                min_height, max_height,
                visualize
            )

            final_output_path = convert_to_h264(output_path, output_path)
            final_output_filename = os.path.basename(final_output_path)
            video_url = url_for("static", filename=f"processed/{final_output_filename}")

            removed_videos_h264 = convert_removed_videos(removed_frames)
            removed_videos = [url_for("static", filename=f"removed_videos/{rf}") for rf in removed_videos_h264]

            if not removed_videos:
                message = "Во всём видео присутствует человек – фрагменты без человека отсутствуют."
            elif all(c == 0 for c in confidences):
                message = "Во всём видео человек отсутствует – итоговое видео пустое."

    return render_template(
        "index.html",
        video_url=video_url,
        removed_videos=removed_videos,
        confidences=confidences,
        message=message
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
