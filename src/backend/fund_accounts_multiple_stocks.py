from web3 import Web3
import json

# === CONFIG ===
WEB3_PROVIDER = "http://localhost:8545"
CHAIN_ID = 1981

# === Load latest deployed addresses ===
with open("../smart-contracts/deployed-addresses-1.json") as f:
    addresses = json.load(f)

TOKENIZED_CASH = Web3.to_checksum_address(addresses["TokenizedCash"])

# Load stock addresses - check if they exist first
stock_symbols = ["AAPL", "GOOGL", "TSLA", "AMZN", "MSFT"]
stock_addresses = {}

for symbol in stock_symbols:
    if symbol in addresses:
        stock_addresses[symbol] = Web3.to_checksum_address(addresses[symbol])
    else:
        print(f"⚠️ Warning: {symbol} not found in deployed-addresses.json")
        print(f"   Please deploy stock tokens first using: npx hardhat run scripts/deploy-stocks.js --network besu")

if len(stock_addresses) == 0:
    print("\n❌ No stock tokens found in deployed-addresses.json!")
    print("Please deploy stock tokens first.")
    exit(1)

print(f"\n✅ Loaded {len(stock_addresses)} stock token addresses")

APPLE_STOCK = stock_addresses.get("AAPL")
GOOGLE_STOCK = stock_addresses.get("GOOGL")
TESLA_STOCK = stock_addresses.get("TSLA")
AMAZON_STOCK = stock_addresses.get("AMZN")
MICROSOFT_STOCK = stock_addresses.get("MSFT")

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

# === Create contract instances ===
cash_token = w3.eth.contract(address=TOKENIZED_CASH, abi=abi_cash)

# Create stock token contracts only for deployed tokens
stock_tokens = {}
if APPLE_STOCK:
    stock_tokens["AAPL"] = w3.eth.contract(address=APPLE_STOCK, abi=abi_sec)
if GOOGLE_STOCK:
    stock_tokens["GOOGL"] = w3.eth.contract(address=GOOGLE_STOCK, abi=abi_sec)
if TESLA_STOCK:
    stock_tokens["TSLA"] = w3.eth.contract(address=TESLA_STOCK, abi=abi_sec)
if AMAZON_STOCK:
    stock_tokens["AMZN"] = w3.eth.contract(address=AMAZON_STOCK, abi=abi_sec)
if MICROSOFT_STOCK:
    stock_tokens["MSFT"] = w3.eth.contract(address=MICROSOFT_STOCK, abi=abi_sec)

if len(stock_tokens) == 0:
    print("\n❌ No stock token contracts available!")
    exit(1)

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
print("=" * 60)
print("🔍 DIAGNOSTICS")
print("=" * 60)

decimals_cash = cash_token.functions.decimals().call()
admin_balance_cash = cash_token.functions.balanceOf(ADMIN_ADDRESS).call()

print(f"\n💰 Admin Cash Balance:")
print(f"   TCASH: {admin_balance_cash / (10 ** decimals_cash)}")
print(f"   Total supply (TCASH): {cash_token.functions.totalSupply().call() / (10 ** decimals_cash)}")

print(f"\n📊 Admin Stock Balances:")
for symbol, token in stock_tokens.items():
    decimals = token.functions.decimals().call()
    balance = token.functions.balanceOf(ADMIN_ADDRESS).call()
    total_supply = token.functions.totalSupply().call()
    print(f"   {symbol}: {balance / (10 ** decimals)} (Total Supply: {total_supply / (10 ** decimals)})")

print(f"\n🔐 Admin Info:")
print(f"   Address: {ADMIN_ADDRESS}")
print(f"   ETH Balance: {w3.from_wei(w3.eth.get_balance(ADMIN_ADDRESS), 'ether')}")

# === Role Checks ===
print(f"\n✅ Role Checks:")
owner_cash = cash_token.functions.owner().call()
print(f"   TCASH contract owner: {owner_cash}")
if owner_cash.lower() != ADMIN_ADDRESS.lower():
    print("   ⚠️ Admin is NOT the TCASH contract owner!")

ISSUER_ROLE = w3.keccak(text="ISSUER_ROLE")
print(f"\n   Stock Token ISSUER_ROLE checks:")
for symbol, token in stock_tokens.items():
    has_issuer_role = token.functions.hasRole(ISSUER_ROLE, ADMIN_ADDRESS).call()
    status = "✅" if has_issuer_role else "❌"
    print(f"   {status} {symbol}: {has_issuer_role}")
    if not has_issuer_role:
        print(f"      ⚠️ Admin lacks ISSUER_ROLE for {symbol}!")

# === Start Funding ===
print("\n" + "=" * 60)
print("🚀 STARTING FUNDING PROCESS")
print("=" * 60)
nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)

# Mint TCASH to admin if needed
required_cash = sum(1 for acc in accounts if acc["role"] == "buyer") * 1000
if admin_balance_cash < required_cash * (10 ** decimals_cash):
    mint_amount = (required_cash + 1000) * (10 ** decimals_cash)
    print(f"\n💰 Minting {mint_amount / (10 ** decimals_cash)} TCASH to admin...")
    receipt = send_tx(cash_token.functions.mint(ADMIN_ADDRESS, mint_amount), nonce)
    nonce += 1
else:
    print("\n✅ Admin already has sufficient TCASH")

# === Distribute TCASH and Stocks to accounts ===
print("\n📦 Distributing tokens to accounts...")
for acc in accounts:
    addr = Web3.to_checksum_address(acc["address"])
    role = acc["role"]
    
    if role == "buyer":
        # Give cash to buyers (increased to allow buying from multiple sellers)
        cash_amount = 5000  # Enough to buy all 5 stocks from multiple sellers
        print(f"\n💸 Sending {cash_amount} TCASH to buyer {addr}...")
        receipt = send_tx(cash_token.functions.transfer(addr, cash_amount * (10 ** decimals_cash)), nonce)
        nonce += 1
        
    elif role == "seller":
        # Give ALL 5 stocks to each seller
        print(f"\n📈 Minting stocks for seller {addr}...")
        for symbol, token in stock_tokens.items():
            print(f"   💎 Minting 100 {symbol}...")
            receipt = send_tx(token.functions.mint(addr, 100 * (10 ** 18)), nonce)
            nonce += 1

# === Final Balances ===
print("\n" + "=" * 60)
print("🔍 FINAL BALANCES")
print("=" * 60)

for acc in accounts:
    addr = Web3.to_checksum_address(acc["address"])
    print(f"\n📍 {addr} ({acc['role']}):")
    
    # Cash balance
    bal_cash = cash_token.functions.balanceOf(addr).call()
    print(f"   💵 TCASH: {bal_cash / (10 ** decimals_cash)}")
    
    # Stock balances
    for symbol, token in stock_tokens.items():
        decimals = token.functions.decimals().call()
        bal_stock = token.functions.balanceOf(addr).call()
        if bal_stock > 0:
            print(f"   📊 {symbol}: {bal_stock / (10 ** decimals)}")

print("\n" + "=" * 60)
print("✅ All accounts funded successfully!")
print("=" * 60)