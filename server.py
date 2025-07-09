import os
from flask import Flask, request,  render_template, session
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity
from flask_bcrypt import Bcrypt

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Database and JWT Configuration ---
app.config['SECRET_KEY'] = 'your-super-secret-key-change-me'
app.config['JWT_SECRET_KEY'] = 'your-jwt-secret-key-change-me'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# --- Database Model ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

# --- Room Management ---
active_rooms = {}

# --- HTTP Routes ---
@app.route('/')
def login_page():
    """Serves the login/register page."""
    return render_template('login.html')

@app.route('/chat')
def index():
    """Serves the main WebRTC application page."""
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return {'msg': 'Username and password required.'}, 400

    if User.query.filter_by(username=username).first():
        return {'msg': 'Username is already taken.'}, 400

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    return {'msg': f'User {username} created successfully.'}, 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        access_token = create_access_token(identity=username)
        return {'access_token': access_token}, 200

    return {'msg': 'Invalid username or password.'}, 401


# --- Socket.IO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    """Authenticates the connection using the JWT token."""
    auth_header = request.args.get('token') or request.headers.get('Authorization')
    print(auth_header)
    if not auth_header:
        print("(Connect) Connection rejected: No token provided.")
        return False # Reject connection

    try:
        # Manually verify the JWT and get the identity
        from flask_jwt_extended.exceptions import JWTDecodeError
        from flask_jwt_extended import decode_token

        decoded_token = decode_token(auth_header)
        username = decoded_token['sub']
        session['username'] = username # Store username for the session
        print(f"(Connect) Client {username} ({request.sid}) connected.")
        print(decoded_token)
    except Exception as e:
        print(f"(Connect) Connection rejected: Invalid token. Reason: {e}")
        return False # Reject connection


@socketio.on('join')
def handle_join(data):
    room = data.get('room')
    active_rooms[room] = {
        'creator': request.sid
    }
    join_room(room)
    # Only tell other users that someone joined
    emit('joined', {'sid': request.sid}, to=room, include_self=False)
    print(f"(Join) {session.get('username')} ({request.sid}) created and joined room {room}")


@socketio.on('ans_join')
def handle_ans_join(data):
    sid = request.sid
    room = data.get('room')
    if room in active_rooms:
        join_room(room)
        # Tell the original creator that someone has joined
        emit('joined', {'sid': sid}, to=room, include_self=False)
        print(f"(Join) {session.get('username')} ({sid}) joined room {room}")
    else:
        print("Room doesn't exist")
        emit('failed join', {'sid': sid}, to=sid)


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


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    username = session.get('username', 'Unknown')
    print(f"(Disconnect) {username} ({sid}) disconnected")
    # You would need to add logic here to find which room the user was in
    # and notify the other participant.
    # For example:
    # room_to_leave = None
    # for room, members in active_rooms.items():
    #     if sid in members.values():
    #         room_to_leave = room
    #         break
    # if room_to_leave:
    #     emit("disconnect_peer", {"sid": sid}, to=room_to_leave, include_self=False)
    #     del active_rooms[room_to_leave]


if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create database tables if they don't exist
    socketio.run(app, host='0.0.0.0', port=8081, allow_unsafe_werkzeug=True, ssl_context=('cert.pem', 'key.pem'))