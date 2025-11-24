"""
Signal generation from verification checks.
"""
import logging
from typing import List, Optional
from datetime import datetime

from worker.models import (
    Signal, SignalStatus, SignalSeverity,
    WhoisResult, DNSResult, WebResult, MXResult, PhoneResult
)
from worker.config import RULE_WEIGHTS

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Generates verification signals from check results."""
    
    def generate_signals(
        self,
        submitted_data: dict,
        whois_result: Optional[WhoisResult],
        dns_result: Optional[DNSResult],
        web_result: Optional[WebResult],
        mx_result: Optional[MXResult],
        phone_result: Optional[PhoneResult]
    ) -> List[Signal]:
        """
        Generate signals by comparing submitted vs discovered data.
        
        Args:
            submitted_data: Original company data submitted
            whois_result: WHOIS lookup result
            dns_result: DNS resolution result
            web_result: Website fetch result
            mx_result: MX validation result
            phone_result: Phone normalization result
            
        Returns:
            List of Signal objects
        """
        signals = []
        
        # Domain age signal
        if whois_result and whois_result.status.value == "success":
            if whois_result.domain_age_days is not None:
                if whois_result.domain_age_days < 365:
                    signals.append(Signal(
                        field="domain_age",
                        status=SignalStatus.SUSPICIOUS,
                        value=f"{whois_result.domain_age_days} days",
                        weight=RULE_WEIGHTS.get("domain_age_lt_1_year", 20),
                        severity=SignalSeverity.HIGH
                    ))
                else:
                    signals.append(Signal(
                        field="domain_age",
                        status=SignalStatus.OK,
                        value=f"{whois_result.domain_age_days} days",
                        weight=0,
                        severity=SignalSeverity.LOW
                    ))
            else:
                signals.append(Signal(
                    field="domain_age",
                    status=SignalStatus.SUSPICIOUS,
                    value="Unknown",
                    weight=RULE_WEIGHTS.get("domain_age_lt_1_year", 20),
                    severity=SignalSeverity.HIGH
                ))
        else:
            signals.append(Signal(
                field="domain_age",
                status=SignalStatus.SUSPICIOUS,
                value="Check failed",
                weight=RULE_WEIGHTS.get("domain_age_lt_1_year", 20),
                severity=SignalSeverity.HIGH
            ))
        
        # WHOIS privacy signal
        if whois_result and whois_result.status.value == "success":
            if whois_result.privacy_enabled:
                signals.append(Signal(
                    field="whois_privacy",
                    status=SignalStatus.SUSPICIOUS,
                    value="Privacy enabled",
                    weight=RULE_WEIGHTS.get("whois_privacy_enabled", 10),
                    severity=SignalSeverity.MEDIUM
                ))
            else:
                signals.append(Signal(
                    field="whois_privacy",
                    status=SignalStatus.OK,
                    value="No privacy protection",
                    weight=0,
                    severity=SignalSeverity.LOW
                ))
        
        # DNS resolution signal
        if dns_result and dns_result.status.value == "success":
            if dns_result.resolves:
                signals.append(Signal(
                    field="dns_resolution",
                    status=SignalStatus.OK,
                    value=f"Resolves to {len(dns_result.a_records)} IP(s)",
                    weight=0,
                    severity=SignalSeverity.LOW
                ))
            else:
                signals.append(Signal(
                    field="dns_resolution",
                    status=SignalStatus.SUSPICIOUS,
                    value="Domain does not resolve",
                    weight=15,  # Custom weight for DNS failure
                    severity=SignalSeverity.HIGH
                ))
        else:
            signals.append(Signal(
                field="dns_resolution",
                status=SignalStatus.SUSPICIOUS,
                value="Check failed",
                weight=15,  # Same weight as "domain does not resolve"
                severity=SignalSeverity.HIGH
            ))
        
        # Website reachability signal
        if web_result and web_result.status.value == "success":
            if web_result.reachable:
                signals.append(Signal(
                    field="website_lookup",
                    status=SignalStatus.OK,
                    value=f"HTTP {web_result.status_code}",
                    weight=0,
                    severity=SignalSeverity.LOW
                ))
            else:
                signals.append(Signal(
                    field="website_lookup",
                    status=SignalStatus.SUSPICIOUS,
                    value=f"Unreachable (HTTP {web_result.status_code})",
                    weight=RULE_WEIGHTS.get("website_unreachable", 25),
                    severity=SignalSeverity.HIGH
                ))
        else:
            signals.append(Signal(
                field="website_lookup",
                status=SignalStatus.SUSPICIOUS,
                value="Check failed",
                weight=RULE_WEIGHTS.get("website_unreachable", 25),
                severity=SignalSeverity.HIGH
            ))
        
        # Email/MX validation signal
        submitted_email = submitted_data.get("email", "")
        submitted_domain = submitted_data.get("domain", "")
        
        if submitted_email and "@" in submitted_email:
            email_domain = submitted_email.split("@")[-1]
            
            # Check if email domain matches company domain
            if email_domain.lower() != submitted_domain.lower():
                signals.append(Signal(
                    field="email_match",
                    status=SignalStatus.MISMATCH,
                    value=f"Email domain ({email_domain}) != company domain ({submitted_domain})",
                    weight=RULE_WEIGHTS.get("email_mismatch", 10),
                    severity=SignalSeverity.MEDIUM
                ))
            else:
                # Validate MX records for email domain
                if mx_result and mx_result.status.value == "success":
                    if mx_result.has_mx_records:
                        signals.append(Signal(
                            field="email_match",
                            status=SignalStatus.OK,
                            value=f"Domain matches, MX records configured ({len(mx_result.mx_records)} records)",
                            weight=0,
                            severity=SignalSeverity.LOW
                        ))
                    else:
                        signals.append(Signal(
                            field="email_match",
                            status=SignalStatus.SUSPICIOUS,
                            value="Domain matches but no MX records",
                            weight=RULE_WEIGHTS.get("no_mx_records", 15),
                            severity=SignalSeverity.MEDIUM
                        ))
                else:
                    signals.append(Signal(
                        field="email_match",
                        status=SignalStatus.SUSPICIOUS,
                        value="Domain matches (MX check failed)",
                        weight=RULE_WEIGHTS.get("no_mx_records", 15),
                        severity=SignalSeverity.MEDIUM
                    ))
        elif mx_result and mx_result.status.value == "success":
            # No email submitted, but check MX for domain
            if not mx_result.has_mx_records:
                signals.append(Signal(
                    field="mx_records",
                    status=SignalStatus.SUSPICIOUS,
                    value="No MX records for domain",
                    weight=RULE_WEIGHTS.get("no_mx_records", 15),
                    severity=SignalSeverity.MEDIUM
                ))
        
        # Phone validation signal
        submitted_phone = submitted_data.get("phone", "")
        if submitted_phone:
            if phone_result and phone_result.status.value == "success":
                if phone_result.valid:
                    # Check for region mismatch (simplified - could be enhanced)
                    signals.append(Signal(
                        field="phone_validation",
                        status=SignalStatus.OK,
                        value=f"Valid ({phone_result.region})",
                        weight=0,
                        severity=SignalSeverity.LOW
                    ))
                else:
                    signals.append(Signal(
                        field="phone_validation",
                        status=SignalStatus.SUSPICIOUS,
                        value="Invalid phone number format",
                        weight=5,  # Lower weight for invalid format
                        severity=SignalSeverity.MEDIUM
                    ))
            else:
                signals.append(Signal(
                    field="phone_validation",
                    status=SignalStatus.SUSPICIOUS,
                    value="Check failed",
                    weight=10,  # Moderate weight since phone is optional
                    severity=SignalSeverity.MEDIUM
                ))
        
        return signals
    
    def compute_hybrid_score(
        self,
        rule_score: int,
        llm_score_adjustment: int
    ) -> int:
        """
        Compute final hybrid risk score combining rule-based and LLM adjustments.
        
        Formula: final_score = clamp(rule_score + llm_score_adjustment, 0, 100)
        
        Args:
            rule_score: Rule-based score (0-100)
            llm_score_adjustment: LLM adjustment (-20 to +20)
            
        Returns:
            Final risk score clamped between 0 and 100
        """
        final_score = max(0, min(100, rule_score + llm_score_adjustment))
        logger.info(
            f"Hybrid score calculation: rule_score={rule_score}, "
            f"llm_adjustment={llm_score_adjustment}, final_score={final_score}"
        )
        return final_score

