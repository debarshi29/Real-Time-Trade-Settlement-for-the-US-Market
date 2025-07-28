import time
import random
import json
from web3 import Web3
from trade_agent import TradeValidator

# === Load deployed contract addresses ===
with open("../smart-contracts/deployed-addresses.json") as f:
    deployed = json.load(f)

TOKENIZED_CASH = deployed["TokenizedCash"]
TOKENIZED_SEC = deployed["TokenizedSecurity"]
ATOMIC_SWAP = deployed["AtomicSwap"]

# === Load participants ===
with open("participants.json") as f:
    all_participants = json.load(f)

buyers = [p for p in all_participants if p["role"] == "buyer"]
sellers = [p for p in all_participants if p["role"] == "seller"]

# === Web3 init + contract ABIs ===
WEB3_PROVIDER = "http://localhost:8545"
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

if not w3.is_connected():
    raise ConnectionError("⚠ Web3 provider not connected.")

CHAIN_ID = w3.eth.chain_id

def load_abi(path):
    with open(path) as f:
        return json.load(f)["abi"]

abi_cash = load_abi("../smart-contracts/artifacts/contracts/TokenizedCash.sol/TokenizedCash.json")
abi_sec = load_abi("../smart-contracts/artifacts/contracts/TokenizedSecurity.sol/TokenizedSecurity.json")
abi_swap = load_abi("../smart-contracts/artifacts/contracts/AtomicSwap.sol/AtomicSwap.json")

cash_token = w3.eth.contract(address=TOKENIZED_CASH, abi=abi_cash)
sec_token = w3.eth.contract(address=TOKENIZED_SEC, abi=abi_sec)
swap_contract = w3.eth.contract(address=ATOMIC_SWAP, abi=abi_swap)

# === Initialize AI agent ===
agent = TradeValidator(w3, TOKENIZED_CASH, TOKENIZED_SEC, abi_cash, abi_sec)

# === Utility ===
def log_balances(buyer, seller):
    buyer_cash = cash_token.functions.balanceOf(buyer["address"]).call()
    buyer_sec = sec_token.functions.balanceOf(buyer["address"]).call()
    seller_cash = cash_token.functions.balanceOf(seller["address"]).call()
    seller_sec = sec_token.functions.balanceOf(seller["address"]).call()
    
    print(f"📊 Buyer Cash: {Web3.from_wei(buyer_cash, 'ether')} | Buyer Sec: {Web3.from_wei(buyer_sec, 'ether')}")
    print(f"📊 Seller Cash: {Web3.from_wei(seller_cash, 'ether')} | Seller Sec: {Web3.from_wei(seller_sec, 'ether')}")

def display_llm_analysis(result):
    """Display the LLM analysis in a formatted way"""
    print(f"\n🤖 LLM ANALYSIS:")
    print(f"   📅 Timestamp: {result.get('trade_timestamp', 'N/A')}")
    
    if result.get('approved'):
        print(f"   ✅ Status: APPROVED")
    else:
        print(f"   ❌ Status: REJECTED")
    
    print(f"   📝 Summary: {result.get('summary', 'No summary available')}")
    print(f"   🔍 Reason: {result.get('reason', 'No reason provided')}")
    
    # Display validation details
    if result.get('balance'):
        print(f"   💰 Balance Check: {result.get('balance')}")
    if result.get('risk'):
        print(f"   ⚠️  Risk Assessment: {result.get('risk')}")
    
    print("-" * 80)

# === Simulation ===
def simulate_market_tick():
    seller = random.choice(sellers)
    buyer = random.choice(buyers)

    shares = random.randint(1, 10)
    price_per_share = random.randint(50, 200)
    total_price = shares * price_per_share

    print(f"\n📈 Trade Attempt: {buyer['address']} buys {shares} shares from {seller['address']} @ {price_per_share} = ${total_price}")

    # === Validate with AI Agent ===
    result = agent.assess_trade(
        trader_cash=buyer["address"],
        trader_sec=seller["address"],
        required_cash=Web3.to_wei(total_price, "ether"),
        required_sec=Web3.to_wei(shares, "ether")
    )

    # === Display AI Analysis ===
    display_llm_analysis(result)

    # === Check if trade is approved ===
    if not result["approved"]:
        print(f"🚫 Trade Not Executed - Validation Failed")
        print("=" * 80)
        return

    # === Execute Trade (only if approved) ===
    try:
        print("🔄 Executing approved trade...")
        
        # === Approve TCASH (Buyer) ===
        nonce_buyer = w3.eth.get_transaction_count(buyer["address"])
        tx1 = cash_token.functions.approve(
            ATOMIC_SWAP, Web3.to_wei(total_price, "ether")
        ).build_transaction({
            "from": buyer["address"],
            "nonce": nonce_buyer,
            "gas": 200000,
            "gasPrice": w3.to_wei("1", "gwei"),
            "chainId": CHAIN_ID
        })
        signed1 = w3.eth.account.sign_transaction(tx1, private_key=buyer["private_key"])
        tx_hash1 = w3.eth.send_raw_transaction(signed1.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash1)

        # === Approve TSEC (Seller) ===
        nonce_seller = w3.eth.get_transaction_count(seller["address"])
        tx2 = sec_token.functions.approve(
            ATOMIC_SWAP, Web3.to_wei(shares, "ether")
        ).build_transaction({
            "from": seller["address"],
            "nonce": nonce_seller,
            "gas": 200000,
            "gasPrice": w3.to_wei("1", "gwei"),
            "chainId": CHAIN_ID
        })
        signed2 = w3.eth.account.sign_transaction(tx2, private_key=seller["private_key"])
        tx_hash2 = w3.eth.send_raw_transaction(signed2.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash2)

        # === Init Trade ===
        nonce_trade = w3.eth.get_transaction_count(buyer["address"])
        tx3 = swap_contract.functions.initTrade(
            seller["address"],
            buyer["address"],
            TOKENIZED_SEC,
            Web3.to_wei(shares, "ether"),
            TOKENIZED_CASH,
            Web3.to_wei(total_price, "ether")
        ).build_transaction({
            "from": buyer["address"],
            "nonce": nonce_trade,
            "gas": 300000,
            "gasPrice": w3.to_wei("1", "gwei"),
            "chainId": CHAIN_ID
        })
        signed3 = w3.eth.account.sign_transaction(tx3, private_key=buyer["private_key"])
        tx_hash3 = w3.eth.send_raw_transaction(signed3.raw_transaction)
        receipt_init = w3.eth.wait_for_transaction_receipt(tx_hash3)
        trade_id = swap_contract.functions.tradeCounter().call() - 1  # Get the tradeId from initTrade

        # === Buyer Approves Trade ===
        nonce_buyer_approve = w3.eth.get_transaction_count(buyer["address"])
        tx4 = swap_contract.functions.approveTrade(trade_id).build_transaction({
            "from": buyer["address"],
            "nonce": nonce_buyer_approve,
            "gas": 200000,
            "gasPrice": w3.to_wei("1", "gwei"),
            "chainId": CHAIN_ID
        })
        signed4 = w3.eth.account.sign_transaction(tx4, private_key=buyer["private_key"])
        tx_hash4 = w3.eth.send_raw_transaction(signed4.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash4)

        # === Seller Approves Trade ===
        nonce_seller_approve = w3.eth.get_transaction_count(seller["address"])
        tx5 = swap_contract.functions.approveTrade(trade_id).build_transaction({
            "from": seller["address"],
            "nonce": nonce_seller_approve,
            "gas": 200000,
            "gasPrice": w3.to_wei("1", "gwei"),
            "chainId": CHAIN_ID
        })
        signed5 = w3.eth.account.sign_transaction(tx5, private_key=seller["private_key"])
        tx_hash5 = w3.eth.send_raw_transaction(signed5.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash5)

        # === Execute Trade ===
        nonce_execute = w3.eth.get_transaction_count(buyer["address"])
        tx6 = swap_contract.functions.executeTrade(trade_id).build_transaction({
            "from": buyer["address"],
            "nonce": nonce_execute,
            "gas": 300000,
            "gasPrice": w3.to_wei("1", "gwei"),
            "chainId": CHAIN_ID
        })
        signed6 = w3.eth.account.sign_transaction(tx6, private_key=buyer["private_key"])
        tx_hash6 = w3.eth.send_raw_transaction(signed6.raw_transaction)
        receipt_execute = w3.eth.wait_for_transaction_receipt(tx_hash6)

        print("✅ Trade Executed Successfully!")
        print(f"   Transaction Hash: {receipt_execute.transactionHash.hex()}")
        print(f"   Trade ID: {trade_id}")
        log_balances(buyer, seller)

    except Exception as e:
        print(f"❌ Transaction failed: {str(e)}")
    
    print("=" * 80)

# === Loop ===
if __name__ == "__main__":
    print("🔁 Starting Market Simulation with AI Validation (Ctrl+C to stop)...")
    print("=" * 80)
    try:
        while True:
            simulate_market_tick()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped by user.")