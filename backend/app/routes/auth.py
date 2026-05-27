from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import datetime
from app.models import User
from app import db

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(
        username=data.get('username'),
        email=data.get('email'),
        full_name=data.get('full_name'),
        phone=data.get('phone')
    )
    user.set_password(data.get('password'))
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    
    if not user or not user.check_password(data.get('password')):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    if user.status != 'active':
        return jsonify({'error': 'Account is not active'}), 403
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200

@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    access_token = create_access_token(identity=user_id)
    return jsonify({'access_token': access_token}), 200

@bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200

@bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    if 'email' in data:
        if User.query.filter_by(email=data['email']).first() and data['email'] != user.email:
            return jsonify({'error': 'Email already exists'}), 400
        user.email = data['email']
    
    if 'full_name' in data:
        user.full_name = data['full_name']
    
    if 'phone' in data:
        user.phone = data['phone']
    
    db.session.commit()
    
    return jsonify(user.to_dict()), 200

@bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    if not user.check_password(data.get('old_password')):
        return jsonify({'error': 'Old password is incorrect'}), 401
    
    user.set_password(data.get('new_password'))
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'}), 200