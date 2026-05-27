import cv2
import numpy as np
import base64
from PIL import Image
import io

class CVService:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        self.driving_thresholds = {
            'eye_aspect_ratio_low': 0.25,
            'mouth_aspect_ratio_high': 0.5,
            'head_pose_threshold': 30,
            'consecutive_frames': 3
        }
        
        self.learning_thresholds = {
            'min_focus_level': 60,
            'distraction_threshold': 0.4
        }
        
        self.eye_closed_frames = 0
        self.yawning_frames = 0
    
    def detect_faces(self, file):
        image = self._load_image(file)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        result = {
            'faces_detected': len(faces) > 0,
            'num_faces': len(faces),
            'faces': [],
            'confidence': 0.9 if len(faces) > 0 else 0.0
        }
        
        for (x, y, w, h) in faces:
            result['faces'].append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
                'center_x': int(x + w/2),
                'center_y': int(y + h/2)
            })
        
        return result
    
    def analyze_fatigue(self, file, mode='driving'):
        image = self._load_image(file)
        result = self._analyze_frame(image, mode)
        
        if result.get('level') in ['high', 'critical']:
            result['alert_type'] = 'DROWSINESS_ALERT'
        
        return result
    
    def analyze_focus(self, file, mode='learning'):
        image = self._load_image(file)
        result = self._analyze_frame(image, mode)
        
        if mode == 'learning':
            result['alert_type'] = 'LOW_FOCUS_ALERT' if result['focus_level'] < 60 else None
        
        return result
    
    def process_frame_base64(self, frame_data, mode='driving'):
        image = self._decode_base64_image(frame_data)
        return self._analyze_frame(image, mode)
    
    def _analyze_frame(self, image, mode):
        faces = self.face_cascade.detectMultiScale(
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),
            scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) == 0:
            return {
                'status': 'no_face_detected',
                'level': 'low',
                'confidence': 0.0,
                'focus_level': 0,
                'details': {'faces_detected': False}
            }
        
        face = faces[0]
        x, y, w, h = face
        
        if mode == 'driving':
            return self._analyze_driving(image, face)
        else:
            return self._analyze_learning(image, face)
    
    def _analyze_driving(self, image, face):
        x, y, w, h = face
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        roi_gray = gray[y:y+h, x:x+w]
        eyes = self.eye_cascade.detectMultiScale(roi_gray)
        
        eye_ratio = 0.3
        if len(eyes) >= 2:
            eye_ratio = self._calculate_eye_ratio(eyes, roi_gray)
        
        mouth_aspect_ratio = self._calculate_mouth_ratio(roi_gray)
        
        fatigue_score = self._calculate_fatigue_score(eye_ratio, mouth_aspect_ratio)
        
        if fatigue_score > 0.8:
            status = 'fatigue_critical'
            level = 'critical'
        elif fatigue_score > 0.6:
            status = 'fatigue_warning'
            level = 'high'
        elif mouth_aspect_ratio > 0.45:
            status = 'yawning'
            level = 'medium'
        elif len(eyes) == 0:
            status = 'eyes_closed'
            level = 'high'
        else:
            status = 'normal'
            level = 'low'
        
        return {
            'status': status,
            'level': level,
            'confidence': fatigue_score,
            'focus_level': int((1 - fatigue_score) * 100),
            'details': {
                'eye_ratio': float(eye_ratio),
                'mouth_ratio': float(mouth_aspect_ratio),
                'fatigue_score': float(fatigue_score),
                'face_detected': True,
                'face_bbox': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
            }
        }
    
    def _analyze_learning(self, image, face):
        x, y, w, h = face
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        roi_gray = gray[y:y+h, x:x+w]
        
        eyes = self.eye_cascade.detectMultiScale(roi_gray)
        
        eye_ratio = 0.3
        if len(eyes) >= 2:
            eye_ratio = self._calculate_eye_ratio(eyes, roi_gray)
        
        focus_score = self._calculate_focus_score(eye_ratio, len(eyes))
        
        if focus_score >= 80:
            status = 'focused'
            level = 'low'
        elif focus_score >= 60:
            status = 'moderate'
            level = 'low'
        elif focus_score >= 40:
            status = 'distracted'
            level = 'medium'
        else:
            status = 'low_focus'
            level = 'high'
        
        return {
            'status': status,
            'level': level,
            'confidence': focus_score / 100,
            'focus_level': int(focus_score),
            'details': {
                'eye_ratio': float(eye_ratio),
                'eyes_detected': len(eyes),
                'focus_score': float(focus_score),
                'face_detected': True,
                'face_bbox': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
            }
        }
    
    def _calculate_eye_ratio(self, eyes, roi_gray):
        if len(eyes) >= 2:
            (ex1, ey1, ew1, eh1) = eyes[0]
            (ex2, ey2, ew2, eh2) = eyes[1]
            
            eye1_center = (ex1 + ew1 // 2, ey1 + eh1 // 2)
            eye2_center = (ex2 + ew2 // 2, ey2 + eh2 // 2)
            
            eye_distance = np.sqrt(
                (eye1_center[0] - eye2_center[0])**2 + 
                (eye1_center[1] - eye2_center[1])**2
            )
            
            avg_eye_height = (eh1 + eh2) / 2
            
            if eye_distance > 0:
                return avg_eye_height / eye_distance
        
        return 0.3
    
    def _calculate_mouth_ratio(self, roi_gray):
        mouth_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_smile.xml')
        mouths = mouth_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=20)
        
        if len(mouths) > 0:
            (mx, my, mw, mh) = mouths[0]
            return mh / mw
        
        return 0.2
    
    def _calculate_fatigue_score(self, eye_ratio, mouth_ratio):
        eye_score = 0.0
        if eye_ratio < 0.25:
            eye_score = 0.7
        
        mouth_score = 0.0
        if mouth_ratio > 0.5:
            mouth_score = 0.5
        
        combined_score = (eye_score * 0.6 + mouth_score * 0.4)
        
        if eye_ratio < 0.2:
            self.eye_closed_frames += 1
        else:
            self.eye_closed_frames = 0
        
        if self.eye_closed_frames > 5:
            combined_score = min(combined_score + 0.2, 1.0)
        
        return combined_score
    
    def _calculate_focus_score(self, eye_ratio, num_eyes):
        base_score = 50
        
        if eye_ratio > 0.25:
            base_score += 30
        elif eye_ratio > 0.15:
            base_score += 15
        
        if num_eyes == 2:
            base_score += 20
        elif num_eyes == 1:
            base_score += 10
        
        return min(base_score, 100)
    
    def _load_image(self, file):
        image = Image.open(file.stream)
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    def _decode_base64_image(self, frame_data):
        img_data = base64.b64decode(frame_data)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)