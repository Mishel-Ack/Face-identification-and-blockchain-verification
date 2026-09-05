from cryptography.fernet import Fernet
import os
import json

class FaceDataEncryptor:
    """Encrypt sensitive face data before storage"""

    def __init__(self, key=None):
        if key is None:
            key = os.getenv('ENCRYPTION_KEY')
            if not key:
                generated_key = Fernet.generate_key().decode()
                print(f"[FaceDataEncryptor] Notice: ENCRYPTION_KEY not set. Using generated session key.")
                key = generated_key

        if isinstance(key, str):
            key = key.encode()

        self.cipher = Fernet(key)

    def encrypt_embedding(self, embedding):
        """Encrypt face embedding before storing"""
        data = json.dumps(embedding)
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()

    def decrypt_embedding(self, encrypted_data):
        """Decrypt face embedding for comparison"""
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        return json.loads(decrypted.decode())

    def anonymize_face_hash(self, face_hash):
        """Replace face hash with zero hash (GDPR right to be forgotten)"""
        return '0x' + '0' * 64
