import cv2
import numpy as np
from collections import deque

class AttentionScorer:
    def __init__(self):
        self.fatigue_history = deque(maxlen=30)
        self.gaze_history = deque(maxlen=30)
        self.posture_history = deque(maxlen=30)
        
        self.WEIGHTS = {
            'fatigue': 0.35,
            'gaze': 0.35,
            'posture': 0.30
        }
        
        self.THRESHOLDS = {
            'fatigue_critical': 0.7,
            'gaze_critical': 0.3,
            'posture_critical': 40
        }
        
        self.attention_trend = deque(maxlen=10)
    
    def calculate_attention(self, fatigue_data, gaze_data, posture_data):
        fatigue_score = 0.0
        gaze_score = 0.0
        posture_score = 0.0
        
        if fatigue_data.get('detected'):
            fatigue_score = 1 - fatigue_data.get('fatigue_level', 0)
            self.fatigue_history.append(fatigue_score)
        else:
            if self.fatigue_history:
                fatigue_score = self.fatigue_history[-1]
            else:
                fatigue_score = 0.8
        
        if gaze_data.get('detected'):
            gaze_score = gaze_data.get('gaze_score', 0)
            self.gaze_history.append(gaze_score)
        else:
            if self.gaze_history:
                gaze_score = self.gaze_history[-1]
            else:
                gaze_score = 0.8
        
        if posture_data.get('detected'):
            posture_score = posture_data.get('posture_score', 0) / 100.0
            self.posture_history.append(posture_score)
        else:
            if self.posture_history:
                posture_score = self.posture_history[-1]
            else:
                posture_score = 0.7
        
        avg_fatigue = np.mean(self.fatigue_history) if self.fatigue_history else fatigue_score
        avg_gaze = np.mean(self.gaze_history) if self.gaze_history else gaze_score
        avg_posture = np.mean(self.posture_history) if self.posture_history else posture_score
        
        attention_score = (
            avg_fatigue * self.WEIGHTS['fatigue'] +
            avg_gaze * self.WEIGHTS['gaze'] +
            avg_posture * self.WEIGHTS['posture']
        )
        
        self.attention_trend.append(attention_score)
        
        trend_score = self.calculate_trend()
        
        final_score = (attention_score * 0.9 + trend_score * 0.1) * 100
        
        status = self.classify_attention(final_score)
        
        alert = self.detect_alert(fatigue_data, gaze_data, posture_data)
        
        return {
            'attention_score': float(final_score),
            'status': status,
            'alert': alert,
            'component_scores': {
                'fatigue': float(avg_fatigue * 100),
                'gaze': float(avg_gaze * 100),
                'posture': float(avg_posture * 100)
            },
            'weights': self.WEIGHTS,
            'trend': float(trend_score * 100)
        }
    
    def calculate_trend(self):
        if len(self.attention_trend) < 3:
            return 0.8
        
        recent = np.array(list(self.attention_trend[-3:]))
        earlier = np.array(list(self.attention_trend[:-3])) if len(self.attention_trend) > 3 else recent
        
        recent_avg = np.mean(recent)
        earlier_avg = np.mean(earlier)
        
        if earlier_avg == 0:
            return 0.8
        
        trend = (recent_avg - earlier_avg) / earlier_avg
        
        return min(max(0.5 + trend * 0.5, 0.3), 1.0)
    
    def classify_attention(self, score):
        if score >= 85:
            return 'high'
        elif score >= 70:
            return 'medium'
        elif score >= 50:
            return 'low'
        else:
            return 'critical'
    
    def detect_alert(self, fatigue_data, gaze_data, posture_data):
        alerts = []
        
        if fatigue_data.get('detected'):
            if fatigue_data.get('fatigue_level', 0) >= self.THRESHOLDS['fatigue_critical']:
                alerts.append({
                    'type': 'fatigue',
                    'severity': 'high',
                    'message': '检测到疲劳状态'
                })
        
        if gaze_data.get('detected'):
            if gaze_data.get('gaze_score', 1) <= self.THRESHOLDS['gaze_critical']:
                alerts.append({
                    'type': 'distraction',
                    'severity': 'medium',
                    'message': '检测到注意力分散'
                })
        
        if posture_data.get('detected'):
            if posture_data.get('posture_score', 100) <= self.THRESHOLDS['posture_critical']:
                alerts.append({
                    'type': 'posture',
                    'severity': 'medium',
                    'message': '坐姿不正确'
                })
        
        return alerts
    
    def set_weights(self, fatigue=None, gaze=None, posture=None):
        if fatigue is not None:
            self.WEIGHTS['fatigue'] = fatigue
        if gaze is not None:
            self.WEIGHTS['gaze'] = gaze
        if posture is not None:
            self.WEIGHTS['posture'] = posture
        
        total = sum(self.WEIGHTS.values())
        if total != 1.0:
            self.WEIGHTS = {k: v / total for k, v in self.WEIGHTS.items()}
    
    def set_thresholds(self, fatigue_critical=None, gaze_critical=None, posture_critical=None):
        if fatigue_critical is not None:
            self.THRESHOLDS['fatigue_critical'] = fatigue_critical
        if gaze_critical is not None:
            self.THRESHOLDS['gaze_critical'] = gaze_critical
        if posture_critical is not None:
            self.THRESHOLDS['posture_critical'] = posture_critical
    
    def get_parameters(self):
        return {
            'weights': self.WEIGHTS,
            'thresholds': self.THRESHOLDS
        }
    
    def reset(self):
        self.fatigue_history.clear()
        self.gaze_history.clear()
        self.posture_history.clear()
        self.attention_trend.clear()