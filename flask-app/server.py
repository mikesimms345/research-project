from flask import Flask, request, render_template
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join(data):
    room = data.get('room')
    join_room(room)
    emit('joined', {'sid': request.sid}, to=room)
    print(f"[JOIN] {request.sid} joined room {room}")

@socketio.on('offer')
def handle_offer(data):
    room = data.get('room')
    offer = data.get('offer')
    emit('offer', offer, to=room, include_self=False)
    print(f"[OFFER] Sent offer from {request.sid} to room {room}")

@socketio.on('answer')
def handle_answer(data):
    room = data.get('room')
    answer = data.get('answer')
    emit('answer', answer, to=room, include_self=False)
    print(f"[ANSWER] Sent answer from {request.sid} to room {room}")

@socketio.on('ice-candidate')
def handle_ice_candidate(data):
    room = data.get('room')
    candidate = data.get('candidate')
    emit('ice-candidate', candidate, to=room, include_self=False)
    print(f'[ICE] Sent candidate from {request.sid} to room {room}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f"[DISCONNECT] {request.sid} disconnected")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8081, allow_unsafe_werkzeug=True, ssl_context=('cert.pem', 'key.pem'))
