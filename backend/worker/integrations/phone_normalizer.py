"""
Phone number normalization integration.
"""
import logging
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

from worker.models import PhoneResult, CheckStatus
from worker.config import WorkerConfig

logger = logging.getLogger(__name__)


class PhoneNormalizer:
    """Client for normalizing phone numbers."""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
    
    def normalize(self, phone: str, region: str = 'US') -> PhoneResult:
        """
        Normalize phone number to E.164 format.
        
        Args:
            phone: Phone number string to normalize
            region: Default region code (ISO 3166-1 alpha-2)
            
        Returns:
            PhoneResult with normalized phone information
        """
        if not phone or not phone.strip():
            return PhoneResult(
                status=CheckStatus.FAILED,
                error="Empty phone number"
            )
        
        try:
            # Parse phone number
            parsed = phonenumbers.parse(phone, region)
            
            # Validate
            is_valid = phonenumbers.is_valid_number(parsed)
            
            # Get region code
            detected_region = phonenumbers.region_code_for_number(parsed)
            
            # Normalize to E.164 format
            normalized = None
            if is_valid:
                normalized = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
            
            return PhoneResult(
                normalized=normalized,
                valid=is_valid,
                region=detected_region,
                status=CheckStatus.SUCCESS
            )
            
        except NumberParseException as e:
            logger.debug(f"Phone parse error for {phone}: {str(e)}")
            return PhoneResult(
                status=CheckStatus.FAILED,
                error=f"Invalid phone number format: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error normalizing phone {phone}: {str(e)}")
            return PhoneResult(
                status=CheckStatus.FAILED,
                error=f"Unexpected error: {str(e)}"
            )

