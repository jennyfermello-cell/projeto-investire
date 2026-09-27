from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'investire/static/uploads'
app.secret_key = 'chave_secreta'
app.permanent_session_lifetime = 3600
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///investire.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)
bcrypt = Bcrypt(app)

# importa as rotas DEPOIS que app e db existem (quebra o ciclo)
from investire import routes

