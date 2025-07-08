from unittest import result
from trade_graph import build_trade_validator, TradeState
import json

class TradeValidator:
    def __init__(self, w3, token_cash, token_sec, abi_cash, abi_sec):
        self.w3 = w3
        self.token_cash = token_cash
        self.token_sec = token_sec
        self.abi_cash = abi_cash
        self.abi_sec = abi_sec
        self.graph = build_trade_validator()

    def assess_trade(self, trader_cash, trader_sec, required_cash, required_sec):
        state = {
            "party_cash": trader_cash,
            "party_sec": trader_sec,
            "required_cash": required_cash,
            "required_sec": required_sec,
            "token_cash": self.token_cash,
            "token_sec": self.token_sec
        }

        print("\n🧪 Passing initial trade state to LangGraph:")
        print(json.dumps(state, indent=2))

        result = self.graph.invoke(state)

        if result is None:
            return {"approved": False, "reason": "Graph returned None (possible early error)"}
        return result

