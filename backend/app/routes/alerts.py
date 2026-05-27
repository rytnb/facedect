from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.models import Alert
from app import db

bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')

@bp.route('', methods=['GET'])
@jwt_required()
def get_alerts():
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    acknowledged = request.args.get('acknowledged')
    severity = request.args.get('severity')
    
    query = Alert.query.filter_by(user_id=user_id)
    
    if acknowledged is not None:
        query = query.filter_by(acknowledged=acknowledged.lower() == 'true')
    
    if severity:
        query = query.filter_by(severity=severity)
    
    alerts = query.order_by(Alert.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'alerts': [a.to_dict() for a in alerts.items],
        'total': alerts.total,
        'pages': alerts.pages,
        'current_page': page
    }), 200

@bp.route('/<int:alert_id>', methods=['GET'])
@jwt_required()
def get_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    
    if alert.user_id != get_jwt_identity():
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify(alert.to_dict()), 200

@bp.route('/<int:alert_id>/acknowledge', methods=['PUT'])
@jwt_required()
def acknowledge_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    
    if alert.user_id != get_jwt_identity():
        return jsonify({'error': 'Unauthorized'}), 403
    
    alert.acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = get_jwt_identity()
    
    db.session.commit()
    
    return jsonify(alert.to_dict()), 200

@bp.route('/unacknowledged', methods=['GET'])
@jwt_required()
def get_unacknowledged():
    user_id = get_jwt_identity()
    
    alerts = Alert.query.filter_by(user_id=user_id, acknowledged=False)\
        .order_by(Alert.severity.desc(), Alert.timestamp.desc())\
        .all()
    
    return jsonify({
        'alerts': [a.to_dict() for a in alerts],
        'count': len(alerts)
    }), 200

@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_alert_stats():
    user_id = get_jwt_identity()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Alert.query.filter_by(user_id=user_id)
    
    if start_date:
        query = query.filter(Alert.timestamp >= datetime.fromisoformat(start_date))
    
    if end_date:
        query = query.filter(Alert.timestamp <= datetime.fromisoformat(end_date))
    
    stats = query.with_entities(
        Alert.alert_type,
        Alert.severity,
        db.func.count(Alert.id).label('count')
    ).group_by(Alert.alert_type, Alert.severity).all()
    
    result = {}
    for stat in stats:
        if stat.alert_type not in result:
            result[stat.alert_type] = {}
        result[stat.alert_type][stat.severity] = stat.count
    
    return jsonify(result), 200