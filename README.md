# Face Detection System with Attention Monitoring

一个基于 Flask 和 OpenCV 的实时人脸检测与注意力监测系统，支持 WebSocket 实时通信。

## 功能特性

- **人脸检测**：使用 Haar 级联分类器进行实时人脸检测
- **疲劳监测**：基于 EAR（眼睛纵横比）和 PERCLOS 算法检测疲劳状态
- **视线估计**：通过瞳孔定位估计视线方向
- **坐姿检测**：检测头部倾斜和面部位置
- **注意力评分**：综合评估用户的注意力状态
- **实时通信**：使用 WebSocket 实现移动端实时视频流传输

## 技术栈

- **后端框架**：Flask 2.0 + Flask-SocketIO
- **计算机视觉**：OpenCV 4.8
- **异步处理**：Eventlet
- **数据库**：SQLite（开发环境）
- **认证**：JWT

## 项目结构

```
facedect/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask 应用初始化
│   │   ├── config.py            # 配置文件
│   │   ├── models.py            # 数据库模型
│   │   ├── routes/              # API 路由
│   │   │   ├── auth.py          # 用户认证
│   │   │   ├── cv.py            # 计算机视觉接口
│   │   │   ├── analysis.py      # 数据分析接口
│   │   │   ├── alerts.py        # 告警管理
│   │   │   ├── sessions.py      # 会话管理
│   │   │   └── websocket.py     # WebSocket 通信
│   │   ├── services/            # 核心服务
│   │   │   ├── fatigue_detector.py    # 疲劳检测
│   │   │   ├── gaze_estimator.py      # 视线估计
│   │   │   ├── posture_detector.py    # 坐姿检测
│   │   │   ├── attention_scorer.py    # 注意力评分
│   │   │   └── cv_service.py          # 图像处理服务
│   │   └── static/              # 静态文件
│   │       ├── index.html       # 主页面
│   │       ├── test.html        # WebSocket 测试页面
│   │       └── stream_test.html # 视频流测试页面
│   ├── instance/                # SQLite 数据库
│   ├── requirements.txt         # 依赖列表
│   ├── run.py                   # 开发服务器启动文件
│   └── wsgi.py                  # WSGI 部署文件
├── SPEC.md                      # 技术规格文档
└── README.md                    # 项目说明
```

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/facedect.git
cd facedect/backend
```

### 2. 创建虚拟环境

```bash
# 使用 venv
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

创建 `.env` 文件：

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
```

### 5. 生成 SSL 证书（可选）

```bash
# 使用 OpenSSL 生成自签名证书
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

## 运行项目

### 开发模式

```bash
python run.py
```

服务器将在 `https://localhost:5000` 启动。

### 生产模式

```bash
gunicorn --worker-class eventlet -w 1 --certfile=cert.pem --keyfile=key.pem wsgi:app
```

## API 接口

### 认证接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/auth/me` | 获取当前用户 |

### 计算机视觉接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/cv/detect` | 单帧人脸检测 |
| POST | `/api/cv/analyze` | 综合分析 |

### 数据分析接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/analysis/session/<session_id>` | 获取会话数据 |
| GET | `/api/analysis/user/<user_id>` | 获取用户历史 |

### WebSocket 事件

| 事件名 | 描述 |
|--------|------|
| `connect` | 客户端连接 |
| `disconnect` | 客户端断开 |
| `frame` | 发送视频帧 |
| `frame_test` | 测试模式发送帧 |
| `frame_result` | 返回分析结果 |
| `alert` | 告警通知 |

## 使用说明

### 移动端测试

1. 确保手机和服务器在同一局域网内
2. 在手机浏览器中访问 `https://<服务器IP>:5000/stream_test.html`
3. 接受自签名证书警告
4. 允许相机访问权限
5. 点击"开始监控"按钮

### 测试页面

- **WebSocket 测试**：`/test.html`
- **视频流测试**：`/stream_test.html`

## 算法说明

### 疲劳检测 (EAR)

$$EAR = \frac{||p_2 - p_6|| + ||p_3 - p_5||}{2 \times ||p_1 - p_4||}$$

### PERCLOS

$$PERCLOS = \frac{\text{闭眼帧数}}{\text{总帧数}} \times 100\%$$

### 注意力评分

综合疲劳、视线、坐姿三个维度的加权评分：

- 疲劳检测：35%
- 视线估计：35%
- 坐姿检测：30%

## 配置参数

### 疲劳检测参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| EAR_THRESHOLD | 0.2 | 眼睛闭合阈值 |
| EAR_CONSEC_FRAMES | 3 | 连续闭眼帧数 |
| PERCLOS_THRESHOLD | 0.3 | PERCLOS 阈值 |
| PERCLOS_TIME_WINDOW | 30 | 时间窗口帧数 |

### 视线估计参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| GAZE_THRESHOLD | 0.3 | 视线偏离阈值 |

### 坐姿检测参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| HEAD_TILT_THRESHOLD | 45.0 | 头部倾斜阈值(度) |
| FACE_CENTER_THRESHOLD | 0.2 | 面部中心偏移阈值 |

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请发送邮件至 your@email.com。
