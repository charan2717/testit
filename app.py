import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

waiting_users = []
user_rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join():
    user_id = request.sid

    if user_id in waiting_users:
        # Already waiting, ignore duplicate join
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        room_id = f"room_{random.randint(1000, 9999)}"

        join_room(room_id, sid=user_id)
        join_room(room_id, sid=partner_id)

        user_rooms[user_id] = room_id
        user_rooms[partner_id] = room_id

        # Notify both users of the match
        emit('match_found', {'room': room_id}, room=room_id)
    else:
        waiting_users.append(user_id)

@socketio.on('offer')
def handle_offer(data):
    room = data['room']
    offer = data['offer']
    # Send offer to everyone in the room except sender
    emit('offer', {'room': room, 'offer': offer}, room=room, include_self=False)

@socketio.on('answer')
def handle_answer(data):
    room = data['room']
    answer = data['answer']
    emit('answer', {'room': room, 'answer': answer}, room=room, include_self=False)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    room = data['room']
    candidate = data['candidate']
    emit('ice_candidate', {'candidate': candidate}, room=room, include_self=False)

@socketio.on('chat_message')
def chat_message(data):
    room = data['room']
    message = data['message']
    emit('chat_message', {'message': message}, room=room, include_self=False)

@socketio.on('leave_room')
def handle_leave(data):
    room = data.get('room')
    user_id = request.sid
    if room:
        leave_room(room)
    if user_id in user_rooms:
        # Remove user from stored room info
        del user_rooms[user_id]

    # Also notify partner that stranger left
    emit('chat_message', {'message': 'Stranger has left the chat.'}, room=room, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    if user_id in waiting_users:
        waiting_users.remove(user_id)

    room = user_rooms.get(user_id)
    if room:
        leave_room(room)
        emit('chat_message', {'message': 'Stranger has disconnected.'}, room=room, include_self=False)
        del user_rooms[user_id]

    print(f"{user_id} disconnected")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
