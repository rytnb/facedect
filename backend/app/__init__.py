from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from datetime import datetime
from app.config import Config
import os

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/test.html')
    def test_page():
        return send_from_directory(app.static_folder, 'test.html')
    
    @app.route('/http_test.html')
    def http_test_page():
        return send_from_directory(app.static_folder, 'http_test.html')
    
    @app.route('/stream_test.html')
    def stream_test_page():
        return send_from_directory(app.static_folder, 'stream_test.html')
    
    @app.route('/api')
    def api_info():
        return {
            'message': 'Smart Monitor Server',
            'status': 'running',
            'version': '1.0.0',
            'endpoints': {
                'auth': '/api/auth',
                'analysis': '/api/analysis',
                'sessions': '/api/sessions',
                'alerts': '/api/alerts',
                'cv': '/api/cv',
                'health': '/api/health'
            }
        }
    
    @app.route('/api/health')
    def health_check():
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    from app.routes import auth, analysis, sessions, alerts, websocket, cv
    app.register_blueprint(auth.bp)
    app.register_blueprint(analysis.bp)
    app.register_blueprint(sessions.bp)
    app.register_blueprint(alerts.bp)
    app.register_blueprint(websocket.bp)
    app.register_blueprint(cv.bp)
    
    with app.app_context():
        db.create_all()
    
    return app