from web3 import Web3
import json

# === CONFIG ===
WEB3_PROVIDER = "http://localhost:8545"

TOKENIZED_CASH = "0xa9ECbe3F9600f9bF3ec88a428387316714ac95a0"
TOKENIZED_SEC = "0x2114De86c8Ea1FD8144C2f1e1e94C74E498afB1b"

ABI_CASH_PATH =r"../smart-contracts/artifacts/contracts/TokenizedCash.sol/TokenizedCash.json"
ABI_SEC_PATH = r"../smart-contracts/artifacts/contracts/TokenizedSecurity.sol/TokenizedSecurity.json"

# Admin account
ADMIN_ADDRESS = "0xFE3B557E8Fb62b89F4916B721be55cEb828dBd73"
ADMIN_PRIVATE_KEY = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113b37c6d3d8b3f0f10c5c8cefb"


# === Accounts to fund ===
accounts = [
    {
        "role": "buyer",
        "address": "0x59b5D0A361b6Cd8Cc22e21bE74f2Dc387f75E9A6",
    },
    {
        "role": "buyer",
        "address": "0xd9f64a61E2F822B6aF88ffb34C436D9A600A2De9",
    },
    {
        "role": "seller",
        "address": "0xA5F05C523aF62ea507a90E78605e2a1796B2c801",
    },
    {
        "role": "seller",
        "address": "0x264B3334C9e6997534ccd403099eD8BFC43fb3F9",
    },
]

# === Setup Web3 ===
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# === Load ABIs ===
# === Load ABIs ===
with open(ABI_CASH_PATH) as f:
    abi_cash = json.load(f)["abi"]  
with open(ABI_SEC_PATH) as f:
    abi_sec = json.load(f)["abi"]   


cash_token = w3.eth.contract(address=TOKENIZED_CASH, abi=abi_cash)
sec_token = w3.eth.contract(address=TOKENIZED_SEC, abi=abi_sec)

# === Funding Function ===
def send_tokens(token_contract, to_address, amount_wei, nonce):
    tx = token_contract.functions.transfer(to_address, amount_wei).build_transaction({
        'from': ADMIN_ADDRESS,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': w3.to_wei('0', 'gwei')  # zero gas for dev
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=ADMIN_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return tx_hash

# === MAIN ===
print("🚀 Starting funding process...")

amount_cash = w3.to_wei(1000, 'ether')
amount_sec = w3.to_wei(100, 'ether')

nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)

for acc in accounts:
    addr = acc["address"]
    role = acc["role"]

    if role == "buyer":
        print(f"💸 Sending $1000 to buyer {addr}...")
        tx_hash = send_tokens(cash_token, addr, amount_cash, nonce)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        nonce += 1
    elif role == "seller":
        print(f"📈 Sending 100 sec tokens to seller {addr}...")
        tx_hash = send_tokens(sec_token, addr, amount_sec, nonce)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        nonce += 1

print("✅ All accounts funded successfully.")
