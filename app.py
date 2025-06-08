import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

waiting_users = []
user_rooms = {}  # Maps socket_id → room_id

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join():
    user_id = request.sid
    print(f"[JOIN] User {user_id} joined")

    if user_id in waiting_users or user_id in user_rooms:
        print(f"[JOIN] Duplicate join from {user_id}, ignoring.")
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        room_id = f"room_{random.randint(1000, 9999)}"

        join_room(room_id, sid=user_id)
        join_room(room_id, sid=partner_id)

        user_rooms[user_id] = room_id
        user_rooms[partner_id] = room_id

        print(f"[ROOM] Matched {user_id} with {partner_id} in {room_id}")
        emit('match_found', {'room': room_id}, room=room_id)

        # Notify both clients stranger connected
        emit('chat_message', {'message': 'Stranger connected.'}, room=room_id)
    else:
        waiting_users.append(user_id)
        print(f"[WAIT] User {user_id} waiting for match")

@socketio.on('offer')
def handle_offer(data):
    room = data.get('room')
    offer = data.get('offer')
    print(f"[OFFER] Received offer for room {room}")
    emit('offer', {'room': room, 'offer': offer}, room=room, include_self=False)

@socketio.on('answer')
def handle_answer(data):
    room = data.get('room')
    answer = data.get('answer')
    print(f"[ANSWER] Received answer for room {room}")
    emit('answer', {'room': room, 'answer': answer}, room=room, include_self=False)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    room = data.get('room')
    candidate = data.get('candidate')
    print(f"[ICE] Candidate for room {room}")
    emit('ice_candidate', {'candidate': candidate}, room=room, include_self=False)

@socketio.on('chat_message')
def handle_chat_message(data):
    room = data.get('room')
    message = data.get('message')
    print(f"[CHAT] Room {room}: {message}")
    emit('chat_message', {'message': message}, room=room, include_self=False)

@socketio.on('leave_room')
def handle_leave(data):
    room = data.get('room')
    user_id = request.sid
    print(f"[LEAVE] User {user_id} leaving room {room}")

    if room:
        leave_room(room)
        emit('chat_message', {'message': 'Stranger has left the chat.'}, room=room, include_self=False)

    if user_id in user_rooms:
        del user_rooms[user_id]

@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    print(f"[DISCONNECT] User {user_id} disconnected")

    if user_id in waiting_users:
        waiting_users.remove(user_id)

    room = user_rooms.get(user_id)
    if room:
        leave_room(room)
        emit('chat_message', {'message': 'Stranger has disconnected.'}, room=room, include_self=False)
        del user_rooms[user_id]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
