from web3 import Web3
import json

# === CONFIG ===
WEB3_PROVIDER = "http://localhost:8545"
CHAIN_ID = 1981  # Match your Besu chain ID

# === Updated Deployed Addresses ===
TOKENIZED_CASH = "0x0f908B9E910492958c6EaA269002AAf6Ae8F11bF"
TOKENIZED_SEC = "0x91810eaDF2d75b4422b39d80Bc81f0AB09B44356"

ABI_CASH_PATH = "../smart-contracts/artifacts/contracts/TokenizedCash.sol/TokenizedCash.json"
ABI_SEC_PATH = "../smart-contracts/artifacts/contracts/TokenizedSecurity.sol/TokenizedSecurity.json"

# === Participants ===
accounts = [
    {"role": "buyer", "address": "0x59b5D0A361b6Cd8Cc22e21bE74f2Dc387f75E9A6"},
    {"role": "buyer", "address": "0xd9f64a61E2F822B6aF88ffb34C436D9A600A2De9"},
    {"role": "seller", "address": "0xA5F05C523aF62ea507a90E78605e2a1796B2c801"},
    {"role": "seller", "address": "0x264B3334C9e6997534ccd403099eD8BFC43fb3F9"},
]

# === Admin ===
ADMIN_PRIVATE_KEY = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113b37c6d3d8b3f0f10c5c8cefb"
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))
ADMIN_ADDRESS = w3.eth.account.from_key(ADMIN_PRIVATE_KEY).address

# === Load ABIs ===
with open(ABI_CASH_PATH) as f:
    abi_cash = json.load(f)["abi"]
with open(ABI_SEC_PATH) as f:
    abi_sec = json.load(f)["abi"]

cash_token = w3.eth.contract(address=TOKENIZED_CASH, abi=abi_cash)
sec_token = w3.eth.contract(address=TOKENIZED_SEC, abi=abi_sec)

# === Utility: Send TX ===
def send_tx(fn, nonce):
    tx = fn.build_transaction({
        "from": ADMIN_ADDRESS,
        "nonce": nonce,
        "gas": 200000,
        "gasPrice": 0,
        "chainId": CHAIN_ID,
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=ADMIN_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash)

# === Step 1: Check Admin Balances ===
admin_cash = cash_token.functions.balanceOf(ADMIN_ADDRESS).call()
admin_sec = sec_token.functions.balanceOf(ADMIN_ADDRESS).call()
print("🧮 Admin Balances:")
print("   TCASH:", w3.from_wei(admin_cash, 'ether'))
print("   TSEC: ", w3.from_wei(admin_sec, 'ether'))

# === Step 2: Funding ===
print("🚀 Starting funding process...")
nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)

amount_cash = w3.to_wei(1000, "ether")
amount_sec = w3.to_wei(100, "ether")

for acc in accounts:
    addr = Web3.to_checksum_address(acc["address"])
    role = acc["role"]

    if role == "buyer":
        print(f"💸 Sending $1000 to buyer {addr}...")
        receipt = send_tx(cash_token.functions.transfer(addr, amount_cash), nonce)
    elif role == "seller":
        print(f"📈 Minting 100 sec tokens to seller {addr}...")
        receipt = send_tx(sec_token.functions.mint(addr, amount_sec), nonce)

    print(f"✅ Confirmed in block {receipt.blockNumber}")
    nonce += 1

# === Step 3: Check Final Balances ===
print("\n🔍 Checking final balances...")
for acc in accounts:
    addr = Web3.to_checksum_address(acc["address"])
    bal_cash = cash_token.functions.balanceOf(addr).call()
    bal_sec = sec_token.functions.balanceOf(addr).call()
    print(f"🔎 Balance of {addr}: ${w3.from_wei(bal_cash, 'ether')} TCASH, 🎯 {w3.from_wei(bal_sec, 'ether')} TSEC")

print("✅ All accounts funded successfully.")
