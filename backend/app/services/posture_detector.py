import cv2
import numpy as np
from collections import deque

class PostureDetector:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        self.SHOULDER_THRESHOLD = 0.15
        self.HEAD_TILT_THRESHOLD = 45.0
        self.FACE_CENTER_THRESHOLD = 0.2
        
        self.posture_history = deque(maxlen=10)
    
    def detect_face(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
        return faces
    
    def calculate_head_tilt(self, image, face):
        x, y, w, h = face
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        
        img_height, img_width = image.shape[:2]
        img_center_x = img_width // 2
        img_center_y = img_height // 2
        
        dx = face_center_x - img_center_x
        dy = face_center_y - img_center_y
        
        if img_width > 0:
            normalized_dx = dx / img_width
            angle = np.arctan2(abs(dy), abs(dx)) * (180 / np.pi)
            return angle, normalized_dx
        return 0.0, 0.0
    
    def calculate_face_position(self, image, face):
        img_height, img_width = image.shape[:2]
        x, y, w, h = face
        
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        
        img_center_x = img_width // 2
        img_center_y = img_height // 2
        
        offset_x = abs(face_center_x - img_center_x) / img_width
        offset_y = abs(face_center_y - img_center_y) / img_height
        
        return offset_x, offset_y, (face_center_x, face_center_y)
    
    def detect_posture(self, image):
        faces = self.detect_face(image)
        
        if len(faces) == 0:
            return {
                'detected': False,
                'posture_score': 0,
                'status': 'no_face_detected',
                'details': {}
            }
        
        face = faces[0]
        head_tilt, normalized_dx = self.calculate_head_tilt(image, face)
        offset_x, offset_y, face_center = self.calculate_face_position(image, face)
        
        head_tilt_score = max(0, min(100, 100 - ((head_tilt - 10) / (self.HEAD_TILT_THRESHOLD - 10) * 100)))
        head_tilt_score = max(40, head_tilt_score)
        
        position_score = max(0, 100 - ((offset_x + offset_y) / (2 * self.FACE_CENTER_THRESHOLD) * 100))
        position_score = max(50, position_score)
        
        posture_score = (head_tilt_score * 0.5 + position_score * 0.5)
        
        self.posture_history.append(posture_score)
        avg_posture = np.mean(self.posture_history)
        
        if avg_posture >= 80:
            status = 'good'
        elif avg_posture >= 60:
            status = 'moderate'
        else:
            status = 'poor'
        
        return {
            'detected': True,
            'posture_score': float(avg_posture),
            'status': status,
            'details': {
                'head_tilt': float(head_tilt),
                'face_offset_x': float(offset_x),
                'face_offset_y': float(offset_y),
                'face_center': {'x': int(face_center[0]), 'y': int(face_center[1])},
                'component_scores': {
                    'head_tilt': float(head_tilt_score),
                    'position': float(position_score)
                }
            }
        }
    
    def set_parameters(self, shoulder_threshold=None, hip_threshold=None,
                      head_tilt_threshold=None, spine_curve_threshold=None):
        if shoulder_threshold is not None:
            self.SHOULDER_THRESHOLD = shoulder_threshold
        if head_tilt_threshold is not None:
            self.HEAD_TILT_THRESHOLD = head_tilt_threshold
    
    def get_parameters(self):
        return {
            'SHOULDER_THRESHOLD': self.SHOULDER_THRESHOLD,
            'HEAD_TILT_THRESHOLD': self.HEAD_TILT_THRESHOLD,
            'FACE_CENTER_THRESHOLD': self.FACE_CENTER_THRESHOLD
        }