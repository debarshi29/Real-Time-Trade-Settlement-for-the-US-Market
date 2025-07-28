from trade_graph import build_trade_validator, TradeState
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

class TradeValidator:
    def __init__(self, w3, token_cash, token_sec, abi_cash, abi_sec, risk_threshold: int = 10**21):
        """
        Initialize TradeValidator
        
        Args:
            w3: Web3 instance
            token_cash: Address of cash token
            token_sec: Address of securities token
            abi_cash: ABI for cash token
            abi_sec: ABI for securities token
            risk_threshold: Threshold for high-risk trades (default: 10^21)
        """
        self.w3 = w3
        self.token_cash = token_cash
        self.token_sec = token_sec
        self.abi_cash = abi_cash
        self.abi_sec = abi_sec
        self.risk_threshold = risk_threshold
        self.graph = build_trade_validator()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    def validate_inputs(self, trader_cash: str, trader_sec: str, 
                       required_cash: int, required_sec: int) -> Optional[str]:
        """
        Validate input parameters before processing
        
        Returns:
            None if valid, error message if invalid
        """
        try:
            # Check if addresses are valid
            if not self.w3.is_address(trader_cash):
                return f"Invalid trader_cash address: {trader_cash}"
            if not self.w3.is_address(trader_sec):
                return f"Invalid trader_sec address: {trader_sec}"
            if not self.w3.is_address(self.token_cash):
                return f"Invalid token_cash address: {self.token_cash}"
            if not self.w3.is_address(self.token_sec):
                return f"Invalid token_sec address: {self.token_sec}"
                
            # Check if amounts are non-negative
            if required_cash < 0:
                return f"Required cash cannot be negative: {required_cash}"
            if required_sec < 0:
                return f"Required securities cannot be negative: {required_sec}"
                
            # Check if amounts are reasonable (not zero for both)
            if required_cash == 0 and required_sec == 0:
                return "Both required amounts cannot be zero"
                
            return None
            
        except Exception as e:
            return f"Input validation error: {str(e)}"

    def assess_trade(self, trader_cash: str, trader_sec: str, 
                    required_cash: int, required_sec: int) -> Dict[str, Any]:
        """
        Assess a trade through the validation pipeline
        
        Args:
            trader_cash: Address of the cash trader
            trader_sec: Address of the securities trader
            required_cash: Required cash amount
            required_sec: Required securities amount
            
        Returns:
            Dictionary with trade assessment results
        """
        start_time = datetime.now()
        
        # Validate inputs first
        validation_error = self.validate_inputs(trader_cash, trader_sec, required_cash, required_sec)
        if validation_error:
            return self._create_error_result(validation_error, start_time)
        
        # Log trade attempt
        self.logger.info(f"Assessing trade: {trader_cash} <-> {trader_sec}, "
                        f"amounts: {required_cash} / {required_sec}")
        
        state = {
            "party_cash": trader_cash,
            "party_sec": trader_sec,
            "required_cash": required_cash,
            "required_sec": required_sec,
            "token_cash": self.token_cash,
            "token_sec": self.token_sec,
            "balance": "",
            "risk": "",
            "approved": False,
            "summary": "",
            "reason": "",
            "trade_timestamp": ""
        }

        try:
            result = self.graph.invoke(state)
            
            if result is None:
                return self._create_error_result(
                    "Graph returned None (possible early error)", 
                    start_time
                )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Log result
            approval_status = "APPROVED" if result.get("approved", False) else "REJECTED"
            self.logger.info(f"Trade {approval_status} in {processing_time:.3f}s: {result.get('reason', 'Unknown')}")
            
            # Return comprehensive result
            return {
                "approved": result.get("approved", False),
                "reason": result.get("reason", "Unknown"),
                "summary": result.get("summary", "No summary available"),
                "trade_timestamp": result.get("trade_timestamp", ""),
                "balance_status": result.get("balance", ""),
                "risk_status": result.get("risk", ""),
                "processing_time_seconds": processing_time,
                "trade_details": {
                    "party_cash": trader_cash,
                    "party_sec": trader_sec,
                    "required_cash": required_cash,
                    "required_sec": required_sec,
                    "token_cash": self.token_cash,
                    "token_sec": self.token_sec,
                    "risk_threshold": self.risk_threshold
                },
                "metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "processing_time_seconds": processing_time
                }
            }
            
        except Exception as e:
            self.logger.error(f"Trade assessment failed: {str(e)}", exc_info=True)
            return self._create_error_result(f"Error during trade assessment: {str(e)}", start_time)

    def _create_error_result(self, error_message: str, start_time: datetime) -> Dict[str, Any]:
        """Create a standardized error result"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "approved": False,
            "reason": error_message,
            "summary": f"Trade processing failed: {error_message}",
            "trade_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "balance_status": "error",
            "risk_status": "error",
            "processing_time_seconds": processing_time,
            "error": error_message,
            "metadata": {
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "processing_time_seconds": processing_time
            }
        }

    def assess_multiple_trades(self, trades: list) -> Dict[str, Any]:
        """
        Assess multiple trades in batch
        
        Args:
            trades: List of trade dictionaries with keys:
                   ['trader_cash', 'trader_sec', 'required_cash', 'required_sec']
                   
        Returns:
            Dictionary with batch results and statistics
        """
        results = []
        start_time = datetime.now()
        
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
                
            except Exception as e:
                self.logger.error(f"Failed to process trade {i}: {str(e)}")
                results.append({
                    "trade_index": i,
                    "approved": False,
                    "reason": f"Processing error: {str(e)}",
                    "error": str(e)
                })
        
        # Calculate batch statistics
        total_trades = len(trades)
        approved_trades = sum(1 for r in results if r.get("approved", False))
        rejected_trades = total_trades - approved_trades
        total_processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "batch_results": results,
            "statistics": {
                "total_trades": total_trades,
                "approved_trades": approved_trades,
                "rejected_trades": rejected_trades,
                "approval_rate": approved_trades / total_trades if total_trades > 0 else 0,
                "total_processing_time_seconds": total_processing_time,
                "average_processing_time_seconds": total_processing_time / total_trades if total_trades > 0 else 0
            },
            "metadata": {
                "batch_start_time": start_time.isoformat(),
                "batch_end_time": datetime.now().isoformat()
            }
        }

    def get_health_status(self) -> Dict[str, Any]:
        """
        Check the health of the validator system
        
        Returns:
            Health status information
        """
        try:
            # Test Web3 connection
            block_number = self.w3.eth.block_number
            network_id = self.w3.net.version
            
            # Test token contracts
            cash_token = self.w3.eth.contract(address=self.token_cash, abi=self.abi_cash)
            sec_token = self.w3.eth.contract(address=self.token_sec, abi=self.abi_sec)
            
            # Try to get token info
            try:
                cash_name = cash_token.functions.name().call() if hasattr(cash_token.functions, 'name') else "Unknown"
                sec_name = sec_token.functions.name().call() if hasattr(sec_token.functions, 'name') else "Unknown"
            except:
                cash_name = "Unable to fetch"
                sec_name = "Unable to fetch"
            
            return {
                "status": "healthy",
                "web3_connected": True,
                "current_block": block_number,
                "network_id": network_id,
                "tokens": {
                    "cash_token": {
                        "address": self.token_cash,
                        "name": cash_name
                    },
                    "sec_token": {
                        "address": self.token_sec,
                        "name": sec_name
                    }
                },
                "risk_threshold": self.risk_threshold,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "web3_connected": False,
                "timestamp": datetime.now().isoformat()
            }