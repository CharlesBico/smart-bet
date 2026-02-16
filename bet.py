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
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")
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
    role = db.Column(db.String(20), default="user")  # user ou admin

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    date_match = db.Column(db.DateTime, nullable=False)
    statut = db.Column(db.String(20), default="ouvert")  # ouvert, validé, terminé

class Pari(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'))
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    choix = db.Column(db.String(100))
    mise = db.Column(db.Float)
    statut = db.Column(db.String(20), default="En attente")  # En attente, Validé, Perdu, Gagné

# -----------------------------
# ROUTES UTILISATEURS
# -----------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    nom = data.get("nom", "").strip()
    tel = data.get("tel", "").strip()

    if not nom or not tel:
        return jsonify({"error": "Nom et téléphone requis"}), 400

    if Utilisateur.query.filter_by(tel=tel).first():
        return jsonify({"error": "Utilisateur existe déjà"}), 400

    # Création admin spécial (tel = 0000000000)
    role = "admin" if tel == "0100000000" else "user"

    user = Utilisateur(nom=nom, tel=tel, solde=0.0, role=role)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        "id": user.id,
        "nom": user.nom,
        "tel": user.tel,
        "solde": user.solde,
        "role": user.role,
        "message": "Utilisateur créé"
    })

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    tel = data.get("tel", "").strip()

    user = Utilisateur.query.filter_by(tel=tel).first()
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 404

    return jsonify({
        "id": user.id,
        "nom": user.nom,
        "tel": user.tel,
        "solde": user.solde,
        "role": user.role
    })

# -----------------------------
# ROUTES PARIS
# -----------------------------
@app.route("/parier", methods=["POST"])
def parier():
    data = request.get_json()
    joueur_tel = data.get("joueur_tel")
    match_nom = data.get("match")
    choix = data.get("choix")
    mise = float(data.get("mise", 0))

    joueur = Utilisateur.query.filter_by(tel=joueur_tel).first()
    match = Match.query.filter_by(nom=match_nom).first()

    if not joueur or not match:
        return jsonify({"error": "Joueur ou match introuvable"}), 404
    if joueur.solde < mise:
        return jsonify({"error": "Solde insuffisant"}), 400
    if match.statut != "ouvert":
        return jsonify({"error": "Match non ouvert"}), 400

    pari = Pari(
        utilisateur_id=joueur.id,
        match_id=match.id,
        choix=choix,
        mise=mise,
        statut="En attente"
    )
    db.session.add(pari)
    db.session.commit()

    return jsonify({"message": "Pari enregistré en attente"})

@app.route("/paris", methods=["GET"])
def liste_paris():
    paris = Pari.query.all()
    result = []
    for p in paris:
        joueur = Utilisateur.query.get(p.utilisateur_id)
        match = Match.query.get(p.match_id)
        result.append({
            "joueur": joueur.nom,
            "match": match.nom,
            "choix": p.choix,
            "mise": p.mise,
            "statut": p.statut
        })
    return jsonify(result)

# -----------------------------
# ROUTES ADMIN
# -----------------------------
@app.route("/admin/joueurs", methods=["GET"])
def admin_joueurs():
    joueurs = Utilisateur.query.all()
    result = []
    for u in joueurs:
        result.append({
            "nom": u.nom,
            "tel": u.tel,
            "solde": u.solde,
            "role": u.role
        })
    return jsonify(result)

@app.route("/admin/solde", methods=["POST"])
def admin_solde():
    data = request.get_json()
    tel = data.get("tel")
    solde = float(data.get("solde", 0))
    joueur = Utilisateur.query.filter_by(tel=tel).first()
    if not joueur:
        return jsonify({"error": "Joueur introuvable"}), 404
    joueur.solde = solde
    db.session.commit()
    return jsonify({"message": f"Solde de {joueur.nom} mis à jour", "nouveau_solde": joueur.solde})

@app.route("/admin/match", methods=["POST"])
def admin_match():
    data = request.get_json()
    action = data.get("action")
    match_nom = data.get("match")
    match = Match.query.filter_by(nom=match_nom).first()

    if action == "creer":
        date_str = data.get("date_match")
        try:
            date_match = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except:
            return jsonify({"error": "Format date invalide"}), 400
        if Match.query.filter_by(nom=match_nom).first():
            return jsonify({"error": "Match déjà existant"}), 400
        new_match = Match(nom=match_nom, date_match=date_match, statut="ouvert")
        db.session.add(new_match)
        db.session.commit()
        return jsonify({"message": f"Match {match_nom} créé"})

    elif action == "terminer":
        if not match:
            return jsonify({"error": "Match introuvable"}), 404
        match.statut = "terminé"
        # traiter les paris
        paris = Pari.query.filter_by(match_id=match.id).all()
        for p in paris:
            joueur = Utilisateur.query.get(p.utilisateur_id)
            if p.choix == data.get("vainqueur"):
                p.statut = "Gagné"
                joueur.solde += p.mise * 2
            else:
                p.statut = "Perdu"
        db.session.commit()
        return jsonify({"message": f"Match {match_nom} terminé et paris traités"})

    elif action == "supprimer":
        if not match:
            return jsonify({"error": "Match introuvable"}), 404
        Pari.query.filter_by(match_id=match.id).delete()
        db.session.delete(match)
        db.session.commit()
        return jsonify({"message": f"Match {match_nom} supprimé"})

    return jsonify({"error": "Action invalide"}), 400

# -----------------------------
# CHECK BACKEND
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
    app.run(host="0.0.0.0", port=5000)
