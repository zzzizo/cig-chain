import time
import hashlib
import json

class Block:
    def __init__(self, index, previous_hash, timestamp, data, nonce=0):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.nonce = nonce
        self.hash = self.calculate_hash()
        self.contract_results = {}  # Store results of smart contract executions
        self.signatures = {}  # For PoS and other signature-based consensus
        self.merkle_root = None  # For efficient transaction verification
    
    def calculate_hash(self):
        """Calculate the hash of the block"""
        block_string = json.dumps({
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": self.data,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        
        return hashlib.sha256(block_string).hexdigest()
    
    def mine_block(self, difficulty):
        """Mine a block with the given difficulty"""
        target = '0' * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        return self
    
    def to_dict(self):
        """Convert block to dictionary"""
        block_dict = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": self.data,
            "nonce": self.nonce,
            "hash": self.hash
        }
        
        # Add optional fields if they exist
        if self.contract_results:
            block_dict["contract_results"] = self.contract_results
        if self.signatures:
            block_dict["signatures"] = self.signatures
        if self.merkle_root:
            block_dict["merkle_root"] = self.merkle_root
            
        return block_dict
    
    def add_signature(self, validator_address, signature):
        """Add a validator's signature to the block"""
        self.signatures[validator_address] = signature
        return len(self.signatures)
    
    def has_signature_from(self, validator_address):
        """Check if the block has a signature from a specific validator"""
        return validator_address in self.signatures
    
    def calculate_merkle_root(self):
        """Calculate the Merkle root of transactions in the block"""
        if "transactions" not in self.data:
            return None
            
        transactions = self.data["transactions"]
        if not transactions:
            return None
            
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
        
        self.merkle_root = tx_hashes[0]
        return self.merkle_root
    
    def execute_smart_contracts(self, contract_engine):
        """Execute any smart contracts in the block's transactions"""
        if "transactions" not in self.data:
            return
            
        for tx_index, tx in enumerate(self.data["transactions"]):
            # Skip if not a contract transaction
            if not isinstance(tx, dict) or tx.get("type") != "contract":
                continue
                
            contract_id = tx.get("contract_id")
            method = tx.get("method")
            params = tx.get("params", {})
            sender = tx.get("from")
            
            if not contract_id or not method:
                continue
                
            # Execute the contract method
            result = contract_engine.execute(contract_id, method, params, sender)
            
            # Store the result
            tx_id = tx.get("id", f"tx_{tx_index}")
            self.contract_results[tx_id] = result
    
    def verify_transactions(self, transaction_validator):
        """Verify all transactions in the block"""
        if "transactions" not in self.data:
            return True
            
        for tx in self.data["transactions"]:
            if not transaction_validator.is_valid(tx):
                return False
                
        return True
    
    @staticmethod
    def from_dict(block_dict):
        """Create a Block instance from a dictionary"""
        block = Block(
            block_dict["index"],
            block_dict["previous_hash"],
            block_dict["timestamp"],
            block_dict["data"],
            block_dict["nonce"]
        )
        block.hash = block_dict["hash"]
        
        # Add optional fields if they exist in the dictionary
        if "contract_results" in block_dict:
            block.contract_results = block_dict["contract_results"]
        if "signatures" in block_dict:
            block.signatures = block_dict["signatures"]
        if "merkle_root" in block_dict:
            block.merkle_root = block_dict["merkle_root"]
            
        return block