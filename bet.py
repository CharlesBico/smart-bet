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
    role = db.Column(db.String(20), default="user")  # ← AJOUT

# Pour simplifier, on peut continuer avec paris en mémoire ou créer une table Match/Pari

# -----------------------------
# ROUTES (exemple)
# -----------------------------
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "SmartBet backend OK"})

# -----------------------------
# REGISTER
# -----------------------------
@app.route("/register", methods=["POST"])

def register():

    data = request.get_json()

    if not data or "nom" not in data or "tel" not in data:
        return jsonify({"error": "Nom et téléphone requis"}), 400

    nom = data["nom"]
    tel = data["tel"]


    # Vérifie si utilisateur existe déjà
    existing_user = Utilisateur.query.filter_by(tel=tel).first()
    if existing_user:
        return jsonify({"error": "Utilisateur déjà existant"}), 400

    role = "admin" if tel == "0700000000" else "user"
    new_user = Utilisateur(nom=nom, tel=tel, role=role)
    # new_user = Utilisateur(nom=nom, tel=tel)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": "Utilisateur créé",
        "id": new_user.id,
        "nom": new_user.nom,
        "tel": new_user.tel,
        "solde": new_user.solde
    }), 201


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or "tel" not in data:
        return jsonify({"error": "Téléphone requis"}), 400

    tel = data["tel"]

    user = Utilisateur.query.filter_by(tel=tel).first()

    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    return jsonify({
        "id": user.id,
        "nom": user.nom,
        "tel": user.tel,
        "solde": user.solde,
        "role": user.role  # ← AJOUT
    }), 200


# -----------------------------
# LANCEMENT
# -----------------------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run()
