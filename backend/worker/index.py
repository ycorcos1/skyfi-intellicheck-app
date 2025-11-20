"""
Lambda entry point - thin wrapper around handler.
This file is used as the Lambda handler entry point.
"""
from worker.handler import lambda_handler

# Lambda expects handler function at module level
__all__ = ['lambda_handler']

# Deployment trigger: Lambda worker ready for SQS processing

