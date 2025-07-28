from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
import json

# Connect to local Ethereum node
w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

# Add POA middleware (for networks like Ganache)
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Check connection
if not w3.is_connected():
    print("Failed to connect to Ethereum node")
    exit(1)

# Admin account (needs to have sufficient balance and private key)
admin_address = w3.to_checksum_address("0xFE3B557E8Fb62b89F4916B721be55cEb828dBd73")
# You need the private key for the admin account to sign transactions
admin_private_key = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"  # Replace with actual private key

with open("participants.json", "r") as f:
    accounts = json.load(f)

# Extract buyer and seller addresses from participants.json
buyers = [acc["address"] for acc in accounts if acc["role"] == "buyer"]
sellers = [acc["address"] for acc in accounts if acc["role"] == "seller"]

# Amount of ETH to send to each participant
amount_in_eth = 1
amount_in_wei = w3.to_wei(amount_in_eth, 'ether')

# Check admin balance and compute required total
admin_balance = w3.eth.get_balance(admin_address)
required_total = amount_in_wei * (len(buyers) + len(sellers))
print(f"Admin balance: {w3.from_wei(admin_balance, 'ether')} ETH")
print(f"Required total: {w3.from_wei(required_total, 'ether')} ETH")

if admin_balance < required_total:
    print("Insufficient balance in admin account")
    exit(1)

# Fund each account
for acct in buyers + sellers:
    try:
        # Get current nonce
        nonce = w3.eth.get_transaction_count(admin_address)
        
        # Get current gas price
        gas_price = w3.eth.gas_price
        
        # Create transaction
        tx = {
            'from': admin_address,
            'to': w3.to_checksum_address(acct),
            'value': amount_in_wei,
            'gas': 21000,
            'gasPrice': gas_price,
            'nonce': nonce,
        }
        
        # Sign transaction
        signed_tx = w3.eth.account.sign_transaction(tx, admin_private_key)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for transaction receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"✅ Sent {amount_in_eth} ETH to {acct}")
        print(f"   Tx Hash: {tx_hash.hex()}")
        print(f"   Gas used: {receipt.gasUsed}")
        print(f"   Block: {receipt.blockNumber}")
        print()
        
    except Exception as e:
        print(f"❌ Failed to send ETH to {acct}: {str(e)}")

print("Funding complete!")

# Verify balances
print("\n--- Final Balances ---")
for acct in buyers + sellers:
    balance = w3.eth.get_balance(w3.to_checksum_address(acct))
    print(f"{acct}: {w3.from_wei(balance, 'ether')} ETH")