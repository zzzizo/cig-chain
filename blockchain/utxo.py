import hashlib
import json

class UTXO:
    def __init__(self, tx_id, output_index, amount, owner):
        self.tx_id = tx_id
        self.output_index = output_index
        self.amount = amount
        self.owner = owner
        self.is_spent = False
    
    def to_dict(self):
        return {
            "tx_id": self.tx_id,
            "output_index": self.output_index,
            "amount": self.amount,
            "owner": self.owner,
            "is_spent": self.is_spent
        }
    
    @classmethod
    def from_dict(cls, data):
        utxo = cls(
            data["tx_id"],
            data["output_index"],
            data["amount"],
            data["owner"]
        )
        utxo.is_spent = data["is_spent"]
        return utxo

class UTXOSet:
    def __init__(self):
        self.utxos = {}  # tx_id:output_index -> UTXO
    
    def add_utxo(self, utxo):
        key = f"{utxo.tx_id}:{utxo.output_index}"
        self.utxos[key] = utxo
    
    def get_utxo(self, tx_id, output_index):
        key = f"{tx_id}:{output_index}"
        return self.utxos.get(key)
    
    def spend_utxo(self, tx_id, output_index):
        key = f"{tx_id}:{output_index}"
        if key in self.utxos:
            self.utxos[key].is_spent = True
            return True
        return False
    
    def get_utxos_for_address(self, address):
        return [utxo for utxo in self.utxos.values() 
                if utxo.owner == address and not utxo.is_spent]
    
    def get_balance(self, address):
        utxos = self.get_utxos_for_address(address)
        return sum(utxo.amount for utxo in utxos)
    
    def to_dict(self):
        return {key: utxo.to_dict() for key, utxo in self.utxos.items()}
    
    @classmethod
    def from_dict(cls, data):
        utxo_set = cls()
        for key, utxo_data in data.items():
            utxo = UTXO.from_dict(utxo_data)
            utxo_set.utxos[key] = utxo
        return utxo_set