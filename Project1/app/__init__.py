from flask import Flask
from pathlib import Path

def create_app():
    app = Flask(__name__)
    from .routes import bp
    app.register_blueprint(bp)
    return app