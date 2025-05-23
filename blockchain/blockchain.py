from .block import Block
from .utxo import UTXOSet, UTXO
from .transaction import Transaction
from .smart_contract import SmartContractEngine
from .consensus import ProofOfWork, ProofOfStake, DelegatedProofOfStake
import time
import json

class Blockchain:
    def __init__(self, consensus_type="pow", difficulty=4):
        self.chain = []
        self.difficulty = difficulty
        self.pending_transactions = []
        self.mining_reward = 100
        self.utxo_set = UTXOSet()
        self.contract_engine = SmartContractEngine(self)
        
        # Initialize consensus mechanism
        self.consensus_type = consensus_type
        if consensus_type == "pow":
            self.consensus = ProofOfWork()
        elif consensus_type == "pos":
            self.consensus = ProofOfStake(self)
        elif consensus_type == "dpos":
            self.consensus = DelegatedProofOfStake(self)
        else:
            raise ValueError(f"Unsupported consensus type: {consensus_type}")
        
        self.create_genesis_block()
    
    def create_genesis_block(self):
        genesis_block = Block(0, "0", time.time(), {
            "transactions": [],
            "message": "Genesis Block"
        })
        
        # For PoW, mine the genesis block
        if self.consensus_type == "pow":
            genesis_block.mine_block(self.difficulty)
        else:
            # For PoS/DPoS, just set a valid hash
            genesis_block.hash = genesis_block.calculate_hash()
        
        self.chain.append(genesis_block)
        
        # Create initial coin distribution in genesis block
        genesis_tx = Transaction.create_coinbase(1000000, "GENESIS_ADDRESS")
        
        # Add the genesis transaction to the UTXO set
        utxo = UTXO(genesis_tx.id, 0, 1000000, "GENESIS_ADDRESS")
        self.utxo_set.add_utxo(utxo)
    
    def get_latest_block(self):
        return self.chain[-1]
    
    def add_transaction(self, transaction):
        # Validate the transaction
        if not transaction.is_valid(self.utxo_set, self.get_public_key):
            return False
        
        # Add to pending transactions
        self.pending_transactions.append(transaction)
        return True
    
    def get_public_key(self, address):
        # In a real implementation, this would retrieve the public key for an address
        # This is a placeholder - would need to be implemented with a proper key store
        return None
    
    def process_block_transactions(self, block):
        if "transactions" not in block.data:
            return True
        
        for tx_data in block.data["transactions"]:
            # Convert dict to Transaction object if needed
            tx = tx_data if isinstance(tx_data, Transaction) else Transaction.from_dict(tx_data)
            
            # Skip validation for coinbase transactions
            if tx.type == "coinbase":
                # Create new UTXOs for the outputs
                for i, output in enumerate(tx.outputs):
                    utxo = UTXO(tx.id, i, output.amount, output.recipient_address)
                    self.utxo_set.add_utxo(utxo)
                continue
            
            # Validate the transaction
            if not tx.is_valid(self.utxo_set, self.get_public_key):
                return False
            
            # Mark inputs as spent
            for tx_input in tx.inputs:
                self.utxo_set.spend_utxo(tx_input.tx_id, tx_input.output_index)
            
            # Create new UTXOs for the outputs
            for i, output in enumerate(tx.outputs):
                utxo = UTXO(tx.id, i, output.amount, output.recipient_address)
                self.utxo_set.add_utxo(utxo)
            
            # Process smart contract transactions
            if tx.type == "contract" and tx.contract_data:
                contract_data = tx.contract_data
                if contract_data.get("action") == "deploy":
                    code = contract_data.get("code")
                    owner = contract_data.get("owner")
                    init_params = contract_data.get("init_params")
                    
                    self.contract_engine.deploy_contract(code, owner, init_params)
                
                elif contract_data.get("action") == "call":
                    contract_id = contract_data.get("contract_id")
                    method = contract_data.get("method")
                    params = contract_data.get("params")
                    
                    self.contract_engine.execute(contract_id, method, params)
        
        return True
    
    def mine_pending_transactions(self, miner_address):
        # Create a coinbase transaction for the mining reward
        coinbase_tx = Transaction.create_coinbase(self.mining_reward, miner_address)
        
        # Add the coinbase transaction to the beginning of the block
        block_transactions = [coinbase_tx]
        
        # Add pending transactions
        block_transactions.extend(self.pending_transactions)
        
        # Create a new block
        block = Block(
            len(self.chain),
            self.get_latest_block().hash,
            time.time(),
            {
                "transactions": [tx.to_dict() for tx in block_transactions],
            }
        )
        
        # Use the appropriate consensus mechanism to create/validate the block
        if self.consensus_type == "pow":
            # Mine the block with proof of work
            block.mine_block(self.difficulty)
        elif self.consensus_type == "pos":
            # For PoS, the miner must be a validator
            if not self.consensus.validate_block(block, miner_address):
                return False
            block.hash = block.calculate_hash()
        elif self.consensus_type == "dpos":
            # For DPoS, the miner must be the selected delegate
            if not self.consensus.validate_block(block, miner_address):
                return False
            block.hash = block.calculate_hash()
        
        # Process the transactions in the block
        if not self.process_block_transactions(block):
            return False
        
        # Execute any smart contracts in the block
        block.execute_smart_contracts(self.contract_engine)
        
        # Add the block to the chain
        self.chain.append(block)
        
        # Clear the pending transactions
        self.pending_transactions = []
        
        # Create a new transaction for the next mining reward
        reward_tx = {
            "from": "SYSTEM",
            "to": miner_address,
            "amount": self.mining_reward
        }
        self.create_transaction(reward_tx)
        
        return True
    
    def create_transaction(self, transaction):
        # If it's a dict, keep it as is for backward compatibility
        if isinstance(transaction, dict):
            self.pending_transactions.append(transaction)
        else:
            # If it's a Transaction object, add it
            self.pending_transactions.append(transaction)
    
    def get_balance(self, address):
        # Use UTXO model for balance calculation
        return self.utxo_set.get_balance(address)
    
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
            
            # Validate all transactions in the block
            if not self.process_block_transactions(current_block):
                print("Block contains invalid transactions")
                return False
        
        return True
    
    def to_json(self):
        blockchain_dict = {
            "chain": [block.to_dict() for block in self.chain],
            "difficulty": self.difficulty,
            "pending_transactions": [
                tx.to_dict() if hasattr(tx, 'to_dict') else tx 
                for tx in self.pending_transactions
            ],
            "mining_reward": self.mining_reward,
            "consensus_type": self.consensus_type,
            "utxo_set": self.utxo_set.to_dict()
        }
        return json.dumps(blockchain_dict, indent=4)
    
    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        blockchain = cls(
            consensus_type=data.get("consensus_type", "pow"),
            difficulty=data["difficulty"]
        )
        
        # Reconstruct the blockchain
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
            if "contract_results" in block_data:
                block.contract_results = block_data["contract_results"]
            blockchain.chain.append(block)
        
        # Reconstruct pending transactions
        blockchain.pending_transactions = []
        for tx_data in data["pending_transactions"]:
            # Handle both dict and Transaction objects
            if isinstance(tx_data, dict):
                if "type" in tx_data and tx_data["type"] in ["regular", "coinbase", "contract"]:
                    tx = Transaction.from_dict(tx_data)
                else:
                    tx = tx_data
            else:
                tx = tx_data
            blockchain.pending_transactions.append(tx)
        
        # Set mining reward
        blockchain.mining_reward = data["mining_reward"]
        
        # Reconstruct UTXO set
        if "utxo_set" in data:
            blockchain.utxo_set = UTXOSet.from_dict(data["utxo_set"])
        
        return blockchain