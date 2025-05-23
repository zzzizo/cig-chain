import argparse
import os
import json
from blockchain import Blockchain, Wallet, Transaction, P2PServer

def create_wallet(args):
    wallet = Wallet()
    wallet_file = args.output or "wallet.dat"
    wallet.save_to_file(wallet_file)
    print(f"New wallet created with address: {wallet.address}")
    print(f"Private key saved to {wallet_file}")

def get_balance(args):
    blockchain = load_blockchain()
    balance = blockchain.get_balance(args.address)
    print(f"Balance for {args.address}: {balance}")

def send_transaction(args):
    blockchain = load_blockchain()
    
    # Load wallet
    try:
        wallet = Wallet.load_from_file(args.wallet)
    except Exception as e:
        print(f"Error loading wallet: {e}")
        return
    
    # Create and sign transaction
    transaction = {
        "from": wallet.address,
        "to": args.to,
        "amount": args.amount
    }
    
    signature = wallet.sign_transaction(transaction)
    transaction["signature"] = signature
    
    # Add to blockchain
    blockchain.create_transaction(transaction)
    save_blockchain(blockchain)
    
    # Broadcast if P2P is enabled
    if args.broadcast:
        server = P2PServer(blockchain=blockchain)
        server.broadcast_transaction(transaction)
    
    print(f"Transaction of {args.amount} sent from {wallet.address} to {args.to}")

def mine_block(args):
    blockchain = load_blockchain()
    
    if not args.reward_address:
        print("Error: Mining reward address is required")
        return
    
    print("Mining block...")
    blockchain.mine_pending_transactions(args.reward_address)
    save_blockchain(blockchain)
    
    # Broadcast if P2P is enabled
    if args.broadcast:
        server = P2PServer(blockchain=blockchain)
        server.broadcast_new_block()
    
    print(f"Block mined and added to the blockchain")
    print(f"Mining reward sent to {args.reward_address}")

def start_node(args):
    blockchain = load_blockchain()
    server = P2PServer(port=args.port, blockchain=blockchain)
    server.start()
    
    if args.connect:
        for peer in args.connect:
            host, port = peer.split(':')
            server.connect_to_peer(host, int(port))
    
    print("Node started. Press Ctrl+C to stop.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.stop()
        save_blockchain(server.blockchain)
        print("Node stopped. Blockchain saved.")

def show_blockchain(args):
    blockchain = load_blockchain()
    if args.json:
        print(blockchain.to_json())
    else:
        print(f"Blockchain with {len(blockchain.chain)} blocks:")
        for i, block in enumerate(blockchain.chain):
            print(f"Block #{i}: {block.hash}")
            print(f"  Timestamp: {block.timestamp}")
            print(f"  Transactions: {len(block.data.get('transactions', []))}")
            print(f"  Nonce: {block.nonce}")
            print()

def load_blockchain():
    blockchain_file = "blockchain.json"
    if os.path.exists(blockchain_file):
        try:
            with open(blockchain_file, 'r') as f:
                return Blockchain.from_json(f.read())
        except Exception as e:
            print(f"Error loading blockchain: {e}")
            return Blockchain()
    return Blockchain()

def save_blockchain(blockchain):
    with open("blockchain.json", 'w') as f:
        f.write(blockchain.to_json())

def main():
    parser = argparse.ArgumentParser(description="CIG Chain - A Simple Blockchain Implementation")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Create wallet command
    wallet_parser = subparsers.add_parser("create-wallet", help="Create a new wallet")
    wallet_parser.add_argument("-o", "--output", help="Output file for the wallet")
    
    # Get balance command
    balance_parser = subparsers.add_parser("balance", help="Get balance for an address")
    balance_parser.add_argument("address", help="Wallet address to check")
    
    # Send transaction command
    send_parser = subparsers.add_parser("send", help="Send coins to an address")
    send_parser.add_argument("--wallet", required=True, help="Wallet file to use")
    send_parser.add_argument("--to", required=True, help="Recipient address")
    send_parser.add_argument("--amount", required=True, type=float, help="Amount to send")
    send_parser.add_argument("--broadcast", action="store_true", help="Broadcast transaction to network")
    
    # Mine block command
    mine_parser = subparsers.add_parser("mine", help="Mine a new block")
    mine_parser.add_argument("--reward-address", required=True, help="Address to receive mining reward")
    mine_parser.add_argument("--broadcast", action="store_true", help="Broadcast new block to network")
    
    # Start node command
    node_parser = subparsers.add_parser("start-node", help="Start a blockchain node")
    node_parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    node_parser.add_argument("--connect", nargs="+", help="Connect to peers (format: host:port)")
    
    # Show blockchain command
    show_parser = subparsers.add_parser("show", help="Show the blockchain")
    show_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    if args.command == "create-wallet":
        create_wallet(args)
    elif args.command == "balance":
        get_balance(args)
    elif args.command == "send":
        send_transaction(args)
    elif args.command == "mine":
        mine_block(args)
    elif args.command == "start-node":
        start_node(args)
    elif args.command == "show":
        show_blockchain(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()