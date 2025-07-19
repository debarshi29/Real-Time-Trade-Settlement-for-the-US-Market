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
    try:
        party_cash = Web3.to_checksum_address(state["party_cash"])
        party_sec = Web3.to_checksum_address(state["party_sec"])
        token_cash = Web3.to_checksum_address(state["token_cash"])
        token_sec = Web3.to_checksum_address(state["token_sec"])
        required_cash = int(state["required_cash"])
        required_sec = int(state["required_sec"])

        w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

        erc20_abi = [{
            "constant": True,
            "inputs": [{"name": "account", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "type": "function"
        }]

        cash_token = w3.eth.contract(address=token_cash, abi=erc20_abi)
        sec_token = w3.eth.contract(address=token_sec, abi=erc20_abi)

        bal_cash = cash_token.functions.balanceOf(party_cash).call()
        bal_sec = sec_token.functions.balanceOf(party_sec).call()

        if bal_cash >= required_cash and bal_sec >= required_sec:
            return "balance_ok"
        else:
            return "insufficient"
        
    except Exception as e:
        return f"error: {str(e)}"

def risk_filter(state: dict) -> str:
    try:
        required_cash = int(state["required_cash"])
        return "high_risk" if required_cash > 10**21 else "approved"
    except:
        return "approved"

# === Tool Wrappers ===
def run_check_balance(state: TradeState):
    result = check_balance(state)
    return {**state, "balance": result}

def run_risk_filter(state: TradeState):
    result = risk_filter(state)
    return {**state, "risk": result}

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
    balance_status = state.get("balance")
    risk_status = state.get("risk")
    
    if balance_status != "balance_ok":
        return "reject"
    if risk_status != "approved":
        return "reject"
    
    return "approve"

def approve(state: TradeState):
    return {**state, "approved": True, "reason": "Trade approved - all checks passed"}

def reject(state: TradeState):
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
