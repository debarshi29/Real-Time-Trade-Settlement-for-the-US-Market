from langgraph.graph import StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from web3 import Web3
import os
import json
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv
from datetime import datetime, timedelta
import requests
import re

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

class AgenticTradeState(TypedDict):
    # Original trade data
    party_cash: str
    party_sec: str
    required_cash: int
    required_sec: int
    token_cash: str
    token_sec: str
    
    # Agent reasoning and memory
    agent_thoughts: List[str]
    investigation_plan: List[str]
    completed_checks: List[str]
    risk_factors: List[str]
    market_context: Dict[str, Any]
    similar_trades: List[Dict]
    
    # Dynamic thresholds (learned/adapted)
    current_risk_threshold: int
    confidence_score: float
    
    # Results
    balance: str
    risk_assessment: str
    final_decision: str
    reasoning_chain: str
    approved: bool
    trade_timestamp: str

# === AGENTIC FUNCTIONS (NOT decorated with @tool) ===

def analyze_trade_pattern(party_cash: str, party_sec: str, required_cash: int, 
                         required_sec: int, trade_timestamp: str) -> dict:
    """AI agent analyzes trade patterns and context"""
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.3, google_api_key=api_key)
    
    prompt = f"""You are a sophisticated trading analysis agent. Analyze this trade and create an investigation plan.

Trade Details:
- Cash Party: {party_cash}
- Security Party: {party_sec}
- Cash Amount: {required_cash}
- Security Amount: {required_sec}
- Timestamp: {trade_timestamp}

Based on this trade, determine:
1. What specific checks should be performed?
2. What red flags or patterns should we look for?
3. What additional context is needed?
4. Risk factors to investigate
5. Confidence level in initial assessment (0-1)

Respond in JSON format with: investigation_plan (list), risk_factors (list), initial_thoughts (list), confidence_score (number)"""

    response = llm.invoke(prompt)
    try:
        # Parse the JSON response
        content = response.content.replace('```json', '').replace('```', '').strip()
        analysis = json.loads(content)
        
        # Ensure investigation_plan is a list of strings
        if "investigation_plan" in analysis:
            analysis["investigation_plan"] = [str(item) if not isinstance(item, str) else item 
                                             for item in analysis["investigation_plan"]]
        
        # Ensure risk_factors is a list of strings
        if "risk_factors" in analysis:
            analysis["risk_factors"] = [str(item) if not isinstance(item, str) else item 
                                       for item in analysis["risk_factors"]]
        
        # Ensure initial_thoughts is a list of strings
        if "initial_thoughts" in analysis:
            analysis["initial_thoughts"] = [str(item) if not isinstance(item, str) else item 
                                           for item in analysis["initial_thoughts"]]
        
        return analysis
    except Exception as e:
        # Fallback if JSON parsing fails
        return {
            "investigation_plan": ["balance_check", "risk_assessment", "pattern_analysis"],
            "risk_factors": ["large_amount", "unknown_parties"],
            "initial_thoughts": [f"Failed to parse AI response: {str(e)[:100]}"],
            "confidence_score": 0.7
        }

def dynamic_balance_check(state: dict) -> dict:
    """Enhanced balance check with contextual analysis"""
    try:
        # Original balance check logic
        party_cash = Web3.to_checksum_address(state["party_cash"])
        party_sec = Web3.to_checksum_address(state["party_sec"])
        token_cash = Web3.to_checksum_address(state["token_cash"])
        token_sec = Web3.to_checksum_address(state["token_sec"])
        required_cash = int(state["required_cash"])
        required_sec = int(state["required_sec"])

        w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
        erc20_abi = [{"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]

        cash_token = w3.eth.contract(address=token_cash, abi=erc20_abi)
        sec_token = w3.eth.contract(address=token_sec, abi=erc20_abi)

        bal_cash = cash_token.functions.balanceOf(party_cash).call()
        bal_sec = sec_token.functions.balanceOf(party_sec).call()

        # Enhanced analysis
        cash_ratio = bal_cash / required_cash if required_cash > 0 else float('inf')
        sec_ratio = bal_sec / required_sec if required_sec > 0 else float('inf')
        
        result = {
            "status": "sufficient" if bal_cash >= required_cash and bal_sec >= required_sec else "insufficient",
            "cash_balance": bal_cash,
            "sec_balance": bal_sec,
            "cash_ratio": cash_ratio,
            "sec_ratio": sec_ratio,
            "analysis": f"Cash coverage: {cash_ratio:.2f}x, Security coverage: {sec_ratio:.2f}x"
        }
        
        return result
        
    except Exception as e:
        return {"status": "error", "error": str(e), "analysis": "Balance check failed"}

def adaptive_risk_assessment(state: dict) -> dict:
    """AI-powered adaptive risk assessment"""
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.2, google_api_key=api_key)
    
    # Get current context
    required_cash = int(state.get("required_cash", 0))
    market_context = state.get("market_context", {})
    risk_factors = state.get("risk_factors", [])
    
    prompt = f"""You are an expert risk assessment agent. Analyze this trade for risk:

Trade Amount: {required_cash}
Market Context: {json.dumps(market_context, indent=2)}
Identified Risk Factors: {risk_factors}
Current Risk Threshold: {state.get('current_risk_threshold', 10**21)}

Consider:
1. Amount relative to market norms
2. Party reputation/history
3. Market conditions
4. Timing patterns
5. Similar trade patterns

Provide risk assessment as JSON:
{{
    "risk_level": "low|medium|high|critical",
    "risk_score": 0.0-1.0,
    "primary_concerns": ["concern1", "concern2"],
    "recommended_threshold": number,
    "reasoning": "detailed explanation"
}}"""

    response = llm.invoke(prompt)
    try:
        content = response.content.replace('```json', '').replace('```', '').strip()
        risk_analysis = json.loads(content)
        
        # Ensure primary_concerns is a list of strings
        if "primary_concerns" in risk_analysis:
            concerns = risk_analysis["primary_concerns"]
            if isinstance(concerns, list):
                risk_analysis["primary_concerns"] = [str(item) if not isinstance(item, str) else item 
                                                    for item in concerns]
            else:
                risk_analysis["primary_concerns"] = [str(concerns)]
        
        return risk_analysis
    except Exception as e:
        # Fallback assessment
        if required_cash > 10**21:
            return {
                "risk_level": "high",
                "risk_score": 0.8,
                "primary_concerns": ["large_amount"],
                "recommended_threshold": 10**21,
                "reasoning": f"Large trade amount exceeds standard threshold. Parse error: {str(e)[:50]}"
            }
        else:
            return {
                "risk_level": "low",
                "risk_score": 0.3,
                "primary_concerns": [],
                "recommended_threshold": 10**21,
                "reasoning": f"Trade amount within normal parameters. Parse error: {str(e)[:50]}"
            }

def market_context_analyzer(state: dict) -> dict:
    """Gather market context and similar trade patterns"""
    current_time = datetime.now()
    
    # Mock market context - replace with real market data APIs
    market_context = {
        "market_volatility": "moderate",
        "recent_volume": "high",
        "time_of_day": current_time.hour,
        "is_weekend": current_time.weekday() >= 5,
        "market_trend": "bullish"
    }
    
    # Mock similar trades analysis
    similar_trades = [
        {"amount": int(state.get("required_cash", 0)) * 0.9, "outcome": "approved", "timestamp": "2024-01-15"},
        {"amount": int(state.get("required_cash", 0)) * 1.1, "outcome": "rejected", "timestamp": "2024-01-10"}
    ]
    
    return {
        "market_context": market_context,
        "similar_trades": similar_trades,
        "market_analysis": f"Market conditions are {market_context['market_volatility']} with {market_context['recent_volume']} volume"
    }

# === AGENTIC NODES ===

def agent_planning_node(state: AgenticTradeState):
    """Agent creates investigation plan"""
    trade_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    analysis = analyze_trade_pattern(
        state.get("party_cash"),
        state.get("party_sec"),
        state.get("required_cash"),
        state.get("required_sec"),
        trade_timestamp
    )
    
    return {
        **state,
        "agent_thoughts": analysis.get("initial_thoughts", []),
        "investigation_plan": analysis.get("investigation_plan", []),
        "risk_factors": analysis.get("risk_factors", []),
        "confidence_score": analysis.get("confidence_score", 0.5),
        "trade_timestamp": trade_timestamp
    }

def context_gathering_node(state: AgenticTradeState):
    """Gather market context and patterns"""
    context_data = market_context_analyzer(state)
    
    return {
        **state,
        "market_context": context_data["market_context"],
        "similar_trades": context_data["similar_trades"],
        "completed_checks": state.get("completed_checks", []) + ["context_analysis"]
    }

def enhanced_balance_node(state: AgenticTradeState):
    """Enhanced balance checking with analysis"""
    balance_result = dynamic_balance_check(state)
    
    return {
        **state,
        "balance": balance_result["status"],
        "completed_checks": state.get("completed_checks", []) + ["balance_check"],
        "agent_thoughts": state.get("agent_thoughts", []) + [balance_result.get("analysis", "")]
    }

def intelligent_risk_node(state: AgenticTradeState):
    """AI-powered risk assessment"""
    risk_result = adaptive_risk_assessment(state)
    
    # Update dynamic threshold based on AI recommendation
    new_threshold = risk_result.get("recommended_threshold", state.get("current_risk_threshold", 10**21))
    
    return {
        **state,
        "risk_assessment": risk_result["risk_level"],
        "current_risk_threshold": new_threshold,
        "confidence_score": min(state.get("confidence_score", 0.5) + 0.1, 1.0),
        "completed_checks": state.get("completed_checks", []) + ["risk_assessment"],
        "agent_thoughts": state.get("agent_thoughts", []) + [risk_result.get("reasoning", "")]
    }

def agent_decision_node(state: AgenticTradeState):
    """Agent makes final decision with robust parsing and explicit override explanation."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.1, google_api_key=api_key)
    
    prompt = f"""You are the final decision-making agent. Review all analysis and make a decision:

INVESTIGATION RESULTS:
- Balance Status: {state.get('balance')}
- Risk Assessment: {state.get('risk_assessment')}
- Confidence Score: {state.get('confidence_score')}
- Completed Checks: {state.get('completed_checks')}
- Agent Thoughts: {state.get('agent_thoughts')}
- Market Context: {state.get('market_context')}
- Risk Factors: {state.get('risk_factors')}

Make a decision (APPROVE / REJECT / MANUAL_REVIEW) and provide detailed reasoning.

**IMPORTANT**: Prefer JSON output like:
{{"decision":"APPROVE|REJECT|MANUAL_REVIEW", "confidence":0.0, "reasoning":"detailed explanation"}}

If you cannot supply strict JSON, include a clearly labeled block:

DECISION: APPROVE
REASONING:
1. ...
2. ...

Format instructions: return either a single JSON object or a `DECISION:` block followed by `REASONING:`. """

    response = llm.invoke(prompt)
    content = response.content.replace("```json", "").replace("```", "").strip()

    # defaults
    extracted_decision = None
    llm_confidence = None
    reasoning_text = content

    # 1) Try JSON parse first
    try:
        parsed = json.loads(content)
        extracted_decision = str(parsed.get("decision", "")).strip().upper() or None
        # Accept both numeric and string confidence
        if "confidence" in parsed:
            try:
                llm_confidence = float(parsed["confidence"])
            except:
                llm_confidence = None
        reasoning_text = parsed.get("reasoning", parsed.get("explanation", reasoning_text))
    except Exception:
        # 2) Regex fallback for DECISION: and REASONING:
        m_dec = re.search(r"DECISION\s*[:\-]\s*(APPROVE|REJECT|APPROVED|REJECTED|MANUAL_REVIEW)", content, re.I)
        if m_dec:
            extracted_decision = m_dec.group(1).upper()
            if extracted_decision == "APPROVED":
                extracted_decision = "APPROVE"
            if extracted_decision == "REJECTED":
                extracted_decision = "REJECT"
        # Extract reasoning block if present
        m_reason = re.search(r"REASONING\s*[:\-]\s*(.*)$", content, re.I | re.S)
        if m_reason:
            reasoning_text = m_reason.group(1).strip()

    # Final normalization
    if extracted_decision:
        extracted_decision = extracted_decision.upper()
        if extracted_decision not in {"APPROVE", "REJECT", "MANUAL_REVIEW"}:
            # fallback to APPROVE/REJECT mapping
            if "APPROVE" in extracted_decision:
                extracted_decision = "APPROVE"
            elif "REJECT" in extracted_decision:
                extracted_decision = "REJECT"
            else:
                extracted_decision = None

    # If LLM returned no explicit decision, fall back to simple heuristics
    if extracted_decision is None:
        # check for single-word signals in the top of content
        if re.search(r"\bAPPROVE(D)?\b", content[:200], re.I):
            extracted_decision = "APPROVE"
        elif re.search(r"\bREJECT(E|ED)?\b", content[:200], re.I):
            extracted_decision = "REJECT"

    # Determine approval flag from LLM decision (pre-override)
    llm_approved = True if extracted_decision == "APPROVE" else False

    # System-level safety overrides
    conf = state.get("confidence_score", 0.5)  # agent pipeline confidence
    risk = (state.get("risk_assessment") or "").lower()
    override_notes = []

    # Example safety policy (tunable)
    # - if LLM says APPROVE but pipeline confidence < 0.5 -> override to reject (or manual_review)
    # - if risk is 'high' or 'critical' -> override to reject
    if llm_approved:
        if conf < 0.5:
            override_notes.append(f"System override: pipeline confidence too low ({conf:.2f})")
            llm_approved = False
        if risk in ("high", "critical"):
            override_notes.append(f"System override: risk level is {risk.upper()}")
            llm_approved = False
    else:
        # If LLM recommended REJECT but confidence high and risk low, keep reject (no-op)
        # If LLM recommended MANUAL_REVIEW, mark as not approved (requires human)
        if extracted_decision == "MANUAL_REVIEW":
            override_notes.append("Decision set to MANUAL_REVIEW by LLM")

    # Finalize outputs
    final_approved = bool(llm_approved)
    final_decision_str = "approved" if final_approved else ("manual_review" if extracted_decision == "MANUAL_REVIEW" else "rejected")

    # Ensure reasoning is explicit about overrides
    reasoning_full = reasoning_text.strip() or ("No reasoning provided by LLM.")
    if override_notes:
        reasoning_full += "\n\nSYSTEM OVERRIDE:\n- " + "\n- ".join(override_notes)

    # Attach structured fields for downstream consumers
    return {
        **state,
        "approved": final_approved,
        "final_decision": final_decision_str,
        "reasoning_chain": reasoning_full,
        "llm_decision_raw": extracted_decision,
        "llm_confidence": llm_confidence,
        "system_overrides": override_notes
    }

def adaptive_router(state: AgenticTradeState):
    """Dynamic routing based on agent's investigation plan"""
    completed = set(state.get("completed_checks", []))
    
    # Convert investigation_plan to set of strings (handle if items are dicts)
    investigation_plan = state.get("investigation_plan", [])
    planned = set()
    for item in investigation_plan:
        if isinstance(item, dict):
            # If it's a dict, try to extract a string key or value
            planned.update(str(k) for k in item.keys())
        elif isinstance(item, str):
            planned.add(item)
        else:
            planned.add(str(item))
    
    # Check what still needs to be done
    if "context_analysis" not in completed and "context_analysis" in planned:
        return "context_gathering"
    elif "balance_check" not in completed:
        return "enhanced_balance"
    elif "risk_assessment" not in completed:
        return "intelligent_risk"
    else:
        return "agent_decision"

def build_agentic_trade_validator():
    """Build the agentic trade validation system"""
    graph = StateGraph(AgenticTradeState)

    # Add agentic nodes
    graph.add_node("agent_planning", agent_planning_node)
    graph.add_node("context_gathering", context_gathering_node)
    graph.add_node("enhanced_balance", enhanced_balance_node)
    graph.add_node("intelligent_risk", intelligent_risk_node)
    graph.add_node("agent_decision", agent_decision_node)

    # Start with planning
    graph.set_entry_point("agent_planning")
    
    # Dynamic routing based on agent's plan
    graph.add_conditional_edges(
        "agent_planning",
        adaptive_router,
        {
            "context_gathering": "context_gathering",
            "enhanced_balance": "enhanced_balance", 
            "intelligent_risk": "intelligent_risk",
            "agent_decision": "agent_decision"
        }
    )
    
    # Continue routing after each step
    for node in ["context_gathering", "enhanced_balance", "intelligent_risk"]:
        graph.add_conditional_edges(
            node,
            adaptive_router,
            {
                "context_gathering": "context_gathering",
                "enhanced_balance": "enhanced_balance",
                "intelligent_risk": "intelligent_risk", 
                "agent_decision": "agent_decision"
            }
        )

    return graph.compile()