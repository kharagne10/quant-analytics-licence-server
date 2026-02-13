import secrets

def generate_licence_key(email):
    # Génère clé unique
    return secrets.token_hex(16)
