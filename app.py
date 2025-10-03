import os
from flask import Flask, render_template, request, url_for
from werkzeug.utils import secure_filename
from analyze_video import process_video

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
OUTPUT_FOLDER = "static/processed"
REMOVED_FOLDER = "static/removed_videos"

# Создаём папки, если их нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(REMOVED_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    video_url = None
    removed_videos = []
    confidences = []
    message = None

    if request.method == "POST":
        file = request.files.get("video")
        if file and file.filename:
            # Безопасное имя файла
            filename = secure_filename(file.filename)
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)

            # Получаем пользовательское название файла или формируем новое
            custom_filename = request.form.get("custom_filename", f"processed_{filename}")
            output_filename = custom_filename if custom_filename.endswith(".mp4") else custom_filename + ".mp4"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)

            # Параметры обработки
            try:
                min_width = int(request.form.get("min_width", 100))
                max_width = int(request.form.get("max_width", 1000))
                min_height = int(request.form.get("min_height", 100))
                max_height = int(request.form.get("max_height", 1000))
            except ValueError:
                min_width, max_width = 100, 1000
                min_height, max_height = 100, 1000

            # Коррекция значений
            min_width = max(1, min_width)
            max_width = min(max_width, 5000)
            if min_width > max_width:
                min_width, max_width = max_width, min_width

            min_height = max(1, min_height)
            max_height = min(max_height, 5000)
            if min_height > max_height:
                min_height, max_height = max_height, min_height

            visualize = "visualize" in request.form

            # Обработка видео
            removed_frames, confidences = process_video(
                input_path, output_path,
                min_width, max_width,
                min_height, max_height,
                visualize
            )

            # Формируем URL для итогового видео
            video_url = url_for("static", filename=f"processed/{output_filename}")

            # Формируем список URL для удалённых видеофрагментов
            removed_videos = [url_for("static", filename=f"removed_videos/{rf}") for rf in removed_frames]

            # Проверка специальных случаев
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
