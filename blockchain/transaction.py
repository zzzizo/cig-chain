import json
import binascii
import hashlib
import time
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

class TransactionInput:
    def __init__(self, tx_id, output_index, signature=None):
        self.tx_id = tx_id
        self.output_index = output_index
        self.signature = signature
    
    def to_dict(self):
        return {
            "tx_id": self.tx_id,
            "output_index": self.output_index,
            "signature": binascii.hexlify(self.signature).decode('ascii') if self.signature else None
        }
    
    @classmethod
    def from_dict(cls, data):
        tx_input = cls(data["tx_id"], data["output_index"])
        if data["signature"]:
            tx_input.signature = binascii.unhexlify(data["signature"])
        return tx_input

class TransactionOutput:
    def __init__(self, amount, recipient_address):
        self.amount = amount
        self.recipient_address = recipient_address
    
    def to_dict(self):
        return {
            "amount": self.amount,
            "recipient_address": self.recipient_address
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(data["amount"], data["recipient_address"])

class Transaction:
    def __init__(self):
        self.id = None
        self.inputs = []
        self.outputs = []
        self.timestamp = time.time()
        self.type = "regular"  # regular, coinbase, contract
        self.contract_data = None
    
    def add_input(self, tx_id, output_index):
        self.inputs.append(TransactionInput(tx_id, output_index))
    
    def add_output(self, amount, recipient_address):
        self.outputs.append(TransactionOutput(amount, recipient_address))
    
    def calculate_hash(self):
        tx_dict = {
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
            "timestamp": self.timestamp,
            "type": self.type
        }
        
        if self.contract_data:
            tx_dict["contract_data"] = self.contract_data
            
        tx_string = json.dumps(tx_dict, sort_keys=True).encode()
        return hashlib.sha256(tx_string).hexdigest()
    
    def sign_input(self, input_index, private_key, utxo_set):
        # Get the UTXO being spent
        tx_input = self.inputs[input_index]
        utxo = utxo_set.get_utxo(tx_input.tx_id, tx_input.output_index)
        
        if not utxo:
            return False
        
        # Create a simplified version of the transaction for signing
        # This prevents transaction malleability
        tx_to_sign = {
            "tx_id": self.calculate_hash(),
            "input_index": input_index,
            "utxo_owner": utxo.owner,
            "outputs": [out.to_dict() for out in self.outputs]
        }
        
        tx_string = json.dumps(tx_to_sign, sort_keys=True).encode()
        
        # Sign the transaction
        signature = private_key.sign(
            tx_string,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Store the signature
        self.inputs[input_index].signature = signature
        return True
    
    def is_valid(self, utxo_set, public_key_provider):
        # Coinbase transactions are always valid
        if self.type == "coinbase":
            return True
        
        # Check if transaction has inputs and outputs
        if not self.inputs or not self.outputs:
            return False
        
        # Calculate the input amount
        input_amount = 0
        for i, tx_input in enumerate(self.inputs):
            # Get the UTXO being spent
            utxo = utxo_set.get_utxo(tx_input.tx_id, tx_input.output_index)
            
            if not utxo or utxo.is_spent:
                return False
            
            # Get the public key for the UTXO owner
            public_key = public_key_provider(utxo.owner)
            if not public_key:
                return False
            
            # Create the same transaction data that was signed
            tx_to_verify = {
                "tx_id": self.calculate_hash(),
                "input_index": i,
                "utxo_owner": utxo.owner,
                "outputs": [out.to_dict() for out in self.outputs]
            }
            
            tx_string = json.dumps(tx_to_verify, sort_keys=True).encode()
            
            # Verify the signature
            try:
                public_key.verify(
                    tx_input.signature,
                    tx_string,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
            except Exception:
                return False
            
            input_amount += utxo.amount
        
        # Calculate the output amount
        output_amount = sum(output.amount for output in self.outputs)
        
        # Check that input amount >= output amount
        if input_amount < output_amount:
            return False
        
        return True
    
    def to_dict(self):
        if not self.id:
            self.id = self.calculate_hash()
            
        return {
            "id": self.id,
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
            "timestamp": self.timestamp,
            "type": self.type,
            "contract_data": self.contract_data
        }
    
    @classmethod
    def from_dict(cls, data):
        tx = cls()
        tx.id = data["id"]
        tx.inputs = [TransactionInput.from_dict(inp) for inp in data["inputs"]]
        tx.outputs = [TransactionOutput.from_dict(out) for out in data["outputs"]]
        tx.timestamp = data["timestamp"]
        tx.type = data["type"]
        tx.contract_data = data.get("contract_data")
        return tx
    
    @classmethod
    def create_coinbase(cls, amount, miner_address):
        tx = cls()
        tx.type = "coinbase"
        tx.add_output(amount, miner_address)
        tx.id = tx.calculate_hash()
        return tx
    
    @classmethod
    def create_contract_transaction(cls, contract_data, sender_address, utxo_set, fee=1):
        tx = cls()
        tx.type = "contract"
        tx.contract_data = contract_data
        
        # Add fee output
        if fee > 0:
            tx.add_output(fee, "MINERS")
        
        # Find UTXOs to cover the fee
        utxos = utxo_set.get_utxos_for_address(sender_address)
        total_input = 0
        
        for utxo in utxos:
            if total_input >= fee:
                break
                
            tx.add_input(utxo.tx_id, utxo.output_index)
            total_input += utxo.amount
        
        # Add change output if necessary
        if total_input > fee:
            tx.add_output(total_input - fee, sender_address)
        
        tx.id = tx.calculate_hash()
        return tx