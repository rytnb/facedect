import cv2
import numpy as np
import base64
from PIL import Image
import io
from collections import deque

class FatigueDetector:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        self.EAR_THRESHOLD = 0.2
        self.EAR_CONSEC_FRAMES = 3
        
        self.PERCLOS_TIME_WINDOW = 30
        self.PERCLOS_THRESHOLD = 0.3
        
        self.eye_closed_counter = 0
        self.total_frames = 0
        self.eye_closed_frames = 0
        
        self.ear_history = deque(maxlen=30)
        self.frame_times = deque(maxlen=30)
    
    def eye_aspect_ratio(self, eye):
        if len(eye) != 4:
            return 0.3
        
        x, y, w, h = eye
        ear = h / w
        
        return min(max(ear, 0.1), 0.4)
    
    def detect_faces(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
        return faces
    
    def detect_eyes(self, image, face):
        x, y, w, h = face
        roi_color = image[y:y+h, x:x+w]
        roi_gray = cv2.cvtColor(roi_color, cv2.COLOR_BGR2GRAY)
        eyes = self.eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
        
        eyes = sorted(eyes, key=lambda e: e[1])[:2]
        
        return eyes
    
    def calculate_EAR(self, eyes):
        if len(eyes) == 0:
            return 0.3, 0.3, 0.3
        elif len(eyes) == 1:
            ear = self.eye_aspect_ratio(eyes[0])
            return ear, ear, ear
        
        left_eye = eyes[0] if eyes[0][0] < eyes[1][0] else eyes[1]
        right_eye = eyes[1] if eyes[0][0] < eyes[1][0] else eyes[0]
        
        left_ear = self.eye_aspect_ratio(left_eye)
        right_ear = self.eye_aspect_ratio(right_eye)
        
        avg_ear = (left_ear + right_ear) / 2.0
        return avg_ear, left_ear, right_ear
    
    def calculate_PERCLOS(self, ear):
        self.total_frames += 1
        self.ear_history.append(ear)
        
        if ear < self.EAR_THRESHOLD:
            self.eye_closed_frames += 1
        
        if self.total_frames > self.PERCLOS_TIME_WINDOW:
            self.total_frames = self.PERCLOS_TIME_WINDOW
            self.eye_closed_frames = sum(1 for e in self.ear_history if e < self.EAR_THRESHOLD)
        
        perclos = self.eye_closed_frames / self.total_frames if self.total_frames > 0 else 0
        
        return perclos
    
    def detect_fatigue(self, image):
        faces = self.detect_faces(image)
        
        if len(faces) == 0:
            return {
                'detected': False,
                'fatigue_level': 0,
                'EAR': 0,
                'PERCLOS': 0,
                'status': 'no_face_detected'
            }
        
        face = faces[0]
        eyes = self.detect_eyes(image, face)
        avg_ear, left_ear, right_ear = self.calculate_EAR(eyes)
        perclos = self.calculate_PERCLOS(avg_ear)
        
        if avg_ear < self.EAR_THRESHOLD:
            self.eye_closed_counter += 1
        else:
            self.eye_closed_counter = max(0, self.eye_closed_counter - 1)
        
        if perclos > self.PERCLOS_THRESHOLD or self.eye_closed_counter >= self.EAR_CONSEC_FRAMES:
            fatigue_level = min(perclos * 3, 0.8)
            status = 'fatigued'
        else:
            fatigue_level = perclos * 2
            status = 'alert'
        
        return {
            'detected': True,
            'fatigue_level': float(fatigue_level),
            'EAR': float(avg_ear),
            'PERCLOS': float(perclos),
            'left_EAR': float(left_ear),
            'right_EAR': float(right_ear),
            'eye_closed_frames': self.eye_closed_counter,
            'status': status,
            'face_bbox': {
                'x': int(face[0]),
                'y': int(face[1]),
                'w': int(face[2]),
                'h': int(face[3])
            }
        }
    
    def set_parameters(self, ear_threshold=None, ear_consec_frames=None, 
                      perclos_threshold=None, perclos_time_window=None):
        if ear_threshold is not None:
            self.EAR_THRESHOLD = ear_threshold
        if ear_consec_frames is not None:
            self.EAR_CONSEC_FRAMES = ear_consec_frames
        if perclos_threshold is not None:
            self.PERCLOS_THRESHOLD = perclos_threshold
        if perclos_time_window is not None:
            self.PERCLOS_TIME_WINDOW = perclos_time_window
    
    def get_parameters(self):
        return {
            'EAR_THRESHOLD': self.EAR_THRESHOLD,
            'EAR_CONSEC_FRAMES': self.EAR_CONSEC_FRAMES,
            'PERCLOS_THRESHOLD': self.PERCLOS_THRESHOLD,
            'PERCLOS_TIME_WINDOW': self.PERCLOS_TIME_WINDOW
        }