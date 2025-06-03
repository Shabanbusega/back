"""
Minimal Flask application to test basic API functionality
"""

from flask import Flask, jsonify
import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return "Pona Health API Server - Minimal Test App"
    
@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Minimal API server is running",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
