"""
Rule-based scoring engine.
"""
import logging
from typing import List

from worker.models import Signal
from worker.config import RULE_WEIGHTS

logger = logging.getLogger(__name__)


class RuleEngine:
    """Calculates risk scores from verification signals."""
    
    RULES = RULE_WEIGHTS
    
    def calculate_score(self, signals: List[Signal]) -> int:
        """
        Calculate risk score from signals using rule weights.
        
        Args:
            signals: List of verification signals
            
        Returns:
            Risk score from 0-100 (clamped)
        """
        total_score = 0
        
        for signal in signals:
            # Only count signals with weight > 0
            if signal.weight > 0:
                total_score += signal.weight
                logger.debug(f"Signal {signal.field}: {signal.status.value} adds {signal.weight} points (total: {total_score})")
        
        # Clamp score between 0 and 100
        final_score = max(0, min(100, total_score))
        
        logger.info(f"Calculated rule_score: {final_score} (from {total_score} raw points)")
        
        return final_score

