import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

waiting_users = []

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join():
    if waiting_users:
        partner = waiting_users.pop(0)
        room_id = f"room_{random.randint(1000, 9999)}"
        join_room(room_id)
        emit('partner_found', {'room': room_id}, room=room_id)
        socketio.emit('partner_found', {'room': room_id}, room=partner)
    else:
        waiting_users.append(request.sid)

@socketio.on('signal')
def handle_signal(data):
    room = data['room']
    signal_data = data['signal']
    emit('signal', {'signal': signal_data}, room=room, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in waiting_users:
        waiting_users.remove(request.sid)
    print(f"{request.sid} disconnected")

@socketio.on('chat_message')
def chat_message(data):
    room = data['room']
    message = data['message']
    emit('chat_message', {'message': message}, room=room, include_self=False)

@socketio.on('leave_room')
def handle_leave(data):
    room = data['room']
    leave_room(room)


if __name__ == "__main__":
    import eventlet
    eventlet.monkey_patch()
    socketio.run(app, host="0.0.0.0", port=5000)

