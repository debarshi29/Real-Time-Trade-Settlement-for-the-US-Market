from web3 import Web3
import json

# === CONFIG ===
WEB3_PROVIDER = "http://localhost:8545"
CHAIN_ID = 1981

# === Load latest deployed addresses ===
with open("../smart-contracts/deployed-addresses.json") as f:
    addresses = json.load(f)
TOKENIZED_CASH = Web3.to_checksum_address(addresses["TokenizedCash"])
TOKENIZED_SEC = Web3.to_checksum_address(addresses["TokenizedSecurity"])

# === Load participants from file ===
with open("participants.json", "r") as f:
    accounts = json.load(f)

# === Admin ===
ADMIN_PRIVATE_KEY = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))
ADMIN_ADDRESS = w3.eth.account.from_key(ADMIN_PRIVATE_KEY).address

# === Load ABIs ===
with open("../smart-contracts/artifacts/contracts/TokenizedCash.sol/TokenizedCash.json") as f:
    abi_cash = json.load(f)["abi"]
with open("../smart-contracts/artifacts/contracts/TokenizedSecurity.sol/TokenizedSecurity.json") as f:
    abi_sec = json.load(f)["abi"]

cash_token = w3.eth.contract(address=TOKENIZED_CASH, abi=abi_cash)
sec_token = w3.eth.contract(address=TOKENIZED_SEC, abi=abi_sec)

# === Utility: Send TX ===
def send_tx(fn, nonce):
    tx = fn.build_transaction({
        "from": ADMIN_ADDRESS,
        "nonce": nonce,
        "gas": 500_000,
        "gasPrice": 0,
        "chainId": CHAIN_ID,
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=ADMIN_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print(f"✅ Transaction successful in block {receipt.blockNumber}")
    else:
        print(f"❌ Transaction failed in block {receipt.blockNumber}")
        raise Exception("Transaction failed")
    return receipt

# === Diagnostics ===
decimals_cash = cash_token.functions.decimals().call()
decimals_sec = sec_token.functions.decimals().call()
admin_balance_cash = cash_token.functions.balanceOf(ADMIN_ADDRESS).call()
admin_balance_sec = sec_token.functions.balanceOf(ADMIN_ADDRESS).call()
print("🧮 Admin Balances:")
print(f"   TCASH: {admin_balance_cash / (10 ** decimals_cash)}")
print(f"   TSEC:  {admin_balance_sec / (10 ** decimals_sec)}")
print("Total supply (TCASH):", cash_token.functions.totalSupply().call() / (10 ** decimals_cash))
print(f"Admin address: {ADMIN_ADDRESS}")
print(f"Admin ETH: {w3.from_wei(w3.eth.get_balance(ADMIN_ADDRESS), 'ether')}")

# === Role Checks ===
owner_cash = cash_token.functions.owner().call()
print(f"TCASH contract owner: {owner_cash}")
if owner_cash.lower() != ADMIN_ADDRESS.lower():
    print("⚠️ Admin is NOT the TCASH contract owner!")

ISSUER_ROLE = w3.keccak(text="ISSUER_ROLE")
has_issuer_role = sec_token.functions.hasRole(ISSUER_ROLE, ADMIN_ADDRESS).call()
print(f"Admin has ISSUER_ROLE for TSEC: {has_issuer_role}")
if not has_issuer_role:
    print("⚠️ Admin lacks ISSUER_ROLE for TSEC!")

# === Start Funding ===
print("🚀 Starting funding process...")
nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)

# Mint TCASH to admin if needed
if admin_balance_cash < 4000 * (10 ** decimals_cash):
    print(f"💰 Minting 5000 TCASH to admin...")
    receipt = send_tx(cash_token.functions.mint(ADMIN_ADDRESS, 5000 * (10 ** decimals_cash)), nonce)
    nonce += 1
else:
    print("✅ Admin already has sufficient TCASH")

# Distribute TCASH and TSEC to accounts
for acc in accounts:
    addr = Web3.to_checksum_address(acc["address"])
    role = acc["role"]
    if role == "buyer":
        print(f"💸 Sending 1000 TCASH to buyer {addr}...")
        receipt = send_tx(cash_token.functions.transfer(addr, 1000 * (10 ** decimals_cash)), nonce)
        nonce += 1
    elif role == "seller":
        print(f"📈 Minting 100 TSEC to seller {addr}...")
        receipt = send_tx(sec_token.functions.mint(addr, 100 * (10 ** decimals_sec)), nonce)
        nonce += 1

# === Final Balances ===
print("\n🔍 Final Balances:")
for acc in accounts:
    addr = Web3.to_checksum_address(acc["address"])
    bal_cash = cash_token.functions.balanceOf(addr).call()
    bal_sec = sec_token.functions.balanceOf(addr).call()
    print(f"   {addr}:")
    print(f"     TCASH: {bal_cash / (10 ** decimals_cash)}")
    print(f"     TSEC:  {bal_sec / (10 ** decimals_sec)}")

print("\n✅ All accounts funded successfully.")
