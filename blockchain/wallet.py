import hashlib
import binascii
import os
import json
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

class Wallet:
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.address = None
        self.generate_keys()
    
    def generate_keys(self):
        # Generate a new RSA key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        
        # Generate a wallet address from the public key
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Create a simple address by hashing the public key
        address_hash = hashlib.sha256(public_key_bytes).digest()
        self.address = binascii.hexlify(address_hash).decode('ascii')[:40]
    
    def sign_transaction(self, transaction):
        # Convert transaction to string and sign it
        transaction_str = json.dumps(transaction, sort_keys=True).encode()
        
        signature = self.private_key.sign(
            transaction_str,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return binascii.hexlify(signature).decode('ascii')
    
    def save_to_file(self, filename):
        # Serialize private key to save to file
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(filename, 'wb') as f:
            f.write(pem)
    
    @classmethod
    def load_from_file(cls, filename):
        with open(filename, 'rb') as f:
            pem_data = f.read()
        
        wallet = cls.__new__(cls)
        wallet.private_key = serialization.load_pem_private_key(
            pem_data,
            password=None,
            backend=default_backend()
        )
        wallet.public_key = wallet.private_key.public_key()
        
        # Regenerate the address
        public_key_bytes = wallet.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        address_hash = hashlib.sha256(public_key_bytes).digest()
        wallet.address = binascii.hexlify(address_hash).decode('ascii')[:40]
        
        return wallet