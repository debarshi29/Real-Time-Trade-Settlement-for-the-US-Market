import json
from web3 import Web3

# === CONFIG ===
WEB3_PROVIDER = "http://localhost:8545"
DEPLOYER = "0xFE3B557E8Fb62b89F4916B721be55cEb828dBd73"
DEPLOYER_KEY = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113b37b60f7fcd0a3e5b6a08c17"  # ⚠️ testnet only!
TOKENIZED_CASH = "0xa9ECbe3F9600f9bF3ec88a428387316714ac95a0"
TOKENIZED_SEC = "0x2114De86c8Ea1FD8144C2f1e1e94C74E498afB1b"

# === Web3 INIT ===
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# === Load ABIs ===
def load_abi(name):
    with open(f"../smart-contracts/artifacts/contracts/{name}.sol/{name}.json") as f:
        return json.load(f)["abi"]

abi_cash = load_abi("TokenizedCash")
abi_sec = load_abi("TokenizedSecurity")

cash = w3.eth.contract(address=TOKENIZED_CASH, abi=abi_cash)
sec = w3.eth.contract(address=TOKENIZED_SEC, abi=abi_sec)

# === Step 1: Generate Accounts ===
participants = []

for i in range(100):
    acct = w3.eth.account.create()
    participants.append({
        "role": "buyer" if i < 50 else "seller",
        "address": acct.address,
        "private_key": acct.key.hex()
    })

with open("participants.json", "w") as f:
    json.dump(participants, f, indent=2)

print("✅ Generated 50 buyers and 50 sellers.")
print("📄 Saved to participants.json")

# === Step 2: Fund Each ===
print("💸 Funding participants...")

for p in participants:
    to = p["address"]
    nonce = w3.eth.get_transaction_count(DEPLOYER)
    if p["role"] == "buyer":
        tx = cash.functions.transfer(to, w3.to_wei(10000, "ether")).build_transaction({
            "from": DEPLOYER,
            "nonce": nonce,
            "gas": 200000,
            "gasPrice": 0
        })
    else:
        tx = sec.functions.transfer(to, w3.to_wei(100, "ether")).build_transaction({
            "from": DEPLOYER,
            "nonce": nonce,
            "gas": 200000,
            "gasPrice": 0
        })

    signed_tx = w3.eth.account.sign_transaction(tx, DEPLOYER_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"✔ Funded {p['role']} {to} → tx: {tx_hash.hex()}")

print("🎉 All participants funded successfully.")
