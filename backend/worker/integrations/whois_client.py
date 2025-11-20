"""
WHOIS lookup integration.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
import whois
from dateutil import parser as date_parser

from worker.models import WhoisResult, CheckStatus
from worker.config import WorkerConfig

logger = logging.getLogger(__name__)


class WhoisClient:
    """Client for performing WHOIS lookups."""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
    
    async def lookup(self, domain: str) -> WhoisResult:
        """
        Perform WHOIS lookup for a domain.
        
        Args:
            domain: Domain name to look up
            
        Returns:
            WhoisResult with domain information
        """
        try:
            # Run WHOIS lookup in executor to avoid blocking
            loop = asyncio.get_event_loop()
            whois_data = await asyncio.wait_for(
                loop.run_in_executor(None, self._sync_whois_lookup, domain),
                timeout=self.config.whois_timeout
            )
            
            if not whois_data:
                return WhoisResult(
                    status=CheckStatus.FAILED,
                    error="No WHOIS data returned"
                )
            
            # Extract domain age
            domain_age_days = None
            creation_date = None
            if hasattr(whois_data, 'creation_date'):
                creation_date = self._parse_date(whois_data.creation_date)
                if creation_date:
                    # Ensure both datetimes are naive (no timezone) for subtraction
                    now = datetime.utcnow()
                    # _parse_date already normalizes to naive, so just subtract
                    from datetime import timedelta
                    age_delta = now - creation_date
                    if isinstance(age_delta, timedelta):
                        domain_age_days = age_delta.days
                    else:
                        # Fallback if subtraction fails
                        domain_age_days = None
            
            # Extract registrar
            registrar = None
            if hasattr(whois_data, 'registrar'):
                registrar = str(whois_data.registrar)
            
            # Check for privacy protection
            privacy_enabled = False
            if hasattr(whois_data, 'name_servers'):
                # Check if nameservers suggest privacy (common privacy services)
                privacy_indicators = ['privacy', 'whoisguard', 'domainsbyproxy', 'namecheap']
                if whois_data.name_servers:
                    for ns in whois_data.name_servers:
                        if any(indicator in str(ns).lower() for indicator in privacy_indicators):
                            privacy_enabled = True
                            break
            
            # Also check registrar name for privacy indicators
            if registrar and any(indicator in registrar.lower() for indicator in privacy_indicators):
                privacy_enabled = True
            
            return WhoisResult(
                domain_age_days=domain_age_days,
                registrar=registrar,
                privacy_enabled=privacy_enabled,
                creation_date=creation_date,
                status=CheckStatus.SUCCESS
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"WHOIS lookup timeout for {domain}")
            return WhoisResult(
                status=CheckStatus.FAILED,
                error="WHOIS lookup timed out"
            )
        except Exception as e:
            logger.error(f"WHOIS lookup failed for {domain}: {str(e)}")
            return WhoisResult(
                status=CheckStatus.FAILED,
                error=f"WHOIS lookup failed: {str(e)}"
            )
    
    def _sync_whois_lookup(self, domain: str):
        """Synchronous WHOIS lookup (runs in executor)."""
        try:
            return whois.whois(domain)
        except Exception as e:
            logger.error(f"WHOIS library error for {domain}: {str(e)}")
            return None
    
    def _parse_date(self, date_value) -> Optional[datetime]:
        """Parse date from various formats."""
        if date_value is None:
            return None
        
        # Handle list of dates (some WHOIS returns multiple)
        if isinstance(date_value, list):
            if not date_value:
                return None
            date_value = date_value[0]
        
        # Already a datetime
        if isinstance(date_value, datetime):
            # Normalize to naive datetime (remove timezone info)
            if date_value.tzinfo is not None:
                return date_value.replace(tzinfo=None)
            return date_value
        
        # Try to parse string
        try:
            parsed = date_parser.parse(str(date_value))
            # Normalize to naive datetime
            if parsed.tzinfo is not None:
                return parsed.replace(tzinfo=None)
            return parsed
        except Exception:
            return None

