from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

DB_FILE = "licences.db"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # mettre en variable d'env
LICENCE_DURATION_DAYS = 30

# ---------------- LOGIN ----------------
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            return render_template('admin_login.html', error="Mot de passe incorrect")
    return render_template('admin_login.html')

# ---------------- LOGOUT ----------------
@admin_bp.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('admin.login'))

# ---------------- DASHBOARD ----------------
@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin.login'))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT licence_key, machine_id, expiry FROM licences")
    licences = c.fetchall()
    conn.close()

    now = datetime.utcnow()
    formatted = []
    for key, machine, expiry in licences:
        status = "Expirée"
        exp_str = "-"
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

# ---------------- RÉVOQUER LICENCE ----------------
@admin_bp.route('/revoke/<licence_key>', methods=['POST'])
def revoke(licence_key):
    if not session.get('admin'):
        return redirect(url_for('admin.login'))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE licences SET expiry=NULL, machine_id=NULL WHERE licence_key=?", (licence_key,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.dashboard'))

# ---------------- RENOUVELER LICENCE ----------------
@admin_bp.route('/renew/<licence_key>', methods=['POST'])
def renew(licence_key):
    if not session.get('admin'):
        return redirect(url_for('admin.login'))

    new_expiry = datetime.utcnow() + timedelta(days=LICENCE_DURATION_DAYS)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE licences SET expiry=? WHERE licence_key=?", (new_expiry.isoformat(), licence_key))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.dashboard'))
