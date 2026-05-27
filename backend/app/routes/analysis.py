from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.models import Analysis, Session, Alert
from app import db
from app.services.cv_service import CVService

bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')
cv_service = CVService()

@bp.route('', methods=['POST'])
@jwt_required()
def receive_analysis():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    analysis_record = Analysis(
        user_id=user_id,
        mode=data.get('mode'),
        timestamp=datetime.fromtimestamp(data.get('timestamp')/1000),
        status=data.get('status'),
        level=data.get('level'),
        confidence=data.get('confidence', 0),
        focus_level=data.get('focus_level', 0),
        details=data.get('details'),
        face_detected=data.get('face_detected', True),
        frame_quality=data.get('frame_quality', 0)
    )
    db.session.add(analysis_record)
    
    if data.get('level') in ['high', 'critical']:
        alert = Alert(
            user_id=user_id,
            session_id=data.get('session_id'),
            mode=data.get('mode'),
            alert_type=data.get('status'),
            severity=data.get('level'),
            timestamp=datetime.fromtimestamp(data.get('timestamp')/1000),
            message=data.get('message'),
            details=data.get('details'),
            acknowledged=False
        )
        db.session.add(alert)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'analysis_id': analysis_record.id,
        'alert_triggered': data.get('level') in ['high', 'critical']
    }), 201

@bp.route('/face-detect', methods=['POST'])
@jwt_required()
def face_detect():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    user_id = get_jwt_identity()
    
    result = cv_service.detect_faces(file)
    
    analysis_record = Analysis(
        user_id=user_id,
        mode='driving',
        timestamp=datetime.utcnow(),
        status='face_detected' if result['faces_detected'] else 'no_face_detected',
        level='low',
        confidence=result.get('confidence', 0),
        details=result,
        face_detected=result['faces_detected']
    )
    db.session.add(analysis_record)
    db.session.commit()
    
    return jsonify(result), 200

@bp.route('/fatigue-analysis', methods=['POST'])
@jwt_required()
def fatigue_analysis():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    user_id = get_jwt_identity()
    mode = request.form.get('mode', 'driving')
    
    result = cv_service.analyze_fatigue(file, mode)
    
    analysis_record = Analysis(
        user_id=user_id,
        mode=mode,
        timestamp=datetime.utcnow(),
        status=result['status'],
        level=result['level'],
        confidence=result.get('confidence', 0),
        details=result
    )
    db.session.add(analysis_record)
    
    if result['level'] in ['high', 'critical']:
        alert = Alert(
            user_id=user_id,
            mode=mode,
            alert_type=result['status'],
            severity=result['level'],
            timestamp=datetime.utcnow(),
            message=f"疲劳检测告警: {result['status']}",
            details=result,
            acknowledged=False
        )
        db.session.add(alert)
    
    db.session.commit()
    
    return jsonify(result), 200

@bp.route('/focus-analysis', methods=['POST'])
@jwt_required()
def focus_analysis():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    user_id = get_jwt_identity()
    mode = request.form.get('mode', 'learning')
    
    result = cv_service.analyze_focus(file, mode)
    
    analysis_record = Analysis(
        user_id=user_id,
        mode=mode,
        timestamp=datetime.utcnow(),
        status=result['status'],
        level=result['level'],
        confidence=result.get('confidence', 0),
        focus_level=result.get('focus_level', 0),
        details=result
    )
    db.session.add(analysis_record)
    
    if result['level'] in ['medium', 'high', 'critical']:
        alert = Alert(
            user_id=user_id,
            mode=mode,
            alert_type='low_focus',
            severity=result['level'],
            timestamp=datetime.utcnow(),
            message=f"专注度告警: {result['focus_level']}%",
            details=result,
            acknowledged=False
        )
        db.session.add(alert)
    
    db.session.commit()
    
    return jsonify(result), 200

@bp.route('/stream', methods=['POST'])
@jwt_required()
def process_stream():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    frame_data = data.get('frame')
    mode = data.get('mode', 'driving')
    
    result = cv_service.process_frame_base64(frame_data, mode)
    
    analysis_record = Analysis(
        user_id=user_id,
        mode=mode,
        timestamp=datetime.utcnow(),
        status=result['status'],
        level=result['level'],
        confidence=result.get('confidence', 0),
        focus_level=result.get('focus_level', 0),
        details=result
    )
    db.session.add(analysis_record)
    
    if result['level'] in ['high', 'critical']:
        alert = Alert(
            user_id=user_id,
            mode=mode,
            alert_type=result['status'],
            severity=result['level'],
            timestamp=datetime.utcnow(),
            details=result,
            acknowledged=False
        )
        db.session.add(alert)
    
    db.session.commit()
    
    return jsonify(result), 200

@bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    mode = request.args.get('mode')
    
    query = Analysis.query.filter_by(user_id=user_id)
    if mode:
        query = query.filter_by(mode=mode)
    
    analyses = query.order_by(Analysis.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'analyses': [a.to_dict() for a in analyses.items],
        'total': analyses.total,
        'pages': analyses.pages,
        'current_page': page
    }), 200