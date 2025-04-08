from cryptography.fernet import Fernet
import os
import base64

# Get the encryption key from environment variables
ENCRYPTION_KEY = os.getenv('EASTERN_ENCRYPTION_KEY')

def encrypt_token(token):
    """Encrypt an access token"""
    if not token:
        return None
    
    # If no encryption key is set, return the token as is (for development)
    if not ENCRYPTION_KEY:
        return token
    
    try:
        f = Fernet(ENCRYPTION_KEY)
        encrypted_token = f.encrypt(token.encode())
        return encrypted_token.decode()
    except Exception as e:
        print(f"Error encrypting token: {e}")
        return None

def decrypt_token(encrypted_token):
    """Decrypt an access token"""
    if not encrypted_token:
        return None
    
    # If no encryption key is set, return the token as is (for development)
    if not ENCRYPTION_KEY:
        return encrypted_token
    
    try:
        f = Fernet(ENCRYPTION_KEY)
        decrypted_token = f.decrypt(encrypted_token.encode())
        return decrypted_token.decode()
    except Exception as e:
        print(f"Error decrypting token: {e}")
        return None

def generate_encryption_key():
    """Generate a new encryption key"""
    return Fernet.generate_key().decode() 