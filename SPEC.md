# 双模式智能监测系统架构设计文档

## 1. 系统概述

### 1.1 系统目标
设计一个支持**驾驶模式**和**学习模式**的智能监测系统，实现对用户行为（驾驶行为/学习状态）的实时监测、分析和反馈。

### 1.2 核心功能
- **驾驶模式**：监测驾驶员疲劳驾驶、注意力分散、危险行为等
- **学习模式**：监测学生学习时的专注度、情绪状态、学习行为等
- 实时视频流处理与行为分析
- 数据统计与历史记录查询
- Web后台管理与配置

### 1.3 系统架构总览
```
┌─────────────┐    ┌─────────────────┐    ┌────────────────┐
│ Android App │◄──►│ Flask Backend   │◄──►│ Web Dashboard  │
│ (Java)      │    │ (Python)        │    │ (Admin)        │
└─────────────┘    └─────────────────┘    └────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Computer Vision Module│
              │ (Face Detection,      │
              │  Gaze Tracking, etc.)│
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ MySQL Database        │
              │ (Data Storage)        │
              └───────────────────────┘
```

---

## 2. Android App框架（Java）

### 2.1 项目结构
```
app/
├── src/main/java/com/smartmonitor/
│   ├── MainActivity.java
│   ├── DrivingModeActivity.java
│   ├── LearningModeActivity.java
│   ├── SettingsActivity.java
│   ├── HistoryActivity.java
│   ├── model/
│   │   ├── User.java
│   │   ├── Alert.java
│   │   ├── Session.java
│   │   └── AnalysisResult.java
│   ├── service/
│   │   ├── CameraService.java
│   │   ├── ApiService.java
│   │   ├── DetectionService.java
│   │   └── AlertService.java
│   ├── utils/
│   │   ├── HttpClient.java
│   │   ├── SharedPreferencesHelper.java
│   │   └── PermissionHelper.java
│   └── adapter/
│       └── AlertAdapter.java
├── res/
│   ├── layout/
│   ├── drawable/
│   └── values/
└── AndroidManifest.xml
```

### 2.2 核心类设计

#### MainActivity（主界面）
```java
public class MainActivity extends AppCompatActivity {
    private Button btnDrivingMode;
    private Button btnLearningMode;
    private TextView tvTodaySummary;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        initializeViews();
        loadTodaySummary();
    }
    
    private void initializeViews() {
        btnDrivingMode = findViewById(R.id.btn_driving_mode);
        btnLearningMode = findViewById(R.id.btn_learning_mode);
        
        btnDrivingMode.setOnClickListener(v -> 
            startActivity(new Intent(this, DrivingModeActivity.class)));
        btnLearningMode.setOnClickListener(v -> 
            startActivity(new Intent(this, LearningModeActivity.class)));
    }
    
    private void loadTodaySummary() {
        // 加载今日统计摘要
    }
}
```

#### DrivingModeActivity（驾驶模式）
```java
public class DrivingModeActivity extends AppCompatActivity {
    private SurfaceView cameraPreview;
    private TextView tvAlertStatus;
    private ImageView ivStatusIndicator;
    private Button btnStartStop;
    
    private CameraService cameraService;
    private DetectionService detectionService;
    private ApiService apiService;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_driving_mode);
        initializeServices();
        setupCamera();
    }
    
    private void initializeServices() {
        cameraService = new CameraService(this);
        detectionService = new DetectionService();
        apiService = new ApiService();
    }
    
    private void setupCamera() {
        cameraPreview = findViewById(R.id.camera_preview);
        cameraService.startPreview(cameraPreview, frame -> {
            // 实时帧处理
            detectionService.processFrame(frame, new DetectionCallback() {
                @Override
                public void onResult(AnalysisResult result) {
                    runOnUiThread(() -> updateUI(result));
                    apiService.sendAnalysisResult(result);
                }
                
                @Override
                public void onAlert(Alert alert) {
                    runOnUiThread(() -> showAlert(alert));
                }
            });
        });
    }
    
    private void updateUI(AnalysisResult result) {
        // 更新状态显示
        tvAlertStatus.setText(result.getStatus());
        ivStatusIndicator.setColorFilter(getStatusColor(result.getLevel()));
    }
    
    private void showAlert(Alert alert) {
        // 显示警告弹窗和声音提示
        AlertService.playAlertSound();
        showAlertDialog(alert);
    }
}
```

#### LearningModeActivity（学习模式）
```java
public class LearningModeActivity extends AppCompatActivity {
    private SurfaceView cameraPreview;
    private TextView tvFocusLevel;
    private ProgressBar progressFocus;
    private Button btnStartSession;
    
    private Session currentSession;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_learning_mode);
        initializeComponents();
    }
    
    private void initializeComponents() {
        cameraPreview = findViewById(R.id.camera_preview);
        tvFocusLevel = findViewById(R.id.tv_focus_level);
        progressFocus = findViewById(R.id.progress_focus);
        btnStartSession = findViewById(R.id.btn_start_session);
        
        btnStartSession.setOnClickListener(v -> startLearningSession());
    }
    
    private void startLearningSession() {
        currentSession = new Session("learning", System.currentTimeMillis());
        cameraService.startPreview(cameraPreview, frame -> {
            detectionService.processLearningFrame(frame, result -> {
                runOnUiThread(() -> updateLearningUI(result));
                apiService.sendAnalysisResult(result);
            });
        });
    }
    
    private void updateLearningUI(AnalysisResult result) {
        int focusLevel = result.getFocusLevel();
        tvFocusLevel.setText("专注度: " + focusLevel + "%");
        progressFocus.setProgress(focusLevel);
    }
}
```

#### CameraService（相机服务）
```java
public class CameraService {
    private Camera camera;
    private boolean isPreviewRunning = false;
    
    public void startPreview(SurfaceView surfaceView, FrameCallback callback) {
        camera = Camera.open();
        Camera.Parameters params = camera.getParameters();
        params.setPreviewFormat(ImageFormat.NV21);
        params.setPreviewSize(640, 480);
        camera.setParameters(params);
        
        camera.setPreviewCallback((bytes, camera) -> {
            if (isPreviewRunning) {
                YuvImage yuvImage = new YuvImage(bytes, ImageFormat.NV21,
                        camera.getParameters().getPreviewSize().width,
                        camera.getParameters().getPreviewSize().height, null);
                ByteArrayOutputStream out = new ByteArrayOutputStream();
                yuvImage.compressToJpeg(new Rect(0, 0, 
                    yuvImage.getWidth(), yuvImage.getHeight()), 50, out);
                byte[] imageBytes = out.toByteArray();
                Bitmap bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.length);
                callback.onFrame(bitmap);
            }
        });
        
        try {
            camera.setPreviewDisplay(surfaceView.getHolder());
            camera.startPreview();
            isPreviewRunning = true;
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    public void stopPreview() {
        isPreviewRunning = false;
        if (camera != null) {
            camera.stopPreview();
            camera.release();
            camera = null;
        }
    }
}
```

#### ApiService（API服务）
```java
public class ApiService {
    private static final String BASE_URL = "http://your-server:5000/api/";
    private OkHttpClient client;
    
    public ApiService() {
        client = new OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .build();
    }
    
    public void sendAnalysisResult(AnalysisResult result, Callback callback) {
        JSONObject json = new JSONObject();
        try {
            json.put("mode", result.getMode());
            json.put("timestamp", result.getTimestamp());
            json.put("status", result.getStatus());
            json.put("level", result.getLevel());
            json.put("details", new JSONObject(result.getDetails()));
        } catch (JSONException e) {
            e.printStackTrace();
        }
        
        RequestBody body = RequestBody.create(json.toString(), 
            MediaType.parse("application/json"));
        Request request = new Request.Builder()
                .url(BASE_URL + "analysis")
                .post(body)
                .build();
        
        client.newCall(request).enqueue(callback);
    }
    
    public void uploadImage(byte[] imageData, Callback callback) {
        RequestBody body = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("image", "frame.jpg",
                    RequestBody.create(imageData, MediaType.parse("image/jpeg")))
                .build();
        
        Request request = new Request.Builder()
                .url(BASE_URL + "upload")
                .post(body)
                .build();
        
        client.newCall(request).enqueue(callback);
    }
}
```

### 2.3 AndroidManifest.xml 配置
```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.smartmonitor">
    
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.VIBRATE" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    
    <uses-feature android:name="android.hardware.camera" android:required="true" />
    <uses-feature android:name="android.hardware.camera.autofocus" android:required="false" />
    
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/AppTheme"
        android:usesCleartextTraffic="true">
        
        <activity android:name=".MainActivity">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
        <activity android:name=".DrivingModeActivity" 
            android:screenOrientation="portrait" />
        <activity android:name=".LearningModeActivity" 
            android:screenOrientation="portrait" />
        <activity android:name=".SettingsActivity" />
        <activity android:name=".HistoryActivity" />
        
        <service android:name=".service.MonitoringService" 
            android:enabled="true" 
            android:exported="false" />
        
    </application>
</manifest>
```

---

## 3. Python Flask 后端服务器架构

### 3.1 项目结构
```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── alert.py
│   │   └── analysis.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── analysis.py
│   │   ├── sessions.py
│   │   ├── alerts.py
│   │   └── admin.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cv_service.py
│   │   ├── alert_service.py
│   │   └── statistics_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── decorators.py
│   │   └── validators.py
│   └── static/
│       └── uploads/
├── run.py
├── requirements.txt
└── .env
```

### 3.2 核心代码实现

#### app/__init__.py（应用工厂）
```python
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from app.config import Config

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    jwt.init_app(app)
    
    from app.routes import auth, analysis, sessions, alerts, admin
    app.register_blueprint(auth.bp)
    app.register_blueprint(analysis.bp)
    app.register_blueprint(sessions.bp)
    app.register_blueprint(alerts.bp)
    app.register_blueprint(admin.bp)
    
    with app.app_context():
        db.create_all()
    
    return app
```

#### app/config.py（配置文件）
```python
import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://user:password@localhost/smart_monitor'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    UPLOAD_FOLDER = 'app/static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4'}
    
    CV_MODEL_PATH = 'models/face_detection_model'
    ALERT_THRESHOLDS = {
        'fatigue': 0.7,
        'distraction': 0.6,
        'low_focus': 40
    }
```

#### app/routes/analysis.py（分析路由）
```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.cv_service import CVService
from app.models import Analysis, Session, Alert
from app import db
from datetime import datetime

bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')
cv_service = CVService()

@bp.route('', methods=['POST'])
@jwt_required()
def receive_analysis():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    analysis_record = Analysis(
        user_id=user_id,
        mode=data.get('mode'),
        timestamp=datetime.fromtimestamp(data.get('timestamp')/1000),
        status=data.get('status'),
        level=data.get('level'),
        details=data.get('details')
    )
    db.session.add(analysis_record)
    
    if data.get('level') in ['high', 'critical']:
        alert = create_alert(user_id, data)
        return jsonify({'alert_triggered': True, 'alert_id': alert.id}), 201
    
    db.session.commit()
    return jsonify({'success': True, 'analysis_id': analysis_record.id}), 201

@bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_frame():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    user_id = get_jwt_identity()
    mode = request.form.get('mode', 'driving')
    
    result = cv_service.process_image(file, mode)
    
    analysis_record = Analysis(
        user_id=user_id,
        mode=mode,
        timestamp=datetime.now(),
        status=result['status'],
        level=result['level'],
        details=result
    )
    db.session.add(analysis_record)
    db.session.commit()
    
    return jsonify(result), 200

@bp.route('/stream', methods=['POST'])
@jwt_required()
def process_stream():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    frame_data = data.get('frame')
    mode = data.get('mode', 'driving')
    
    result = cv_service.process_frame_base64(frame_data, mode)
    
    analysis_record = Analysis(
        user_id=user_id,
        mode=mode,
        timestamp=datetime.now(),
        status=result['status'],
        level=result['level'],
        details=result
    )
    db.session.add(analysis_record)
    db.session.commit()
    
    return jsonify(result), 200

def create_alert(user_id, data):
    alert = Alert(
        user_id=user_id,
        mode=data.get('mode'),
        alert_type=data.get('status'),
        severity=data.get('level'),
        timestamp=datetime.fromtimestamp(data.get('timestamp')/1000),
        details=data.get('details'),
        acknowledged=False
    )
    db.session.add(alert)
    db.session.commit()
    return alert
```

#### app/routes/sessions.py（会话路由）
```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Session
from app import db
from datetime import datetime
from sqlalchemy import func

bp = Blueprint('sessions', __name__, url_prefix='/api/sessions')

@bp.route('', methods=['POST'])
@jwt_required()
def start_session():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    session = Session(
        user_id=user_id,
        mode=data.get('mode'),
        start_time=datetime.now(),
        end_time=None,
        duration=0,
        total_alerts=0,
        avg_focus_level=0
    )
    db.session.add(session)
    db.session.commit()
    
    return jsonify({
        'session_id': session.id,
        'start_time': session.start_time.isoformat()
    }), 201

@bp.route('/<int:session_id>', methods=['PUT'])
@jwt_required()
def end_session(session_id):
    session = Session.query.get_or_404(session_id)
    
    session.end_time = datetime.now()
    session.duration = (session.end_time - session.start_time).seconds
    
    stats = db.session.query(
        func.avg(Analysis.level).label('avg_level'),
        func.count(Alert.id).label('alert_count')
    ).outerjoin(Alert).filter(
        Analysis.session_id == session_id
    ).first()
    
    session.avg_focus_level = float(stats.avg_level) if stats.avg_level else 0
    session.total_alerts = stats.alert_count or 0
    
    db.session.commit()
    
    return jsonify({
        'session_id': session.id,
        'duration': session.duration,
        'avg_focus_level': session.avg_focus_level,
        'total_alerts': session.total_alerts
    }), 200

@bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    mode = request.args.get('mode', None)
    
    query = Session.query.filter_by(user_id=user_id)
    if mode:
        query = query.filter_by(mode=mode)
    
    sessions = query.order_by(Session.start_time.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'sessions': [s.to_dict() for s in sessions.items],
        'total': sessions.total,
        'pages': sessions.pages,
        'current_page': page
    }), 200
```

#### run.py（应用入口）
```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### 3.3 requirements.txt
```
Flask==2.3.2
Flask-CORS==4.0.0
Flask-SQLAlchemy==3.0.3
Flask-JWT-Extended==4.5.2
PyMySQL==1.1.0
cryptography==41.0.3
opencv-python==4.8.0.74
face-recognition==1.3.0
dlib==19.24.2
numpy==1.24.3
Pillow==10.0.0
PyJWT==2.8.0
python-dotenv==1.0.0
gunicorn==21.2.0
redis==5.0.0
celery==5.3.1
```

---

## 4. 计算机视觉模块架构

### 4.1 模块结构
```
cv_module/
├── face_detector.py
├── gaze_tracker.py
├── fatigue_detector.py
├── focus_analyzer.py
├── emotion_recognizer.py
├── models/
│   ├── haarcascade_frontalface_default.xml
│   ├── shape_predictor_68_face_landmarks.dat
│   └── emotion_model.pth
├── utils/
│   ├── image_processor.py
│   └── video_processor.py
└── config.py
```

### 4.2 核心实现

#### cv_service.py（CV服务主类）
```python
import cv2
import numpy as np
import base64
from PIL import Image
import io
from app.services.face_detector import FaceDetector
from app.services.gaze_tracker import GazeTracker
from app.services.fatigue_detector import FatigueDetector
from app.services.focus_analyzer import FocusAnalyzer
from app.services.emotion_recognizer import EmotionRecognizer

class CVService:
    def __init__(self):
        self.face_detector = FaceDetector()
        self.gaze_tracker = GazeTracker()
        self.fatigue_detector = FatigueDetector()
        self.focus_analyzer = FocusAnalyzer()
        self.emotion_recognizer = EmotionRecognizer()
        
        self.driving_thresholds = {
            'eye_aspect_ratio_low': 0.25,
            'mouth_aspect_ratio_high': 0.5,
            'head_pose_threshold': 30,
            'consecutive_frames': 3
        }
        
        self.learning_thresholds = {
            'min_focus_level': 60,
            'distraction_threshold': 0.4,
            'emotion_weights': {
                'focused': 1.0,
                'neutral': 0.7,
                'happy': 0.8,
                'tired': 0.3,
                'distracted': 0.2
            }
        }
    
    def process_image(self, file, mode='driving'):
        image = self._load_image(file)
        return self._analyze_frame(image, mode)
    
    def process_frame_base64(self, frame_data, mode='driving'):
        image = self._decode_base64_image(frame_data)
        return self._analyze_frame(image, mode)
    
    def _analyze_frame(self, image, mode):
        faces = self.face_detector.detect(image)
        
        if len(faces) == 0:
            return {
                'status': 'no_face_detected',
                'level': 'low',
                'confidence': 0.0,
                'details': {}
            }
        
        face = faces[0]
        landmarks = self.face_detector.get_landmarks(image, face)
        
        if mode == 'driving':
            return self._analyze_driving(image, face, landmarks)
        else:
            return self._analyze_learning(image, face, landmarks)
    
    def _analyze_driving(self, image, face, landmarks):
        eye_ratio = self.fatigue_detector.get_eye_aspect_ratio(landmarks)
        mouth_ratio = self.fatigue_detector.get_mouth_aspect_ratio(landmarks)
        head_pose = self.gaze_tracker.get_head_pose(landmarks)
        
        fatigue_score = self.fatigue_detector.calculate_fatigue_score(
            eye_ratio, mouth_ratio)
        
        if fatigue_score > 0.7:
            status = 'fatigue'
            level = 'critical'
            alert_type = 'DROWSINESS_ALERT'
        elif head_pose['yaw'] > self.driving_thresholds['head_pose_threshold']:
            status = 'distraction'
            level = 'high'
            alert_type = 'DISTRACTION_ALERT'
        else:
            status = 'normal'
            level = 'low'
            alert_type = None
        
        return {
            'status': status,
            'level': level,
            'confidence': fatigue_score,
            'alert_type': alert_type,
            'details': {
                'eye_ratio': float(eye_ratio),
                'mouth_ratio': float(mouth_ratio),
                'head_pose': head_pose,
                'fatigue_score': float(fatigue_score)
            }
        }
    
    def _analyze_learning(self, image, face, landmarks):
        gaze_direction = self.gaze_tracker.get_gaze_direction(landmarks)
        emotion = self.emotion_recognizer.recognize(landmarks)
        focus_score = self.focus_analyzer.calculate_focus(
            gaze_direction, emotion)
        
        if focus_score < self.learning_thresholds['min_focus_level']:
            status = 'low_focus'
            level = 'medium'
        elif focus_score < 80:
            status = 'distracted'
            level = 'low'
        else:
            status = 'focused'
            level = 'low'
        
        return {
            'status': status,
            'focus_level': int(focus_score),
            'level': level,
            'confidence': focus_score / 100,
            'details': {
                'gaze_direction': gaze_direction,
                'emotion': emotion,
                'focus_score': float(focus_score)
            }
        }
    
    def _load_image(self, file):
        image = Image.open(file.stream)
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    def _decode_base64_image(self, frame_data):
        img_data = base64.b64decode(frame_data)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
```

#### face_detector.py（人脸检测）
```python
import cv2
import numpy as np
from pathlib import Path

class FaceDetector:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.detector = self._load_dlib_detector()
        self.predictor = self._load_landmark_predictor()
    
    def detect(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return faces
    
    def detect_dlib(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray, 1)
        return [(f.left(), f.top(), f.right(), f.bottom()) for f in faces]
    
    def get_landmarks(self, image, face):
        if len(face) == 4:
            x, y, w, h = face
            rect = self._to_dlib_rect(x, y, w, h)
        else:
            rect = face
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        landmarks = self.predictor(gray, rect)
        
        points = []
        for i in range(68):
            pt = landmarks.part(i)
            points.append((pt.x, pt.y))
        
        return np.array(points)
    
    def _load_dlib_detector(self):
        try:
            import dlib
            return dlib.get_frontal_face_detector()
        except:
            return None
    
    def _load_landmark_predictor(self):
        try:
            import dlib
            predictor_path = 'cv_module/models/shape_predictor_68_face_landmarks.dat'
            return dlib.shape_predictor(predictor_path)
        except:
            return None
    
    def _to_dlib_rect(self, x, y, w, h):
        import dlib
        return dlib.rectangle(x, y, x + w, y + h)
```

#### fatigue_detector.py（疲劳检测）
```python
import numpy as np

class FatigueDetector:
    def __init__(self):
        self.eye_points = [36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]
        self.left_eye = [36, 37, 38, 39, 40, 41]
        self.right_eye = [42, 43, 44, 45, 46, 47]
        self.mouth_points = [48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67]
        
        self.eye_closed_frames = 0
        self.eye_open_frames = 0
        self.yawning_frames = 0
    
    def get_eye_aspect_ratio(self, landmarks):
        left_eye = landmarks[self.left_eye]
        right_eye = landmarks[self.right_eye]
        
        left_ear = self._calculate_ear(left_eye)
        right_ear = self._calculate_ear(right_eye)
        
        return (left_ear + right_ear) / 2.0
    
    def _calculate_ear(self, eye_points):
        A = np.linalg.norm(eye_points[1] - eye_points[5])
        B = np.linalg.norm(eye_points[2] - eye_points[4])
        C = np.linalg.norm(eye_points[0] - eye_points[3])
        
        ear = (A + B) / (2.0 * C)
        return ear
    
    def get_mouth_aspect_ratio(self, landmarks):
        mouth = landmarks[self.mouth_points]
        
        A = np.linalg.norm(mouth[2] - mouth[10])
        B = np.linalg.norm(mouth[4] - mouth[8])
        C = np.linalg.norm(mouth[0] - mouth[6])
        
        mar = (A + B) / (2.0 * C)
        return mar
    
    def calculate_fatigue_score(self, eye_ratio, mouth_ratio, threshold=0.25):
        eye_score = 1.0 if eye_ratio < threshold else 0.0
        mouth_score = 1.0 if mouth_ratio > 0.5 else 0.0
        
        if eye_ratio < threshold:
            self.eye_closed_frames += 1
            self.eye_open_frames = 0
        else:
            self.eye_open_frames += 1
            self.eye_closed_frames = 0
        
        if mouth_ratio > 0.5:
            self.yawning_frames += 1
        else:
            self.yawning_frames = 0
        
        prolonged_eye_closed = self.eye_closed_frames > 15
        prolonged_yawning = self.yawning_frames > 10
        
        fatigue_score = (eye_score * 0.5 + mouth_score * 0.3 + 
                        (0.2 if prolonged_eye_closed else 0) +
                        (0.2 if prolonged_yawning else 0))
        
        return min(fatigue_score, 1.0)
    
    def reset_counters(self):
        self.eye_closed_frames = 0
        self.eye_open_frames = 0
        self.yawning_frames = 0
```

#### focus_analyzer.py（专注度分析）
```python
import numpy as np

class FocusAnalyzer:
    def __init__(self):
        self.emotion_weights = {
            'focused': 1.0,
            'neutral': 0.7,
            'happy': 0.8,
            'sad': 0.5,
            'angry': 0.3,
            'fear': 0.2,
            'surprise': 0.4,
            'tired': 0.2,
            'distracted': 0.1
        }
        
        self.gaze_center_weight = 0.4
        self.emotion_weight = 0.3
        self.stability_weight = 0.3
        
        self.gaze_history = []
        self.max_history = 30
    
    def calculate_focus(self, gaze_direction, emotion):
        center_score = self._calculate_center_score(gaze_direction)
        emotion_score = self.emotion_weights.get(emotion, 0.5)
        stability_score = self._calculate_stability_score()
        
        focus_score = (center_score * self.gaze_center_weight + 
                      emotion_score * self.emotion_weight +
                      stability_score * self.stability_weight)
        
        return min(max(focus_score * 100, 0), 100)
    
    def _calculate_center_score(self, gaze_direction):
        x, y, z = gaze_direction
        
        x_deviation = abs(x) / 30.0
        y_deviation = abs(y) / 20.0
        
        deviation_score = (x_deviation + y_deviation) / 2.0
        
        center_score = 1.0 - min(deviation_score, 1.0)
        
        return center_score
    
    def _calculate_stability_score(self):
        if len(self.gaze_history) < 5:
            return 0.8
        
        gaze_array = np.array(self.gaze_history[-self.max_history:])
        std_dev = np.std(gaze_array, axis=0)
        avg_std = np.mean(std_dev)
        
        stability_score = 1.0 - min(avg_std / 50.0, 1.0)
        
        return stability_score
    
    def update_gaze_history(self, gaze_direction):
        self.gaze_history.append(gaze_direction)
        if len(self.gaze_history) > self.max_history:
            self.gaze_history.pop(0)
```

---

## 5. Web管理界面架构

### 5.1 前端技术栈
- HTML5 + CSS3 + JavaScript
- Vue.js 3 (Composition API)
- Element Plus (UI组件库)
- ECharts (数据可视化)
- WebSocket (实时通信)

### 5.2 项目结构
```
web_admin/
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── router/
│   │   └── index.js
│   ├── views/
│   │   ├── Login.vue
│   │   ├── Dashboard.vue
│   │   ├── UserManagement.vue
│   │   ├── SessionHistory.vue
│   │   ├── AlertManagement.vue
│   │   └── Settings.vue
│   ├── components/
│   │   ├── Sidebar.vue
│   │   ├── Header.vue
│   │   ├── RealTimeMonitor.vue
│   │   ├── StatisticsChart.vue
│   │   └── AlertTable.vue
│   ├── services/
│   │   ├── api.js
│   │   └── websocket.js
│   ├── stores/
│   │   └── user.js
│   └── utils/
│       └── helpers.js
├── public/
├── index.html
└── package.json
```

### 5.3 核心组件实现

#### Dashboard.vue（仪表盘）
```vue
<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon driving">
            <i class="el-icon-location"></i>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.activeDrivingSessions }}</div>
            <div class="stat-label">当前驾驶监测</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon learning">
            <i class="el-icon-reading"></i>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.activeLearningSessions }}</div>
            <div class="stat-label">当前学习监测</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon alert">
            <i class="el-icon-warning"></i>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.todayAlerts }}</div>
            <div class="stat-label">今日告警</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon users">
            <i class="el-icon-user"></i>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.totalUsers }}</div>
            <div class="stat-label">总用户数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="chart-row">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>告警趋势</span>
          </template>
          <div ref="alertChartRef" style="width: 100%; height: 300px;"></div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>使用统计</span>
          </template>
          <div ref="usageChartRef" style="width: 100%; height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row>
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>实时监测</span>
            <el-button type="primary" size="small" @click="refreshData">
              刷新
            </el-button>
          </template>
          <RealTimeMonitor :sessions="activeSessions" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getDashboardStats, getAlertTrend, getActiveSessions } from '@/services/api'

const stats = ref({
  activeDrivingSessions: 0,
  activeLearningSessions: 0,
  todayAlerts: 0,
  totalUsers: 0
})

const alertChartRef = ref(null)
const usageChartRef = ref(null)
const activeSessions = ref([])

let alertChart = null
let usageChart = null

onMounted(async () => {
  await loadDashboardData()
  initCharts()
  startRealTimeUpdates()
})

onUnmounted(() => {
  if (alertChart) alertChart.dispose()
  if (usageChart) usageChart.dispose()
})

async function loadDashboardData() {
  try {
    const [statsData, trendData, sessionsData] = await Promise.all([
      getDashboardStats(),
      getAlertTrend(),
      getActiveSessions()
    ])
    
    stats.value = statsData
    activeSessions.value = sessionsData
    updateCharts(trendData)
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

function initCharts() {
  alertChart = echarts.init(alertChartRef.value)
  usageChart = echarts.init(usageChartRef.value)
}

function updateCharts(trendData) {
  const alertOption = {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: trendData.labels
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '疲劳告警',
        type: 'line',
        data: trendData.fatigue,
        itemStyle: { color: '#ff6b6b' }
      },
      {
        name: '注意力分散',
        type: 'line',
        data: trendData.distraction,
        itemStyle: { color: '#ffa500' }
      }
    ]
  }
  
  const usageOption = {
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { value: stats.value.activeDrivingSessions, name: '驾驶模式' },
          { value: stats.value.activeLearningSessions, name: '学习模式' }
        ]
      }
    ]
  }
  
  alertChart.setOption(alertOption)
  usageChart.setOption(usageOption)
}

function refreshData() {
  loadDashboardData()
}

let updateInterval = null
function startRealTimeUpdates() {
  updateInterval = setInterval(loadDashboardData, 30000)
}
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 10px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: white;
  margin-right: 15px;
}

.stat-icon.driving { background: linear-gradient(135deg, #667eea, #764ba2); }
.stat-icon.learning { background: linear-gradient(135deg, #f093fb, #f5576c); }
.stat-icon.alert { background: linear-gradient(135deg, #ffecd2, #fcb69f); }
.stat-icon.users { background: linear-gradient(135deg, #4facfe, #00f2fe); }

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.chart-row {
  margin-top: 20px;
  margin-bottom: 20px;
}
</style>
```

#### RealTimeMonitor.vue（实时监测组件）
```vue
<template>
  <div class="real-time-monitor">
    <el-table :data="sessions" style="width: 100%" v-loading="loading">
      <el-table-column prop="user_name" label="用户" width="120" />
      <el-table-column prop="mode" label="模式" width="100">
        <template #default="{ row }">
          <el-tag :type="row.mode === 'driving' ? 'primary' : 'success'">
            {{ row.mode === 'driving' ? '驾驶' : '学习' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="focus_level" label="专注度" width="200">
        <template #default="{ row }">
          <el-progress 
            :percentage="row.focus_level || 0"
            :color="getProgressColor(row.focus_level)" />
        </template>
      </el-table-column>
      <el-table-column prop="start_time" label="开始时间" width="180" />
      <el-table-column prop="alerts" label="告警数" width="100">
        <template #default="{ row }">
          <el-badge :value="row.alerts" :max="99" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button size="small" @click="viewDetails(row)">详情</el-button>
          <el-button size="small" type="danger" @click="endSession(row)">
            结束
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  sessions: {
    type: Array,
    default: () => []
  }
})

const loading = ref(false)

function getStatusType(status) {
  const types = {
    'normal': 'success',
    'warning': 'warning',
    'danger': 'danger'
  }
  return types[status] || 'info'
}

function getStatusText(status) {
  const texts = {
    'normal': '正常',
    'warning': '注意',
    'danger': '危险',
    'focused': '专注',
    'distracted': '分心'
  }
  return texts[status] || status
}

function getProgressColor(percentage) {
  if (percentage >= 80) return '#67c23a'
  if (percentage >= 60) return '#e6a23c'
  return '#f56c6c'
}

function viewDetails(row) {
  console.log('View details:', row)
}

function endSession(row) {
  console.log('End session:', row)
}
</script>

<style scoped>
.real-time-monitor {
  padding: 10px 0;
}
</style>
```

---

## 6. 数据库设计

### 6.1 ER图
```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    Users    │       │   Sessions  │       │  Analysis   │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │──┐    │ id (PK)     │──┐    │ id (PK)     │
│ username    │  │    │ user_id(FK) │  │    │ session_id  │
│ email       │  └───►│ mode        │  └───►│ (FK)        │
│ password    │       │ start_time  │       │ user_id(FK) │
│ role        │       │ end_time    │       │ mode        │
│ created_at  │       │ duration    │       │ status      │
└─────────────┘       │ avg_focus   │       │ level       │
                      │ total_alerts│       │ timestamp   │
                      └─────────────┘       │ details     │
                                            └─────────────┘
                                                    │
                      ┌─────────────┐               │
                      │   Alerts    │◄──────────────┘
                      ├─────────────┤
                      │ id (PK)     │
                      │ session_id  │
                      │ (FK)        │
                      │ user_id(FK) │
                      │ alert_type  │
                      │ severity    │
                      │ timestamp   │
                      │ acknowledged│
                      │ details     │
                      └─────────────┘
```

### 6.2 数据表创建脚本

#### users表
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    role ENUM('user', 'admin', 'super_admin') DEFAULT 'user',
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_email (email),
    INDEX idx_username (username),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### sessions表
```sql
CREATE TABLE sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    mode ENUM('driving', 'learning') NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NULL,
    duration INT DEFAULT 0 COMMENT '持续时间（秒）',
    total_frames INT DEFAULT 0 COMMENT '处理帧数',
    avg_focus_level DECIMAL(5,2) DEFAULT 0 COMMENT '平均专注度',
    avg_confidence DECIMAL(5,2) DEFAULT 0 COMMENT '平均置信度',
    total_alerts INT DEFAULT 0 COMMENT '总告警数',
    fatigue_alerts INT DEFAULT 0 COMMENT '疲劳告警数',
    distraction_alerts INT DEFAULT 0 COMMENT '分心告警数',
    status ENUM('active', 'completed', 'interrupted') DEFAULT 'active',
    device_info VARCHAR(255) COMMENT '设备信息',
    location VARCHAR(255) COMMENT '位置信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_mode (mode),
    INDEX idx_start_time (start_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### analysis表
```sql
CREATE TABLE analysis (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT,
    user_id INT NOT NULL,
    mode ENUM('driving', 'learning') NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL COMMENT 'normal, fatigue, distraction, etc.',
    level ENUM('low', 'medium', 'high', 'critical') NOT NULL,
    confidence DECIMAL(5,2) DEFAULT 0,
    focus_level INT DEFAULT 0 COMMENT '专注度评分（0-100）',
    details JSON COMMENT '详细分析结果',
    face_detected BOOLEAN DEFAULT TRUE,
    frame_quality DECIMAL(3,2) DEFAULT 0 COMMENT '帧质量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_status (status),
    INDEX idx_level (level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### alerts表
```sql
CREATE TABLE alerts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT,
    user_id INT NOT NULL,
    mode ENUM('driving', 'learning') NOT NULL,
    alert_type VARCHAR(50) NOT NULL COMMENT 'DROWSINESS, DISTRACTION, etc.',
    severity ENUM('low', 'medium', 'high', 'critical') NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    message TEXT,
    details JSON COMMENT '告警详情',
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP NULL,
    acknowledged_by INT NULL,
    response_action VARCHAR(100) COMMENT '响应动作',
    frame_snapshot VARCHAR(255) COMMENT '告警帧快照路径',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (acknowledged_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_alert_type (alert_type),
    INDEX idx_severity (severity),
    INDEX idx_acknowledged (acknowledged),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### user_settings表
```sql
CREATE TABLE user_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL UNIQUE,
    alert_sound_enabled BOOLEAN DEFAULT TRUE,
    alert_vibration_enabled BOOLEAN DEFAULT TRUE,
    alert_notifications_enabled BOOLEAN DEFAULT TRUE,
    driving_sensitivity ENUM('low', 'medium', 'high') DEFAULT 'medium',
    learning_sensitivity ENUM('low', 'medium', 'high') DEFAULT 'medium',
    fatigue_threshold DECIMAL(3,2) DEFAULT 0.70,
    distraction_threshold DECIMAL(3,2) DEFAULT 0.60,
    focus_threshold INT DEFAULT 60,
    auto_report BOOLEAN DEFAULT FALSE,
    report_frequency ENUM('daily', 'weekly', 'monthly') DEFAULT 'daily',
    dark_mode BOOLEAN DEFAULT FALSE,
    language VARCHAR(10) DEFAULT 'zh-CN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### statistics_view（统计视图）
```sql
CREATE VIEW statistics_daily AS
SELECT 
    DATE(created_at) as date,
    mode,
    COUNT(*) as total_sessions,
    SUM(duration) / 60 as total_duration_minutes,
    AVG(avg_focus_level) as avg_focus,
    SUM(total_alerts) as total_alerts,
    COUNT(DISTINCT user_id) as unique_users
FROM sessions
WHERE status = 'completed'
GROUP BY DATE(created_at), mode;

CREATE VIEW alert_statistics AS
SELECT 
    DATE(timestamp) as date,
    alert_type,
    severity,
    COUNT(*) as alert_count,
    COUNT(DISTINCT user_id) as affected_users
FROM alerts
GROUP BY DATE(timestamp), alert_type, severity;
```

---

## 7. 部署方案

### 7.1 系统架构拓扑
```
                    ┌─────────────────────────────────────┐
                    │           Nginx Reverse Proxy        │
                    │         (Load Balancer + SSL)        │
                    └─────────────────────────────────────┘
                                     │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│   Flask Backend   │    │   Flask Backend   │    │   Flask Backend   │
│     Instance 1    │    │     Instance 2    │    │     Instance 3    │
│   (Gunicorn)      │    │   (Gunicorn)      │    │   (Gunicorn)      │
└───────────────────┘    └───────────────────┘    └───────────────────┘
           │                        │                        │
           └────────────────────────┼────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
          ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
          │   MySQL DB   │  │    Redis     │  │   Celery     │
          │  (Primary)   │  │  (Cache)     │  │  (Workers)   │
          └─────────────┘  └─────────────┘  └─────────────┘
                    │               
                    ▼               
          ┌─────────────────┐      
          │   MySQL DB      │      
          │   (Replica)     │      
          └─────────────────┘      

┌─────────────────────────────────────────────────────────────┐
│                      Android Clients                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Web Admin    │
                    │   Dashboard   │
                    └───────────────┘
```

### 7.2 Docker Compose配置

#### docker-compose.yml
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: smart_monitor_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend1
      - backend2
      - backend3
    networks:
      - smart_monitor_network

  backend1:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: backend1
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=mysql+pymysql://user:password@mysql:3306/smart_monitor
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./backend:/app
      - ./cv_models:/app/models
    depends_on:
      - mysql
      - redis
    networks:
      - smart_monitor_network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  backend2:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: backend2
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=mysql+pymysql://user:password@mysql:3306/smart_monitor
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./backend:/app
      - ./cv_models:/app/models
    depends_on:
      - mysql
      - redis
    networks:
      - smart_monitor_network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  backend3:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: backend3
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=mysql+pymysql://user:password@mysql:3306/smart_monitor
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./backend:/app
      - ./cv_models:/app/models
    depends_on:
      - mysql
      - redis
    networks:
      - smart_monitor_network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: celery_worker
    command: celery -A app.celery worker --loglevel=info
    environment:
      - DATABASE_URL=mysql+pymysql://user:password@mysql:3306/smart_monitor
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./backend:/app
      - ./cv_models:/app/models
    depends_on:
      - mysql
      - redis
    networks:
      - smart_monitor_network

  mysql:
    image: mysql:8.0
    container_name: mysql_primary
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=smart_monitor
      - MYSQL_USER=user
      - MYSQL_PASSWORD=password
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql/init:/docker-entrypoint-initdb.d:ro
      - ./mysql/conf.d:/etc/mysql/conf.d:ro
    ports:
      - "3306:3306"
    networks:
      - smart_monitor_network
    command: --default-authentication-plugin=mysql_native_password

  mysql_replica:
    image: mysql:8.0
    container_name: mysql_replica
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=smart_monitor
      - MYSQL_MASTER_USER=replica_user
      - MYSQL_MASTER_PASSWORD=replica_password
    volumes:
      - mysql_replica_data:/var/lib/mysql
    depends_on:
      - mysql
    networks:
      - smart_monitor_network
    command: --default-authentication-plugin=mysql_native_password

  redis:
    image: redis:7-alpine
    container_name: redis_cache
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - smart_monitor_network
    command: redis-server --appendonly yes

  web_admin:
    build:
      context: ./web_admin
      dockerfile: Dockerfile
    container_name: web_admin
    environment:
      - VITE_API_BASE_URL=http://nginx/api
    volumes:
      - ./web_admin:/app
      - /app/node_modules
    depends_on:
      - backend1
    networks:
      - smart_monitor_network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

volumes:
  mysql_data:
  mysql_replica_data:
  redis_data:

networks:
  smart_monitor_network:
    driver: bridge
```

### 7.3 Nginx配置

#### nginx/nginx.conf
```nginx
upstream backend_servers {
    least_conn;
    server backend1:5000 weight=5;
    server backend2:5000 weight=5;
    server backend3:5000 weight=5;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location /api/ {
        proxy_pass http://backend_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    location /admin/ {
        proxy_pass http://web_admin:80/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://backend_servers;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
}
```

### 7.4 后端Dockerfile

#### backend/Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libpng-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "run:app"]
```

### 7.5 环境变量配置

#### .env
```env
FLASK_APP=run.py
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

DATABASE_URL=mysql+pymysql://user:password@mysql:3306/smart_monitor
REDIS_URL=redis://redis:6379/0

ALERT_THRESHOLD_FATIGUE=0.7
ALERT_THRESHOLD_DISTRACTION=0.6
FOCUS_THRESHOLD_LEARNING=60

CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

### 7.6 服务器硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| **应用服务器** | 4核CPU, 8GB RAM | 8核CPU, 16GB RAM |
| **数据库服务器** | 4核CPU, 16GB RAM, 100GB SSD | 8核CPU, 32GB RAM, 500GB SSD |
| **缓存服务器** | 2核CPU, 4GB RAM | 4核CPU, 8GB RAM |
| **Web服务器** | 2核CPU, 2GB RAM | 4核CPU, 4GB RAM |

### 7.7 部署检查清单

```markdown
## 部署前检查
- [ ] 所有代码已提交并测试
- [ ] 数据库迁移脚本准备完毕
- [ ] SSL证书已配置
- [ ] 环境变量已设置
- [ ] 备份策略已配置
- [ ] 监控告警已设置

## 部署步骤
1. 拉取最新代码
2. 构建Docker镜像
3. 执行数据库迁移
4. 启动服务（按依赖顺序）
5. 验证服务健康状态
6. 配置域名解析
7. 测试API端点
8. 配置监控告警

## 回滚方案
- 保留最近3个版本的Docker镜像
- 数据库每日备份
- 配置版本控制
```

---

## 8. 系统安全考虑

### 8.1 身份认证
- JWT Token认证
- Token自动刷新机制
- Refresh Token存储在HttpOnly Cookie

### 8.2 数据安全
- HTTPS全站加密
- 敏感数据加密存储
- 数据脱敏处理
- 定期安全审计

### 8.3 API安全
- Rate Limiting限制
- 输入验证与过滤
- SQL注入防护
- XSS防护

---

本设计文档提供了完整的双模式智能监测系统架构，包括Android客户端、Python Flask后端、计算机视觉模块、Web管理界面、数据库设计和部署方案。如需进一步细化或实现特定模块，请随时告知。
