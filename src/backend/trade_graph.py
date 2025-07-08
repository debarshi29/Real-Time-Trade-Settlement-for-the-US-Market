from langgraph.graph import StateGraph
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from web3 import Web3
import os
import json
from typing import TypedDict
from dotenv import load_dotenv
load_dotenv()

# === GOOGLE GEMINI API KEY ===
api_key = os.getenv("GOOGLE_API_KEY")

# === Trade State ===
from typing import TypedDict

class TradeState(TypedDict):
    party_cash: str
    party_sec: str
    required_cash: int
    required_sec: int
    token_cash: str
    token_sec: str
    balance: str
    risk: str
    approved: bool
    summary: str
    reason: str

# === TOOLS ===
def check_balance(state: dict) -> str:
    """Check if the trader has enough tokenized cash and securities."""
    try:
        party_cash = state["party_cash"]
        party_sec = state["party_sec"]
        required_cash = int(state["required_cash"])
        required_sec = int(state["required_sec"])
        token_cash = state["token_cash"]
        token_sec = state["token_sec"]

        # Create a proper Web3 connection instead of using Web3()
        # You might need to adjust this based on your setup
        w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))  # Adjust URL as needed
        
        # Minimal ERC20 ABI for balanceOf
        erc20_abi = [{
            "constant": True,
            "inputs": [{"name": "account", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "type": "function"
        }]

        cash_token = w3.eth.contract(
            address=Web3.to_checksum_address(token_cash), 
            abi=erc20_abi
        )
        sec_token = w3.eth.contract(
            address=Web3.to_checksum_address(token_sec), 
            abi=erc20_abi
        )

        bal_cash = cash_token.functions.balanceOf(party_cash).call()
        bal_sec = sec_token.functions.balanceOf(party_sec).call()

        print(f"DEBUG: Cash balance: {bal_cash}, Required: {required_cash}")
        print(f"DEBUG: Sec balance: {bal_sec}, Required: {required_sec}")

        return "balance_ok" if bal_cash >= required_cash and bal_sec >= required_sec else "insufficient"
    except Exception as e:
        print(f"ERROR in check_balance: {e}")
        return f"error: {str(e)}"

def risk_filter(state: dict) -> str:
    """Flag trades with unusually large cash amounts."""
    try:
        required_cash = int(state["required_cash"])
        return "high_risk" if required_cash > 10**21 else "approved"
    except:
        return "approved"

# === Tool Wrappers ===

def run_check_balance(state: TradeState):
    print(f"DEBUG: State keys available: {list(state.keys())}")
    print(f"DEBUG: Full state: {state}")
    try:
        result = check_balance(state)
        print(f"DEBUG: Balance check result: {result}")
        return {**state, "balance": result}
    except Exception as e:
        print(f"ERROR in check_balance: {e}")
        return {**state, "balance": "error"}

def run_risk_filter(state: TradeState):
    print(f"DEBUG: Risk filter state: {state}")
    try:
        result = risk_filter(state)
        print(f"DEBUG: Risk filter result: {result}")
        return {**state, "risk": result}
    except Exception as e:
        print(f"ERROR in risk_filter: {e}")
        return {**state, "risk": "error"}

# === LLM Summary ===

def generate_llm_summary(state: TradeState):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=api_key)
    prompt = f"""A trade has been rejected. Here are the trade details:

- party_cash: {state.get('party_cash')}
- party_sec: {state.get('party_sec')}
- amount_cash: {state.get('required_cash')}
- amount_sec: {state.get('required_sec')}
- balance_status: {state.get('balance')}
- risk_status: {state.get('risk')}

Please explain concisely why this trade was rejected."""
    response = llm.invoke(prompt)
    return {**state, "summary": response.content, "approved": False}

# === Routing Logic ===

def decision_router(state: TradeState):
    """Route based on balance and risk checks."""
    print(f"DEBUG: Decision router state: {state}")
    balance_status = state.get("balance")
    risk_status = state.get("risk")
    print(f"DEBUG: Balance status: {balance_status}, Risk status: {risk_status}")
    
    if balance_status != "balance_ok":
        print("DEBUG: Routing to reject due to balance")
        return "reject"
    if risk_status != "approved":
        print("DEBUG: Routing to reject due to risk")
        return "reject"
    
    print("DEBUG: Routing to approve")
    return "approve"

def approve(state: TradeState):
    return {**state, "approved": True, "reason": "Trade approved - all checks passed"}

def reject(state: TradeState):
    # Create a reason based on the rejection cause
    reasons = []
    if state.get("balance") != "balance_ok":
        reasons.append(f"Balance check failed: {state.get('balance')}")
    if state.get("risk") != "approved":
        reasons.append(f"Risk check failed: {state.get('risk')}")
    
    reason = "; ".join(reasons) if reasons else "Trade rejected"
    return {**state, "approved": False, "reason": reason}

# === Graph Builder ===

def build_trade_validator():
    graph = StateGraph(TradeState)

    graph.add_node("check_balance", run_check_balance)
    graph.add_node("risk_filter", run_risk_filter)
    graph.add_node("generate_llm_summary", generate_llm_summary)
    graph.add_node("approve", approve)
    graph.add_node("reject", reject)

    graph.set_entry_point("check_balance")
    graph.add_edge("check_balance", "risk_filter")
    
    # Fixed conditional edges - removed condition_key parameter
    graph.add_conditional_edges(
        "risk_filter",
        decision_router,
        {
            "approve": "approve",
            "reject": "generate_llm_summary"
        }
    )

    graph.add_edge("generate_llm_summary", "reject")

    return graph.compile()