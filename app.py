from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import sqlite3
import uuid
import os

from admin.dashboard import admin_bp
app.register_blueprint(admin_bp)

DB_FILE = "licences.db"
ADMIN_PASSWORD = "ADMIN2026"
LICENCE_DURATION_DAYS = 30

app = Flask(__name__)

# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS licences (
            licence_key TEXT PRIMARY KEY,
            machine_id TEXT,
            expiry TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- GENERATE ----------------

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

# ---------------- ACTIVATE ----------------

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

# ---------------- VERIFY ----------------

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

    expiry = datetime.fromisoformat(expiry_str)
    if datetime.utcnow() > expiry:
        return jsonify({"valid": False})

    return jsonify({"valid": True})

# ---------------- ROOT ----------------

@app.route("/")
def home():
    return render_template("index.html")


from flask import render_template, request, redirect, url_for
from payments.wave import create_payment_link  # ton module de paiement

from flask import Flask, render_template, request, redirect
from models import db, Licence
from payments.wave import create_payment_link
from licence import generate_licence_key
from email_service import send_licence_email

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@host:port/dbname'
db.init_app(app)

@app.route('/licence', methods=['GET', 'POST'])
def licence():
    if request.method == 'POST':
        data = request.get_json()  # On reçoit JSON depuis le JS
        email = data.get('email')
        amount = data.get('amount')
        if not email or not amount:
            return jsonify({"message": "Email et montant requis"}), 400

        # Crée le lien de paiement via ton module Wave
        payment_url = create_payment_link(email, amount)
        return redirect(payment_url)

    return render_template('licence.html')


@app.route('/webhook/payment', methods=['POST'])
def payment_webhook():
    data = request.json
    if data.get('status') == 'paid':
        email = data.get('customer_email')
        licence_key = generate_licence_key(email)
        # Créer licence en base
        new_licence = Licence(client_email=email, key=licence_key, status='active')
        db.session.add(new_licence)
        db.session.commit()
        # Envoyer email
        send_licence_email(email, licence_key)
    return "OK", 200


@app.route("/debug")
def debug():
    return "SERVER VERSION OK"

# ---------------- RUN LOCAL ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

