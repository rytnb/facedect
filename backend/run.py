import eventlet
eventlet.monkey_patch()

from app import create_app
import os
import ssl

app = create_app()

if __name__ == '__main__':
    cert_path = os.path.join(os.path.dirname(__file__), 'cert.pem')
    key_path = os.path.join(os.path.dirname(__file__), 'key.pem')
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        from app import socketio
        print('Starting server with SSL on port 5000...')
        socketio.run(app, host='0.0.0.0', port=5000, debug=True,
                     certfile=cert_path, keyfile=key_path)
    else:
        from app import socketio
        print('Starting server without SSL on port 5000...')
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)