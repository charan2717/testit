import os
import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

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
        partner_sid = waiting_users.pop(0)
        room_id = f"room_{random.randint(1000, 9999)}"
        # Join both users to the same room
        join_room(room_id)
        socketio.server.enter_room(partner_sid, room_id)
        # Notify both clients with room info so they start signaling
        emit('partner_found', {'room': room_id}, room=room_id)
    else:
        waiting_users.append(request.sid)

@socketio.on('signal')
def handle_signal(data):
    room = data['room']
    signal_data = data['signal']
    emit('signal', {'signal': signal_data, 'from': request.sid}, room=room, include_self=False)

@socketio.on('chat_message')
def chat_message(data):
    room = data['room']
    message = data['message']
    emit('chat_message', {'message': message}, room=room, include_self=False)

@socketio.on('leave_room')
def handle_leave(data):
    room = data['room']
    leave_room(room)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in waiting_users:
        waiting_users.remove(request.sid)
    print(f"{request.sid} disconnected")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
