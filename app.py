import os
import uuid
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy

# ==============================
# CONFIGURATION
# ==============================

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ==============================
# MODELE LICENCE
# ==============================

class Licence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    licence_key = db.Column(db.String(64), unique=True, nullable=False)
    machine_id = db.Column(db.String(128), nullable=True)
    expiry_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=False)

# ==============================
# CREATION TABLES
# ==============================

with app.app_context():
    db.create_all()

# ==============================
# PAGE LICENCE (SITE CLIENT)
# ==============================

@app.route("/licence")
def licence_page():
    return render_template_string("""
    <h1>Quant Analytics – Licence</h1>
    <p>Achetez votre licence pour activer le logiciel.</p>
    <p>Contact : contact@quant-analytics.com</p>
    """)

# ==============================
# ADMIN – GENERER CLE (TEMPORAIRE)
# ==============================

@app.route("/admin/generate")
def generate_key():
    new_key = str(uuid.uuid4()).replace("-", "").upper()[:20]

    licence = Licence(
        licence_key=new_key,
        is_active=False
    )

    db.session.add(licence)
    db.session.commit()

    return jsonify({
        "status": "ok",
        "key": new_key
    })

# ==============================
# ACTIVATION LICENCE (30 JOURS)
# ==============================

@app.route("/api/activate", methods=["POST"])
def activate():
    data = request.get_json()

    licence_key = data.get("licence_key")
    machine_id = data.get("machine_id")

    if not licence_key or not machine_id:
        return jsonify({"status": "error", "message": "Données manquantes"}), 400

    licence = Licence.query.filter_by(licence_key=licence_key).first()

    if not licence:
        return jsonify({"status": "error", "message": "Clé invalide"}), 400

    # Déjà utilisée sur autre machine
    if licence.machine_id and licence.machine_id != machine_id:
        return jsonify({
            "status": "error",
            "message": "Licence déjà utilisée sur une autre machine"
        }), 403

    # Activation
    licence.machine_id = machine_id
    licence.expiry_date = datetime.utcnow() + timedelta(days=30)
    licence.is_active = True

    db.session.commit()

    return jsonify({
        "status": "ok",
        "expiry": licence.expiry_date.isoformat()
    })

# ==============================
# VERIFICATION LICENCE
# ==============================

@app.route("/api/verify", methods=["POST"])
def verify():
    data = request.get_json()

    licence_key = data.get("licence_key")
    machine_id = data.get("machine_id")

    licence = Licence.query.filter_by(licence_key=licence_key).first()

    if not licence:
        return jsonify({"valid": False})

    if licence.machine_id != machine_id:
        return jsonify({"valid": False})

    if not licence.expiry_date:
        return jsonify({"valid": False})

    if licence.expiry_date < datetime.utcnow():
        return jsonify({"valid": False})

    return jsonify({"valid": True})

# ==============================
# ROUTE TEST
# ==============================

@app.route("/")
def home():
    return "Quant Analytics Licence Server Running 🚀"

# ==============================
# LANCEMENT
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
