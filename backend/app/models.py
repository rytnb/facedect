from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    role = db.Column(db.Enum('user', 'admin', 'super_admin'), default='user')
    status = db.Column(db.Enum('active', 'inactive', 'suspended'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    sessions = db.relationship('Session', backref='user', lazy=True)
    analyses = db.relationship('Analysis', backref='user', lazy=True)
    alerts = db.relationship('Alert', backref='user', lazy=True, foreign_keys='Alert.user_id')
    acknowledged_alerts = db.relationship('Alert', backref='acknowledged_by_user', lazy=True, foreign_keys='Alert.acknowledged_by')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mode = db.Column(db.Enum('driving', 'learning'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer, default=0)
    total_frames = db.Column(db.Integer, default=0)
    avg_focus_level = db.Column(db.Float, default=0)
    avg_confidence = db.Column(db.Float, default=0)
    total_alerts = db.Column(db.Integer, default=0)
    fatigue_alerts = db.Column(db.Integer, default=0)
    distraction_alerts = db.Column(db.Integer, default=0)
    status = db.Column(db.Enum('active', 'completed', 'interrupted'), default='active')
    device_info = db.Column(db.String(255))
    location = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    analyses = db.relationship('Analysis', backref='session', lazy=True)
    alerts = db.relationship('Alert', backref='session', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'mode': self.mode,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'total_frames': self.total_frames,
            'avg_focus_level': float(self.avg_focus_level),
            'avg_confidence': float(self.avg_confidence),
            'total_alerts': self.total_alerts,
            'fatigue_alerts': self.fatigue_alerts,
            'distraction_alerts': self.distraction_alerts,
            'status': self.status,
            'device_info': self.device_info,
            'location': self.location
        }

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mode = db.Column(db.Enum('driving', 'learning'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)
    level = db.Column(db.Enum('low', 'medium', 'high', 'critical'), nullable=False)
    confidence = db.Column(db.Float, default=0)
    focus_level = db.Column(db.Integer, default=0)
    details = db.Column(db.JSON)
    face_detected = db.Column(db.Boolean, default=True)
    frame_quality = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'mode': self.mode,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status,
            'level': self.level,
            'confidence': float(self.confidence),
            'focus_level': self.focus_level,
            'details': self.details,
            'face_detected': self.face_detected,
            'frame_quality': float(self.frame_quality)
        }

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mode = db.Column(db.Enum('driving', 'learning'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.Enum('low', 'medium', 'high', 'critical'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    message = db.Column(db.Text)
    details = db.Column(db.JSON)
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    response_action = db.Column(db.String(100))
    frame_snapshot = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'mode': self.mode,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat(),
            'message': self.message,
            'details': self.details,
            'acknowledged': self.acknowledged,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'acknowledged_by': self.acknowledged_by,
            'response_action': self.response_action,
            'frame_snapshot': self.frame_snapshot
        }