from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import sqlite3
import uuid

# --- CONFIG ---
DB_FILE = "licences.db"
ADMIN_PASSWORD = "ADMIN2026"  # ⚠️ à changer pour production
LICENCE_DURATION_DAYS = 30

app = Flask(__name__)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS licences (
            licence_key TEXT PRIMARY KEY,
            machine_id TEXT,
            expiry TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- GENERATE KEY (admin only) ---
@app.route("/generate", methods=["POST"])
def generate_key():
    data = request.json
    password = data.get("password")
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    new_key = str(uuid.uuid4()).upper()[:18]  # Exemple : 18 caractères
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO licences (licence_key) VALUES (?)", (new_key,))
    conn.commit()
    conn.close()
    return jsonify({"key": new_key})

# --- ACTIVATE LICENCE ---
@app.route("/api/activate", methods=["POST"])
def activate():
    data = request.json
    licence_key = data.get("licence_key")
    machine_id = data.get("machine_id")

    if not licence_key or not machine_id:
        return jsonify({"status": "error", "message": "Licence key and machine_id required"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT expiry FROM licences WHERE licence_key = ?", (licence_key,))
    row = c.fetchone()
    now = datetime.now()

    if row:
        # Déjà activée ? -> Renouveler
        expiry = datetime.fromisoformat(row[0]) if row[0] else now
        new_expiry = max(expiry, now) + timedelta(days=LICENCE_DURATION_DAYS)
        c.execute("UPDATE licences SET machine_id=?, expiry=? WHERE licence_key=?", 
                  (machine_id, new_expiry.isoformat(), licence_key))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "expiry": new_expiry.isoformat()})
    else:
        conn.close()
        return jsonify({"status": "error", "message": "Licence key not found"}), 404

# --- VERIFY LICENCE ---
@app.route("/api/verify", methods=["POST"])
def verify():
    data = request.json
    licence_key = data.get("licence_key")
    machine_id = data.get("machine_id")

    if not licence_key or not machine_id:
        return jsonify({"valid": False, "message": "Licence key and machine_id required"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT machine_id, expiry FROM licences WHERE licence_key=?", (licence_key,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"valid": False, "message": "Licence not found"}), 404

    db_machine_id, expiry_str = row
    expiry = datetime.fromisoformat(expiry_str) if expiry_str else None

    if db_machine_id != machine_id:
        return jsonify({"valid": False, "message": "Machine ID mismatch"}), 403
    if not expiry or datetime.now() > expiry:
        return jsonify({"valid": False, "message": "Licence expired"}), 403

    return jsonify({"valid": True, "expiry": expiry.isoformat()})

# --- TEST ---
@app.route("/")
def index():
    return "Licence Server Running 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
