# trade_agent.py  -- AgenticTradeValidator (single-file, merged version)

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import re
from web3 import Web3  # for checksum helpers (fallback)
from ml_fraud_detector import MLFraudDetector  # ensure this exists
from trade_graph import build_agentic_trade_validator, AgenticTradeState

# Configure module logger (optional, can be adjusted in your app)
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class AgenticTradeValidator:
    def __init__(self, w3,
                 token_cash, token_sec,
                 abi_cash, abi_sec,
                 initial_risk_threshold: int = 10**21,
                 enable_learning: bool = True,
                 enable_ml_fraud_detection: bool = True,
                 ml_model_path: str = 'fraud_detection_model.pkl'):
        """
        Unified AgenticTradeValidator with ML integration and learning.

        Args:
            w3: Web3 instance
            token_cash: Address of cash token
            token_sec: Address of securities token
            abi_cash: ABI for cash token
            abi_sec: ABI for securities token
            initial_risk_threshold: Initial threshold for risk assessment (human units or wei)
            enable_learning: Enable learning from past trades
            enable_ml_fraud_detection: Enable ML-based fraud detection
            ml_model_path: Path to trained ML model
        """
        self.w3 = w3
        self.token_cash = token_cash
        self.token_sec = token_sec
        self.abi_cash = abi_cash
        self.abi_sec = abi_sec

        # assume ERC20 with 18 decimals unless specified otherwise
        self.decimals = 10**18

        # normalize threshold → always stored in human units
        if initial_risk_threshold > 10**9:
            # heuristic: if it's huge, assume it's in wei
            self.current_risk_threshold = int(initial_risk_threshold / self.decimals)
        else:
            self.current_risk_threshold = int(initial_risk_threshold)

        self.enable_learning = enable_learning
        self.graph = build_agentic_trade_validator()

        # Agent memory for learning
        self.trade_history: List[Dict[str, Any]] = []
        self.learned_patterns = {
            "approved_trades": [],
            "rejected_trades": [],
            "risk_adjustments": []
        }

        # Logging
        self.logger = logging.getLogger(__name__)
        self.logger.info(
            f"Agentic Trade Validator initializing "
            f"(risk threshold: {self.current_risk_threshold}, learning: {self.enable_learning})"
        )

        # ML Fraud Detector setup (safe)
        self.enable_ml_fraud_detection = enable_ml_fraud_detection
        self.ml_detector = None
        if enable_ml_fraud_detection:
            try:
                self.ml_detector = MLFraudDetector(model_path=ml_model_path)
                self.logger.info("✅ ML Fraud Detection enabled")
            except Exception as e:
                self.logger.warning(f"⚠️ ML Fraud Detection initialization failed: {e}")
                self.logger.warning("   Continuing without ML fraud detection")
                self.enable_ml_fraud_detection = False

        self.logger.info(
            f"Agentic Trade Validator initialized with adaptive capabilities "
            f"(risk threshold set to {self.current_risk_threshold} in human units, "
            f"ML enabled: {self.enable_ml_fraud_detection})"
        )

    # -------------------------
    # Input validation (single robust method)
    # -------------------------
    def validate_inputs(self, trader_cash: str, trader_sec: str,
                        required_cash: int, required_sec: int) -> Optional[str]:
        """
        Robust address + numeric validator compatible across web3.py versions.

        Returns:
            None if valid, else an error string.
        """
        # ---- Address validation helper ----
        def _is_valid_address(addr: str) -> bool:
            # Quick checks
            if not isinstance(addr, str):
                return False
            if not addr.startswith("0x") or len(addr) != 42:
                return False

            # Try version-safe checksum conversion (works on common web3 versions)
            try:
                to_checksum = getattr(Web3, "toChecksumAddress", None) or getattr(Web3, "to_checksum_address", None)
                if to_checksum:
                    try:
                        checksum = to_checksum(addr)
                        return isinstance(checksum, str) and checksum.startswith("0x") and len(checksum) == 42
                    except Exception:
                        return False
            except Exception:
                pass

            # Fallback: hex and length checks
            hex_body = addr[2:]
            if re.fullmatch(r"[0-9a-fA-F]{40}", hex_body):
                return True
            return False

        # ---- Check addresses ----
        try:
            for name, a in [("trader_cash", trader_cash), ("trader_sec", trader_sec),
                            ("token_cash", self.token_cash), ("token_sec", self.token_sec)]:
                if a is None:
                    return f"Missing address: {name}"
                if not _is_valid_address(a):
                    return f"Invalid address format for {name}: {a}"
        except Exception as e:
            return f"Address validation error: {str(e)}"

        # ---- Numeric checks ----
        try:
            for name, val in [("required_cash", required_cash), ("required_sec", required_sec)]:
                if val is None:
                    return f"Missing value: {name}"
                if not isinstance(val, (int, float)):
                    return f"Invalid type for {name}: {type(val).__name__}"
                if val < 0:
                    return f"Negative value for {name}: {val}"

            # Avoid degenerate trades
            if required_cash == 0 and required_sec == 0:
                return "Both required_cash and required_sec cannot be zero"

        except Exception as e:
            return f"Numeric validation error: {str(e)}"

        return None

    # -------------------------
    # Historical trade helpers
    # -------------------------
    def _get_similar_trades(self, required_cash: int, required_sec: int, limit: int = 5) -> List[Dict]:
        """Get similar historical trades for context"""
        if not self.trade_history:
            return []

        # Find trades with similar amounts (within 20% range)
        similar = []
        for trade in self.trade_history[-50:]:  # Look at recent 50 trades
            cash_diff = abs(trade['required_cash'] - required_cash) / max(required_cash, 1)
            sec_diff = abs(trade['required_sec'] - required_sec) / max(required_sec, 1)

            if cash_diff < 0.2 and sec_diff < 0.2:
                similar.append({
                    "amount_cash": trade['required_cash'],
                    "amount_sec": trade['required_sec'],
                    "outcome": "approved" if trade['approved'] else "rejected",
                    "timestamp": trade['timestamp'],
                    "confidence": trade.get('confidence_score', 0.5)
                })

        return similar[:limit]

    def _update_learning(self, result: Dict[str, Any]):
        """Update agent's learning from trade result"""
        if not self.enable_learning:
            return

        # Store trade in history
        trade_record = {
            "timestamp": result.get("trade_timestamp") or datetime.now().isoformat(),
            "required_cash": result["trade_details"]["required_cash"],
            "required_sec": result["trade_details"]["required_sec"],
            "approved": result.get("approved", False),
            "confidence_score": result.get("confidence_score", 0.5),
            "risk_level": result.get("risk_assessment", "unknown"),
            "reasoning": result.get("reasoning_chain", "")
        }

        self.trade_history.append(trade_record)

        # Update learned patterns
        if result.get("approved"):
            self.learned_patterns["approved_trades"].append(trade_record)
        else:
            self.learned_patterns["rejected_trades"].append(trade_record)

        # Adapt risk threshold based on results if recommended
        if result.get("recommended_threshold"):
            try:
                old_threshold = self.current_risk_threshold
                new_threshold = int(result["recommended_threshold"])
                # Gradually adjust threshold (weighted average)
                self.current_risk_threshold = int(old_threshold * 0.7 + new_threshold * 0.3)
                self.learned_patterns["risk_adjustments"].append({
                    "timestamp": datetime.now().isoformat(),
                    "old_threshold": old_threshold,
                    "new_threshold": self.current_risk_threshold,
                    "reason": "AI-recommended adjustment"
                })
                self.logger.info(f"Risk threshold adapted: {old_threshold} -> {self.current_risk_threshold}")
            except Exception as e:
                self.logger.warning(f"Failed to adapt threshold: {e}")

        # Keep history manageable (last 1000 trades)
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]

    # -------------------------
    # ML fraud detection wrapper
    # -------------------------
    def _run_ml_fraud_detection(self, trader_cash: str, trader_sec: str,
                                required_cash: int, required_sec: int) -> Dict[str, Any]:
        """
        Run ML-based fraud detection on the trade.
        Returns a dict with standardized keys.
        """
        if not self.enable_ml_fraud_detection or self.ml_detector is None:
            return {
                'is_fraudulent': False,
                'fraud_probability': 0.0,
                'risk_level': 'UNKNOWN',
                'action': 'ALLOW',
                'reasoning': 'ML fraud detection disabled',
                'features_extracted': {},
                'processing_time_ms': 0
            }

        try:
            # Minimal balance read; errors are handled and ML will default to allow
            cash_token = self.w3.eth.contract(address=self.token_cash, abi=self.abi_cash)
            sec_token = self.w3.eth.contract(address=self.token_sec, abi=self.abi_sec)

            buyer_balance = cash_token.functions.balanceOf(trader_cash).call()
            seller_balance = sec_token.functions.balanceOf(trader_sec).call()

            # Convert to human units (ether) if balances are wei
            try:
                buyer_bal_human = self.w3.fromWei(buyer_balance, 'ether')
                seller_bal_human = self.w3.fromWei(seller_balance, 'ether')
            except Exception:
                # Some Web3 builds use different casing for fromWei/from_wei; try both
                try:
                    buyer_bal_human = getattr(self.w3, "from_wei")(buyer_balance, 'ether')
                    seller_bal_human = getattr(self.w3, "from_wei")(seller_balance, 'ether')
                except Exception:
                    buyer_bal_human = (buyer_balance / (10 ** 18)) if isinstance(buyer_balance, (int, float)) else 0
                    seller_bal_human = (seller_balance / (10 ** 18)) if isinstance(seller_balance, (int, float)) else 0

            trade_price = (required_cash / required_sec) if required_sec > 0 else 0

            trade_data = {
                'token': 'GENERIC',
                'buyer_id': trader_cash,
                'seller_id': trader_sec,
                'trade_size': required_sec,
                'trade_price': trade_price,
                'market_price': trade_price,
                'buyer_balance': buyer_bal_human,
                'seller_balance': seller_bal_human,
                'timestamp': datetime.now()
            }

            ml_result = self.ml_detector.predict_fraud(trade_data)

            # Ensure keys exist and return safely
            return {
                'is_fraudulent': bool(ml_result.get('is_fraudulent', False)),
                'fraud_probability': float(ml_result.get('fraud_probability', 0.0)),
                'risk_level': ml_result.get('risk_level', 'UNKNOWN'),
                'action': ml_result.get('action', 'ALLOW'),
                'reasoning': ml_result.get('reasoning', ''),
                'features_extracted': ml_result.get('features_extracted', {}),
                'processing_time_ms': ml_result.get('processing_time_ms', 0)
            }

        except Exception as e:
            self.logger.error(f"ML fraud detection failed: {e}", exc_info=True)
            return {
                'is_fraudulent': False,
                'fraud_probability': 0.0,
                'risk_level': 'ERROR',
                'action': 'ALLOW',
                'reasoning': f'ML detection error: {str(e)}',
                'features_extracted': {},
                'processing_time_ms': 0,
                'error': str(e)
            }

    # -------------------------
    # Main assessment method
    # -------------------------
    def assess_trade(self, trader_cash: str, trader_sec: str,
                     required_cash: int, required_sec: int) -> Dict[str, Any]:
        """
        Assess a trade through both agentic validation and ML fraud detection.
        """
        start_time = datetime.now()

        # Defensive debug log
        self.logger.debug("assess_trade inputs: %s %s %s %s", trader_cash, trader_sec, required_cash, required_sec)

        # Validate inputs first
        validation_error = self.validate_inputs(trader_cash, trader_sec, required_cash, required_sec)
        if validation_error:
            return self._create_error_result(validation_error, start_time)

        # === STEP 1: ML Fraud Detection (Fast, first line of defense) ===
        ml_result = self._run_ml_fraud_detection(trader_cash, trader_sec, required_cash, required_sec)

        if ml_result.get('is_fraudulent'):
            self.logger.warning(
                f"🚨 ML FRAUD DETECTED: {trader_cash[:10]}... <-> {trader_sec[:10]}..., "
                f"probability: {ml_result.get('fraud_probability', 0):.2%}, "
                f"risk: {ml_result.get('risk_level')}"
            )

        # === STEP 2: Agentic AI Validation (Comprehensive analysis) ===
        self.logger.info(f"Agent assessing trade: {trader_cash} <-> {trader_sec}, amounts: {required_cash} / {required_sec}, threshold: {self.current_risk_threshold}")

        similar_trades = self._get_similar_trades(required_cash, required_sec)

        # Prepare agentic state with ML context
        state = {
            "party_cash": trader_cash,
            "party_sec": trader_sec,
            "required_cash": required_cash,
            "required_sec": required_sec,
            "token_cash": self.token_cash,
            "token_sec": self.token_sec,
            "agent_thoughts": [],
            "investigation_plan": [],
            "completed_checks": [],
            "risk_factors": [],
            "market_context": {},
            "similar_trades": similar_trades,
            "ml_fraud_detection": ml_result,
            "current_risk_threshold": self.current_risk_threshold,
            "confidence_score": 0.5,
            "balance": "",
            "risk_assessment": "",
            "final_decision": "",
            "reasoning_chain": "",
            "approved": False,
            "trade_timestamp": ""
        }

        try:
            result = self.graph.invoke(state)

            if result is None:
                return self._create_error_result("Agentic graph returned None (possible early error)", start_time)

            # Combine ML and agentic results
            agent_approved = result.get("approved", False)
            ml_fraud_detected = ml_result.get('is_fraudulent', False)
            ml_fraud_probability = ml_result.get('fraud_probability', 0.0)

            final_approved = agent_approved and not ml_fraud_detected

            override_reason = ""
            if agent_approved and ml_fraud_detected:
                override_reason = (
                    f"\n\n🤖 ML FRAUD DETECTION OVERRIDE:\n"
                    f"   Trade was approved by agentic AI but ML model detected fraud\n"
                    f"   Fraud Probability: {ml_fraud_probability:.1%}\n"
                    f"   Risk Level: {ml_result.get('risk_level')}\n"
                    f"   ML Reasoning: {ml_result.get('reasoning')}\n"
                    f"   FINAL DECISION: REJECTED due to ML fraud detection"
                )

            processing_time = (datetime.now() - start_time).total_seconds()
            approval_status = "APPROVED" if final_approved else "REJECTED"
            confidence = result.get("confidence_score", 0.5)
            self.logger.info(
                f"Combined decision: {approval_status} "
                f"(Agent: {'✓' if agent_approved else '✗'}, ML Fraud: {'🚨' if ml_fraud_detected else '✓'}, confidence: {confidence:.2f}) in {processing_time:.3f}s"
            )

            comprehensive_result = {
                "approved": final_approved,
                "final_decision": "approved" if final_approved else "rejected",
                "confidence_score": result.get("confidence_score", 0.5),
                "reasoning_chain": result.get("reasoning_chain", "No reasoning provided") + override_reason,
                "agent_thoughts": result.get("agent_thoughts", []),
                "investigation_plan": result.get("investigation_plan", []),
                "completed_checks": result.get("completed_checks", []),
                "risk_assessment": result.get("risk_assessment", "unknown"),
                "risk_factors": result.get("risk_factors", []),
                "market_context": result.get("market_context", {}),
                "similar_trades_analyzed": len(similar_trades),
                "ml_fraud_detection": {
                    "enabled": self.enable_ml_fraud_detection,
                    "fraud_detected": ml_fraud_detected,
                    "fraud_probability": ml_fraud_probability,
                    "risk_level": ml_result.get('risk_level', 'UNKNOWN'),
                    "reasoning": ml_result.get('reasoning', ''),
                    "processing_time_ms": ml_result.get('processing_time_ms', 0),
                    "features_used": ml_result.get('features_extracted', {})
                },
                "agent_decision": agent_approved,
                "ml_override": ml_fraud_detected and agent_approved,
                "balance_status": result.get("balance", ""),
                "trade_timestamp": result.get("trade_timestamp", datetime.now().isoformat()),
                "processing_time_seconds": processing_time,
                "trade_details": {
                    "party_cash": trader_cash,
                    "party_sec": trader_sec,
                    "required_cash": required_cash,
                    "required_sec": required_sec,
                    "token_cash": self.token_cash,
                    "token_sec": self.token_sec,
                    "current_risk_threshold": self.current_risk_threshold
                },
                "recommended_threshold": result.get("current_risk_threshold", self.current_risk_threshold),
                "threshold_adjusted": result.get("current_risk_threshold", self.current_risk_threshold) != self.current_risk_threshold,
                "metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "processing_time_seconds": processing_time,
                    "validator_type": "agentic_with_ml",
                    "learning_enabled": self.enable_learning,
                    "ml_fraud_detection_enabled": self.enable_ml_fraud_detection,
                    "historical_trades_count": len(self.trade_history)
                }
            }

            # Learn from this trade
            self._update_learning(comprehensive_result)

            return comprehensive_result

        except Exception as e:
            self.logger.error(f"Agentic trade assessment failed: {e}", exc_info=True)
            return self._create_error_result(f"Error during agentic assessment: {str(e)}", start_time)

    # -------------------------
    # Utility / batch / health methods
    # -------------------------
    def get_ml_detection_stats(self) -> Dict[str, Any]:
        """Get ML fraud detection statistics"""
        if self.ml_detector:
            return getattr(self.ml_detector, "get_detection_stats", lambda: {})()
        return {"error": "ML fraud detection not enabled"}

    def _create_error_result(self, error_message: str, start_time: datetime) -> Dict[str, Any]:
        """Create a standardized error result"""
        processing_time = (datetime.now() - start_time).total_seconds()

        return {
            "approved": False,
            "final_decision": "error",
            "confidence_score": 0.0,
            "reasoning_chain": f"Error occurred: {error_message}",
            "agent_thoughts": [f"Processing failed: {error_message}"],
            "investigation_plan": [],
            "completed_checks": [],
            "risk_assessment": "error",
            "risk_factors": ["processing_error"],
            "balance_status": "error",
            "trade_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processing_time_seconds": processing_time,
            "error": error_message,
            "metadata": {
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "processing_time_seconds": processing_time,
                "validator_type": "agentic"
            }
        }

    def assess_multiple_trades(self, trades: list) -> Dict[str, Any]:
        """
        Assess multiple trades in batch with agent learning across the batch
        """
        results = []
        start_time = datetime.now()

        self.logger.info(f"Starting agentic batch assessment of {len(trades)} trades")

        batch_insights = {
            "patterns_detected": [],
            "risk_adjustments": [],
            "confidence_progression": []
        }

        for i, trade in enumerate(trades):
            try:
                result = self.assess_trade(
                    trade['trader_cash'],
                    trade['trader_sec'],
                    trade['required_cash'],
                    trade['required_sec']
                )
                result['trade_index'] = i
                results.append(result)

                batch_insights["confidence_progression"].append({
                    "trade_index": i,
                    "confidence": result.get("confidence_score", 0.5)
                })

                if i > 0 and result.get("approved") == results[i - 1].get("approved"):
                    batch_insights["patterns_detected"].append(
                        f"Trades {i - 1} and {i} have similar outcomes"
                    )

            except Exception as e:
                self.logger.error(f"Failed to process trade {i}: {e}")
                results.append({
                    "trade_index": i,
                    "approved": False,
                    "final_decision": "error",
                    "confidence_score": 0.0,
                    "reasoning_chain": f"Processing error: {str(e)}",
                    "error": str(e)
                })

        total_trades = len(trades)
        approved_trades = sum(1 for r in results if r.get("approved", False))
        rejected_trades = total_trades - approved_trades
        total_processing_time = (datetime.now() - start_time).total_seconds()
        avg_confidence = sum(r.get("confidence_score", 0) for r in results) / total_trades if total_trades > 0 else 0
        risk_levels = [r.get("risk_assessment", "unknown") for r in results]
        high_risk_count = sum(1 for r in risk_levels if r == "high" or r == "critical")

        return {
            "batch_results": results,
            "statistics": {
                "total_trades": total_trades,
                "approved_trades": approved_trades,
                "rejected_trades": rejected_trades,
                "approval_rate": approved_trades / total_trades if total_trades > 0 else 0,
                "average_confidence": avg_confidence,
                "high_risk_trades": high_risk_count,
                "total_processing_time_seconds": total_processing_time,
                "average_processing_time_seconds": total_processing_time / total_trades if total_trades > 0 else 0
            },
            "agent_insights": {
                "patterns_detected": batch_insights["patterns_detected"],
                "confidence_progression": batch_insights["confidence_progression"],
                "final_risk_threshold": self.current_risk_threshold,
                "trades_learned_from": len(self.trade_history),
                "learning_enabled": self.enable_learning
            },
            "metadata": {
                "batch_start_time": start_time.isoformat(),
                "batch_end_time": datetime.now().isoformat(),
                "validator_type": "agentic"
            }
        }

    def get_agent_memory(self) -> Dict[str, Any]:
        return {
            "total_trades_processed": len(self.trade_history),
            "current_risk_threshold": self.current_risk_threshold,
            "learned_patterns": {
                "total_approved": len(self.learned_patterns["approved_trades"]),
                "total_rejected": len(self.learned_patterns["rejected_trades"]),
                "threshold_adjustments": len(self.learned_patterns["risk_adjustments"]),
                "recent_adjustments": self.learned_patterns["risk_adjustments"][-5:]
            },
            "recent_trades": self.trade_history[-10:] if self.trade_history else [],
            "learning_enabled": self.enable_learning,
            "timestamp": datetime.now().isoformat()
        }

    def reset_learning(self):
        self.trade_history = []
        self.learned_patterns = {
            "approved_trades": [],
            "rejected_trades": [],
            "risk_adjustments": []
        }
        self.logger.info("Agent memory and learning reset")

    def get_health_status(self) -> Dict[str, Any]:
        try:
            block_number = self.w3.eth.block_number
            network_id = self.w3.net.version

            cash_token = self.w3.eth.contract(address=self.token_cash, abi=self.abi_cash)
            sec_token = self.w3.eth.contract(address=self.token_sec, abi=self.abi_sec)

            try:
                cash_name = cash_token.functions.name().call() if hasattr(cash_token.functions, 'name') else "Unknown"
                sec_name = sec_token.functions.name().call() if hasattr(sec_token.functions, 'name') else "Unknown"
            except Exception:
                cash_name = "Unable to fetch"
                sec_name = "Unable to fetch"

            return {
                "status": "healthy",
                "validator_type": "agentic",
                "web3_connected": True,
                "current_block": block_number,
                "network_id": network_id,
                "tokens": {
                    "cash_token": {"address": self.token_cash, "name": cash_name},
                    "sec_token": {"address": self.token_sec, "name": sec_name}
                },
                "agent_state": {
                    "current_risk_threshold": self.current_risk_threshold,
                    "learning_enabled": self.enable_learning,
                    "trades_processed": len(self.trade_history),
                    "memory_size_kb": len(json.dumps(self.learned_patterns)) / 1024
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "validator_type": "agentic",
                "error": str(e),
                "web3_connected": False,
                "timestamp": datetime.now().isoformat()
            }
