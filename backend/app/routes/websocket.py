from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import emit, join_room, leave_room
from app import socketio
from app.models import User
from app.services.fatigue_detector import FatigueDetector
from app.services.gaze_estimator import GazeEstimator
from app.services.posture_detector import PostureDetector
from app.services.attention_scorer import AttentionScorer
import json

bp = Blueprint('websocket', __name__)

active_users = {}
test_rooms = {}
streaming_clients = set()

detectors = {}

def get_detectors(room_id):
    if room_id not in detectors:
        detectors[room_id] = {
            'fatigue': FatigueDetector(),
            'gaze': GazeEstimator(),
            'posture': PostureDetector(),
            'attention': AttentionScorer()
        }
    return detectors[room_id]

def process_frame_async(frame_data, mode, room_id):
    try:
        import cv2
        import numpy as np
        import base64
        from datetime import datetime
        
        if not frame_data or len(frame_data) < 100:
            emit('frame_error', {'error': 'Invalid or empty frame data'}, room=room_id)
            return None
        
        try:
            img_data = base64.b64decode(frame_data)
        except Exception as e:
            emit('frame_error', {'error': f'Base64 decode failed: {str(e)}'}, room=room_id)
            return None
        
        if len(img_data) == 0:
            emit('frame_error', {'error': 'Decoded image data is empty'}, room=room_id)
            return None
        
        nparr = np.frombuffer(img_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            emit('frame_error', {'error': 'Failed to decode image'}, room=room_id)
            return None
        
        max_dim = 240
        h, w = image.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            image = cv2.resize(image, (int(w * scale), int(h * scale)))
        
        det = get_detectors(room_id)
        fatigue_detector = det['fatigue']
        gaze_estimator = det['gaze']
        posture_detector = det['posture']
        attention_scorer = det['attention']
        
        fatigue_result = fatigue_detector.detect_fatigue(image)
        gaze_result = gaze_estimator.estimate_gaze(image)
        posture_result = posture_detector.detect_posture(image)
        
        attention_result = attention_scorer.calculate_attention(
            fatigue_result, gaze_result, posture_result
        )
        
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'mode': mode,
            'fatigue': fatigue_result,
            'gaze': gaze_result,
            'posture': posture_result,
            'attention': attention_result
        }
        
        emit('frame_result', result, room=room_id)
        
        if attention_result.get('status') in ['low', 'critical']:
            alert_data = {
                'type': 'attention_warning',
                'severity': attention_result['status'],
                'message': get_alert_message(result),
                'timestamp': result.get('timestamp'),
                'details': result
            }
            emit('alert', alert_data, room=room_id)
        
        return result
    except Exception as e:
        print(f'Error processing frame: {e}')
        emit('frame_error', {'error': str(e)}, room=room_id)
        return None

def get_alert_message(result):
    attention = result.get('attention', {})
    status = attention.get('status', '')
    
    if status == 'critical':
        return '⚠️ 检测到严重疲劳或注意力不集中，请休息！'
    elif status == 'low':
        return '⚠️ 注意力下降，请保持专注！'
    return '检测到异常状态'

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connected', {'sid': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    user_id = None
    for uid, sid in active_users.items():
        if sid == request.sid:
            user_id = uid
            break
    
    if user_id:
        del active_users[user_id]
        leave_room(f'user_{user_id}')
        if f'user_{user_id}' in detectors:
            del detectors[f'user_{user_id}']
        print(f'User {user_id} disconnected')
    
    test_room_id = None
    for rid, sid in test_rooms.items():
        if sid == request.sid:
            test_room_id = rid
            break
    
    if test_room_id:
        del test_rooms[test_room_id]
        if test_room_id in detectors:
            del detectors[test_room_id]
        print(f'Test client disconnected: {test_room_id}')
    
    if request.sid in streaming_clients:
        streaming_clients.remove(request.sid)
        print(f'Client stopped streaming: {request.sid}')

@socketio.on('join')
@jwt_required()
def handle_join(data):
    user_id = get_jwt_identity()
    active_users[user_id] = request.sid
    room = f'user_{user_id}'
    join_room(room)
    
    emit('joined', {'room': room, 'user_id': user_id}, room=room)
    print(f'User {user_id} joined room {room}')

@socketio.on('join_test')
def handle_join_test():
    room_id = f'test_{request.sid}'
    test_rooms[room_id] = request.sid
    join_room(room_id)
    
    emit('joined_test', {'room': room_id}, room=room_id)
    print(f'Test client joined room: {room_id}')

@socketio.on('leave')
@jwt_required()
def handle_leave(data):
    user_id = get_jwt_identity()
    room = f'user_{user_id}'
    leave_room(room)
    
    if user_id in active_users:
        del active_users[user_id]
    
    emit('left', {'room': room}, room=room)
    print(f'User {user_id} left room {room}')

@socketio.on('frame')
@jwt_required()
def handle_frame(data):
    user_id = get_jwt_identity()
    frame_data = data.get('frame')
    mode = data.get('mode', 'driving')
    
    result = process_frame_async(frame_data, mode, f'user_{user_id}')
    
    if result and result.get('attention') and result['attention'].get('status') in ['high', 'critical']:
        emit_alert(result, user_id)

@socketio.on('frame_test')
def handle_frame_test(data):
    frame_data = data.get('frame')
    mode = data.get('mode', 'driving')
    
    room_id = f'test_{request.sid}'
    
    emit('frame_received', {'status': 'processing'}, room=room_id)
    
    result = process_frame_async(frame_data, mode, room_id)
    
    if result:
        print(f'Test frame processed: mode={mode}, attention_score={result.get("attention", {}).get("attention_score", 0)}')

@socketio.on('start_stream')
def handle_start_stream(data):
    mode = data.get('mode', 'driving')
    room_id = f'test_{request.sid}'
    
    streaming_clients.add(request.sid)
    emit('stream_started', {
        'mode': mode,
        'message': '视频流已开始'
    }, room=room_id)
    
    print(f'Client started streaming: {request.sid}, mode={mode}')

@socketio.on('stop_stream')
def handle_stop_stream(data=None):
    room_id = f'test_{request.sid}'
    
    if request.sid in streaming_clients:
        streaming_clients.remove(request.sid)
    
    emit('stream_stopped', {
        'message': '视频流已停止'
    }, room=room_id)
    
    print(f'Client stopped streaming: {request.sid}')

@socketio.on('heartbeat')
def handle_heartbeat():
    emit('heartbeat_response', {'timestamp': datetime.utcnow().isoformat()})

@socketio.on('start_monitoring')
@jwt_required()
def handle_start_monitoring(data):
    user_id = get_jwt_identity()
    mode = data.get('mode', 'driving')
    
    emit('monitoring_started', {
        'mode': mode,
        'timestamp': data.get('timestamp')
    }, room=f'user_{user_id}')
    
    print(f'Monitoring started for user {user_id} in {mode} mode')

@socketio.on('stop_monitoring')
@jwt_required()
def handle_stop_monitoring(data):
    user_id = get_jwt_identity()
    
    emit('monitoring_stopped', {
        'timestamp': data.get('timestamp')
    }, room=f'user_{user_id}')
    
    print(f'Monitoring stopped for user {user_id}')

def emit_alert(result, user_id):
    alert_data = {
        'type': result.get('status'),
        'severity': result.get('level'),
        'message': f"检测到{result.get('status')}",
        'timestamp': result.get('timestamp'),
        'details': result.get('details')
    }
    
    emit('alert', alert_data, room=f'user_{user_id}')
    print(f'Alert emitted to user {user_id}: {alert_data}')

def broadcast_alert(alert):
    user_id = alert.user_id
    room = f'user_{user_id}'
    
    alert_data = {
        'id': alert.id,
        'type': alert.alert_type,
        'severity': alert.severity,
        'message': alert.message,
        'timestamp': alert.timestamp.isoformat(),
        'details': alert.details
    }
    
    emit('alert', alert_data, room=room)