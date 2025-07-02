from flask import Flask, request,  render_template
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*")

active_rooms = {}

#Display Webpage
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join(data):
    room = data.get('room')
    active_rooms[room] = {
        'creator': request.sid
    }
    join_room(room)
    emit('joined', {'sid': request.sid}, to=room, include_self=False)
    print(f"(Join) {request.sid} joined room {room}")

@socketio.on('ans_join')
def handle_ans_join(data):
    sid = request.sid
    room = data.get('room')
    if room in active_rooms:
        join_room(room)
        emit('joined', {'sid': sid}, to=room, include_self=False)
        print(f"(Join) {sid} joined room {room}")
    else:
        print("room doesn't exist dummy")
        emit('failed join', {'sid': sid}, to=sid)
        print(len(active_rooms))


@socketio.on('offer')
def handle_offer(data):
    room = data.get('room')
    offer = data.get('offer')
    emit('offer', offer, to=room, include_self=False)
    print(f"(Offer) Sent offer from {request.sid} to room {room}")

@socketio.on('answer')
def handle_answer(data):
    room = data.get('room')
    answer = data.get('answer')
    emit('answer', answer, to=room, include_self=False)
    print(f"(Answer) Sent answer from {request.sid} to room {room}")

@socketio.on('ice-candidate')
def handle_ice_candidate(data):
    room = data.get('room')
    candidate = data.get('candidate')
    emit('ice-candidate', candidate, to=room, include_self=False)
    print(f'(ICE) Sent candidate from {request.sid} to room {room}')

# FIGURE THIS OUT ON WEDNESDAY
@socketio.on('disconnect')
def handle_disconnect(data):
    print(data)
    sid = request.sid
    room = data.get('room')
    active_rooms[room].remove(sid)
    room = data.get('room')
    print(f"(Disconnect) {sid} disconnected")
    emit("disconnect", {"sid": request.sid}, to=room, include_self=False)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8081, allow_unsafe_werkzeug=True, ssl_context=('cert.pem', 'key.pem'))
