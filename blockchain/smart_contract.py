import hashlib
import json
import time
import inspect

class SmartContractEngine:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.contracts = {}
        self.contract_states = {}
    
    def deploy_contract(self, code, owner, init_params=None):
        # Generate a unique contract ID
        contract_id = hashlib.sha256(f"{code}{owner}{time.time()}".encode()).hexdigest()[:16]
        
        try:
            # Compile the contract code (in a real system, this would be more sophisticated)
            contract_namespace = {}
            exec(code, contract_namespace)
            
            # Get the contract class - assuming the code defines a class that inherits from SmartContract
            contract_class = None
            for item in contract_namespace.values():
                if inspect.isclass(item) and issubclass(item, SmartContract) and item != SmartContract:
                    contract_class = item
                    break
            
            if not contract_class:
                raise ValueError("No valid smart contract class found in code")
            
            # Initialize the contract
            contract_instance = contract_class()
            contract_instance.contract_id = contract_id
            contract_instance.owner = owner
            
            # Store the contract
            self.contracts[contract_id] = contract_instance
            self.contract_states[contract_id] = {}
            
            # Call init method if it exists and params are provided
            if init_params and hasattr(contract_instance, 'init'):
                contract_instance.init(init_params)
            
            return contract_id
        except Exception as e:
            print(f"Error deploying contract: {e}")
            return None
    
    def execute(self, contract_id, method_name, params=None):
        if contract_id not in self.contracts:
            return {"error": "Contract not found"}
        
        contract = self.contracts[contract_id]
        
        if not hasattr(contract, method_name):
            return {"error": f"Method {method_name} not found in contract"}
        
        try:
            # Set the current state for the contract
            contract.state = self.contract_states.get(contract_id, {})
            
            # Execute the method
            method = getattr(contract, method_name)
            result = method(params or {})
            
            # Save the updated state
            self.contract_states[contract_id] = contract.state
            
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}
    
    def get_contract_state(self, contract_id):
        return self.contract_states.get(contract_id, {})

class SmartContract:
    """Base class for all smart contracts"""
    def __init__(self):
        self.contract_id = None
        self.owner = None
        self.state = {}
    
    def require(self, condition, message="Condition not met"):
        if not condition:
            raise Exception(message)
    
    def require_owner(self):
        self.require(self.sender == self.owner, "Only the owner can call this method")
    
    def set_state(self, key, value):
        self.state[key] = value
    
    def get_state(self, key, default=None):
        return self.state.get(key, default)

# Example smart contract
class TokenContract(SmartContract):
    def init(self, params):
        self.set_state("name", params.get("name", "Token"))
        self.set_state("symbol", params.get("symbol", "TKN"))
        self.set_state("total_supply", params.get("total_supply", 1000000))
        self.set_state("balances", {self.owner: self.get_state("total_supply")})
    
    def transfer(self, params):
        sender = params.get("from", self.owner)
        to = params.get("to")
        amount = params.get("amount")
        
        self.require(to, "Recipient address is required")
        self.require(amount > 0, "Amount must be greater than 0")
        
        balances = self.get_state("balances", {})
        sender_balance = balances.get(sender, 0)
        
        self.require(sender_balance >= amount, "Insufficient balance")
        
        # Update balances
        balances[sender] = sender_balance - amount
        balances[to] = balances.get(to, 0) + amount
        self.set_state("balances", balances)
        
        return {"from": sender, "to": to, "amount": amount}
    
    def balance_of(self, params):
        address = params.get("address")
        self.require(address, "Address is required")
        
        balances = self.get_state("balances", {})
        return {"address": address, "balance": balances.get(address, 0)}