"""
Test script for Lambda worker deployment.
Tests both direct Lambda invocation and SQS trigger.
"""
import json
import boto3
import sys
import time
from datetime import datetime
from typing import Optional

def get_aws_account_id() -> str:
    """Get AWS account ID from STS."""
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']


def test_lambda_direct_invocation(function_name: str, company_id: str, region: str = 'us-east-1'):
    """Test Lambda function with direct invocation."""
    print(f"\n{'='*60}")
    print(f"TEST 1: Direct Lambda Invocation")
    print(f"{'='*60}")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Create test event
    test_event = {
        "Records": [
            {
                "body": json.dumps({
                    "company_id": company_id,
                    "retry_mode": "full"
                }),
                "messageAttributes": {
                    "CorrelationId": {
                        "stringValue": f"test-{int(time.time())}"
                    }
                }
            }
        ]
    }
    
    print(f"Invoking Lambda function: {function_name}")
    print(f"Payload: {json.dumps(test_event, indent=2)}")
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read())
        print(f"\n✅ Lambda invocation successful!")
        print(f"Status Code: {response['StatusCode']}")
        print(f"Response: {json.dumps(payload, indent=2)}")
        
        if response.get('FunctionError'):
            print(f"\n⚠️  Function Error: {response.get('FunctionError')}")
            return None
        
        return payload
        
    except Exception as e:
        print(f"\n❌ Lambda invocation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_sqs_trigger(queue_url: str, company_id: str, region: str = 'us-east-1'):
    """Test Lambda function via SQS trigger."""
    print(f"\n{'='*60}")
    print(f"TEST 2: SQS → Lambda Trigger")
    print(f"{'='*60}")
    
    sqs_client = boto3.client('sqs', region_name=region)
    
    message = {
        "company_id": company_id,
        "retry_mode": "full"
    }
    
    correlation_id = f"test-sqs-{int(time.time())}"
    
    print(f"Sending message to SQS: {queue_url}")
    print(f"Message: {json.dumps(message, indent=2)}")
    print(f"Correlation ID: {correlation_id}")
    
    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
            MessageAttributes={
                'CorrelationId': {
                    'StringValue': correlation_id,
                    'DataType': 'String'
                }
            }
        )
        
        print(f"\n✅ Message sent to SQS!")
        print(f"Message ID: {response['MessageId']}")
        print(f"\n⏳ Waiting for Lambda to process (check CloudWatch Logs)...")
        print(f"Search for Correlation ID: {correlation_id}")
        
        return response['MessageId'], correlation_id
        
    except Exception as e:
        print(f"\n❌ SQS send failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


def check_cloudwatch_logs(function_name: str, correlation_id: Optional[str] = None, minutes: int = 5, region: str = 'us-east-1'):
    """Check recent CloudWatch logs for Lambda function."""
    print(f"\n{'='*60}")
    print(f"TEST 3: CloudWatch Logs Check")
    print(f"{'='*60}")
    
    logs_client = boto3.client('logs', region_name=region)
    log_group = f"/aws/lambda/{function_name}"
    
    try:
        # Get recent log streams
        end_time = int(time.time() * 1000)
        start_time = end_time - (minutes * 60 * 1000)
        
        print(f"Checking logs in: {log_group}")
        print(f"Time range: Last {minutes} minutes")
        if correlation_id:
            print(f"Filtering for Correlation ID: {correlation_id}")
        
        filter_pattern = f'"{correlation_id}"' if correlation_id else None
        
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            filterPattern=filter_pattern,
            limit=50
        )
        
        events = response.get('events', [])
        print(f"\n✅ Found {len(events)} log events")
        
        if events:
            print("\n--- Recent Log Events ---")
            for event in events[-10:]:  # Show last 10
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                print(f"[{timestamp}] {message}")
        else:
            print("\n⚠️  No log events found. This could mean:")
            print("   - Lambda hasn't been invoked yet")
            print("   - Logs haven't been written yet (wait a few seconds)")
            print("   - Log group doesn't exist")
        
        return events
        
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"\n⚠️  Log group not found: {log_group}")
        print("   This is normal if Lambda hasn't been invoked yet")
        return None
    except Exception as e:
        print(f"\n❌ Log check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def check_lambda_configuration(function_name: str, region: str = 'us-east-1'):
    """Check Lambda function configuration."""
    print(f"\n{'='*60}")
    print(f"TEST 4: Lambda Configuration Check")
    print(f"{'='*60}")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    try:
        config = lambda_client.get_function_configuration(FunctionName=function_name)
        
        print(f"✅ Function Configuration:")
        print(f"   Name: {config['FunctionName']}")
        print(f"   Runtime: {config['Runtime']}")
        print(f"   Handler: {config['Handler']}")
        print(f"   State: {config['State']}")
        print(f"   Last Modified: {config['LastModified']}")
        print(f"   Code Size: {config['CodeSize'] / 1024 / 1024:.2f} MB")
        print(f"   Memory Size: {config['MemorySize']} MB")
        print(f"   Timeout: {config['Timeout']} seconds")
        print(f"   Version: {config['Version']}")
        
        # Check environment variables (excluding sensitive ones)
        env_vars = config.get('Environment', {}).get('Variables', {})
        print(f"\n   Environment Variables ({len(env_vars)}):")
        for key in sorted(env_vars.keys()):
            if 'KEY' in key.upper() or 'SECRET' in key.upper() or 'PASSWORD' in key.upper():
                print(f"     {key}: [REDACTED]")
            else:
                print(f"     {key}: {env_vars[key]}")
        
        # Check VPC configuration
        if config.get('VpcConfig'):
            vpc_config = config['VpcConfig']
            print(f"\n   VPC Configuration:")
            print(f"     Subnets: {len(vpc_config.get('SubnetIds', []))}")
            print(f"     Security Groups: {len(vpc_config.get('SecurityGroupIds', []))}")
        
        return config
        
    except Exception as e:
        print(f"\n❌ Configuration check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_deployment.py <environment> [company_id] [region]")
        print("Example: python test_deployment.py dev abc123-... us-east-1")
        sys.exit(1)
    
    environment = sys.argv[1]
    company_id = sys.argv[2] if len(sys.argv) > 2 else None
    region = sys.argv[3] if len(sys.argv) > 3 else 'us-east-1'
    
    function_name = f"skyfi-intellicheck-worker-{environment}"
    
    # Get queue URL (construct from account ID and queue name)
    try:
        account_id = get_aws_account_id()
        queue_name = f"skyfi-intellicheck-verification-queue-{environment}"
        queue_url = f"https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}"
    except Exception as e:
        print(f"⚠️  Could not determine queue URL: {e}")
        queue_url = None
    
    print(f"\n{'#'*60}")
    print(f"# Lambda Worker Deployment Test")
    print(f"# Environment: {environment}")
    print(f"# Function: {function_name}")
    print(f"# Region: {region}")
    if queue_url:
        print(f"# Queue URL: {queue_url}")
    print(f"{'#'*60}")
    
    # Test 0: Configuration check
    check_lambda_configuration(function_name, region)
    
    if not company_id:
        print("\n⚠️  No company_id provided, skipping invocation tests")
        print("To test with real company: python test_deployment.py dev <company_id>")
    else:
        # Test 1: Direct invocation
        test_lambda_direct_invocation(function_name, company_id, region)
        
        # Wait before SQS test
        print("\n\nWaiting 5 seconds before SQS test...")
        time.sleep(5)
        
        # Test 2: SQS trigger
        if queue_url:
            message_id, correlation_id = test_sqs_trigger(queue_url, company_id, region)
        else:
            print("\n⚠️  Skipping SQS test (queue URL not available)")
            correlation_id = None
    
    # Test 3: CloudWatch logs
    time.sleep(2)
    check_cloudwatch_logs(function_name, correlation_id if 'correlation_id' in locals() else None, minutes=10, region=region)
    
    print(f"\n{'#'*60}")
    print("# Tests Complete!")
    print(f"{'#'*60}\n")

