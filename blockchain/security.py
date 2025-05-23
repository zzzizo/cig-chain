import hashlib
import time
import json
import base64
import secrets
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet

class SecurityManager:
    def __init__(self):
        self.merkle_tree_cache = {}
    
    def calculate_merkle_root(self, transactions):
        """Calculate the Merkle root of a list of transactions"""
        if not transactions:
            return hashlib.sha256("".encode()).hexdigest()
        
        # Convert transactions to hashes if they're not already
        tx_hashes = []
        for tx in transactions:
            if isinstance(tx, str) and len(tx) == 64:  # Assuming it's already a hash
                tx_hashes.append(tx)
            else:
                # Convert to JSON and hash
                tx_json = json.dumps(tx, sort_keys=True).encode()
                tx_hashes.append(hashlib.sha256(tx_json).hexdigest())
        
        # Build the Merkle tree
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])  # Duplicate the last hash if odd number
            
            next_level = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i+1]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            
            tx_hashes = next_level
        
        return tx_hashes[0]
    
    def verify_merkle_proof(self, tx_hash, merkle_proof, merkle_root):
        """Verify that a transaction is part of a block using a Merkle proof"""
        current_hash = tx_hash
        
        for sibling_hash, is_left in merkle_proof:
            if is_left:
                current_hash = hashlib.sha256((sibling_hash + current_hash).encode()).hexdigest()
            else:
                current_hash = hashlib.sha256((current_hash + sibling_hash).encode()).hexdigest()
        
        return current_hash == merkle_root
    
    def generate_merkle_proof(self, tx_hash, transactions):
        """Generate a Merkle proof for a transaction"""
        # Convert transactions to hashes
        tx_hashes = []
        tx_index = -1
        
        for i, tx in enumerate(transactions):
            if isinstance(tx, str) and len(tx) == 64:
                tx_hash_i = tx
            else:
                tx_json = json.dumps(tx, sort_keys=True).encode()
                tx_hash_i = hashlib.sha256(tx_json).hexdigest()
            
            tx_hashes.append(tx_hash_i)
            if tx_hash_i == tx_hash:
                tx_index = i
        
        if tx_index == -1:
            return None  # Transaction not found
        
        proof = []
        index = tx_index
        
        # Build the proof by traversing up the tree
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])
            
            next_level = []
            for i in range(0, len(tx_hashes), 2):
                if i == index or i + 1 == index:
                    # This is the sibling we need for the proof
                    sibling_index = i if index == i + 1 else i + 1
                    is_left = sibling_index < index
                    proof.append((tx_hashes[sibling_index], is_left))
                    
                    # Update index for the next level
                    index = i // 2
                
                combined = tx_hashes[i] + tx_hashes[i+1]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            
            tx_hashes = next_level
        
        return proof
    
    def encrypt_data(self, data, key):
        """Encrypt data using Fernet symmetric encryption"""
        if isinstance(key, str):
            # Convert string key to bytes
            key = key.encode()
        
        # Ensure the key is valid for Fernet (32 bytes, base64-encoded)
        if len(key) != 32:
            # Derive a proper key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'blockchain_salt',  # In production, use a unique salt
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key))
        else:
            key = base64.urlsafe_b64encode(key)
        
        f = Fernet(key)
        
        # Convert data to JSON string if it's not already a string
        if not isinstance(data, str):
            data = json.dumps(data)
        
        # Encrypt the data
        encrypted_data = f.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_data(self, encrypted_data, key):
        """Decrypt data using Fernet symmetric encryption"""
        if isinstance(key, str):
            key = key.encode()
        
        # Ensure the key is valid for Fernet
        if len(key) != 32:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'blockchain_salt',
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key))
        else:
            key = base64.urlsafe_b64encode(key)
        
        f = Fernet(key)
        
        # Decode the base64 encrypted data
        encrypted_data = base64.urlsafe_b64decode(encrypted_data)
        
        # Decrypt the data
        decrypted_data = f.decrypt(encrypted_data).decode()
        
        # Try to parse as JSON if possible
        try:
            return json.loads(decrypted_data)
        except json.JSONDecodeError:
            return decrypted_data
    
    def generate_secure_random(self, length=32):
        """Generate cryptographically secure random bytes"""
        return secrets.token_bytes(length)
    
    def hash_password(self, password, salt=None):
        """Hash a password with a salt using PBKDF2"""
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = kdf.derive(password.encode())
        return {
            'key': base64.b64encode(key).decode(),
            'salt': base64.b64encode(salt).decode()
        }
    
    def verify_password(self, password, hashed_password, salt):
        """Verify a password against its hash"""
        if isinstance(salt, str):
            salt = base64.b64decode(salt)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = kdf.derive(password.encode())
        expected_key = base64.b64decode(hashed_password)
        
        return key == expected_key