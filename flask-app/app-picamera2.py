import flask
from flask import request, render_template, Response
import cv2
import socket
import time
from picamera2 import Picamera2

app = flask.Flask(__name__)

def gen_frames():
    picam = Picamera2()
    picam.start()
    time.sleep(3.0)
    while True:
        frame = picam.capture_array()
        success, encoded_image = cv2.imencode('.jpg', frame)
        if not success:
            print("Failed to encode image")
            continue
        frame_bytes = encoded_image.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template("index.html")

if __name__=='__main__':
    app.run(debug=True,use_reloader=False, port=8000)