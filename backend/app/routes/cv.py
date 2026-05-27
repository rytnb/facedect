from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.fatigue_detector import FatigueDetector
from app.services.posture_detector import PostureDetector
from app.services.gaze_estimator import GazeEstimator
from app.services.attention_scorer import AttentionScorer
import cv2
import numpy as np
import base64

bp = Blueprint('cv', __name__, url_prefix='/api/cv')

fatigue_detector = FatigueDetector()
posture_detector = PostureDetector()
gaze_estimator = GazeEstimator()
attention_scorer = AttentionScorer()

def process_image_for_analysis(frame_data):
    img_data = base64.b64decode(frame_data)
    nparr = np.frombuffer(img_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    max_dim = 320
    h, w = image.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)))
    
    fatigue_result = fatigue_detector.detect_fatigue(image)
    gaze_result = gaze_estimator.estimate_gaze(image)
    posture_result = posture_detector.detect_posture(image)
    attention_result = attention_scorer.calculate_attention(
        fatigue_result, gaze_result, posture_result
    )
    
    return {
        'attention': attention_result,
        'fatigue': fatigue_result,
        'gaze': gaze_result,
        'posture': posture_result
    }

def decode_base64_image(frame_data):
    import base64
    import numpy as np
    import cv2
    
    img_data = base64.b64decode(frame_data)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

@bp.route('/fatigue', methods=['POST'])
@jwt_required()
def detect_fatigue():
    data = request.get_json()
    frame_data = data.get('frame')
    
    if not frame_data:
        return jsonify({'error': 'No frame data provided'}), 400
    
    try:
        image = decode_base64_image(frame_data)
        result = fatigue_detector.detect_fatigue(image)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/posture', methods=['POST'])
@jwt_required()
def detect_posture():
    data = request.get_json()
    frame_data = data.get('frame')
    
    if not frame_data:
        return jsonify({'error': 'No frame data provided'}), 400
    
    try:
        image = decode_base64_image(frame_data)
        result = posture_detector.detect_posture(image)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/gaze', methods=['POST'])
@jwt_required()
def estimate_gaze():
    data = request.get_json()
    frame_data = data.get('frame')
    
    if not frame_data:
        return jsonify({'error': 'No frame data provided'}), 400
    
    try:
        image = decode_base64_image(frame_data)
        result = gaze_estimator.estimate_gaze(image)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/attention', methods=['POST'])
@jwt_required()
def calculate_attention():
    data = request.get_json()
    frame_data = data.get('frame')
    
    if not frame_data:
        return jsonify({'error': 'No frame data provided'}), 400
    
    try:
        image = decode_base64_image(frame_data)
        
        fatigue_result = fatigue_detector.detect_fatigue(image)
        gaze_result = gaze_estimator.estimate_gaze(image)
        posture_result = posture_detector.detect_posture(image)
        
        attention_result = attention_scorer.calculate_attention(
            fatigue_result, gaze_result, posture_result
        )
        
        return jsonify({
            'attention': attention_result,
            'fatigue': fatigue_result,
            'gaze': gaze_result,
            'posture': posture_result
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/parameters/fatigue', methods=['GET'])
@jwt_required()
def get_fatigue_params():
    params = fatigue_detector.get_parameters()
    return jsonify(params), 200

@bp.route('/parameters/fatigue', methods=['PUT'])
@jwt_required()
def set_fatigue_params():
    data = request.get_json()
    fatigue_detector.set_parameters(
        ear_threshold=data.get('EAR_THRESHOLD'),
        ear_consec_frames=data.get('EAR_CONSEC_FRAMES'),
        perclos_threshold=data.get('PERCLOS_THRESHOLD'),
        perclos_time_window=data.get('PERCLOS_TIME_WINDOW')
    )
    return jsonify({'message': 'Fatigue parameters updated', 'params': fatigue_detector.get_parameters()}), 200

@bp.route('/parameters/posture', methods=['GET'])
@jwt_required()
def get_posture_params():
    params = posture_detector.get_parameters()
    return jsonify(params), 200

@bp.route('/parameters/posture', methods=['PUT'])
@jwt_required()
def set_posture_params():
    data = request.get_json()
    posture_detector.set_parameters(
        shoulder_threshold=data.get('SHOULDER_THRESHOLD'),
        hip_threshold=data.get('HIP_THRESHOLD'),
        head_tilt_threshold=data.get('HEAD_TILT_THRESHOLD'),
        spine_curve_threshold=data.get('SPINE_CURVE_THRESHOLD')
    )
    return jsonify({'message': 'Posture parameters updated', 'params': posture_detector.get_parameters()}), 200

@bp.route('/parameters/gaze', methods=['GET'])
@jwt_required()
def get_gaze_params():
    params = gaze_estimator.get_parameters()
    return jsonify(params), 200

@bp.route('/parameters/gaze', methods=['PUT'])
@jwt_required()
def set_gaze_params():
    data = request.get_json()
    gaze_estimator.set_parameters(
        gaze_threshold=data.get('GAZE_THRESHOLD')
    )
    return jsonify({'message': 'Gaze parameters updated', 'params': gaze_estimator.get_parameters()}), 200

@bp.route('/parameters/attention', methods=['GET'])
@jwt_required()
def get_attention_params():
    params = attention_scorer.get_parameters()
    return jsonify(params), 200

@bp.route('/parameters/attention', methods=['PUT'])
@jwt_required()
def set_attention_params():
    data = request.get_json()
    
    if 'weights' in data:
        weights = data['weights']
        attention_scorer.set_weights(
            fatigue=weights.get('fatigue'),
            gaze=weights.get('gaze'),
            posture=weights.get('posture')
        )
    
    if 'thresholds' in data:
        thresholds = data['thresholds']
        attention_scorer.set_thresholds(
            fatigue_critical=thresholds.get('fatigue_critical'),
            gaze_critical=thresholds.get('gaze_critical'),
            posture_critical=thresholds.get('posture_critical')
        )
    
    return jsonify({'message': 'Attention parameters updated', 'params': attention_scorer.get_parameters()}), 200

@bp.route('/parameters/all', methods=['GET'])
@jwt_required()
def get_all_params():
    return jsonify({
        'fatigue': fatigue_detector.get_parameters(),
        'posture': posture_detector.get_parameters(),
        'gaze': gaze_estimator.get_parameters(),
        'attention': attention_scorer.get_parameters()
    }), 200

@bp.route('/reset', methods=['POST'])
@jwt_required()
def reset_detectors():
    global fatigue_detector, posture_detector, gaze_estimator, attention_scorer
    fatigue_detector = FatigueDetector()
    posture_detector = PostureDetector()
    gaze_estimator = GazeEstimator()
    attention_scorer = AttentionScorer()
    return jsonify({'message': 'All detectors reset to default parameters'}), 200

@bp.route('/test/attention', methods=['POST'])
def test_attention():
    import traceback
    
    data = request.get_json()
    frame_data = data.get('frame')
    
    if not frame_data:
        return jsonify({'error': 'No frame data provided'}), 400
    
    try:
        print(f"Received frame data: {len(frame_data)} bytes")
        
        result = process_image_for_analysis(frame_data)
        
        print(f"Analysis completed successfully")
        return jsonify(result), 200
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error processing image: {error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500