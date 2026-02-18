import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
CORS(app)

# -----------------------------
# CONFIG DATABASE
# -----------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
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


class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True)
    date_match = db.Column(db.String(50))
    statut = db.Column(db.String(20), default="ouvert")


class Pari(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey("utilisateur.id"))
    match_id = db.Column(db.Integer, db.ForeignKey("match.id"))
    choix = db.Column(db.String(100))
    mise = db.Column(db.Float)
    statut = db.Column(db.String(20), default="En attente")


# -----------------------------
# ROUTE TEST
# -----------------------------
@app.route("/")
def index():
    return jsonify({"status": "SmartBet backend OK"})


# -----------------------------
# AUTH
# -----------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    nom = data.get("nom", "").strip()
    tel = data.get("tel", "").strip()

    if tel == "0100000000":
        return jsonify({"error": "Admin ne peut pas s'inscrire"}), 400

    if not nom or not tel:
        return jsonify({"error": "Nom et téléphone requis"}), 400

    if Utilisateur.query.filter_by(tel=tel).first():
        return jsonify({"error": "Utilisateur existe déjà"}), 400

    user = Utilisateur(nom=nom, tel=tel)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Utilisateur créé",
        "nom": user.nom,
        "tel": user.tel,
        "solde": user.solde
    })


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    tel = data.get("tel")

    if tel == "0100000000":
        return jsonify({"role": "admin"})

    user = Utilisateur.query.filter_by(tel=tel).first()
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    return jsonify({
        "role": "user",
        "nom": user.nom,
        "tel": user.tel,
        "solde": user.solde
    })


# -----------------------------
# JOUEUR - CREER MATCH
# -----------------------------
@app.route("/match", methods=["POST"])
def creer_match():
    data = request.get_json()

    nom = data.get("nom")
    date_match = data.get("date_match")

    if Match.query.filter_by(nom=nom).first():
        return jsonify({"error": "Match existe déjà"}), 400

    new_match = Match(nom=nom, date_match=date_match)
    db.session.add(new_match)
    db.session.commit()

    return jsonify({"message": "Match créé"})


@app.route("/matchs", methods=["GET"])
def liste_matchs():
    matchs = Match.query.all()

    return jsonify([
        {
            "id": m.id,
            "nom": m.nom,
            "date_match": m.date_match,
            "statut": m.statut
        }
        for m in matchs
    ])


# -----------------------------
# PARIER
# -----------------------------
@app.route("/parier", methods=["POST"])
def parier():
    data = request.get_json()

    joueur = Utilisateur.query.filter_by(tel=data.get("joueur_tel")).first()
    match = Match.query.filter_by(nom=data.get("match")).first()
    mise = float(data.get("mise", 0))

    if not joueur or not match:
        return jsonify({"error": "Joueur ou match introuvable"}), 404

    if match.statut != "ouvert":
        return jsonify({"error": "Match non ouvert"}), 400

    if joueur.solde < mise:
        return jsonify({"error": "Solde insuffisant"}), 400

    # Déduction immédiate
    joueur.solde -= mise

    pari = Pari(
        utilisateur_id=joueur.id,
        match_id=match.id,
        choix=data.get("choix"),
        mise=mise
    )

    db.session.add(pari)
    db.session.commit()

    return jsonify({"message": "Pari enregistré"})


# -----------------------------
# ADMIN - GESTION SOLDES
# -----------------------------
@app.route("/admin/solde", methods=["PUT"])
def update_solde():
    data = request.get_json()

    user = Utilisateur.query.filter_by(tel=data.get("tel")).first()
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    user.solde = float(data.get("solde"))
    db.session.commit()

    return jsonify({"message": "Solde mis à jour"})


# -----------------------------
# ADMIN - TERMINER MATCH
# -----------------------------
@app.route("/admin/match/<int:id>/terminer", methods=["PUT"])
def terminer_match(id):
    match = Match.query.get(id)
    if not match:
        return jsonify({"error": "Match introuvable"}), 404

    match.statut = "termine"

    vainqueur = request.get_json().get("vainqueur")

    paris = Pari.query.filter_by(match_id=match.id).all()

    for p in paris:
        joueur = Utilisateur.query.get(p.utilisateur_id)
        if p.choix == vainqueur:
            p.statut = "Gagné"
            joueur.solde += p.mise * 2
        else:
            p.statut = "Perdu"

    db.session.commit()

    return jsonify({"message": "Match terminé et paris traités"})


@app.route("/admin/match/<int:id>", methods=["DELETE"])
def supprimer_match(id):
    match = Match.query.get(id)
    if not match:
        return jsonify({"error": "Match introuvable"}), 404

    Pari.query.filter_by(match_id=match.id).delete()
    db.session.delete(match)
    db.session.commit()

    return jsonify({"message": "Match supprimé"})


# -----------------------------
# INIT DB
# -----------------------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
