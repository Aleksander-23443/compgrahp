import os
from flask import Flask, render_template, request
from analyze_video import process_video

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
OUTPUT_FOLDER = "static/processed"
REMOVED_FOLDER = "static/removed_videos"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(REMOVED_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    processed_video = None
    removed_videos = []
    confidences = []
    message = None

    if request.method == "POST":
        file = request.files.get("video")
        if file:
            filename = file.filename
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)

            output_filename = "processed_" + filename
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)

            # Получаем параметры обработки
            try:
                min_size = int(request.form.get("min_size", 100))
                max_size = int(request.form.get("max_size", 1000))
            except ValueError:
                min_size, max_size = 100, 1000

            # Коррекция значений
            min_size = max(1, min_size)
            max_size = min(max_size, 5000)
            if min_size > max_size:
                min_size, max_size = max_size, min_size

            visualize = "visualize" in request.form

            # Обработка видео
            removed_frames, confidences = process_video(
                input_path, output_path, min_size, max_size, visualize
            )

            # Сохраняем результат
            processed_video = output_filename
            removed_videos = removed_frames

            # Проверка специальных случаев
            if not removed_videos:
                message = "Во всём видео присутствует человек – фрагменты без человека отсутствуют."
            elif all(c == 0 for c in confidences):
                message = "Во всём видео человек отсутствует – итоговое видео пустое."

    return render_template(
        "index.html",
        processed_video=processed_video,
        removed_videos=removed_videos,
        confidences=confidences,
        message=message
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
