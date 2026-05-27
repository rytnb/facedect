import cv2
import numpy as np
from collections import deque

class GazeEstimator:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        self.GAZE_THRESHOLD = 0.3
        self.gaze_history = deque(maxlen=10)
    
    def get_eye_region(self, image, face, eye):
        fx, fy, fw, fh = face
        ex, ey, ew, eh = eye
        
        eye_region = image[fy+ey:fy+ey+eh, fx+ex:fx+ex+ew]
        return eye_region, (fx+ex, fy+ey)
    
    def detect_pupil(self, eye_region):
        if eye_region is None or eye_region.size == 0:
            return None
        
        gray = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        
        adaptive_threshold = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        contours, _ = cv2.findContours(adaptive_threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours is None or len(contours) == 0:
            return None
        
        contours = [c for c in contours if cv2.contourArea(c) > 10]
        
        if len(contours) == 0:
            return None
        
        largest_contour = max(contours, key=cv2.contourArea)
        moments = cv2.moments(largest_contour)
        
        if moments['m00'] == 0:
            return None
        
        cx = int(moments['m10'] / moments['m00'])
        cy = int(moments['m01'] / moments['m00'])
        
        return (cx, cy)
    
    def estimate_gaze(self, image):
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
            
            if faces is None or len(faces) == 0:
                return {
                    'detected': False,
                    'gaze_direction': 'unknown',
                    'gaze_score': 0,
                    'details': {}
                }
            
            face = faces[0]
            fx, fy, fw, fh = face
            roi_gray = gray[fy:fy+fh, fx:fx+fw]
            eyes = self.eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
            
            if eyes is None:
                eyes = []
            
            eyes = sorted(eyes, key=lambda e: e[1])[:2]
            
            if len(eyes) < 2:
                last_gaze = self.gaze_history[-1] if self.gaze_history else 0.7
                return {
                    'detected': True,
                    'gaze_direction': 'center',
                    'gaze_score': float(last_gaze),
                    'details': {'eyes_not_detected': True}
                }
            
            left_eye = eyes[0] if eyes[0][0] < eyes[1][0] else eyes[1]
            right_eye = eyes[1] if eyes[0][0] < eyes[1][0] else eyes[0]
            
            left_eye_region, left_offset = self.get_eye_region(image, face, left_eye)
            right_eye_region, right_offset = self.get_eye_region(image, face, right_eye)
            
            left_pupil = self.detect_pupil(left_eye_region)
            right_pupil = self.detect_pupil(right_eye_region)
            
            if left_pupil is None or right_pupil is None:
                last_gaze = self.gaze_history[-1] if self.gaze_history else 0.7
                return {
                    'detected': True,
                    'gaze_direction': 'center',
                    'gaze_score': float(last_gaze),
                    'details': {'pupil_not_detected': True}
                }
            
            left_eye_center = (left_offset[0] + left_eye[2]//2, left_offset[1] + left_eye[3]//2)
            right_eye_center = (right_offset[0] + right_eye[2]//2, right_offset[1] + right_eye[3]//2)
            
            left_pupil_abs = (left_pupil[0] + left_offset[0], left_pupil[1] + left_offset[1])
            right_pupil_abs = (right_pupil[0] + right_offset[0], right_pupil[1] + right_offset[1])
            
            dx_left = left_pupil_abs[0] - left_eye_center[0]
            dy_left = left_pupil_abs[1] - left_eye_center[1]
            dx_right = right_pupil_abs[0] - right_eye_center[0]
            dy_right = right_pupil_abs[1] - right_eye_center[1]
            
            avg_dx = (dx_left + dx_right) / 2
            avg_dy = (dy_left + dy_right) / 2
            
            gaze_direction = self.classify_direction(avg_dx, avg_dy)
            
            eye_width = min(left_eye[2], right_eye[2])
            max_deviation = eye_width * 0.3
            
            distance = np.sqrt(avg_dx**2 + avg_dy**2)
            gaze_score = max(0, min(1, 1 - (distance / max_deviation)))
            
            self.gaze_history.append(gaze_score)
            avg_gaze = np.mean(self.gaze_history)
            
            return {
                'detected': True,
                'gaze_direction': gaze_direction,
                'gaze_score': float(avg_gaze),
                'details': {
                    'left_pupil': {'x': int(left_pupil_abs[0]), 'y': int(left_pupil_abs[1])},
                    'right_pupil': {'x': int(right_pupil_abs[0]), 'y': int(right_pupil_abs[1])},
                    'left_eye_center': {'x': int(left_eye_center[0]), 'y': int(left_eye_center[1])},
                    'right_eye_center': {'x': int(right_eye_center[0]), 'y': int(right_eye_center[1])},
                    'gaze_vector': {'dx': float(avg_dx), 'dy': float(avg_dy)}
                }
            }
        except Exception as e:
            last_gaze = self.gaze_history[-1] if self.gaze_history else 0.7
            return {
                'detected': True,
                'gaze_direction': 'center',
                'gaze_score': float(last_gaze),
                'details': {'error': str(e)}
            }
    
    def classify_direction(self, dx, dy):
        threshold = 8
        
        if abs(dx) < threshold and abs(dy) < threshold:
            return 'center'
        elif dx < -threshold:
            return 'left'
        elif dx > threshold:
            return 'right'
        elif dy < -threshold:
            return 'up'
        else:
            return 'down'
    
    def set_parameters(self, gaze_threshold=None):
        if gaze_threshold is not None:
            self.GAZE_THRESHOLD = gaze_threshold
    
    def get_parameters(self):
        return {
            'GAZE_THRESHOLD': self.GAZE_THRESHOLD
        }