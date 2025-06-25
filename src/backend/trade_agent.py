from langgraph.graph import StateGraph
from langchain_core.tools import tool
from langchain.chat_models import ChatOpenAI
from web3 import Web3

# === CONFIG ===
WEB3_PROVIDER = "http://localhost:8545"
TOKENIZED_CASH = "0xF5f0b6c754226E67B723226C72d9451f9E2b68B5"
TOKENIZED_SEC = "0xYourTokenizedSecurityAddress"
BLACKLIST = {"0xBadActorAddress"}

# === WEB3 INIT ===
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))


# === TRADE STATE OBJECT ===
class TradeState(dict):
    pass


# === TOOLS ===

@tool
def check_balance(state: dict) -> str:
    try:
        amount_cash = int(state["required_cash"])
        amount_sec = int(state["required_sec"])
        trader_cash = state["party_cash"]
        trader_sec = state["party_sec"]

        cash_token = w3.eth.contract(address=Web3.to_checksum_address(state["token_cash"]), abi=[{
            "constant": True, "inputs": [{"name": "account", "type": "address"}],
            "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"
        }])

        sec_token = w3.eth.contract(address=Web3.to_checksum_address(state["token_sec"]), abi=[{
            "constant": True, "inputs": [{"name": "account", "type": "address"}],
            "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"
        }])

        bal_cash = cash_token.functions.balanceOf(trader_cash).call()
        bal_sec = sec_token.functions.balanceOf(trader_sec).call()

        if bal_cash < amount_cash or bal_sec < amount_sec:
            return "insufficient"
        return "balance_ok"
    except Exception as e:
        return f"error: {str(e)}"


@tool
def check_compliance(state: dict) -> str:
    if state["party_cash"].lower() in BLACKLIST or state["party_sec"].lower() in BLACKLIST:
        return "blacklisted"
    return "compliant"


@tool
def risk_filter(state: dict) -> str:
    try:
        amount = int(state["required_cash"])
        return "high_risk" if amount > 10**21 else "approved"
    except:
        return "approved"


# === TOOL WRAPPERS ===

def run_check_balance(state: TradeState):
    result = check_balance.invoke(state)
    return {"balance": result}

def run_check_compliance(state: TradeState):
    result = check_compliance.invoke(state)
    return {"compliance": result}

def run_risk_filter(state: TradeState):
    result = risk_filter.invoke(state)
    return {"risk": result}


# === LLM SUMMARY ON REJECTION ===

def generate_llm_summary(state: TradeState):
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    prompt = f"""A trade has been rejected. Here are the trade details:

- party_cash: {state.get('party_cash')}
- party_sec: {state.get('party_sec')}
- amount_cash: {state.get('required_cash')}
- amount_sec: {state.get('required_sec')}
- balance_status: {state.get('balance')}
- compliance_status: {state.get('compliance')}
- risk_status: {state.get('risk')}

Please explain concisely why this trade was rejected."""
    response = llm.predict(prompt)
    return {"summary": response, "approved": False}


# === DECISION LOGIC ===

def decision(state: TradeState):
    if state.get("balance") != "balance_ok":
        return "reject"
    if state.get("compliance") != "compliant":
        return "reject"
    if state.get("risk") != "approved":
        return "reject"
    return "approve"


def approve(state: TradeState):
    return {"approved": True}

def reject(state: TradeState):
    return {"approved": False}


# === GRAPH ===

def build_trade_validator():
    graph = StateGraph(TradeState)

    graph.add_node("check_balance", run_check_balance)
    graph.add_node("check_compliance", run_check_compliance)
    graph.add_node("risk_filter", run_risk_filter)
    graph.add_node("decision", decision)
    graph.add_node("generate_llm_summary", generate_llm_summary)
    graph.add_node("approve", approve)
    graph.add_node("reject", reject)

    graph.set_entry_point("check_balance")
    graph.add_edge("check_balance", "check_compliance")
    graph.add_edge("check_compliance", "risk_filter")
    graph.add_edge("risk_filter", "decision")

    graph.add_conditional_edges("decision", {
        "approve": "approve",
        "reject": "generate_llm_summary"
    })

    graph.add_edge("generate_llm_summary", "reject")

    return graph.compile()
