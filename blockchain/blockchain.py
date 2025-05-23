from .block import Block
import time
import json

class Blockchain:
    def __init__(self, difficulty=4):
        self.chain = []
        self.difficulty = difficulty
        self.pending_transactions = []
        self.mining_reward = 100
        self.create_genesis_block()
    
    def create_genesis_block(self):
        genesis_block = Block(0, "0", time.time(), {
            "transactions": [],
            "message": "Genesis Block"
        })
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
    
    def get_latest_block(self):
        return self.chain[-1]
    
    def mine_pending_transactions(self, mining_reward_address):
        # Create a new block with all pending transactions and mine it
        block = Block(
            len(self.chain),
            self.get_latest_block().hash,
            time.time(),
            {
                "transactions": self.pending_transactions,
            }
        )
        
        block.mine_block(self.difficulty)
        print("Block successfully mined!")
        self.chain.append(block)
        
        # Reset the pending transactions and send the mining reward
        self.pending_transactions = [
            {
                "from": "SYSTEM",
                "to": mining_reward_address,
                "amount": self.mining_reward
            }
        ]
    
    def create_transaction(self, transaction):
        self.pending_transactions.append(transaction)
    
    def get_balance(self, address):
        balance = 0
        
        for block in self.chain:
            if "transactions" in block.data:
                for transaction in block.data["transactions"]:
                    if transaction.get("to") == address:
                        balance += transaction.get("amount", 0)
                    if transaction.get("from") == address:
                        balance -= transaction.get("amount", 0)
        
        return balance
    
    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # Check if the current block's hash is valid
            if current_block.hash != current_block.calculate_hash():
                print("Current hash is invalid")
                return False
            
            # Check if the current block points to the correct previous hash
            if current_block.previous_hash != previous_block.hash:
                print("Previous hash reference is invalid")
                return False
        
        return True
    
    def to_json(self):
        blockchain_dict = {
            "chain": [block.to_dict() for block in self.chain],
            "difficulty": self.difficulty,
            "pending_transactions": self.pending_transactions,
            "mining_reward": self.mining_reward
        }
        return json.dumps(blockchain_dict, indent=4)
    
    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        blockchain = cls(difficulty=data["difficulty"])
        blockchain.chain = []
        
        for block_data in data["chain"]:
            block = Block(
                block_data["index"],
                block_data["previous_hash"],
                block_data["timestamp"],
                block_data["data"],
                block_data["nonce"]
            )
            block.hash = block_data["hash"]
            blockchain.chain.append(block)
        
        blockchain.pending_transactions = data["pending_transactions"]
        blockchain.mining_reward = data["mining_reward"]
        
        return blockchain