"""
API Key Encryption/Decryption Utility
Securely encrypts and decrypts API keys using Fernet symmetric encryption with per-user salts
"""

import os
import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

load_dotenv()


class EncryptionService:
    """Service for encrypting and decrypting sensitive data with per-user salts"""

    def __init__(self):
        # Get encryption key from environment
        self.secret = os.getenv("SECRET_KEY", "default-secret-key-change-this")

    def _derive_key(self, salt: bytes) -> bytes:
        """
        Derive an encryption key from the secret and a unique salt

        Args:
            salt: Unique salt bytes for this encryption

        Returns:
            Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.secret.encode()))

    def generate_salt(self) -> str:
        """
        Generate a unique salt for a user

        Returns:
            Base64-encoded salt string
        """
        salt_bytes = secrets.token_bytes(16)
        return base64.urlsafe_b64encode(salt_bytes).decode()

    def encrypt(self, plaintext: str, salt: str) -> str:
        """
        Encrypt a string using a unique salt

        Args:
            plaintext: String to encrypt (e.g., API key)
            salt: Base64-encoded salt string (unique per user)

        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return ""

        if not salt:
            raise ValueError("Salt is required for encryption")

        # Decode salt from base64
        salt_bytes = base64.urlsafe_b64decode(salt.encode())

        # Derive key using salt
        key = self._derive_key(salt_bytes)
        cipher = Fernet(key)

        # Encrypt
        encrypted = cipher.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, ciphertext: str, salt: str) -> str:
        """
        Decrypt a string using the same salt used for encryption

        Args:
            ciphertext: Encrypted string to decrypt
            salt: Base64-encoded salt string (must match encryption salt)

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""

        if not salt:
            print("Warning: No salt provided for decryption")
            return ""

        try:
            # Decode salt from base64
            salt_bytes = base64.urlsafe_b64decode(salt.encode())

            # Derive key using salt
            key = self._derive_key(salt_bytes)
            cipher = Fernet(key)

            # Decrypt
            decrypted = cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            # If decryption fails, return empty string
            # This can happen if salt changed or SECRET_KEY changed
            print(f"Decryption error: {e}")
            return ""


# Singleton instance
encryption_service = EncryptionService()
