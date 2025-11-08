import random
import json
from datetime import datetime
from web3 import Web3
from trade_graph import build_trade_validator, TradeState

# === Load participants ===
with open("participants.json") as f:
    all_participants = json.load(f)

buyers = [p for p in all_participants if p["role"] == "buyer"]
sellers = [p for p in all_participants if p["role"] == "seller"]

# === On-chain ERC20 ABI ===
erc20_abi = [{
    "constant": True,
    "inputs": [{"name": "account", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "", "type": "uint256"}],
    "type": "function"
}]

# === Web3 Connection ===
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# === Hardcoded token addresses for demo ===
TOKEN_CASH = "0xc1Ef73B9ccc4612246d723F00d34EEef56DBD4c3"  # Replace with your deployed ERC20 cash token
TOKEN_SEC = "0xddfF69F60b480aB37Dd79a2B93e4298fceFAf8De"   # Replace with your deployed ERC20 sec token

# === Helper to get on-chain cash balance ===
def get_onchain_cash_balance(participant):
    try:
        token_cash = Web3.to_checksum_address(TOKEN_CASH)
        party_cash = Web3.to_checksum_address(participant["address"])
        cash_token = w3.eth.contract(address=token_cash, abi=erc20_abi)
        return cash_token.functions.balanceOf(party_cash).call()
    except Exception as e:
        print(f"Error fetching balance for {participant.get('address', 'unknown')}: {e}")
        return 0

# === Find buyer with lowest on-chain balance ===
lowest_balance_buyer = min(buyers, key=get_onchain_cash_balance)
print("Lowest on-chain balance buyer:", lowest_balance_buyer)

# === Trade simulation using LangGraph validator ===
def simulate_trade(buyer, seller):
    state = TradeState(
        party_cash=buyer["address"],
        party_sec=seller["address"],
        required_cash=1500,  # >1000
        required_sec=random.randint(1, 10),
        token_cash=TOKEN_CASH,
        token_sec=TOKEN_SEC,
        balance="Insufficient",   # Force failure
        risk="High",              # Force failure
        approved=False,           # Start as fail
        summary="Forced failure demo",
        reason="Balance check failed: Insufficient funds",
        trade_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    trade_validator = build_trade_validator()
    result_state = trade_validator.invoke(state)

    # Force override to always fail
    result_state["approved"] = False
    result_state["reason"] = "Balance check failed (forced demo failure)"

    print(f"Trade result: {result_state['approved']}, Reason: {result_state['reason']}")
    return result_state["approved"]

# === Pick ANY buyer and seller for demo ===
buyer_for_trades = random.choice(buyers)
seller_for_trades = random.choice(sellers)

# === Conduct 3 trades with failure tracking ===
consecutive_failures = 0
for i in range(3):
    print(f"\n--- Trade {i+1} ---")
    trade_success = simulate_trade(buyer_for_trades, seller_for_trades)
    if not trade_success:
        consecutive_failures += 1
        if consecutive_failures == 3:
            print("\n⚠ HUMAN-IN-THE-LOOP INTERVENTION REQUIRED: 3 consecutive trades failed.")
            # Manual approval/alert logic here
    else:
        consecutive_failures = 0
