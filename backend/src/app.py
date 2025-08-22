from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS 
from config import Config
from routes.game import game_bp

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])
app.config.from_object(Config)

db = SQLAlchemy(app)

app.register_blueprint(game_bp, url_prefix='/api/games')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)