from .auth import bp as auth_bp
from .analysis import bp as analysis_bp
from .sessions import bp as sessions_bp
from .alerts import bp as alerts_bp
from .websocket import bp as websocket_bp
from .cv import bp as cv_bp

__all__ = ['auth', 'analysis', 'sessions', 'alerts', 'websocket', 'cv']