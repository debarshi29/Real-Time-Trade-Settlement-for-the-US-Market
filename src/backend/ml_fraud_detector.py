# ==========================
# 🤖 ML Fraud Detection Integration Module
# ==========================
# Add this new file: ml_fraud_detector.py

import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from collections import deque

class MLFraudDetector:
    """
    Machine Learning Fraud Detection System
    Integrates trained Random Forest model for real-time fraud detection
    """
    
    def __init__(self, model_path: str = 'fraud_detection_model.pkl'):
        """
        Initialize ML Fraud Detector
        
        Args:
            model_path: Path to the saved model package
        """
        self.logger = logging.getLogger(__name__)
        
        # Load the trained model package
        try:
            self.package = joblib.load(model_path)
            self.model = self.package['model']
            self.scaler = self.package['scaler']
            self.threshold = self.package['threshold']
            self.feature_names = self.package['feature_names']
            self.metadata = self.package['metadata']
            
            self.logger.info(f"✅ ML Fraud Detector loaded successfully")
            self.logger.info(f"   Model: {self.metadata['model_type']}")
            self.logger.info(f"   Threshold: {self.threshold}")
            self.logger.info(f"   ROC AUC: {self.metadata['performance_metrics']['roc_auc']:.4f}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load model: {str(e)}")
            raise
        
        # Initialize feature tracking for real-time calculation
        self.trade_history = deque(maxlen=1000)  # Track recent trades
        self.price_history = {}  # Track prices by token
        self.trader_stats = {}  # Track trader statistics
        
        # Performance tracking
        self.detection_stats = {
            'total_checks': 0,
            'fraud_detected': 0,
            'high_risk': 0,
            'medium_risk': 0,
            'low_risk': 0
        }
    
    def _calculate_rolling_volatility(self, token: str, current_price: float) -> float:
        """Calculate rolling price volatility for a token"""
        if token not in self.price_history:
            self.price_history[token] = deque(maxlen=100)
        
        self.price_history[token].append(current_price)
        
        if len(self.price_history[token]) < 2:
            return 0.1  # Default volatility
        
        prices = list(self.price_history[token])
        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                  for i in range(1, len(prices))]
        
        return float(np.std(returns)) if returns else 0.1
    
    def _get_market_trend(self, token: str) -> int:
        """Determine market trend (-1: down, 0: flat, 1: up)"""
        if token not in self.price_history or len(self.price_history[token]) < 10:
            return 0
        
        prices = list(self.price_history[token])
        recent_avg = np.mean(prices[-5:])
        older_avg = np.mean(prices[-10:-5])
        
        if recent_avg > older_avg * 1.02:
            return 1
        elif recent_avg < older_avg * 0.98:
            return -1
        return 0
    
    def _get_trader_balance_ratio(self, trader_address: str, balance: float, 
                                   total_balance: float) -> float:
        """Calculate trader's balance ratio"""
        if total_balance == 0:
            return 0.5
        return min(balance / total_balance, 1.0)
    
    def _get_trade_frequency(self, trader_address: str) -> int:
        """Get trader's recent trade frequency"""
        if trader_address not in self.trader_stats:
            self.trader_stats[trader_address] = {
                'trade_count': 0,
                'last_trade_time': None
            }
        
        return self.trader_stats[trader_address]['trade_count']
    
    def _check_counterparty_repeat(self, buyer: str, seller: str) -> int:
        """Check if buyer and seller have traded before"""
        recent_trades = list(self.trade_history)[-100:]
        pair_trades = sum(1 for t in recent_trades 
                         if (t['buyer'] == buyer and t['seller'] == seller) or
                            (t['buyer'] == seller and t['seller'] == buyer))
        return 1 if pair_trades > 0 else 0
    
    def _detect_manipulation_attempt(self, trade_data: Dict) -> int:
        """Detect potential manipulation patterns"""
        # Check for rapid price changes
        token = trade_data.get('token', 'UNKNOWN')
        price_deviation = abs(trade_data.get('price_deviation_pct', 0))
        
        # Flag if price deviation > 5% and volatility is low (suspicious)
        if price_deviation > 5.0 and trade_data.get('rolling_volatility', 1.0) < 0.1:
            return 1
        
        # Check for unusual trade patterns
        buyer = trade_data.get('buyer_id', '')
        seller = trade_data.get('seller_id', '')
        
        recent_trades = list(self.trade_history)[-20:]
        buyer_trades = sum(1 for t in recent_trades if t.get('buyer') == buyer)
        seller_trades = sum(1 for t in recent_trades if t.get('seller') == seller)
        
        # Flag if same party involved in many recent trades
        if buyer_trades > 10 or seller_trades > 10:
            return 1
        
        return 0
    
    def extract_features(self, trade_data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Extract features from raw trade data
        
        Args:
            trade_data: Dictionary containing:
                - token: Token symbol (e.g., 'AAPL')
                - buyer_id: Buyer address
                - seller_id: Seller address
                - trade_size: Number of shares/tokens
                - trade_price: Price per unit
                - market_price: Current market price
                - buyer_balance: Buyer's cash balance
                - seller_balance: Seller's security balance
                - timestamp: Trade timestamp
        
        Returns:
            DataFrame with features ready for model prediction
        """
        try:
            # Extract basic trade info
            token = trade_data.get('token', 'UNKNOWN')
            trade_size = float(trade_data.get('trade_size', 0))
            trade_price = float(trade_data.get('trade_price', 0))
            market_price = float(trade_data.get('market_price', trade_price))
            trade_value = trade_size * trade_price
            
            # Calculate derived features
            price_deviation_pct = ((trade_price - market_price) / market_price * 100) if market_price > 0 else 0
            rolling_volatility = self._calculate_rolling_volatility(token, trade_price)
            market_trend = self._get_market_trend(token)
            
            # Trader features
            buyer_id = trade_data.get('buyer_id', '')
            seller_id = trade_data.get('seller_id', '')
            buyer_balance = float(trade_data.get('buyer_balance', 0))
            seller_balance = float(trade_data.get('seller_balance', 0))
            
            # Balance ratios (simplified - in production, use total market balance)
            buyer_balance_ratio = self._get_trader_balance_ratio(buyer_id, buyer_balance, buyer_balance + 1000)
            seller_balance_ratio = self._get_trader_balance_ratio(seller_id, seller_balance, seller_balance + 1000)
            
            # Trade frequency and patterns
            trade_frequency = self._get_trade_frequency(buyer_id)
            counterparty_repeat = self._check_counterparty_repeat(buyer_id, seller_id)
            attempted_manip = self._detect_manipulation_attempt({
                'token': token,
                'price_deviation_pct': price_deviation_pct,
                'rolling_volatility': rolling_volatility,
                'buyer_id': buyer_id,
                'seller_id': seller_id
            })
            
            # Time features
            timestamp = trade_data.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            hour = timestamp.hour
            weekday = timestamp.weekday()
            
            # Create feature dictionary matching training data
            features = {
                'trade_size': trade_size,
                'trade_price': trade_price,
                'trade_value': trade_value,
                'market_price': market_price,
                'price_deviation_pct': price_deviation_pct,
                'rolling_volatility': rolling_volatility,
                'market_trend': market_trend,
                'buyer_balance_ratio': buyer_balance_ratio,
                'seller_balance_ratio': seller_balance_ratio,
                'trade_frequency': trade_frequency,
                'attempted_manip': attempted_manip,
                'hour': hour,
                'weekday': weekday,
                'counterparty_repeat': counterparty_repeat
            }
            
            # Create DataFrame with correct feature order
            feature_df = pd.DataFrame([features])[self.feature_names]
            
            # Update trade history
            self.trade_history.append({
                'timestamp': timestamp,
                'token': token,
                'buyer': buyer_id,
                'seller': seller_id,
                'size': trade_size,
                'price': trade_price
            })
            
            # Update trader stats
            for trader in [buyer_id, seller_id]:
                if trader not in self.trader_stats:
                    self.trader_stats[trader] = {'trade_count': 0, 'last_trade_time': None}
                self.trader_stats[trader]['trade_count'] += 1
                self.trader_stats[trader]['last_trade_time'] = timestamp
            
            return feature_df
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {str(e)}")
            return None
    
    def predict_fraud(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict if a trade is fraudulent
        
        Args:
            trade_data: Raw trade data dictionary
        
        Returns:
            Dictionary with prediction results
        """
        start_time = datetime.now()
        self.detection_stats['total_checks'] += 1
        
        # Extract features
        features = self.extract_features(trade_data)
        
        if features is None:
            return {
                'is_fraudulent': False,
                'fraud_probability': 0.0,
                'confidence': 0.0,
                'risk_level': 'UNKNOWN',
                'action': 'ALLOW',
                'reasoning': 'Feature extraction failed - defaulting to ALLOW',
                'processing_time_ms': 0,
                'error': 'Feature extraction failed'
            }
        
        try:
            # Get fraud probability
            fraud_probability = float(self.model.predict_proba(features)[0, 1])
            
            # Make decision using optimal threshold
            is_fraudulent = fraud_probability >= self.threshold
            
            # Calculate confidence
            confidence = fraud_probability if is_fraudulent else (1 - fraud_probability)
            
            # Determine risk level
            if fraud_probability >= 0.5:
                risk_level = 'CRITICAL'
                self.detection_stats['high_risk'] += 1
            elif fraud_probability >= 0.2:
                risk_level = 'HIGH'
                self.detection_stats['high_risk'] += 1
            elif fraud_probability >= 0.1:
                risk_level = 'MEDIUM'
                self.detection_stats['medium_risk'] += 1
            else:
                risk_level = 'LOW'
                self.detection_stats['low_risk'] += 1
            
            # Determine action
            action = 'BLOCK' if is_fraudulent else 'ALLOW'
            
            if is_fraudulent:
                self.detection_stats['fraud_detected'] += 1
            
            # Generate reasoning
            reasoning_parts = []
            if is_fraudulent:
                reasoning_parts.append(f"⚠️ FRAUD DETECTED (probability: {fraud_probability:.1%})")
                
                # Identify key risk factors
                feature_values = features.iloc[0].to_dict()
                if abs(feature_values.get('price_deviation_pct', 0)) > 5:
                    reasoning_parts.append(f"- Large price deviation: {feature_values['price_deviation_pct']:.1f}%")
                if feature_values.get('attempted_manip', 0) == 1:
                    reasoning_parts.append("- Manipulation pattern detected")
                if feature_values.get('rolling_volatility', 0) > 0.3:
                    reasoning_parts.append("- High market volatility")
            else:
                reasoning_parts.append(f"✅ Trade appears legitimate (fraud probability: {fraud_probability:.1%})")
            
            reasoning = "\n".join(reasoning_parts)
            
            # Processing time
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'is_fraudulent': bool(is_fraudulent),
                'fraud_probability': float(fraud_probability),
                'confidence': float(confidence),
                'risk_level': risk_level,
                'action': action,
                'reasoning': reasoning,
                'processing_time_ms': processing_time_ms,
                'features_extracted': features.to_dict('records')[0],
                'model_metadata': {
                    'model_type': self.metadata['model_type'],
                    'threshold': self.threshold,
                    'expected_roc_auc': self.metadata['performance_metrics']['roc_auc']
                }
            }
            
        except Exception as e:
            self.logger.error(f"Prediction failed: {str(e)}")
            return {
                'is_fraudulent': False,
                'fraud_probability': 0.0,
                'confidence': 0.0,
                'risk_level': 'UNKNOWN',
                'action': 'ALLOW',
                'reasoning': f'Prediction error: {str(e)} - defaulting to ALLOW',
                'processing_time_ms': 0,
                'error': str(e)
            }
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get fraud detection statistics"""
        total = self.detection_stats['total_checks']
        
        return {
            'total_checks': total,
            'fraud_detected': self.detection_stats['fraud_detected'],
            'fraud_rate': self.detection_stats['fraud_detected'] / total if total > 0 else 0,
            'risk_distribution': {
                'high': self.detection_stats['high_risk'],
                'medium': self.detection_stats['medium_risk'],
                'low': self.detection_stats['low_risk']
            },
            'model_info': {
                'threshold': self.threshold,
                'expected_recall': self.metadata['performance_metrics']['recall_at_threshold']
            }
        }