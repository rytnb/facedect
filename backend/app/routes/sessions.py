from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.models import Session, Analysis, Alert
from app import db
from sqlalchemy import func

bp = Blueprint('sessions', __name__, url_prefix='/api/sessions')

@bp.route('', methods=['POST'])
@jwt_required()
def start_session():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    session = Session(
        user_id=user_id,
        mode=data.get('mode'),
        start_time=datetime.utcnow(),
        device_info=data.get('device_info'),
        location=data.get('location')
    )
    db.session.add(session)
    db.session.commit()
    
    return jsonify({
        'session_id': session.id,
        'start_time': session.start_time.isoformat()
    }), 201

@bp.route('/<int:session_id>', methods=['GET'])
@jwt_required()
def get_session(session_id):
    session = Session.query.get_or_404(session_id)
    
    if session.user_id != get_jwt_identity():
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify(session.to_dict()), 200

@bp.route('/<int:session_id>', methods=['PUT'])
@jwt_required()
def end_session(session_id):
    session = Session.query.get_or_404(session_id)
    
    if session.user_id != get_jwt_identity():
        return jsonify({'error': 'Unauthorized'}), 403
    
    session.end_time = datetime.utcnow()
    session.duration = (session.end_time - session.start_time).seconds
    session.status = 'completed'
    
    stats = db.session.query(
        func.avg(Analysis.confidence).label('avg_confidence'),
        func.avg(Analysis.focus_level).label('avg_focus'),
        func.count(Analysis.id).label('total_frames'),
        func.sum(case((Alert.alert_type == 'fatigue', 1), else_=0)).label('fatigue_alerts'),
        func.sum(case((Alert.alert_type == 'distraction', 1), else_=0)).label('distraction_alerts'),
        func.count(Alert.id).label('total_alerts')
    ).outerjoin(Alert, Alert.session_id == Analysis.session_id)\
     .filter(Analysis.session_id == session_id)\
     .first()
    
    if stats:
        session.avg_confidence = float(stats.avg_confidence) if stats.avg_confidence else 0
        session.avg_focus_level = float(stats.avg_focus) if stats.avg_focus else 0
        session.total_frames = stats.total_frames or 0
        session.fatigue_alerts = stats.fatigue_alerts or 0
        session.distraction_alerts = stats.distraction_alerts or 0
        session.total_alerts = stats.total_alerts or 0
    
    db.session.commit()
    
    return jsonify(session.to_dict()), 200

@bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    mode = request.args.get('mode')
    
    query = Session.query.filter_by(user_id=user_id)
    if mode:
        query = query.filter_by(mode=mode)
    
    sessions = query.order_by(Session.start_time.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'sessions': [s.to_dict() for s in sessions.items],
        'total': sessions.total,
        'pages': sessions.pages,
        'current_page': page
    }), 200

@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    user_id = get_jwt_identity()
    mode = request.args.get('mode')
    
    query = Session.query.filter_by(user_id=user_id, status='completed')
    if mode:
        query = query.filter_by(mode=mode)
    
    stats = query.with_entities(
        func.count(Session.id).label('total_sessions'),
        func.sum(Session.duration).label('total_duration'),
        func.avg(Session.avg_focus_level).label('avg_focus'),
        func.sum(Session.total_alerts).label('total_alerts')
    ).first()
    
    return jsonify({
        'total_sessions': stats.total_sessions or 0,
        'total_duration_hours': (stats.total_duration or 0) / 3600,
        'avg_focus_level': float(stats.avg_focus) if stats.avg_focus else 0,
        'total_alerts': stats.total_alerts or 0
    }), 200

from sqlalchemy import case