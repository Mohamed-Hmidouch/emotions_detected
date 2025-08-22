from flask import Flask, render_template, request, Response
import tensorflow as tf
from tensorflow.keras.models import load_model
import numpy as np
from PIL import Image
import cv2
import os

# 🔹 إعداد Flask
app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 🔹 تحميل الموديل
model = load_model('best.h5')

# 🔹 أسماء العواطف
emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# 🔹 تحميل الكاسكيد مرة وحدة
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# 📌 الصفحة الرئيسية
@app.route('/')
def index():
    return render_template('index.html')

# 📌 معالجة الصورة المرفوعة
@app.route('/predict', methods=['POST'])
def predict():
    file = request.files['image']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    emotion = model_predict(filepath)

    return render_template('index.html', result=emotion, image_path=filepath)

# 📌 دالة التنبؤ
def model_predict(img_path):
    img = Image.open(img_path).convert('L').resize((48, 48))  # Gray + Resize
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=-1)  # (48, 48, 1)
    img_array = np.expand_dims(img_array, axis=0)   # (1, 48, 48, 1)

    prediction = model.predict(img_array)
    emotion_index = np.argmax(prediction)
    return emotion_labels[emotion_index]

# 📌 بث الكاميرا
def generate_frames():
    cap = cv2.VideoCapture(0)  # فتح الكاميرا
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                roi_gray = gray[y:y+h, x:x+w]
                roi_gray = cv2.resize(roi_gray, (48, 48))
                roi_gray = roi_gray / 255.0
                roi_gray = np.expand_dims(roi_gray, axis=-1)
                roi_gray = np.expand_dims(roi_gray, axis=0)

                prediction = model.predict(roi_gray)
                emotion = emotion_labels[np.argmax(prediction)]

                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(frame, emotion, (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

# 📌 صفحة الكاميرا
@app.route('/camera')
def camera():
    return render_template('camera.html')

# 📌 بث الفيديو من الكاميرا
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 🔹 تشغيل Flask
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
