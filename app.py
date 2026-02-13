from flask import Flask, request, jsonify, render_template, redirect, url_for
from datetime import datetime, timedelta
import sqlite3
import uuid
import os

# Modules externes
from admin.dashboard import admin_bp
from models import db, Licence
# from payments.wave import create_payment_link  # Commenté pour test
from licence import generate_licence_key
from email_service import send_licence_email

# ---------------- CONFIG ----------------
DB_FILE = "licences.db"
ADMIN_PASSWORD = "ADMIN2026"
LICENCE_DURATION_DAYS = 30

# ---------------- APP INIT ----------------
app = Flask(__name__)

# PostgreSQL (Railway)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Enregistrement blueprint admin
app.register_blueprint(admin_bp)

# ---------------- SQLITE DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS licences (
            licence_key TEXT PRIMARY KEY,
            client_email TEXT,
            machine_id TEXT,
            expiry TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- GENERATE LICENCE (ADMIN) ----------------
@app.route("/generate", methods=["POST"])
def generate_key():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400

    data = request.get_json()
    password = data.get("password")

    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    new_key = str(uuid.uuid4()).upper().replace("-", "")[:18]

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO licences (licence_key) VALUES (?)", (new_key,))
    conn.commit()
    conn.close()

    return jsonify({"key": new_key})

# ---------------- ACTIVATE LICENCE ----------------
@app.route("/api/activate", methods=["POST"])
def activate():
    if not request.is_json:
        return jsonify({"status": "error", "message": "JSON required"}), 400

    data = request.get_json()
    licence_key = data.get("licence_key")
    machine_id = data.get("machine_id")

    if not licence_key or not machine_id:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT expiry FROM licences WHERE licence_key=?", (licence_key,))
    row = c.fetchone()

    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "Licence not found"}), 404

    now = datetime.utcnow()
    new_expiry = now + timedelta(days=LICENCE_DURATION_DAYS)

    c.execute("""
        UPDATE licences
        SET machine_id=?, expiry=?
        WHERE licence_key=?
    """, (machine_id, new_expiry.isoformat(), licence_key))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "ok",
        "expiry": new_expiry.isoformat()
    })

# ---------------- VERIFY LICENCE ----------------
@app.route("/api/verify", methods=["POST"])
def verify():
    if not request.is_json:
        return jsonify({"valid": False}), 400

    data = request.get_json()
    licence_key = data.get("licence_key")
    machine_id = data.get("machine_id")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT machine_id, expiry FROM licences WHERE licence_key=?", (licence_key,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"valid": False})

    db_machine_id, expiry_str = row

    if db_machine_id != machine_id:
        return jsonify({"valid": False})

    if not expiry_str:
        return jsonify({"valid": False})

    expiry = datetime.fromisoformat(expiry_str)

    if datetime.utcnow() > expiry:
        return jsonify({"valid": False})

    return jsonify({"valid": True})

# ---------------- PAGE ACCUEIL ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- PAGE LICENCE (TEST SANS PAIEMENT) ----------------
@app.route('/licence', methods=['GET', 'POST'])
def licence_page():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        amount = data.get('amount')

        if not email or not amount:
            return jsonify({"message": "Email et montant requis"}), 400

        # Génération clé directement pour test
        licence_key = generate_licence_key(email)

        # Enregistrer en base SQLite
        expiry = datetime.utcnow() + timedelta(days=LICENCE_DURATION_DAYS)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO licences (licence_key, client_email, expiry) VALUES (?, ?, ?)",
                  (licence_key, email, expiry.isoformat()))
        conn.commit()
        conn.close()

        # Pour plus tard si Wave est activé
        # payment_url = create_payment_link(email, amount)
        # return jsonify({"payment_url": payment_url})

        return jsonify({"licence_key": licence_key})

    return render_template('licence.html')

# ---------------- WEBHOOK PAIEMENT (Commenté pour test) ----------------
"""
@app.route('/webhook/payment', methods=['POST'])
def payment_webhook():
    data = request.json
    if data and data.get('status') == 'paid':
        email = data.get('customer_email')
        licence_key = generate_licence_key(email)
        new_licence = Licence(client_email=email, key=licence_key, status='active')
        db.session.add(new_licence)
        db.session.commit()
        send_licence_email(email, licence_key)
    return "OK", 200
"""

# ---------------- DEBUG ----------------
@app.route("/debug")
def debug():
    return "SERVER VERSION OK"

# ---------------- RUN LOCAL ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
