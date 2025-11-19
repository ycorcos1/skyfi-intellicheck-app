# Lambda Worker - Company Verification

This directory contains the Lambda worker that performs automated company verification.

## Structure

```
worker/
├── __init__.py
├── index.py              # Lambda entry point
├── handler.py            # Main handler logic
├── config.py             # Configuration
├── models.py             # Data models
├── db_utils.py           # Database utilities
├── requirements.txt      # Python dependencies
├── integrations/         # External API integrations
│   ├── whois_client.py
│   ├── dns_client.py
│   ├── web_scraper.py
│   ├── mx_validator.py
│   └── phone_normalizer.py
└── scoring/              # Scoring engine
    ├── rule_engine.py
    └── signal_generator.py
```

## Deployment

The Lambda package must include:
1. `worker/` directory (this directory)
2. `app/` directory (for models and database utilities)
3. All dependencies from `requirements.txt`

### Building the Lambda Package

```bash
# From backend/ directory
cd backend
pip install -r worker/requirements.txt -t lambda_package/
cp -r worker lambda_package/
cp -r app lambda_package/
cd lambda_package
zip -r ../lambda_worker.zip .
```

### Handler Configuration

- Handler: `index.lambda_handler`
- Runtime: Python 3.11
- Timeout: 900 seconds (15 minutes)
- Memory: 1024 MB

## Environment Variables

- `DB_SECRET_ARN`: AWS Secrets Manager ARN for database credentials
- `S3_BUCKET_NAME`: S3 bucket for documents
- `ENVIRONMENT`: Environment name (dev/prod)
- `WHOIS_TIMEOUT`: WHOIS lookup timeout (default: 30)
- `DNS_TIMEOUT`: DNS resolution timeout (default: 30)
- `HTTP_TIMEOUT`: HTTP request timeout (default: 30)
- `MX_TIMEOUT`: MX lookup timeout (default: 30)
- `MAX_RETRIES`: Maximum retries (default: 3)
- `LOG_LEVEL`: Logging level (default: INFO)
- `AWS_REGION`: AWS region

## Testing

To test locally:

```python
# Test event
event = {
    "Records": [
        {
            "body": json.dumps({
                "company_id": "uuid-here",
                "retry_mode": "full"
            })
        }
    ]
}

# Run handler
from worker.handler import lambda_handler
result = lambda_handler(event, None)
```

## Checks Performed

1. **WHOIS Lookup**: Domain age, registrar, privacy protection
2. **DNS Resolution**: A records, nameservers
3. **MX Validation**: Email domain MX records
4. **Website Scrape**: Homepage fetch and parsing
5. **Phone Normalization**: Phone number validation and E.164 formatting

## Scoring

The worker uses a rule-based scoring engine that calculates risk scores from 0-100 based on:
- Domain age < 1 year: +20 points
- WHOIS privacy enabled: +10 points
- Email mismatch: +10 points
- Phone region mismatch: +10 points
- Website unreachable: +25 points
- No MX records: +15 points

Final score is clamped between 0 and 100.

## Partial Failure Handling

The worker supports partial failures:
- If ≥3 checks succeed, analysis is marked as `incomplete` but results are saved
- Failed checks are tracked in `failed_checks` array
- Supports retry of failed checks only via `retry_mode: "failed_only"`

