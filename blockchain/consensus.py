import random
import time
import hashlib

class ProofOfWork:
    @staticmethod
    def mine(block, difficulty):
        target = '0' * difficulty
        while block.hash[:difficulty] != target:
            block.nonce += 1
            block.hash = block.calculate_hash()
        return block

class ProofOfStake:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.validators = {}  # address -> stake amount
        self.last_block_time = time.time()
        self.min_stake = 10  # Minimum stake required to be a validator
    
    def register_validator(self, address, stake_amount):
        if stake_amount >= self.min_stake:
            self.validators[address] = stake_amount
            return True
        return False
    
    def remove_validator(self, address):
        if address in self.validators:
            del self.validators[address]
            return True
        return False
    
    def get_next_validator(self):
        if not self.validators:
            return None
        
        # Calculate time since last block
        current_time = time.time()
        time_diff = current_time - self.last_block_time
        
        # Calculate total stake
        total_stake = sum(self.validators.values())
        
        # Select validator based on stake weight and time elapsed
        # This is a simplified version of PoS
        validator_scores = {}
        for address, stake in self.validators.items():
            # Score is based on stake amount and a random factor influenced by time
            random.seed(f"{address}{current_time}")
            score = (stake / total_stake) * random.random() * time_diff
            validator_scores[address] = score
        
        # Select the validator with the highest score
        selected_validator = max(validator_scores.items(), key=lambda x: x[1])[0]
        
        # Update last block time
        self.last_block_time = current_time
        
        return selected_validator
    
    def validate_block(self, block, validator_address):
        # In a real PoS system, the validator would sign the block
        # Here we just check if they're a registered validator
        if validator_address not in self.validators:
            return False
        
        # Verify the block's hash
        if block.hash != block.calculate_hash():
            return False
        
        return True

class DelegatedProofOfStake:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.delegates = {}  # address -> votes
        self.active_delegates = []  # List of addresses of active delegates
        self.delegate_count = 21  # Number of active delegates
        self.round = 0
    
    def vote(self, voter_address, delegate_address, vote_weight):
        if delegate_address in self.delegates:
            self.delegates[delegate_address] += vote_weight
        else:
            self.delegates[delegate_address] = vote_weight
        
        # Update active delegates
        self._update_active_delegates()
    
    def _update_active_delegates(self):
        # Sort delegates by vote count and select the top ones
        sorted_delegates = sorted(self.delegates.items(), key=lambda x: x[1], reverse=True)
        self.active_delegates = [addr for addr, _ in sorted_delegates[:self.delegate_count]]
    
    def get_next_delegate(self):
        if not self.active_delegates:
            return None
        
        # Round-robin selection of delegates
        delegate = self.active_delegates[self.round % len(self.active_delegates)]
        self.round += 1
        
        return delegate
    
    def validate_block(self, block, delegate_address):
        # Check if the delegate is active
        if delegate_address not in self.active_delegates:
            return False
        
        # Verify the block's hash
        if block.hash != block.calculate_hash():
            return False
        
        return True

class PracticalByzantineFaultTolerance:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.validators = set()  # Set of validator addresses
        self.min_validators = 4  # Minimum number of validators required
        self.current_view = 0  # Current view number
        self.primary = None  # Primary validator for the current view
        self.prepared_messages = {}  # Block hash -> set of validators who prepared
        self.committed_messages = {}  # Block hash -> set of validators who committed
    
    def add_validator(self, address):
        """Add a validator to the PBFT network"""
        self.validators.add(address)
        self._update_primary()
        return True
    
    def remove_validator(self, address):
        """Remove a validator from the PBFT network"""
        if address in self.validators:
            self.validators.remove(address)
            self._update_primary()
            return True
        return False
    
    def _update_primary(self):
        """Update the primary validator for the current view"""
        if not self.validators:
            self.primary = None
            return
        
        # Sort validators to ensure deterministic selection
        sorted_validators = sorted(list(self.validators))
        self.primary = sorted_validators[self.current_view % len(sorted_validators)]
    
    def change_view(self):
        """Change to the next view (used when primary is suspected to be faulty)"""
        self.current_view += 1
        self._update_primary()
        # Clear prepared and committed messages for the new view
        self.prepared_messages = {}
        self.committed_messages = {}
    
    def pre_prepare(self, block, validator_address):
        """Primary broadcasts a pre-prepare message"""
        if validator_address != self.primary:
            return False, "Only the primary can pre-prepare"
        
        if len(self.validators) < self.min_validators:
            return False, "Not enough validators"
        
        # In a real implementation, this would broadcast to all validators
        # For simplicity, we'll just return success
        return True, "Pre-prepare successful"
    
    def prepare(self, block_hash, validator_address):
        """Validator broadcasts a prepare message"""
        if validator_address not in self.validators:
            return False, "Not a validator"
        
        if block_hash not in self.prepared_messages:
            self.prepared_messages[block_hash] = set()
        
        self.prepared_messages[block_hash].add(validator_address)
        
        # Check if we have enough prepare messages (2f+1 where f is max faulty nodes)
        f = (len(self.validators) - 1) // 3
        if len(self.prepared_messages[block_hash]) >= 2*f + 1:
            return True, "Prepared"
        
        return True, "Prepare recorded"
    
    def commit(self, block_hash, validator_address):
        """Validator broadcasts a commit message"""
        if validator_address not in self.validators:
            return False, "Not a validator"
        
        # Check if we have enough prepare messages first
        f = (len(self.validators) - 1) // 3
        if block_hash not in self.prepared_messages or len(self.prepared_messages[block_hash]) < 2*f + 1:
            return False, "Not prepared yet"
        
        if block_hash not in self.committed_messages:
            self.committed_messages[block_hash] = set()
        
        self.committed_messages[block_hash].add(validator_address)
        
        # Check if we have enough commit messages
        if len(self.committed_messages[block_hash]) >= 2*f + 1:
            return True, "Committed"
        
        return True, "Commit recorded"
    
    def is_committed(self, block_hash):
        """Check if a block is committed"""
        f = (len(self.validators) - 1) // 3
        return (block_hash in self.committed_messages and 
                len(self.committed_messages[block_hash]) >= 2*f + 1)
    
    def validate_block(self, block, validator_address):
        """Validate a block in the PBFT system"""
        # For a block to be valid in PBFT, it must be committed
        return self.is_committed(block.hash)

class ProofOfAuthority:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.authorities = set()  # Set of authorized validator addresses
        self.block_time = 15  # Seconds between blocks
        self.last_block_time = time.time()
        self.current_authority_index = 0
    
    def add_authority(self, address):
        """Add an authority to the network"""
        self.authorities.add(address)
        return True
    
    def remove_authority(self, address):
        """Remove an authority from the network"""
        if address in self.authorities:
            self.authorities.remove(address)
            return True
        return False
    
    def get_next_authority(self):
        """Get the next authority in round-robin fashion"""
        if not self.authorities:
            return None
        
        # Check if enough time has passed since the last block
        current_time = time.time()
        if current_time - self.last_block_time < self.block_time:
            return None
        
        # Get authorities in a deterministic order
        sorted_authorities = sorted(list(self.authorities))
        
        # Select the next authority in round-robin fashion
        authority = sorted_authorities[self.current_authority_index % len(sorted_authorities)]
        self.current_authority_index += 1
        
        # Update last block time
        self.last_block_time = current_time
        
        return authority
    
    def validate_block(self, block, authority_address):
        """Validate a block in the PoA system"""
        # Check if the authority is registered
        if authority_address not in self.authorities:
            return False
        
        # Verify the block's hash
        if block.hash != block.calculate_hash():
            return False
        
        return True
class ProofOfBurn:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.burn_addresses = {}  # address -> amount burned
        self.min_burn_amount = 10  # Minimum amount required to participate
        self.burn_decay_factor = 0.9  # Decay factor for burned coins (simulates coin aging)
        self.last_update_time = time.time()
    
    def burn_coins(self, address, amount):
        """Record coins as burned by sending to an unspendable address"""
        if amount < self.min_burn_amount:
            return False, "Burn amount too small"
        
        # Update existing burns with decay
        self._apply_decay()
        
        # Add new burn amount
        if address in self.burn_addresses:
            self.burn_addresses[address] += amount
        else:
            self.burn_addresses[address] = amount
        
        return True, f"Burned {amount} coins"
    
    def _apply_decay(self):
        """Apply decay to burned coins to simulate coin aging"""
        current_time = time.time()
        time_diff_days = (current_time - self.last_update_time) / (24 * 3600)  # Convert to days
        
        if time_diff_days > 0:
            decay_factor = self.burn_decay_factor ** time_diff_days
            for address in self.burn_addresses:
                self.burn_addresses[address] *= decay_factor
            
            self.last_update_time = current_time
    
    def get_next_validator(self):
        """Select the next validator based on burned coins"""
        if not self.burn_addresses:
            return None
        
        # Apply decay to burned coins
        self._apply_decay()
        
        # Calculate total burned coins
        total_burned = sum(self.burn_addresses.values())
        
        # Select validator based on burn weight
        validator_scores = {}
        for address, burned in self.burn_addresses.items():
            # Score is based on burn amount and a random factor
            random.seed(f"{address}{time.time()}")
            score = (burned / total_burned) * random.random()
            validator_scores[address] = score
        
        # Select the validator with the highest score
        selected_validator = max(validator_scores.items(), key=lambda x: x[1])[0]
        
        return selected_validator
    
    def validate_block(self, block, validator_address):
        """Validate a block in the PoB system"""
        # Check if the validator has burned coins
        if validator_address not in self.burn_addresses:
            return False
        
        # Check if they've burned enough
        if self.burn_addresses[validator_address] < self.min_burn_amount:
            return False
        
        # Verify the block's hash
        if block.hash != block.calculate_hash():
            return False
        
        return True

class HybridConsensus:
    """A hybrid consensus mechanism that combines PoW and PoS"""
    def __init__(self, blockchain, pow_weight=0.3, pos_weight=0.7):
        self.blockchain = blockchain
        self.pow = ProofOfWork()
        self.pos = ProofOfStake(blockchain)
        self.pow_weight = pow_weight
        self.pos_weight = pos_weight
        self.difficulty = 2  # Lower difficulty for PoW component
    
    def register_validator(self, address, stake_amount):
        """Register a validator with stake"""
        return self.pos.register_validator(address, stake_amount)
    
    def get_next_validator(self):
        """Get the next validator using PoS"""
        return self.pos.get_next_validator()
    
    def mine_block(self, block, validator_address):
        """Mine a block using hybrid approach"""
        # First, partially mine with PoW (reduced difficulty)
        self.pow.mine(block, self.difficulty)
        
        # Then validate with PoS
        if not self.pos.validate_block(block, validator_address):
            return False
        
        return True
    
    def validate_block(self, block, validator_address):
        """Validate a block using hybrid approach"""
        # Check PoW component
        if block.hash[:self.difficulty] != '0' * self.difficulty:
            return False
        
        # Check PoS component
        if not self.pos.validate_block(block, validator_address):
            return False
        
        return True

class ShardingConsensus:
    """A consensus mechanism that supports sharding for scalability"""
    def __init__(self, blockchain, shard_count=4):
        self.blockchain = blockchain
        self.shard_count = shard_count
        self.shards = [{
            'validators': set(),
            'consensus': ProofOfStake(blockchain)
        } for _ in range(shard_count)]
        self.global_consensus = ProofOfStake(blockchain)  # For cross-shard transactions
        self.validator_to_shard = {}  # Maps validators to their assigned shards
    
    def assign_validator(self, address, stake_amount, shard_id=None):
        """Assign a validator to a shard"""
        # If shard_id is not specified, assign to the shard with fewest validators
        if shard_id is None:
            shard_sizes = [len(shard['validators']) for shard in self.shards]
            shard_id = shard_sizes.index(min(shard_sizes))
        
        # Ensure shard_id is valid
        if shard_id < 0 or shard_id >= self.shard_count:
            return False, f"Invalid shard ID. Must be between 0 and {self.shard_count-1}"
        
        # Register with the shard's consensus
        if self.shards[shard_id]['consensus'].register_validator(address, stake_amount):
            self.shards[shard_id]['validators'].add(address)
            self.validator_to_shard[address] = shard_id
            
            # Also register with global consensus for cross-shard transactions
            self.global_consensus.register_validator(address, stake_amount)
            
            return True, f"Validator assigned to shard {shard_id}"
        
        return False, "Failed to register validator"
    
    def get_shard_for_transaction(self, transaction):
        """Determine which shard should process a transaction"""
        # Simple sharding by address - in a real implementation, this would be more sophisticated
        if isinstance(transaction, dict):
            # Handle dict-style transactions
            if 'from' in transaction:
                address = transaction['from']
            elif 'to' in transaction:
                address = transaction['to']
            else:
                # Default to shard 0 if no address found
                return 0
        else:
            # Assume transaction object with sender/recipient
            try:
                address = transaction.sender or transaction.recipient
            except AttributeError:
                return 0
        
        # Hash the address to determine shard
        address_hash = int(hashlib.sha256(address.encode()).hexdigest(), 16)
        return address_hash % self.shard_count
    
    def get_next_validator(self, shard_id=None):
        """Get the next validator for a specific shard or for cross-shard consensus"""
        if shard_id is None:
            # For cross-shard transactions, use global consensus
            return self.global_consensus.get_next_validator()
        
        # Ensure shard_id is valid
        if shard_id < 0 or shard_id >= self.shard_count:
            return None
        
        # Get validator from the shard's consensus
        return self.shards[shard_id]['consensus'].get_next_validator()
    
    def validate_block(self, block, validator_address, shard_id=None):
        """Validate a block for a specific shard or for cross-shard consensus"""
        # Check if validator is assigned to the correct shard
        if validator_address in self.validator_to_shard:
            validator_shard = self.validator_to_shard[validator_address]
            
            if shard_id is not None and validator_shard != shard_id:
                return False, f"Validator not assigned to shard {shard_id}"
            
            # Use the appropriate consensus mechanism
            if shard_id is None:
                # Cross-shard block
                return self.global_consensus.validate_block(block, validator_address), "Validated with global consensus"
            else:
                # Shard-specific block
                return self.shards[shard_id]['consensus'].validate_block(block, validator_address), f"Validated for shard {shard_id}"
        
        return False, "Validator not registered"