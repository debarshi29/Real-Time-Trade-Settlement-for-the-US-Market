# ==========================
# 🚀 Multi-Stock Trading Simulation with ML Fraud Detection
# ==========================

import time
import random
import json
from web3 import Web3
from trade_agent import AgenticTradeValidator

# === Load deployed contract addresses ===
with open("../smart-contracts/deployed-addresses-1.json") as f:
    deployed = json.load(f)

TOKENIZED_CASH = deployed["TokenizedCash"]

# Multiple stock addresses
stock_addresses = {
    "AAPL": deployed.get("AAPL"),
    "GOOGL": deployed.get("GOOGL"),
    "TSLA": deployed.get("TSLA"),
    "AMZN": deployed.get("AMZN"),
    "MSFT": deployed.get("MSFT")
}

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
    raise ConnectionError("⚠️ Web3 provider not connected.")

CHAIN_ID = w3.eth.chain_id

def load_abi(path):
    with open(path) as f:
        return json.load(f)["abi"]

abi_cash = load_abi("../smart-contracts/artifacts/contracts/TokenizedCash.sol/TokenizedCash.json")
abi_stock = load_abi("../smart-contracts/artifacts/contracts/TokenizedSecurity.sol/TokenizedSecurity.json")
abi_swap = load_abi("../smart-contracts/artifacts/contracts/AtomicSwap.sol/AtomicSwap.json")

cash_token = w3.eth.contract(address=TOKENIZED_CASH, abi=abi_cash)
swap_contract = w3.eth.contract(address=ATOMIC_SWAP, abi=abi_swap)

# Create stock token contracts
stock_contracts = {}
for symbol, address in stock_addresses.items():
    if address:
        stock_contracts[symbol] = w3.eth.contract(address=address, abi=abi_stock)

# === Market Price Data (simulated real-time prices) ===
market_prices = {
    "AAPL": 180.0,
    "GOOGL": 140.0,
    "TSLA": 240.0,
    "AMZN": 150.0,
    "MSFT": 370.0
}

def update_market_prices():
    """Simulate market price movements"""
    for symbol in market_prices:
        # Random price movement ±2%
        change_pct = random.uniform(-0.02, 0.02)
        market_prices[symbol] *= (1 + change_pct)

# === Initialize ML Fraud Detectors for each stock ===
print("🤖 Initializing Multi-Stock Trading System with ML Fraud Detection...")

# We'll use a single agent but track different stocks
# In production, you might want separate models per stock
agents = {}
for symbol, stock_address in stock_addresses.items():
    if stock_address:
        print(f"   Setting up validator for {symbol}...")
        try:
            agent = AgenticTradeValidator(
                w3, 
                TOKENIZED_CASH, 
                stock_address,  # Different stock for each
                abi_cash, 
                abi_stock,
                initial_risk_threshold=10**21,
                enable_learning=True,
                enable_ml_fraud_detection=True,
                ml_model_path='fraud_detection_model.pkl'
            )
            agents[symbol] = agent
            print(f"   ✅ {symbol} validator ready")
        except Exception as e:
            print(f"   ⚠️ Failed to initialize {symbol}: {str(e)}")

print(f"✅ Initialized {len(agents)} stock validators with ML fraud detection\n")

# === Simulation Stats ===
simulation_stats = {
    "total_attempts": 0,
    "approved_trades": 0,
    "rejected_trades": 0,
    "ml_fraud_blocked": 0,
    "agent_rejected": 0,
    "executed_trades": 0,
    "execution_failures": 0,
    "total_volume": 0,
    "high_confidence_decisions": 0,
    "agent_adaptations": 0,
    "stock_stats": {symbol: {"attempts": 0, "executed": 0, "blocked": 0, "volume": 0} 
                    for symbol in stock_addresses.keys()},
    "ml_detection_stats": {
        "critical_risk": 0,
        "high_risk": 0,
        "medium_risk": 0,
        "low_risk": 0
    }
}

# === Utility Functions ===
def get_stock_name(symbol):
    """Get full stock name"""
    names = {
        "AAPL": "Apple",
        "GOOGL": "Google",
        "TSLA": "Tesla",
        "AMZN": "Amazon",
        "MSFT": "Microsoft"
    }
    return names.get(symbol, symbol)

def log_balances(buyer, seller, stock_symbol):
    """Log balances for buyer and seller"""
    buyer_cash = cash_token.functions.balanceOf(buyer["address"]).call()
    seller_cash = cash_token.functions.balanceOf(seller["address"]).call()
    
    stock_contract = stock_contracts.get(stock_symbol)
    if stock_contract:
        buyer_stock = stock_contract.functions.balanceOf(buyer["address"]).call()
        seller_stock = stock_contract.functions.balanceOf(seller["address"]).call()
        
        print(f"📊 Buyer: ${Web3.from_wei(buyer_cash, 'ether'):.2f} cash | {Web3.from_wei(buyer_stock, 'ether'):.2f} {stock_symbol}")
        print(f"📊 Seller: ${Web3.from_wei(seller_cash, 'ether'):.2f} cash | {Web3.from_wei(seller_stock, 'ether'):.2f} {stock_symbol}")

def display_ml_fraud_analysis(ml_result):
    """Display ML fraud detection analysis"""
    if not ml_result.get('enabled', False):
        return
    
    print(f"\n🤖 ML FRAUD DETECTION ANALYSIS:")
    
    fraud_detected = ml_result.get('fraud_detected', False)
    fraud_prob = ml_result.get('fraud_probability', 0.0)
    risk_level = ml_result.get('risk_level', 'UNKNOWN')
    
    if fraud_detected:
        print(f"   🚨 STATUS: FRAUD DETECTED")
        simulation_stats['ml_fraud_blocked'] += 1
    else:
        print(f"   ✅ STATUS: LEGITIMATE")
    
    prob_emoji = "🔴" if fraud_prob > 0.5 else "🟡" if fraud_prob > 0.2 else "🟢"
    print(f"   {prob_emoji} Fraud Probability: {fraud_prob:.1%}")
    
    risk_emoji = {
        'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 
        'LOW': '🟢', 'UNKNOWN': '⚪'
    }.get(risk_level, '⚪')
    print(f"   {risk_emoji} Risk Level: {risk_level}")
    
    if risk_level in ['CRITICAL', 'HIGH']:
        simulation_stats['ml_detection_stats']['high_risk'] += 1
    elif risk_level == 'MEDIUM':
        simulation_stats['ml_detection_stats']['medium_risk'] += 1
    elif risk_level == 'LOW':
        simulation_stats['ml_detection_stats']['low_risk'] += 1
    
    reasoning = ml_result.get('reasoning', 'No reasoning provided')
    print(f"\n   💡 ML Reasoning:")
    for line in reasoning.split('\n')[:3]:
        if line.strip():
            print(f"      {line.strip()}")
    
    ml_time = ml_result.get('processing_time_ms', 0)
    print(f"   ⚡ ML Processing Time: {ml_time:.2f}ms")
    print("-" * 80)

def display_agentic_analysis(result, stock_symbol):
    """Display combined agentic AI + ML analysis"""
    print(f"\n🧠 AGENTIC AI ANALYSIS ({stock_symbol}):")
    print(f"   📅 Timestamp: {result.get('trade_timestamp', 'N/A')}")
    
    if result.get('approved'):
        print(f"   ✅ Final Status: APPROVED")
    else:
        print(f"   ❌ Final Status: REJECTED")
        if result.get('ml_override', False):
            print(f"   🚨 Reason: ML FRAUD DETECTION OVERRIDE")
    
    confidence = result.get('confidence_score', 0.0)
    confidence_emoji = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.5 else "🔴"
    print(f"   {confidence_emoji} Agent Confidence: {confidence:.2%}")
    
    agent_decision = result.get('agent_decision', False)
    ml_override = result.get('ml_override', False)
    print(f"\n   📋 Decision Breakdown:")
    print(f"      Agent Decision: {'✓ APPROVE' if agent_decision else '✗ REJECT'}")
    print(f"      ML Override: {'⚠️ YES' if ml_override else '✓ NO'}")
    
    ml_result = result.get('ml_fraud_detection', {})
    display_ml_fraud_analysis(ml_result)
    
    print(f"   🤔 Agent's Reasoning Chain:")
    reasoning = result.get('reasoning_chain', 'No reasoning provided')
    for line in reasoning.split('\n')[:4]:
        if line.strip():
            print(f"      {line.strip()}")
    
    completed_checks = result.get('completed_checks', [])
    if completed_checks:
        print(f"\n   ✓ Completed Checks: {', '.join(completed_checks)}")
    
    risk_level = result.get('risk_assessment', 'unknown')
    risk_emoji = "🟢" if risk_level == "low" else "🟡" if risk_level == "medium" else "🔴"
    print(f"   {risk_emoji} Agent Risk Level: {risk_level.upper()}")
    
    print(f"\n   ⏱️ Total Processing Time: {result.get('processing_time_seconds', 0):.3f}s")
    print("-" * 80)

def display_simulation_stats():
    """Display cumulative simulation statistics"""
    print(f"\n📊 SIMULATION STATISTICS:")
    print(f"   Total Trade Attempts: {simulation_stats['total_attempts']}")
    print(f"   ✅ Approved: {simulation_stats['approved_trades']}")
    print(f"   ❌ Rejected: {simulation_stats['rejected_trades']}")
    print(f"      ↳ 🤖 ML Fraud Blocked: {simulation_stats['ml_fraud_blocked']}")
    print(f"      ↳ 🧠 Agent Rejected: {simulation_stats['agent_rejected']}")
    print(f"   🔄 Executed: {simulation_stats['executed_trades']}")
    print(f"   💥 Execution Failures: {simulation_stats['execution_failures']}")
    
    if simulation_stats['total_attempts'] > 0:
        approval_rate = simulation_stats['approved_trades'] / simulation_stats['total_attempts']
        fraud_block_rate = simulation_stats['ml_fraud_blocked'] / simulation_stats['total_attempts']
        print(f"   📈 Approval Rate: {approval_rate:.1%}")
        print(f"   🚨 ML Fraud Block Rate: {fraud_block_rate:.1%}")
    
    print(f"\n   📊 STOCK-WISE BREAKDOWN:")
    for symbol, stats in simulation_stats['stock_stats'].items():
        if stats['attempts'] > 0:
            exec_rate = stats['executed'] / stats['attempts'] if stats['attempts'] > 0 else 0
            print(f"      {symbol} ({get_stock_name(symbol):9s}): "
                  f"{stats['attempts']:3d} attempts | "
                  f"{stats['executed']:3d} executed ({exec_rate:.0%}) | "
                  f"${stats['volume']:,.0f} volume")
    
    print(f"\n   🤖 ML RISK DISTRIBUTION:")
    print(f"      High/Critical: {simulation_stats['ml_detection_stats']['high_risk']}")
    print(f"      Medium: {simulation_stats['ml_detection_stats']['medium_risk']}")
    print(f"      Low: {simulation_stats['ml_detection_stats']['low_risk']}")
    
    print(f"\n   💰 Total Volume: ${simulation_stats['total_volume']:,.2f}")
    print(f"   🎯 High Confidence Decisions: {simulation_stats['high_confidence_decisions']}")
    print(f"   🧠 Agent Adaptations: {simulation_stats['agent_adaptations']}")
    
    print(f"\n   📈 CURRENT MARKET PRICES:")
    for symbol, price in market_prices.items():
        print(f"      {symbol}: ${price:.2f}")
    
    print("-" * 80)

# === Main Simulation Function ===
def simulate_market_tick():
    """Simulate one market tick with random stock selection"""
    
    # Select random stock
    available_stocks = [s for s in stock_addresses.keys() if s in agents]
    if not available_stocks:
        print("⚠️ No stocks available for trading")
        return
    
    stock_symbol = random.choice(available_stocks)
    stock_address = stock_addresses[stock_symbol]
    agent = agents[stock_symbol]
    stock_contract = stock_contracts[stock_symbol]
    
    # Select random buyer and seller
    seller = random.choice(sellers)
    buyer = random.choice(buyers)
    
    # Generate trade parameters based on current market price
    shares = random.randint(1, 20)
    market_price = market_prices[stock_symbol]
    
    # Price can deviate ±10% from market price (some trades are suspicious!)
    price_deviation = random.uniform(-0.10, 0.10)
    # Make some trades more suspicious (15% chance of large deviation)
    if random.random() < 0.15:
        price_deviation = random.uniform(-0.25, 0.25)  # Large deviation = suspicious
    
    price_per_share = market_price * (1 + price_deviation)
    total_price = shares * price_per_share
    
    simulation_stats['total_attempts'] += 1
    simulation_stats['stock_stats'][stock_symbol]['attempts'] += 1
    simulation_stats['total_volume'] += total_price
    
    print(f"\n{'='*80}")
    print(f"📈 Trade Attempt #{simulation_stats['total_attempts']}")
    print(f"{'='*80}")
    print(f"   Stock: {stock_symbol} ({get_stock_name(stock_symbol)})")
    print(f"   Market Price: ${market_price:.2f}")
    print(f"   Trade Price: ${price_per_share:.2f} ({price_deviation:+.1%} from market)")
    print(f"   Buyer: {buyer['address'][:10]}...")
    print(f"   Seller: {seller['address'][:10]}...")
    print(f"   Shares: {shares}")
    print(f"   Total Value: ${total_price:.2f}")
    
    # Prepare trade amounts
    required_cash_human = int(total_price)
    required_stock_human = shares
    
    # === Validate with Agentic AI + ML Fraud Detection ===
    result = agent.assess_trade(
        trader_cash=buyer["address"],
        trader_sec=seller["address"],
        required_cash=required_cash_human,
        required_sec=required_stock_human
    )
    
    # === Display Combined Analysis ===
    display_agentic_analysis(result, stock_symbol)
    
    # Track statistics
    if result.get('confidence_score', 0) > 0.7:
        simulation_stats['high_confidence_decisions'] += 1
    
    # === Check if trade is approved ===
    if not result["approved"]:
        simulation_stats['rejected_trades'] += 1
        simulation_stats['stock_stats'][stock_symbol]['blocked'] += 1
        
        if not result.get('ml_override', False):
            simulation_stats['agent_rejected'] += 1
        
        print(f"🚫 Trade Not Executed - Validation Failed")
        rejection_reason = "ML FRAUD DETECTED" if result.get('ml_override') else "AGENT REJECTED"
        print(f"   Rejection Type: {rejection_reason}")
        print(f"   Details: {result.get('reasoning_chain', 'Unknown')[:150]}...")
        print("=" * 80)
        return
    
    simulation_stats['approved_trades'] += 1
    
    # === Execute Trade (only if approved) ===
    try:
        print("🔄 Executing approved trade...")
        
        required_cash_wei = Web3.to_wei(int(total_price), "ether")
        required_stock_wei = Web3.to_wei(shares, "ether")
        
        # === Approve TCASH (Buyer) ===
        nonce_buyer = w3.eth.get_transaction_count(buyer["address"])
        tx1 = cash_token.functions.approve(
            ATOMIC_SWAP, required_cash_wei
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
        
        # === Approve Stock (Seller) ===
        nonce_seller = w3.eth.get_transaction_count(seller["address"])
        tx2 = stock_contract.functions.approve(
            ATOMIC_SWAP, required_stock_wei
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
            stock_address,
            required_stock_wei,
            TOKENIZED_CASH,
            required_cash_wei
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
        trade_id = swap_contract.functions.tradeCounter().call() - 1
        
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
        
        simulation_stats['executed_trades'] += 1
        simulation_stats['stock_stats'][stock_symbol]['executed'] += 1
        simulation_stats['stock_stats'][stock_symbol]['volume'] += total_price
        
        print("✅ Trade Executed Successfully!")
        print(f"   Stock: {stock_symbol}")
        print(f"   Transaction Hash: {receipt_execute.transactionHash.hex()}")
        print(f"   Trade ID: {trade_id}")
        print(f"   Gas Used: {receipt_execute.gasUsed}")
        log_balances(buyer, seller, stock_symbol)
        
    except Exception as e:
        simulation_stats['execution_failures'] += 1
        print(f"❌ Transaction failed: {str(e)}")
    
    print("=" * 80)

# === Main Loop ===
if __name__ == "__main__":
    print("=" * 80)
    print("🤖 MULTI-STOCK MARKET SIMULATION WITH ML FRAUD DETECTION")
    print("=" * 80)
    print("🚀 Starting Enhanced Market Simulation")
    print(f"   • 📊 Trading {len(agents)} stocks: {', '.join(agents.keys())}")
    print("   • 🧠 Agentic AI validation per stock")
    print("   • 🤖 ML fraud detection (Random Forest)")
    print("   • 📈 Real-time market prices")
    print("   • 🎯 Adaptive learning")
    print("   • Press Ctrl+C to stop and view statistics")
    print("=" * 80)
    
    # Check system health
    print(f"\n✅ System Health Check:")
    for symbol, agent in agents.items():
        health = agent.get_health_status()
        if health['status'] == 'healthy':
            print(f"   {symbol}: ✅ Ready (Block: {health['current_block']})")
        else:
            print(f"   {symbol}: ⚠️ {health.get('error', 'Unknown error')}")
    
    print("=" * 80)
    
    try:
        tick_count = 0
        while True:
            # Update market prices periodically
            if tick_count % 5 == 0:
                update_market_prices()
            
            simulate_market_tick()
            tick_count += 1
            
            # Display stats every 10 trades
            if tick_count % 10 == 0:
                display_simulation_stats()
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n" + "=" * 80)
        print("🛑 Simulation stopped by user")
        print("=" * 80)
        
        # Final statistics
        display_simulation_stats()
        
        # Display final state for each stock
        print("\n🧠 FINAL AGENT STATES:")
        for symbol, agent in agents.items():
            memory = agent.get_agent_memory()
            print(f"\n   {symbol} ({get_stock_name(symbol)}):")
            print(f"      Trades Processed: {memory['total_trades_processed']}")
            print(f"      Risk Threshold: {memory['current_risk_threshold']}")
            print(f"      Threshold Adjustments: {memory['learned_patterns']['threshold_adjustments']}")
        
        print("\n" + "=" * 80)
        print("Thank you for using Multi-Stock Agentic Trade Validator!")
        print("=" * 80)