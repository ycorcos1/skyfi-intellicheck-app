"""
HTTP homepage fetch and parsing integration.
"""
import asyncio
import logging
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from worker.models import WebResult, CheckStatus
from worker.config import WorkerConfig

logger = logging.getLogger(__name__)


class WebScraper:
    """Client for fetching and parsing website homepages."""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.timeout = httpx.Timeout(self.config.http_timeout, connect=10.0)
    
    async def fetch_homepage(self, url: str) -> WebResult:
        """
        Fetch and parse homepage content.
        
        Args:
            url: URL to fetch
            
        Returns:
            WebResult with website information
        """
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; SkyFiIntelliCheck/1.0; +https://skyfi.com)'
                })
                
                status_code = response.status_code
                reachable = 200 <= status_code < 400
                content_length = len(response.content)
                
                # Parse HTML for title and description
                title = None
                description = None
                
                if reachable and response.headers.get('content-type', '').startswith('text/html'):
                    try:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract title
                        title_tag = soup.find('title')
                        if title_tag:
                            title = title_tag.get_text(strip=True)
                        
                        # Extract meta description
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        if meta_desc:
                            description = meta_desc.get('content', '').strip()
                        
                    except Exception as parse_error:
                        logger.debug(f"HTML parsing error for {url}: {str(parse_error)}")
                
                return WebResult(
                    reachable=reachable,
                    status_code=status_code,
                    title=title,
                    description=description,
                    content_length=content_length,
                    status=CheckStatus.SUCCESS
                )
                
        except httpx.TimeoutException:
            logger.warning(f"HTTP request timeout for {url}")
            return WebResult(
                status=CheckStatus.FAILED,
                error="HTTP request timed out"
            )
        except httpx.RequestError as e:
            logger.error(f"HTTP request failed for {url}: {str(e)}")
            return WebResult(
                status=CheckStatus.FAILED,
                error=f"HTTP request failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {str(e)}")
            return WebResult(
                status=CheckStatus.FAILED,
                error=f"Unexpected error: {str(e)}"
            )

