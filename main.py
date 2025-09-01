from flask import Flask, request
from routes.api import api_bp
from routes.views import views_bp
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR)

app.register_blueprint(api_bp)
app.register_blueprint(views_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)