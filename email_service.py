import smtplib
from email.mime.text import MIMEText

EMAIL_EXPEDITEUR = "ton-email@gmail.com"
EMAIL_MDP = "mot_de_passe_app"

def send_licence_email(to_email, licence_key):
    sujet = "Votre clé de licence Quant Analytics"
    message = f"Bonjour,\n\nVoici votre clé de licence : {licence_key}\nMerci pour votre achat !"
    
    msg = MIMEText(message)
    msg['Subject'] = sujet
    msg['From'] = EMAIL_EXPEDITEUR
    msg['To'] = to_email
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_EXPEDITEUR, EMAIL_MDP)
        server.send_message(msg)
