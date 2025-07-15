import os
from flask import Flask, request,  render_template, session, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, \
    set_access_cookies, get_jwt, unset_jwt_cookies, get_jwt_identity
from flask_bcrypt import Bcrypt
from datetime import timedelta, datetime, timezone

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*")

app.config['SECRET_KEY'] = 'your-super-secret-key-change-me'
app.config['JWT_SECRET_KEY'] = 'your-jwt-secret-key-change-me'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = True
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config["SESSION_COOKIE_SAMESITE"] = ['Strict']
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

active_rooms = {}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class TokenBlocklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

@jwt.token_in_blocklist_loader
def check_if_token_in_blocklist(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    token = db.session.query(TokenBlocklist).filter_by(jti=jti).scalar()
    print("Token checked")
    return token is not None

@app.route('/login', methods=['GET', 'POST'])
@app.route('/')
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            response = jsonify({"message": "Login Successful"})
            access_token = create_access_token(identity=username)
            set_access_cookies(response, access_token)
            return response

        return {'msg': 'Invalid username or password.'}, 401
    else:
        return render_template('login.html')


@app.route('/chat')
@jwt_required()
def index():
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

@socketio.on('connect')
@jwt_required()
def handle_connect():
    try:
        jwt_data = get_jwt()
        username = jwt_data.get('sub')
        session['username'] = username
        print(f"(Connect) Client {username} ({request.sid}) connected.")
    except Exception as e:
        print(f"(Connect) Connection rejected: Invalid token. Reason: {e}")
        return False

@app.after_request
def refresh(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=2))
        if target_timestamp > exp_timestamp:
            identity = get_jwt_identity()
            access_token = create_access_token(identity=identity)
            set_access_cookies(response, access_token)
            print(f"Refreshed token for user: {identity}")
        return response
    except (RuntimeError, KeyError):
        return response

@app.route('/logout', methods=['POST', 'DELETE'])
@jwt_required()
def logout():
    try:
        print("it made it this far")
        jti = get_jwt()["jti"]
        now = datetime.now(timezone.utc)
        db.session.add(TokenBlocklist(jti=jti, created_at=now))
        db.session.commit()
        print("jti ", jti, " added to blocklist")
    except Exception as e:
        print("Blocklist was not updated")
    response = jsonify({"message": "Logout Successful"})
    unset_jwt_cookies(response)
    print(f"Logout Successful")
    return response


@socketio.on('join')
def handle_join(data):
    room = data.get('room')
    active_rooms[room] = {
        'creator': request.sid
    }
    join_room(room)
    emit('joined', {'sid': request.sid}, to=room, include_self=False)
    print(f"(Join) {session.get('username')} ({request.sid}) created and joined room {room}")


@socketio.on('ans_join')
def handle_ans_join(data):
    sid = request.sid
    room = data.get('room')
    if room in active_rooms:
        join_room(room)
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
    jti = session.get('jti')
    response = jsonify({'message': 'logout successful'})
    unset_jwt_cookies(response)
    print(f"(Disconnect) {username} ({sid}) disconnected")
    return response, 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create database tables if they don't exist
    socketio.run(app, host='0.0.0.0', port=8082, allow_unsafe_werkzeug=True, ssl_context=('cert.pem', 'key.pem'))