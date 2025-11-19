"""
MX record lookup integration.
"""
import asyncio
import logging
import dns.resolver
import dns.exception

from worker.models import MXResult, CheckStatus
from worker.config import WorkerConfig

logger = logging.getLogger(__name__)


class MXValidator:
    """Client for validating MX records."""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
    
    async def validate_mx(self, domain: str) -> MXResult:
        """
        Validate MX records for an email domain.
        
        Args:
            domain: Email domain to validate (e.g., 'example.com' from 'user@example.com')
            
        Returns:
            MXResult with MX record information
        """
        try:
            loop = asyncio.get_event_loop()
            mx_records = await asyncio.wait_for(
                loop.run_in_executor(None, self._resolve_mx_records, domain),
                timeout=self.config.mx_timeout
            )
            
            has_mx_records = len(mx_records) > 0
            email_configured = has_mx_records
            
            return MXResult(
                has_mx_records=has_mx_records,
                mx_records=mx_records,
                email_configured=email_configured,
                status=CheckStatus.SUCCESS
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"MX lookup timeout for {domain}")
            return MXResult(
                status=CheckStatus.FAILED,
                error="MX lookup timed out"
            )
        except Exception as e:
            logger.error(f"MX lookup failed for {domain}: {str(e)}")
            return MXResult(
                status=CheckStatus.FAILED,
                error=f"MX lookup failed: {str(e)}"
            )
    
    def _resolve_mx_records(self, domain: str) -> list:
        """Resolve MX records synchronously."""
        try:
            answers = dns.resolver.resolve(domain, 'MX')
            # Sort by priority and return as list of strings
            mx_list = []
            for rdata in answers:
                mx_list.append(f"{rdata.preference} {str(rdata.exchange).rstrip('.')}")
            return sorted(mx_list)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException) as e:
            logger.debug(f"No MX records for {domain}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error resolving MX records for {domain}: {str(e)}")
            return []

