"""
DNS query integration.
"""
import asyncio
import logging
import dns.resolver
import dns.exception

from worker.models import DNSResult, CheckStatus
from worker.config import WorkerConfig

logger = logging.getLogger(__name__)


class DNSClient:
    """Client for performing DNS queries."""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
    
    async def resolve(self, domain: str) -> DNSResult:
        """
        Resolve DNS records for a domain.
        
        Args:
            domain: Domain name to resolve
            
        Returns:
            DNSResult with DNS information
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Resolve A records
            a_records = await asyncio.wait_for(
                loop.run_in_executor(None, self._resolve_a_records, domain),
                timeout=self.config.dns_timeout
            )
            
            # Resolve nameservers
            nameservers = await asyncio.wait_for(
                loop.run_in_executor(None, self._resolve_nameservers, domain),
                timeout=self.config.dns_timeout
            )
            
            resolves = len(a_records) > 0
            
            return DNSResult(
                resolves=resolves,
                nameservers=nameservers,
                a_records=a_records,
                status=CheckStatus.SUCCESS
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"DNS resolution timeout for {domain}")
            return DNSResult(
                status=CheckStatus.FAILED,
                error="DNS resolution timed out"
            )
        except Exception as e:
            logger.error(f"DNS resolution failed for {domain}: {str(e)}")
            return DNSResult(
                status=CheckStatus.FAILED,
                error=f"DNS resolution failed: {str(e)}"
            )
    
    def _resolve_a_records(self, domain: str) -> list:
        """Resolve A records synchronously."""
        try:
            answers = dns.resolver.resolve(domain, 'A')
            return [str(rdata) for rdata in answers]
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException) as e:
            logger.debug(f"No A records for {domain}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error resolving A records for {domain}: {str(e)}")
            return []
    
    def _resolve_nameservers(self, domain: str) -> list:
        """Resolve nameservers synchronously."""
        try:
            answers = dns.resolver.resolve(domain, 'NS')
            return [str(rdata).rstrip('.') for rdata in answers]
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException) as e:
            logger.debug(f"No NS records for {domain}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error resolving NS records for {domain}: {str(e)}")
            return []

