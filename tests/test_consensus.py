import sys
import os
import time
import random

# Add the parent directory to the path so we can import the blockchain modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.consensus import (
    ProofOfWork, 
    ProofOfStake, 
    DelegatedProofOfStake, 
    PracticalByzantineFaultTolerance,
    ProofOfAuthority,
    ProofOfBurn,
    HybridConsensus,
    ShardingConsensus
)
from blockchain.block import Block

# Mock blockchain for testing
class MockBlockchain:
    def __init__(self):
        self.chain = []

def test_proof_of_work():
    print("\n=== Testing Proof of Work ===")
    pow_consensus = ProofOfWork()
    
    # Create a test block
    block = Block(1, "previous_hash", time.time(), {"data": "test"})
    
    # Mine the block
    print(f"Mining block with difficulty 3...")
    start_time = time.time()
    pow_consensus.mine(block, 3)
    end_time = time.time()
    
    print(f"Block mined in {end_time - start_time:.2f} seconds")
    print(f"Block hash: {block.hash}")
    print(f"Block nonce: {block.nonce}")
    
    # Verify the block meets the difficulty requirement
    assert block.hash.startswith('000'), "Block hash should start with '000'"
    print("✓ Block hash meets difficulty requirement")

def test_proof_of_stake():
    print("\n=== Testing Proof of Stake ===")
    blockchain = MockBlockchain()
    pos_consensus = ProofOfStake(blockchain)
    
    # Register validators with different stake amounts
    validators = {
        "validator1": 100,
        "validator2": 200,
        "validator3": 50,
        "validator4": 150
    }
    
    for address, stake in validators.items():
        result = pos_consensus.register_validator(address, stake)
        print(f"Registered {address} with stake {stake}: {result}")
    
    # Test getting next validator multiple times
    print("\nSelecting validators:")
    validator_counts = {addr: 0 for addr in validators}
    
    for i in range(100):
        next_validator = pos_consensus.get_next_validator()
        validator_counts[next_validator] += 1
        # Add a small delay to change the time factor
        time.sleep(0.01)
    
    print("Validator selection distribution over 100 rounds:")
    for validator, count in validator_counts.items():
        stake = validators[validator]
        print(f"{validator} (stake: {stake}): selected {count} times")
    
    # Test block validation
    block = Block(1, "previous_hash", time.time(), {"data": "test"})
    block.hash = block.calculate_hash()
    
    # Valid validator
    valid = pos_consensus.validate_block(block, "validator1")
    print(f"\nValidation by registered validator: {valid}")
    
    # Invalid validator
    invalid = pos_consensus.validate_block(block, "unknown_validator")
    print(f"Validation by unregistered validator: {invalid}")

def test_delegated_proof_of_stake():
    print("\n=== Testing Delegated Proof of Stake ===")
    blockchain = MockBlockchain()
    dpos_consensus = DelegatedProofOfStake(blockchain)
    
    # Create some delegates
    delegates = ["delegate1", "delegate2", "delegate3", "delegate4", "delegate5"]
    
    # Vote for delegates with different weights
    print("Voting for delegates:")
    for i, delegate in enumerate(delegates):
        # Different voters vote with different weights
        for j in range(5):
            voter = f"voter{j}"
            weight = random.randint(1, 10) * (i + 1)
            dpos_consensus.vote(voter, delegate, weight)
            print(f"{voter} voted for {delegate} with weight {weight}")
    
    print("\nActive delegates:")
    for delegate in dpos_consensus.active_delegates:
        print(f"{delegate} - votes: {dpos_consensus.delegates[delegate]}")
    
    # Test round-robin selection
    print("\nDelegate selection (round-robin):")
    for i in range(10):
        next_delegate = dpos_consensus.get_next_delegate()
        print(f"Round {i+1}: {next_delegate}")
    
    # Test block validation
    block = Block(1, "previous_hash", time.time(), {"data": "test"})
    block.hash = block.calculate_hash()
    
    # Valid delegate
    if dpos_consensus.active_delegates:
        valid_delegate = dpos_consensus.active_delegates[0]
        valid = dpos_consensus.validate_block(block, valid_delegate)
        print(f"\nValidation by active delegate: {valid}")
    
    # Invalid delegate
    invalid = dpos_consensus.validate_block(block, "unknown_delegate")
    print(f"Validation by non-delegate: {invalid}")

def test_pbft():
    print("\n=== Testing Practical Byzantine Fault Tolerance ===")
    blockchain = MockBlockchain()
    pbft_consensus = PracticalByzantineFaultTolerance(blockchain)
    
    # Add validators
    validators = ["validator1", "validator2", "validator3", "validator4", "validator5", "validator6", "validator7"]
    for validator in validators:
        pbft_consensus.add_validator(validator)
    
    print(f"Added {len(validators)} validators")
    print(f"Primary validator: {pbft_consensus.primary}")
    
    # Create a test block
    block = Block(1, "previous_hash", time.time(), {"data": "test"})
    block.hash = block.calculate_hash()
    
    # Test pre-prepare phase
    success, message = pbft_consensus.pre_prepare(block, pbft_consensus.primary)
    print(f"Pre-prepare by primary: {success} - {message}")
    
    success, message = pbft_consensus.pre_prepare(block, "validator2")
    print(f"Pre-prepare by non-primary: {success} - {message}")
    
    # Test prepare phase
    print("\nPrepare phase:")
    for validator in validators:
        success, message = pbft_consensus.prepare(block.hash, validator)
        print(f"Prepare by {validator}: {success} - {message}")
    
    # Test commit phase
    print("\nCommit phase:")
    for validator in validators:
        success, message = pbft_consensus.commit(block.hash, validator)
        print(f"Commit by {validator}: {success} - {message}")
    
    # Check if block is committed
    is_committed = pbft_consensus.is_committed(block.hash)
    print(f"\nBlock committed: {is_committed}")
    
    # Test view change
    print("\nChanging view:")
    old_primary = pbft_consensus.primary
    pbft_consensus.change_view()
    print(f"Primary changed from {old_primary} to {pbft_consensus.primary}")

def test_proof_of_authority():
    print("\n=== Testing Proof of Authority ===")
    blockchain = MockBlockchain()
    poa_consensus = ProofOfAuthority(blockchain)
    
    # Add authorities
    authorities = ["authority1", "authority2", "authority3", "authority4"]
    for authority in authorities:
        poa_consensus.add_authority(authority)
    
    print(f"Added {len(authorities)} authorities")
    
    # Test getting next authority
    print("\nAuthority selection (round-robin with time delay):")
    
    # Override block time for testing
    poa_consensus.block_time = 0.1
    
    for i in range(10):
        next_authority = poa_consensus.get_next_authority()
        if next_authority:
            print(f"Round {i+1}: {next_authority}")
        else:
            print(f"Round {i+1}: None (waiting for block time)")
        time.sleep(0.15)  # Wait longer than block time
    
    # Test block validation
    block = Block(1, "previous_hash", time.time(), {"data": "test"})
    block.hash = block.calculate_hash()
    
    # Valid authority
    valid = poa_consensus.validate_block(block, "authority1")
    print(f"\nValidation by registered authority: {valid}")
    
    # Invalid authority
    invalid = poa_consensus.validate_block(block, "unknown_authority")
    print(f"Validation by unregistered authority: {invalid}")

def test_proof_of_burn():
    print("\n=== Testing Proof of Burn ===")
    blockchain = MockBlockchain()
    pob_consensus = ProofOfBurn(blockchain)
    
    # Burn coins for different addresses
    addresses = ["address1", "address2", "address3", "address4"]
    burn_amounts = [50, 100, 25, 75]
    
    print("Burning coins:")
    for address, amount in zip(addresses, burn_amounts):
        success, message = pob_consensus.burn_coins(address, amount)
        print(f"{address} burns {amount} coins: {success} - {message}")
    
    # Test getting next validator
    print("\nValidator selection based on burned coins:")
    validator_counts = {addr: 0 for addr in addresses}
    
    for i in range(100):
        next_validator = pob_consensus.get_next_validator()
        validator_counts[next_validator] += 1
        # Add a small delay to change the time factor
        time.sleep(0.01)
    
    print("Validator selection distribution over 100 rounds:")
    for validator, count in validator_counts.items():
        burn_amount = pob_consensus.burn_addresses[validator]
        print(f"{validator} (burned: {burn_amount:.2f}): selected {count} times")
    
    # Test decay over time
    print("\nTesting burn decay over time:")
    print("Initial burn amounts:")
    for address, amount in pob_consensus.burn_addresses.items():
        print(f"{address}: {amount:.2f}")
    
    # Simulate passage of time (10 days)
    pob_consensus.last_update_time -= 10 * 24 * 3600
    pob_consensus._apply_decay()
    
    print("\nBurn amounts after 10 days (with decay factor 0.9):")
    for address, amount in pob_consensus.burn_addresses.items():
        print(f"{address}: {amount:.2f}")

def test_hybrid_consensus():
    print("\n=== Testing Hybrid Consensus (PoW + PoS) ===")
    blockchain = MockBlockchain()
    hybrid_consensus = HybridConsensus(blockchain)
    
    # Register validators
    validators = {
        "validator1": 100,
        "validator2": 200,
        "validator3": 50
    }
    
    for address, stake in validators.items():
        result = hybrid_consensus.register_validator(address, stake)
        print(f"Registered {address} with stake {stake}: {result}")
    
    # Create a test block
    block = Block(1, "previous_hash", time.time(), {"data": "test"})
    
    # Get a validator
    validator = hybrid_consensus.get_next_validator()
    print(f"\nSelected validator: {validator}")
    
    # Mine the block with hybrid approach
    print(f"Mining block with hybrid approach...")
    start_time = time.time()
    success = hybrid_consensus.mine_block(block, validator)
    end_time = time.time()
    
    print(f"Block mined in {end_time - start_time:.2f} seconds")
    print(f"Block hash: {block.hash}")
    print(f"Mining success: {success}")
    
    # Validate the block
    valid = hybrid_consensus.validate_block(block, validator)
    print(f"Block validation: {valid}")

def test_sharding_consensus():
    print("\n=== Testing Sharding Consensus ===")
    blockchain = MockBlockchain()
    sharding_consensus = ShardingConsensus(blockchain, shard_count=3)
    
    # Assign validators to shards
    validators = [
        ("validator1", 100, 0),  # Explicit shard 0
        ("validator2", 150, 1),  # Explicit shard 1
        ("validator3", 200, 2),  # Explicit shard 2
        ("validator4", 120, None),  # Auto-assign
        ("validator5", 180, None),  # Auto-assign
        ("validator6", 90, None)    # Auto-assign
    ]
    
    print("Assigning validators to shards:")
    for validator, stake, shard_id in validators:
        success, message = sharding_consensus.assign_validator(validator, stake, shard_id)
        print(f"{validator} with stake {stake}: {message}")
    
    # Print validator distribution
    print("\nValidator distribution across shards:")
    for shard_id in range(sharding_consensus.shard_count):
        validators_in_shard = [v for v, s in sharding_consensus.validator_to_shard.items() if s == shard_id]
        print(f"Shard {shard_id}: {validators_in_shard}")
    
    # Test transaction sharding
    print("\nTransaction sharding:")
    test_transactions = [
        {"from": "user1", "to": "user2", "amount": 10},
        {"from": "user3", "to": "user4", "amount": 20},
        {"from": "user5", "to": "user6", "amount": 30}
    ]
    
    for tx in test_transactions:
        shard_id = sharding_consensus.get_shard_for_transaction(tx)
        print(f"Transaction {tx} assigned to shard {shard_id}")
    
    # Test getting validators for different shards
    print("\nSelecting validators for each shard:")
    for shard_id in range(sharding_consensus.shard_count):
        validator = sharding_consensus.get_next_validator(shard_id)
        print(f"Shard {shard_id} validator: {validator}")
    
    # Test cross-shard validator
    cross_shard_validator = sharding_consensus.get_next_validator()
    print(f"Cross-shard validator: {cross_shard_validator}")
    
    # Test block validation
    block = Block(1, "previous_hash", time.time(), {"data": "test"})
    block.hash = block.calculate_hash()
    
    print("\nBlock validation:")
    for validator, shard_id in sharding_consensus.validator_to_shard.items():
        # Test validation in correct shard
        success, message = sharding_consensus.validate_block(block, validator, shard_id)
        print(f"Validator {validator} in shard {shard_id}: {success} - {message}")
        
        # Test validation in wrong shard
        wrong_shard = (shard_id + 1) % sharding_consensus.shard_count
        success, message = sharding_consensus.validate_block(block, validator, wrong_shard)
        print(f"Validator {validator} in wrong shard {wrong_shard}: {success} - {message}")
        
        # Test cross-shard validation
        success, message = sharding_consensus.validate_block(block, validator, None)
        print(f"Validator {validator} for cross-shard: {success} - {message}")
        
        # Only test one validator for brevity
        break

if __name__ == "__main__":
    # Create tests directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    
    # Run all tests
    test_proof_of_work()
    test_proof_of_stake()
    test_delegated_proof_of_stake()
    test_pbft()
    test_proof_of_authority()
    test_proof_of_burn()
    test_hybrid_consensus()
    test_sharding_consensus()
    
    print("\nAll consensus tests completed!")