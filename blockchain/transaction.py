import json
import binascii
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

class Transaction:
    def __init__(self, from_address, to_address, amount):
        self.from_address = from_address
        self.to_address = to_address
        self.amount = amount
        self.signature = None
    
    def calculate_hash(self):
        transaction_data = {
            "from": self.from_address,
            "to": self.to_address,
            "amount": self.amount
        }
        return json.dumps(transaction_data, sort_keys=True)
    
    def sign_transaction(self, signing_key):
        # Don't sign if it's a mining reward
        if self.from_address == "SYSTEM":
            return
        
        # Check if the signer is the sender
        public_key_bytes = signing_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        transaction_hash = self.calculate_hash().encode()
        
        self.signature = signing_key.sign(
            transaction_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    
    def is_valid(self, public_key=None):
        # Mining rewards are always valid as they come from the system
        if self.from_address == "SYSTEM":
            return True
        
        if not self.signature:
            print("No signature found in this transaction")
            return False
        
        if not public_key:
            print("Public key required to verify transaction")
            return False
        
        try:
            transaction_hash = self.calculate_hash().encode()
            
            public_key.verify(
                self.signature,
                transaction_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False
    
    def to_dict(self):
        return {
            "from": self.from_address,
            "to": self.to_address,
            "amount": self.amount,
            "signature": binascii.hexlify(self.signature).decode('ascii') if self.signature else None
        }