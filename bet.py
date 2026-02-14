import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)

# -----------------------------
# CONFIG DATABASE
# -----------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")  # compatibilité SQLAlchemy
else:
    DATABASE_URL = "sqlite:///smartbet.db"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------
# MODELS
# -----------------------------
class Utilisateur(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    tel = db.Column(db.String(20), unique=True, nullable=False)
    solde = db.Column(db.Float, default=0.0)

# Pour simplifier, on peut continuer avec paris en mémoire ou créer une table Match/Pari

# -----------------------------
# ROUTES (exemple)
# -----------------------------
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "SmartBet backend OK"})

# -----------------------------
# LANCEMENT
# -----------------------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run()
