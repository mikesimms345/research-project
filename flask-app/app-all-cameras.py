import flask
from flask import request, render_template, Response
import cv2
import socket
import time

app = flask.Flask(__name__)

def generate_frames():
    cam = cv2.VideoCapture(0)
    while True:
        ret, frame = cam.read()
        if not ret:
            continue
        frame_bytes = frame.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template("index.html")

if __name__=='__main__':
    app.run(debug=True,use_reloader=False, port=8000)
