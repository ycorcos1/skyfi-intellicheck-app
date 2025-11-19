"""
OpenAI integration for LLM-based risk assessment.
"""
import json
import logging
import time
from typing import Dict, Any, Optional
from openai import OpenAI

from worker.config import WorkerConfig

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI API integration."""
    
    def __init__(self, config: WorkerConfig):
        """
        Initialize OpenAI client.
        
        Args:
            config: Worker configuration containing OpenAI settings
        """
        self.config = config
        self.api_key = config.openai_api_key
        self.model = config.openai_model
        self.timeout = config.openai_timeout
        self.max_retries = config.max_retries
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        self.client = OpenAI(
            api_key=self.api_key,
            timeout=self.timeout
        )
        
        # Rate limiting: 3 requests/second
        self._last_request_time = 0
        self._min_request_interval = 1.0 / 3.0  # 0.333 seconds between requests
    
    def _rate_limit_wait(self):
        """Ensure we don't exceed 3 requests/second."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            wait_time = self._min_request_interval - time_since_last
            time.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    def _build_prompt(
        self,
        submitted_data: Dict[str, Any],
        discovered_data: Dict[str, Any],
        signals: list,
        rule_score: int
    ) -> str:
        """
        Build structured prompt for OpenAI.
        
        Args:
            submitted_data: Original company data submitted
            discovered_data: Data discovered from external checks
            signals: List of verification signals
            rule_score: Current rule-based score
            
        Returns:
            Formatted prompt string
        """
        # Format signals for prompt
        signals_text = []
        for signal in signals:
            signal_dict = signal if isinstance(signal, dict) else {
                'field': signal.field,
                'status': signal.status.value if hasattr(signal.status, 'value') else str(signal.status),
                'value': signal.value,
                'weight': signal.weight,
                'severity': signal.severity.value if hasattr(signal.severity, 'value') else str(signal.severity)
            }
            signals_text.append(
                f"- {signal_dict['field']}: {signal_dict['status']} "
                f"({signal_dict['value']}, weight: {signal_dict['weight']}, severity: {signal_dict['severity']})"
            )
        
        prompt = f"""You are a risk assessment AI for enterprise verification.

Company Submitted Data:
- Name: {submitted_data.get('name', 'N/A')}
- Domain: {submitted_data.get('domain', 'N/A')}
- Email: {submitted_data.get('email', 'N/A')}
- Phone: {submitted_data.get('phone', 'N/A')}
- Website URL: {submitted_data.get('website_url', 'N/A')}

Discovered Data:
{json.dumps(discovered_data, indent=2)}

Rule-Based Signals:
{chr(10).join(signals_text)}

Current Rule Score: {rule_score}/100

Task: Provide a risk assessment adjustment based on qualitative analysis of the company's verification data.

Consider:
- Overall consistency of submitted vs discovered data
- Patterns that might indicate fraud or legitimate business
- Contextual factors not captured by rules
- Professional judgment on risk level

Output your response as a JSON object with exactly these fields:
{{
  "llm_summary": "2-3 sentence executive summary of the risk assessment",
  "llm_details": "Detailed paragraph explaining your reasoning, notable patterns, and any concerns or positive indicators",
  "llm_score_adjustment": <integer between -20 and +20>
}}

The llm_score_adjustment should modify the rule_score based on qualitative factors:
- Negative values (-20 to -1) for lower risk indicators
- Positive values (+1 to +20) for higher risk indicators
- 0 if no adjustment needed

Respond with ONLY the JSON object, no additional text."""
        
        return prompt
    
    def generate_analysis(
        self,
        submitted_data: Dict[str, Any],
        discovered_data: Dict[str, Any],
        signals: list,
        rule_score: int
    ) -> Dict[str, Any]:
        """
        Generate LLM-based analysis and score adjustment.
        
        Args:
            submitted_data: Original company data submitted
            discovered_data: Data discovered from external checks
            signals: List of verification signals
            rule_score: Current rule-based score
            
        Returns:
            Dictionary with:
            - llm_summary: str
            - llm_details: str
            - llm_score_adjustment: int
            
        Raises:
            Exception: If API call fails after retries
        """
        prompt = self._build_prompt(submitted_data, discovered_data, signals, rule_score)
        
        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                self._rate_limit_wait()
                
                logger.info(f"Calling OpenAI API (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a risk assessment AI for enterprise verification. Always respond with valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for more consistent results
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                )
                
                # Parse response
                content = response.choices[0].message.content
                logger.debug(f"OpenAI response: {content}")
                
                # Parse JSON response
                try:
                    result = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse OpenAI JSON response: {e}")
                    # Try to extract JSON from response if wrapped in text
                    import re
                    json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        raise ValueError(f"Invalid JSON response from OpenAI: {content}")
                
                # Validate response structure
                required_fields = ['llm_summary', 'llm_details', 'llm_score_adjustment']
                for field in required_fields:
                    if field not in result:
                        raise ValueError(f"Missing required field in OpenAI response: {field}")
                
                # Validate and clamp score adjustment
                adjustment = result['llm_score_adjustment']
                if not isinstance(adjustment, int):
                    adjustment = int(adjustment)
                result['llm_score_adjustment'] = max(-20, min(20, adjustment))
                
                logger.info(
                    f"OpenAI analysis complete: "
                    f"summary_length={len(result['llm_summary'])}, "
                    f"adjustment={result['llm_score_adjustment']}"
                )
                
                return result
                
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                
                # Check if it's a rate limit error (common patterns)
                is_rate_limit = (
                    "rate limit" in str(e).lower() or 
                    "429" in str(e) or
                    error_type == "RateLimitError"
                )
                
                if is_rate_limit:
                    wait_time = (2 ** attempt) * 1.0  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Rate limit error (attempt {attempt + 1}/{self.max_retries}): {e}. Waiting {wait_time}s")
                    if attempt < self.max_retries - 1:
                        time.sleep(wait_time)
                        continue
                
                # For other API errors, retry with backoff
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 1.0
                    logger.warning(f"API error (attempt {attempt + 1}/{self.max_retries}): {e}. Waiting {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.error(f"OpenAI API error after {self.max_retries} attempts: {e}")
                    raise
        
        # If we get here, all retries failed
        raise Exception(f"OpenAI API call failed after {self.max_retries} attempts: {last_error}")

