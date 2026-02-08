from flask import Flask, jsonify, request
import random
import time
from threading import Thread

app = Flask(__name__)

# =========================
# CONFIGURATION
# =========================
DUREE_PARIS = 300   # 5 minutes avant fermeture
paris = []          # liste de tous les paris
# Structure d'un pari :
# {
#   "joueur": "Ali",
#   "match": "Real vs Barca",
#   "heure_debut": timestamp,
#   "vainqueur": "Real",
#   "mise": 1000,
#   "statut": "En attente" / "Validé"
# }

# =========================
# ENDPOINTS EXISTANTS
# =========================
@app.route("/parier", methods=["POST"])
def add_pari():
    data = request.get_json()
    joueur = data.get("joueur")
    match = data.get("match")
    heure_debut = data.get("heure_debut")  # timestamp ou string
    vainqueur = data.get("vainqueur")
    mise = data.get("mise")

    # Vérifier que H-5 min n'est pas dépassé
    heure_timestamp = time.mktime(time.strptime(heure_debut, "%Y-%m-%d %H:%M"))
    if time.time() > heure_timestamp - DUREE_PARIS:
        return jsonify({"error": "Paris fermés (H-5 minutes)"}), 400

    # Ajouter le pari avec statut "En attente"
    pari = {
        "joueur": joueur,
        "match": match,
        "heure_debut": heure_timestamp,
        "vainqueur": vainqueur,
        "mise": mise,
        "statut": "En attente"
    }
    paris.append(pari)

    # Vérifier si on peut valider (même match, même mise, équipe adverse)
    for autre_pari in paris:
        if (
            autre_pari["match"] == match
            and autre_pari["mise"] == mise
            and autre_pari["vainqueur"] != vainqueur
            and autre_pari["statut"] == "En attente"
        ):
            # Valider les deux paris
            pari["statut"] = "Validé"
            autre_pari["statut"] = "Validé"
            break

    return jsonify({"message": "Pari enregistré", "statut": pari["statut"]})

# =========================
# NOUVEL ENDPOINT : LISTE DES PARIS
# =========================
@app.route("/paris")
def liste_paris():
    # Retourner tous les paris
    resultats = []
    for p in paris:
        resultats.append({
            "joueur": p["joueur"],
            "match": p["match"],
            "heure_debut": time.strftime("%Y-%m-%d %H:%M", time.localtime(p["heure_debut"])),
            "vainqueur": p["vainqueur"],
            "mise": p["mise"],
            "statut": p["statut"]
        })
    return jsonify(resultats)

# =========================
# LANCEMENT
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
