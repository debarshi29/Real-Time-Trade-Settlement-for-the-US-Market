import time
import random
import json
from web3 import Web3
from trade_agent import TradeValidator  # Your agentic validator

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

# === Simulation ===
def simulate_market_tick():
    seller = random.choice(sellers)
    buyer = random.choice(buyers)

    shares = random.randint(1, 10)
    price_per_share = random.randint(50, 200)
    total_price = shares * price_per_share

    print(f"\n📈 Trade Attempt: {buyer['address']} buys {shares} shares from {seller['address']} @ {price_per_share} = ${total_price}")

    # === Validate ===
    result = agent.assess_trade(
        trader_cash=buyer["address"],
        trader_sec=seller["address"],
        required_cash=w3.to_wei(total_price, "ether"),
        required_sec=w3.to_wei(shares, "ether")
    )

    if not result["approved"]:
        print(f"❌ Trade Rejected: {result['reason']}")
        return

    try:
        # === Approve TCASH (Buyer) ===
        nonce_buyer = w3.eth.get_transaction_count(buyer["address"])
        tx1 = cash_token.functions.approve(
            ATOMIC_SWAP, w3.to_wei(total_price, "ether")
        ).build_transaction({
            "from": buyer["address"],
            "nonce": nonce_buyer,
            "gas": 200000,
            "gasPrice": 0
        })
        signed1 = w3.eth.account.sign_transaction(tx1, private_key=buyer["private_key"])
        w3.eth.send_raw_transaction(signed1.rawTransaction)

        # === Approve TSEC (Seller) ===
        nonce_seller = w3.eth.get_transaction_count(seller["address"])
        tx2 = sec_token.functions.approve(
            ATOMIC_SWAP, w3.to_wei(shares, "ether")
        ).build_transaction({
            "from": seller["address"],
            "nonce": nonce_seller,
            "gas": 200000,
            "gasPrice": 0
        })
        signed2 = w3.eth.account.sign_transaction(tx2, private_key=seller["private_key"])
        w3.eth.send_raw_transaction(signed2.rawTransaction)

        time.sleep(1.5)

        # === Init Trade ===
        nonce_trade = w3.eth.get_transaction_count(buyer["address"])
        tx3 = swap_contract.functions.initTrade(
            seller["address"],
            buyer["address"],
            TOKENIZED_SEC,
            w3.to_wei(shares, "ether"),
            TOKENIZED_CASH,
            w3.to_wei(total_price, "ether")
        ).build_transaction({
            "from": buyer["address"],
            "nonce": nonce_trade,
            "gas": 300000,
            "gasPrice": 0
        })
        signed3 = w3.eth.account.sign_transaction(tx3, private_key=buyer["private_key"])
        tx_hash = w3.eth.send_raw_transaction(signed3.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        print("✅ Trade Executed:", receipt.transactionHash.hex())

    except Exception as e:
        print("❌ Transaction failed:", str(e))

# === Loop ===
if __name__ == "__main__":
    print("🔁 Starting Market Simulation (2 buyers, 2 sellers)...")
    while True:
        simulate_market_tick()
        time.sleep(5)
