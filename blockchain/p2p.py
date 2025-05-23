import socket
import threading
import json
import time
from .blockchain import Blockchain

class P2PServer:
    def __init__(self, host='0.0.0.0', port=5000, blockchain=None):
        self.host = host
        self.port = port
        self.blockchain = blockchain or Blockchain()
        self.peers = set()
        self.server_socket = None
    
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        print(f"P2P Server started on {self.host}:{self.port}")
        
        # Start listening for connections in a separate thread
        threading.Thread(target=self.listen_for_connections, daemon=True).start()
    
    def listen_for_connections(self):
        while True:
            client, address = self.server_socket.accept()
            print(f"New connection from {address[0]}:{address[1]}")
            
            # Handle client in a new thread
            threading.Thread(target=self.handle_client, args=(client, address), daemon=True).start()
    
    def handle_client(self, client_socket, address):
        peer_address = f"{address[0]}:{address[1]}"
        self.peers.add(peer_address)
        
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                message = json.loads(data.decode('utf-8'))
                self.handle_message(message, client_socket)
        except Exception as e:
            print(f"Error handling client {peer_address}: {e}")
        finally:
            client_socket.close()
            if peer_address in self.peers:
                self.peers.remove(peer_address)
    
    def handle_message(self, message, client_socket):
        message_type = message.get('type')
        
        if message_type == 'get_blockchain':
            # Send the entire blockchain
            response = {
                'type': 'blockchain',
                'data': self.blockchain.to_json()
            }
            client_socket.send(json.dumps(response).encode('utf-8'))
        
        elif message_type == 'blockchain':
            # Received a blockchain, validate and potentially replace ours
            received_chain = Blockchain.from_json(message['data'])
            
            # Simple validation: longer chain wins
            if len(received_chain.chain) > len(self.blockchain.chain) and received_chain.is_chain_valid():
                print("Received a longer valid blockchain. Replacing our chain.")
                self.blockchain = received_chain
        
        elif message_type == 'new_transaction':
            # Add the transaction to our pending transactions
            transaction = message['data']
            self.blockchain.create_transaction(transaction)
            print("Added new transaction to pending transactions")
        
        elif message_type == 'new_block':
            # Validate and potentially add the new block
            # This would require more complex logic in a real implementation
            print("Received new block notification")
            # Request the latest blockchain to compare
            self.request_blockchain(client_socket)
    
    def broadcast(self, message):
        for peer in self.peers:
            try:
                host, port = peer.split(':')
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect((host, int(port)))
                client.send(json.dumps(message).encode('utf-8'))
                client.close()
            except Exception as e:
                print(f"Failed to send to peer {peer}: {e}")
    
    def connect_to_peer(self, host, port):
        peer_address = f"{host}:{port}"
        if peer_address in self.peers:
            print(f"Already connected to {peer_address}")
            return
        
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((host, int(port)))
            self.peers.add(peer_address)
            
            # Request the blockchain from the new peer
            self.request_blockchain(client)
            client.close()
            
            print(f"Connected to peer {peer_address}")
        except Exception as e:
            print(f"Failed to connect to peer {host}:{port}: {e}")
    
    def request_blockchain(self, client_socket):
        message = {
            'type': 'get_blockchain'
        }
        client_socket.send(json.dumps(message).encode('utf-8'))
    
    def broadcast_transaction(self, transaction):
        message = {
            'type': 'new_transaction',
            'data': transaction
        }
        self.broadcast(message)
    
    def broadcast_new_block(self):
        message = {
            'type': 'new_block'
        }
        self.broadcast(message)
    
    def stop(self):
        if self.server_socket:
            self.server_socket.close()
            print("P2P Server stopped")