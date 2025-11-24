"""
Lambda handler for company verification worker.
"""
import copy
import json
import logging
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from worker.config import WorkerConfig
from worker.db_utils import DatabaseManager
from worker.integrations.whois_client import WhoisClient
from worker.integrations.dns_client import DNSClient
from worker.integrations.web_scraper import WebScraper
from worker.integrations.mx_validator import MXValidator
from worker.integrations.phone_normalizer import PhoneNormalizer
from worker.integrations.openai_client import OpenAIClient
from worker.scoring.signal_generator import SignalGenerator
from worker.scoring.rule_engine import RuleEngine
from worker.correlation import (
    set_correlation_id,
    get_correlation_id,
    extract_correlation_id_from_sqs,
    generate_correlation_id,
    setup_structured_logging
)
from worker.rate_limiter import get_rate_limiter
from worker.observability import WorkerMetrics, WorkerLogger
from app.models.company import AnalysisStatus
from worker.models import (
    WhoisResult,
    DNSResult,
    WebResult,
    MXResult,
    PhoneResult,
    CheckStatus,
)

# Configure basic logging (will be replaced by structured logging in handler)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


CHECK_KEY_MAP = {
    "whois": "whois",
    "dns": "dns",
    "mx_validation": "mx",
    "website_scrape": "website",
    "phone": "phone",
}


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 datetime strings that may include trailing Z."""
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def _hydrate_whois_result(discovered: Dict[str, Any]) -> Optional[WhoisResult]:
    data = (discovered or {}).get("whois")
    if not data:
        return None
    if "error" in data:
        return WhoisResult(status=CheckStatus.FAILED, error=data.get("error"))
    return WhoisResult(
        domain_age_days=data.get("domain_age_days"),
        registrar=data.get("registrar"),
        privacy_enabled=data.get("privacy_enabled"),
        creation_date=_parse_iso_datetime(data.get("creation_date")),
        status=CheckStatus.SUCCESS,
    )


def _hydrate_dns_result(discovered: Dict[str, Any]) -> Optional[DNSResult]:
    data = (discovered or {}).get("dns")
    if not data:
        return None
    if "error" in data:
        return DNSResult(status=CheckStatus.FAILED, error=data.get("error"))
    return DNSResult(
        resolves=data.get("resolves", False),
        nameservers=data.get("nameservers", []) or [],
        a_records=data.get("a_records", []) or [],
        status=CheckStatus.SUCCESS,
    )


def _hydrate_mx_result(discovered: Dict[str, Any]) -> Optional[MXResult]:
    data = (discovered or {}).get("mx")
    if not data:
        return None
    if "error" in data:
        return MXResult(status=CheckStatus.FAILED, error=data.get("error"))
    return MXResult(
        has_mx_records=data.get("has_mx_records", False),
        mx_records=data.get("mx_records", []) or [],
        email_configured=data.get("email_configured", False),
        status=CheckStatus.SUCCESS,
    )


def _hydrate_web_result(discovered: Dict[str, Any]) -> Optional[WebResult]:
    data = (discovered or {}).get("website")
    if not data:
        return None
    if "error" in data:
        return WebResult(status=CheckStatus.FAILED, error=data.get("error"))
    return WebResult(
        reachable=data.get("reachable", False),
        status_code=data.get("status_code"),
        title=data.get("title"),
        description=data.get("description"),
        content_length=data.get("content_length", 0),
        status=CheckStatus.SUCCESS,
    )


def _hydrate_phone_result(discovered: Dict[str, Any]) -> Optional[PhoneResult]:
    data = (discovered or {}).get("phone")
    if not data:
        return None
    if "error" in data:
        return PhoneResult(status=CheckStatus.FAILED, error=data.get("error"))
    return PhoneResult(
        normalized=data.get("normalized"),
        valid=data.get("valid", False),
        region=data.get("region"),
        status=CheckStatus.SUCCESS,
    )


async def _process_company(
    company_id: str,
    retry_mode: str,
    failed_checks_to_retry: list,
    config: WorkerConfig,
    db_manager: DatabaseManager,
    whois_client: WhoisClient,
    dns_client: DNSClient,
    web_scraper: WebScraper,
    mx_validator: MXValidator,
    phone_normalizer: PhoneNormalizer,
    signal_generator: SignalGenerator,
    rule_engine: RuleEngine,
    openai_client: Optional[OpenAIClient],
    metrics: Optional[WorkerMetrics] = None,
    worker_logger: Optional[WorkerLogger] = None
) -> Dict[str, Any]:
    """Process a single company verification."""
    import time
    start_time = time.time()
    correlation_id = get_correlation_id() or "unknown"
    
    if worker_logger is None:
        worker_logger = WorkerLogger(correlation_id)
    if metrics is None:
        metrics = WorkerMetrics()
    
    worker_logger.info(
        "Processing company",
        company_id=company_id,
        retry_mode=retry_mode
    )
    
    # Fetch company
    company = db_manager.fetch_company(company_id)
    
    # Update status to in_progress
    db_manager.update_company_step(
        company_id,
        'whois',
        AnalysisStatus.IN_PROGRESS
    )
    
    # Prepare submitted data
    submitted_data = {
        'name': company.name,
        'domain': company.domain,
        'website_url': company.website_url,
        'email': company.email,
        'phone': company.phone,
    }
    
    # Prepare historical context for selective retry
    failed_checks_to_retry = failed_checks_to_retry or []
    retry_check_set = set(failed_checks_to_retry)
    previous_analysis = None
    previous_failed_checks = set()
    previous_discovered_data: Dict[str, Any] = {}
    
    if retry_mode == 'failed_only':
        previous_analysis = db_manager.fetch_latest_analysis(company_id)
        if previous_analysis:
            previous_failed_checks = set(previous_analysis.failed_checks or [])
            previous_discovered_data = previous_analysis.discovered_data or {}
    
    discovered_data = copy.deepcopy(previous_discovered_data) if previous_discovered_data else {}
    successful_checks = set()
    failed_checks = set()
    
    for check_name in ['whois', 'dns', 'mx_validation', 'website_scrape', 'phone']:
        data_key = CHECK_KEY_MAP[check_name]
        if check_name in previous_failed_checks:
            failed_checks.add(check_name)
        elif data_key in discovered_data:
            successful_checks.add(check_name)
    
    # Determine which checks to run
    checks_to_run = ['whois', 'dns', 'mx_validation', 'website_scrape', 'phone']
    if retry_mode == 'failed_only':
        if retry_check_set:
            checks_to_run = [c for c in checks_to_run if c in retry_check_set]
        else:
            logger.info(
                "Selective retry requested but no failed checks provided; defaulting to previous results."
            )
    
    # Execute WHOIS lookup
    whois_result = None
    if 'whois' in checks_to_run:
        successful_checks.discard('whois')
        failed_checks.discard('whois')
        try:
            # Apply rate limiting
            whois_limiter = get_rate_limiter('whois', config.whois_rate_limit)
            whois_limiter.wait()
            
            logger.info(f"Executing WHOIS lookup for {company.domain}")
            whois_result = await whois_client.lookup(company.domain)
            
            if whois_result.status.value == "success":
                successful_checks.add('whois')
                discovered_data['whois'] = {
                    'domain_age_days': whois_result.domain_age_days,
                    'registrar': whois_result.registrar,
                    'privacy_enabled': whois_result.privacy_enabled,
                    'creation_date': whois_result.creation_date.isoformat() if whois_result.creation_date else None
                }
                metrics.record_integration_success("whois", correlation_id)
            else:
                failed_checks.add('whois')
                discovered_data['whois'] = {'error': whois_result.error}
                metrics.record_integration_failure("whois", "check_failed", correlation_id)
        except Exception as e:
            worker_logger.error("WHOIS check failed", error=str(e), integration="whois")
            failed_checks.add('whois')
            discovered_data['whois'] = {'error': str(e)}
            metrics.record_integration_failure("whois", type(e).__name__, correlation_id)
        finally:
            db_manager.update_company_step(company_id, 'dns')
    else:
        whois_result = _hydrate_whois_result(discovered_data)
        if 'whois' in previous_failed_checks:
            failed_checks.add('whois')
        elif whois_result:
            successful_checks.add('whois')
        db_manager.update_company_step(company_id, 'dns')
    
    # Execute DNS resolution
    dns_result = None
    if 'dns' in checks_to_run:
        successful_checks.discard('dns')
        failed_checks.discard('dns')
        try:
            # Apply rate limiting
            dns_limiter = get_rate_limiter('dns', config.dns_rate_limit)
            dns_limiter.wait()
            
            logger.info(f"Executing DNS resolution for {company.domain}")
            dns_result = await dns_client.resolve(company.domain)
            
            if dns_result.status.value == "success":
                successful_checks.add('dns')
                discovered_data['dns'] = {
                    'resolves': dns_result.resolves,
                    'nameservers': dns_result.nameservers,
                    'a_records': dns_result.a_records
                }
                metrics.record_integration_success("dns", correlation_id)
            else:
                failed_checks.add('dns')
                discovered_data['dns'] = {'error': dns_result.error}
                metrics.record_integration_failure("dns", "check_failed", correlation_id)
        except Exception as e:
            worker_logger.error("DNS check failed", error=str(e), integration="dns")
            failed_checks.add('dns')
            discovered_data['dns'] = {'error': str(e)}
            metrics.record_integration_failure("dns", type(e).__name__, correlation_id)
        finally:
            db_manager.update_company_step(company_id, 'mx_validation')
    else:
        dns_result = _hydrate_dns_result(discovered_data)
        if 'dns' in previous_failed_checks:
            failed_checks.add('dns')
        elif dns_result:
            successful_checks.add('dns')
        db_manager.update_company_step(company_id, 'mx_validation')
    
    # Execute MX validation
    mx_result = None
    if 'mx_validation' in checks_to_run:
        successful_checks.discard('mx_validation')
        failed_checks.discard('mx_validation')
        try:
            email_domain = company.email.split('@')[-1] if company.email and '@' in company.email else company.domain
            logger.info(f"Executing MX validation for {email_domain}")
            mx_result = await mx_validator.validate_mx(email_domain)
            
            if mx_result.status.value == "success":
                successful_checks.add('mx_validation')
                discovered_data['mx'] = {
                    'has_mx_records': mx_result.has_mx_records,
                    'mx_records': mx_result.mx_records,
                    'email_configured': mx_result.email_configured
                }
                metrics.record_integration_success("mx_validation", correlation_id)
            else:
                failed_checks.add('mx_validation')
                discovered_data['mx'] = {'error': mx_result.error}
                metrics.record_integration_failure("mx_validation", "check_failed", correlation_id)
        except Exception as e:
            worker_logger.error("MX check failed", error=str(e), integration="mx_validation")
            failed_checks.add('mx_validation')
            discovered_data['mx'] = {'error': str(e)}
            metrics.record_integration_failure("mx_validation", type(e).__name__, correlation_id)
        finally:
            db_manager.update_company_step(company_id, 'website_scrape')
    else:
        mx_result = _hydrate_mx_result(discovered_data)
        if 'mx_validation' in previous_failed_checks:
            failed_checks.add('mx_validation')
        elif mx_result:
            successful_checks.add('mx_validation')
        db_manager.update_company_step(company_id, 'website_scrape')
    
    # Execute website scrape
    web_result = None
    if 'website_scrape' in checks_to_run:
        successful_checks.discard('website_scrape')
        failed_checks.discard('website_scrape')
        try:
            # Apply rate limiting
            http_limiter = get_rate_limiter('http', config.http_rate_limit)
            http_limiter.wait()
            
            website_url = company.website_url or f"https://{company.domain}"
            logger.info(f"Executing website scrape for {website_url}")
            web_result = await web_scraper.fetch_homepage(website_url)
            
            if web_result.status.value == "success":
                successful_checks.add('website_scrape')
                discovered_data['website'] = {
                    'reachable': web_result.reachable,
                    'status_code': web_result.status_code,
                    'title': web_result.title,
                    'description': web_result.description,
                    'content_length': web_result.content_length
                }
                metrics.record_integration_success("website_scrape", correlation_id)
            else:
                failed_checks.add('website_scrape')
                discovered_data['website'] = {'error': web_result.error}
                metrics.record_integration_failure("website_scrape", "check_failed", correlation_id)
        except Exception as e:
            worker_logger.error("Website scrape failed", error=str(e), integration="website_scrape")
            failed_checks.add('website_scrape')
            discovered_data['website'] = {'error': str(e)}
            metrics.record_integration_failure("website_scrape", type(e).__name__, correlation_id)
        finally:
            db_manager.update_company_step(company_id, 'phone')
    else:
        web_result = _hydrate_web_result(discovered_data)
        if 'website_scrape' in previous_failed_checks:
            failed_checks.add('website_scrape')
        elif web_result:
            successful_checks.add('website_scrape')
        db_manager.update_company_step(company_id, 'phone')
    
    # Execute phone normalization
    phone_result = None
    if 'phone' in checks_to_run and company.phone:
        successful_checks.discard('phone')
        failed_checks.discard('phone')
        try:
            logger.info(f"Executing phone normalization for {company.phone}")
            phone_result = phone_normalizer.normalize(company.phone)
            
            if phone_result.status.value == "success":
                successful_checks.add('phone')
                discovered_data['phone'] = {
                    'normalized': phone_result.normalized,
                    'valid': phone_result.valid,
                    'region': phone_result.region
                }
                metrics.record_integration_success("phone", correlation_id)
            else:
                failed_checks.add('phone')
                discovered_data['phone'] = {'error': phone_result.error}
                metrics.record_integration_failure("phone", "check_failed", correlation_id)
        except Exception as e:
            worker_logger.error("Phone normalization failed", error=str(e), integration="phone")
            failed_checks.add('phone')
            discovered_data['phone'] = {'error': str(e)}
            metrics.record_integration_failure("phone", type(e).__name__, correlation_id)
        finally:
            db_manager.update_company_step(company_id, 'llm_processing')
    else:
        phone_result = _hydrate_phone_result(discovered_data)
        if company.phone:
            if 'phone' in previous_failed_checks:
                failed_checks.add('phone')
            elif phone_result:
                successful_checks.add('phone')
        db_manager.update_company_step(company_id, 'llm_processing')
    
    # Generate signals
    logger.info("Generating signals from check results")
    signals = signal_generator.generate_signals(
        submitted_data,
        whois_result,
        dns_result,
        web_result,
        mx_result,
        phone_result
    )
    
    # Calculate rule score
    logger.info("Calculating rule score")
    rule_score = rule_engine.calculate_score(signals)
    
    # Call OpenAI for LLM analysis (PR #8 - optional for PR #7)
    llm_summary = None
    llm_details = None
    llm_score_adjustment = 0
    llm_attempted = False
    llm_succeeded = False
    
    if openai_client:
        # Update step to LLM processing
        db_manager.update_company_step(company_id, 'llm_processing')
        llm_attempted = True
        
        try:
            logger.info("Calling OpenAI for LLM analysis")
            # OpenAI client handles rate limiting internally (3 req/sec)
            llm_result = openai_client.generate_analysis(
                submitted_data=submitted_data,
                discovered_data=discovered_data,
                signals=signals,
                rule_score=rule_score
            )
            llm_summary = llm_result.get('llm_summary')
            llm_details = llm_result.get('llm_details')
            llm_score_adjustment = llm_result.get('llm_score_adjustment', 0)
            llm_succeeded = True
            logger.info(f"OpenAI analysis complete: adjustment={llm_score_adjustment}")
        except Exception as e:
            worker_logger.error("OpenAI analysis failed", error=str(e), integration="llm_processing")
            failed_checks.add('llm_processing')
            metrics.record_integration_failure("llm_processing", type(e).__name__, correlation_id)
            # Continue with rule_score only
    else:
        logger.debug("OpenAI client not available, skipping LLM analysis (PR #7 mode)")
    
    # Compute hybrid score (for PR #7, this is just rule_score if no LLM)
    if llm_attempted:
        final_risk_score = signal_generator.compute_hybrid_score(
            rule_score=rule_score,
            llm_score_adjustment=llm_score_adjustment
        )
    else:
        # PR #7: Use rule_score directly if LLM not configured
        final_risk_score = rule_score
    
    # Determine completeness
    # PR #7: Consider complete if at least 3 checks succeeded (LLM is optional)
    # PR #8: If LLM was attempted, it must succeed for complete status
    is_complete = len(successful_checks) >= 3 and len(failed_checks) == 0
    
    # If LLM was attempted but failed, mark as incomplete (PR #8 requirement)
    if llm_attempted and not llm_succeeded:
        is_complete = False
    
    # Save analysis
    duration_seconds = time.time() - start_time
    failed_checks_list = sorted(failed_checks)
    successful_checks_list = sorted(successful_checks)
    
    worker_logger.info(
        "Saving analysis",
        rule_score=rule_score,
        llm_adjustment=llm_score_adjustment,
        final_score=final_risk_score,
        is_complete=is_complete,
        duration_seconds=duration_seconds
    )

    analysis = db_manager.save_analysis(
        company_id=company_id,
        risk_score=final_risk_score,
        signals=signals,
        failed_checks=failed_checks_list,
        submitted_data=submitted_data,
        discovered_data=discovered_data,
        is_complete=is_complete,
        algorithm_version=config.algorithm_version,
        llm_summary=llm_summary,
        llm_details=llm_details
    )
    
    # Get analysis version (db_manager.save_analysis now sets it before returning)
    analysis_version = analysis.version
    
    # Record metrics
    if is_complete:
        metrics.record_analysis_success(company_id, duration_seconds, correlation_id)
    elif len(failed_checks) > 0:
        metrics.record_analysis_incomplete(company_id, len(failed_checks), correlation_id)
    else:
        metrics.record_analysis_failure(company_id, "unknown", correlation_id)
    
    metrics.record_worker_execution_duration(duration_seconds, correlation_id)
    
    return {
        'company_id': company_id,
        'status': 'success',
        'rule_score': rule_score,
        'llm_score_adjustment': llm_score_adjustment,
        'final_risk_score': final_risk_score,
        'is_complete': is_complete,
        'successful_checks': successful_checks_list,
        'failed_checks': failed_checks_list,
        'analysis_version': analysis_version,
        'duration_seconds': duration_seconds
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda entry point for processing company verification.
    
    Expected SQS event format:
    {
        "Records": [
            {
                "body": "{\"company_id\": \"uuid\", \"retry_mode\": \"full\"}",
                "messageAttributes": {
                    "CorrelationId": {
                        "stringValue": "uuid"
                    }
                }
            }
        ]
    }
    """
    # Initialize basic logging first (before any other operations)
    import logging as basic_logging
    basic_logging.basicConfig(
        level=basic_logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    basic_logger = basic_logging.getLogger(__name__)
    
    try:
        basic_logger.info("Lambda handler invoked", extra={"event_keys": list(event.keys()) if isinstance(event, dict) else "not_a_dict"})
        
        # Load configuration
        try:
            config = WorkerConfig.from_env()
            basic_logger.info("Configuration loaded successfully", extra={"has_db_secret_arn": bool(config.db_secret_arn)})
        except Exception as config_error:
            basic_logger.error(f"Failed to load configuration: {str(config_error)}", exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': f'Configuration error: {str(config_error)}'
                })
            }
        
        # Set up structured logging
        try:
            setup_structured_logging(config.log_level)
        except Exception as logging_error:
            basic_logger.warning(f"Failed to setup structured logging: {str(logging_error)}, using basic logging")
        
        # Parse SQS event
        if 'Records' not in event:
            basic_logger.error("Invalid event format: missing 'Records'", extra={"event": str(event)[:500]})
            raise ValueError("Invalid event format: missing 'Records'")
        
        basic_logger.info(f"Processing {len(event['Records'])} SQS record(s)")
        
        # Process all records
        async def process_all():
            results = []
            for record in event['Records']:
                # Extract correlation ID from message attributes
                message_attributes = record.get('messageAttributes') or {}
                correlation_id = extract_correlation_id_from_sqs(message_attributes) or generate_correlation_id()
                set_correlation_id(correlation_id)
                
                basic_logger.info(f"Processing record - Correlation ID: {correlation_id}")
                logger.info(f"Worker started - Correlation ID: {correlation_id}")
                
                try:
                    # Initialize components (per record to ensure clean state)
                    basic_logger.info("Initializing database manager...")
                    db_manager = DatabaseManager(config)
                    basic_logger.info("Database manager initialized successfully")
                    whois_client = WhoisClient(config)
                    dns_client = DNSClient(config)
                    web_scraper = WebScraper(config)
                    mx_validator = MXValidator(config)
                    phone_normalizer = PhoneNormalizer(config)
                    signal_generator = SignalGenerator()
                    rule_engine = RuleEngine()
                    
                    # Initialize observability
                    metrics = WorkerMetrics()
                    worker_logger = WorkerLogger(correlation_id)
                    
                    # Initialize OpenAI client (may be None if API key not configured)
                    openai_client = None
                    try:
                        if config.openai_api_key:
                            openai_client = OpenAIClient(config)
                            worker_logger.info("OpenAI client initialized")
                        else:
                            worker_logger.warning("OpenAI API key not configured, LLM analysis will be skipped")
                    except Exception as e:
                        worker_logger.warning("Failed to initialize OpenAI client", error=str(e))
                        openai_client = None
                    
                    # Parse message body
                    if isinstance(record.get('body'), str):
                        message_body = json.loads(record['body'])
                    else:
                        message_body = record.get('body', {})
                    
                    company_id = message_body.get('company_id')
                    if not company_id:
                        raise ValueError("Missing company_id in message")
                    
                    retry_mode = message_body.get('retry_mode', 'full')
                    failed_checks_to_retry = message_body.get('failed_checks', [])
                    
                    result = await _process_company(
                        company_id,
                        retry_mode,
                        failed_checks_to_retry,
                        config,
                        db_manager,
                        whois_client,
                        dns_client,
                        web_scraper,
                        mx_validator,
                        phone_normalizer,
                        signal_generator,
                        rule_engine,
                        openai_client,
                        metrics=metrics,
                        worker_logger=worker_logger
                    )
                    result['correlation_id'] = correlation_id
                    results.append(result)
                    
                except Exception as e:
                    correlation_id = get_correlation_id() or correlation_id
                    worker_logger = WorkerLogger(correlation_id)
                    metrics = WorkerMetrics()
                    
                    worker_logger.error("Error processing record", error=str(e), exc_info=True)
                    
                    # Try to update company status to FAILED
                    try:
                        company_id = None
                        if isinstance(record.get('body'), str):
                            message_body = json.loads(record['body'])
                        else:
                            message_body = record.get('body', {})
                        company_id = message_body.get('company_id')
                        
                        if company_id:
                            db_manager = DatabaseManager(config)
                            db_manager.update_company_analysis_status(
                                company_id,
                                AnalysisStatus.COMPLETE,
                                mark_suspicious=True
                            )
                            metrics.record_analysis_failure(company_id, type(e).__name__, correlation_id)
                            worker_logger.info("Updated company status to FAILED", company_id=company_id)
                    except Exception as update_error:
                        worker_logger.error("Failed to update company status", error=str(update_error))
                    
                    results.append({
                        'status': 'error',
                        'error': str(e),
                        'correlation_id': correlation_id
                    })
                    # Re-raise to trigger SQS retry
                    raise
            
            return results
        
        # Run async processing
        results = asyncio.run(process_all())
        
        # Get correlation ID from context (last one processed)
        correlation_id = get_correlation_id() or "unknown"
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'correlation_id': correlation_id,
                'results': results
            })
        }
        
    except Exception as e:
        correlation_id = get_correlation_id() or generate_correlation_id()
        logger.error(f"Fatal error in worker: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'correlation_id': correlation_id,
                'error': str(e)
            })
        }

