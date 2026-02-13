from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

DB_FILE = "licences.db"

# Page dashboard
@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT licence_key, machine_id, expiry FROM licences")
    licences = c.fetchall()
    conn.close()

    # Formater les dates et statut
    formatted = []
    now = datetime.utcnow()
    for key, machine, expiry in licences:
        status = "Expirée"
        exp_str = expiry
        if expiry:
            expiry_dt = datetime.fromisoformat(expiry)
            status = "Active" if expiry_dt > now else "Expirée"
            exp_str = expiry_dt.strftime("%Y-%m-%d %H:%M")
        formatted.append({
            "key": key,
            "machine": machine or "-",
            "expiry": exp_str,
            "status": status
        })

    return render_template("admin_dashboard.html", licences=formatted)

# Révoquer licence
@admin_bp.route('/revoke/<licence_key>', methods=['POST'])
def revoke(licence_key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE licences SET expiry=NULL, machine_id=NULL WHERE licence_key=?", (licence_key,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.dashboard'))

# Renouveler licence
@admin_bp.route('/renew/<licence_key>', methods=['POST'])
def renew(licence_key):
    new_expiry = datetime.utcnow() + timedelta(days=30)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE licences SET expiry=? WHERE licence_key=?", (new_expiry.isoformat(), licence_key))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.dashboard'))
