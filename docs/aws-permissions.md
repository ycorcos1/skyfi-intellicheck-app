# AWS IAM Permissions for SkyFi IntelliCheck

This document describes the minimum IAM permissions required for the SkyFi IntelliCheck project. These permissions should be attached to an IAM user or role used for development and deployment.

## IAM Policy

The following JSON policy provides the minimum permissions needed for Terraform/CDK deployments and AWS CLI operations:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "VPCManagement",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVpc",
        "ec2:DeleteVpc",
        "ec2:DescribeVpcs",
        "ec2:ModifyVpcAttribute",
        "ec2:CreateSubnet",
        "ec2:DeleteSubnet",
        "ec2:DescribeSubnets",
        "ec2:ModifySubnetAttribute",
        "ec2:CreateInternetGateway",
        "ec2:DeleteInternetGateway",
        "ec2:AttachInternetGateway",
        "ec2:DetachInternetGateway",
        "ec2:DescribeInternetGateways",
        "ec2:CreateNatGateway",
        "ec2:DeleteNatGateway",
        "ec2:DescribeNatGateways",
        "ec2:AllocateAddress",
        "ec2:ReleaseAddress",
        "ec2:DescribeAddresses",
        "ec2:DescribeAddressesAttribute",
        "ec2:CreateRouteTable",
        "ec2:DeleteRouteTable",
        "ec2:DescribeRouteTables",
        "ec2:CreateRoute",
        "ec2:DeleteRoute",
        "ec2:AssociateRouteTable",
        "ec2:DisassociateRouteTable",
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeAccountAttributes"
      ],
      "Resource": "*"
    },
    {
      "Sid": "RDSManagement",
      "Effect": "Allow",
      "Action": [
        "rds:CreateDBInstance",
        "rds:DeleteDBInstance",
        "rds:DescribeDBInstances",
        "rds:ModifyDBInstance",
        "rds:CreateDBSubnetGroup",
        "rds:DeleteDBSubnetGroup",
        "rds:DescribeDBSubnetGroups",
        "rds:CreateDBParameterGroup",
        "rds:DeleteDBParameterGroup",
        "rds:DescribeDBParameterGroups"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3Management",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:GetBucketVersioning",
        "s3:PutBucketVersioning",
        "s3:GetBucketPublicAccessBlock",
        "s3:PutBucketPublicAccessBlock",
        "s3:GetBucketCors",
        "s3:PutBucketCors",
        "s3:GetBucketEncryption",
        "s3:PutBucketEncryption",
        "s3:GetBucketLifecycleConfiguration",
        "s3:PutBucketLifecycleConfiguration",
        "s3:GetBucketWebsite",
        "s3:GetBucketAccelerateConfiguration",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucketMultipartUploads",
        "s3:AbortMultipartUpload"
      ],
      "Resource": [
        "arn:aws:s3:::skyfi-intellicheck-*",
        "arn:aws:s3:::skyfi-intellicheck-*/*"
      ]
    },
    {
      "Sid": "SQSManagement",
      "Effect": "Allow",
      "Action": [
        "sqs:CreateQueue",
        "sqs:DeleteQueue",
        "sqs:GetQueueUrl",
        "sqs:GetQueueAttributes",
        "sqs:SetQueueAttributes",
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:ListQueues"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaManagement",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:DeleteFunction",
        "lambda:GetFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:ListFunctions",
        "lambda:AddPermission",
        "lambda:RemovePermission",
        "lambda:CreateEventSourceMapping",
        "lambda:DeleteEventSourceMapping",
        "lambda:ListEventSourceMappings",
        "lambda:GetEventSourceMapping",
        "lambda:InvokeFunction",
        "lambda:TagResource",
        "lambda:UntagResource",
        "lambda:ListTags",
        "lambda:PublishVersion",
        "lambda:CreateAlias",
        "lambda:DeleteAlias",
        "lambda:UpdateAlias",
        "lambda:GetAlias",
        "lambda:ListAliases",
        "lambda:ListVersionsByFunction"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2InstanceManagement",
      "Effect": "Allow",
      "Action": [
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:CreateTags",
        "ec2:DeleteTags",
        "ec2:DescribeTags"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:ResourceTag/Project": "skyfi-intellicheck"
        }
      }
    },
    {
      "Sid": "ECSMangement",
      "Effect": "Allow",
      "Action": [
        "ecs:CreateCluster",
        "ecs:DeleteCluster",
        "ecs:DescribeClusters",
        "ecs:ListClusters",
        "ecs:CreateService",
        "ecs:DeleteService",
        "ecs:DescribeServices",
        "ecs:UpdateService",
        "ecs:ListServices",
        "ecs:RegisterTaskDefinition",
        "ecs:DeregisterTaskDefinition",
        "ecs:DescribeTaskDefinition",
        "ecs:ListTaskDefinitions",
        "ecs:RunTask",
        "ecs:StopTask",
        "ecs:DescribeTasks",
        "ecs:ListTasks"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ELBManagement",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:CreateLoadBalancer",
        "elasticloadbalancing:DeleteLoadBalancer",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:CreateTargetGroup",
        "elasticloadbalancing:DeleteTargetGroup",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:RegisterTargets",
        "elasticloadbalancing:DeregisterTargets",
        "elasticloadbalancing:DescribeTargetHealth",
        "elasticloadbalancing:ModifyLoadBalancerAttributes",
        "elasticloadbalancing:DescribeLoadBalancerAttributes",
        "elasticloadbalancing:ModifyTargetGroupAttributes",
        "elasticloadbalancing:DescribeTargetGroupAttributes",
        "elasticloadbalancing:CreateListener",
        "elasticloadbalancing:DeleteListener",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:ModifyListener",
        "elasticloadbalancing:DescribeTags",
        "elasticloadbalancing:AddTags",
        "elasticloadbalancing:RemoveTags",
        "elasticloadbalancing:DescribeListenerAttributes"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CognitoManagement",
      "Effect": "Allow",
      "Action": [
        "cognito-idp:CreateUserPool",
        "cognito-idp:DeleteUserPool",
        "cognito-idp:DescribeUserPool",
        "cognito-idp:UpdateUserPool",
        "cognito-idp:ListUserPools",
        "cognito-idp:CreateUserPoolClient",
        "cognito-idp:DeleteUserPoolClient",
        "cognito-idp:DescribeUserPoolClient",
        "cognito-idp:UpdateUserPoolClient",
        "cognito-idp:ListUserPoolClients",
        "cognito-idp:AdminCreateUser",
        "cognito-idp:AdminDeleteUser",
        "cognito-idp:AdminGetUser",
        "cognito-idp:ListUsers",
        "cognito-idp:TagResource",
        "cognito-idp:UntagResource",
        "cognito-idp:GetUserPoolMfaConfig",
        "cognito-idp:SetUserPoolMfaConfig"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SecretsManagerManagement",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:CreateSecret",
        "secretsmanager:DeleteSecret",
        "secretsmanager:DescribeSecret",
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:UpdateSecret",
        "secretsmanager:ListSecrets",
        "secretsmanager:TagResource",
        "secretsmanager:UntagResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMRoleManagement",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:ListRoles",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:ListAttachedRolePolicies",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:GetRolePolicy",
        "iam:ListRolePolicies",
        "iam:PassRole",
        "iam:CreatePolicy",
        "iam:DeletePolicy",
        "iam:GetPolicy",
        "iam:ListPolicies",
        "iam:TagRole",
        "iam:UntagRole"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:DeleteLogGroup",
        "logs:DescribeLogGroups",
        "logs:CreateLogStream",
        "logs:DeleteLogStream",
        "logs:DescribeLogStreams",
        "logs:PutLogEvents",
        "logs:PutRetentionPolicy",
        "logs:TagResource",
        "logs:UntagResource",
        "logs:ListTagsForResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchMetrics",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DeleteMetricAlarm",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:DescribeAlarmsForMetric",
        "cloudwatch:ListTagsForResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ApplicationAutoScaling",
      "Effect": "Allow",
      "Action": [
        "application-autoscaling:RegisterScalableTarget",
        "application-autoscaling:DeregisterScalableTarget",
        "application-autoscaling:DescribeScalableTargets",
        "application-autoscaling:PutScalingPolicy",
        "application-autoscaling:DeleteScalingPolicy",
        "application-autoscaling:DescribeScalingPolicies",
        "application-autoscaling:TagResource",
        "application-autoscaling:ListTagsForResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "APIGatewayManagement",
      "Effect": "Allow",
      "Action": [
        "apigateway:POST",
        "apigateway:GET",
        "apigateway:PUT",
        "apigateway:DELETE",
        "apigateway:PATCH"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFrontManagement",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateDistribution",
        "cloudfront:DeleteDistribution",
        "cloudfront:GetDistribution",
        "cloudfront:UpdateDistribution",
        "cloudfront:ListDistributions",
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation",
        "cloudfront:ListInvalidations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ACMManagement",
      "Effect": "Allow",
      "Action": [
        "acm:RequestCertificate",
        "acm:DeleteCertificate",
        "acm:DescribeCertificate",
        "acm:ListCertificates"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Route53Management",
      "Effect": "Allow",
      "Action": [
        "route53:CreateHostedZone",
        "route53:DeleteHostedZone",
        "route53:GetHostedZone",
        "route53:ListHostedZones",
        "route53:ChangeResourceRecordSets",
        "route53:ListResourceRecordSets",
        "route53:GetChange"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRManagement",
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository",
        "ecr:DeleteRepository",
        "ecr:DescribeRepositories",
        "ecr:ListRepositories",
        "ecr:PutLifecyclePolicy",
        "ecr:GetLifecyclePolicy",
        "ecr:DeleteLifecyclePolicy",
        "ecr:PutImageScanningConfiguration",
        "ecr:SetRepositoryPolicy",
        "ecr:GetRepositoryPolicy",
        "ecr:TagResource",
        "ecr:UntagResource",
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Sid": "STSAssumeRole",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "sts:AssumeRole"
      ],
      "Resource": "*"
    }
  ]
}
```

## IAM User Setup

1. **Create IAM User:**
   ```bash
   aws iam create-user --user-name skyfi-intellicheck-dev
   ```

2. **Attach Policy:**
   - Create a policy from the JSON above
   - Attach to the user:
   ```bash
   aws iam put-user-policy \
     --user-name skyfi-intellicheck-dev \
     --policy-name SkyFiIntelliCheckPolicy \
     --policy-document file://aws-permissions-policy.json
   ```

3. **Create Access Keys:**
   ```bash
   aws iam create-access-key --user-name skyfi-intellicheck-dev
   ```

4. **Configure AWS CLI:**
   ```bash
   aws configure
   # Enter Access Key ID
   # Enter Secret Access Key
   # Enter region: us-east-1
   # Enter output format: json
   ```

5. **Verify Configuration:**
   ```bash
   aws sts get-caller-identity
   ```

## Security Best Practices

1. **Use IAM Roles for ECS/Lambda:** The above policy is for Terraform/CDK operations. ECS tasks and Lambda functions should use IAM roles with minimal permissions.

2. **Least Privilege:** In production, restrict resource ARNs to specific resources rather than using `"Resource": "*"`.

3. **Separate Environments:** Use different IAM users/roles for dev and prod environments.

4. **Rotate Credentials:** Regularly rotate access keys and use temporary credentials when possible.

5. **Enable MFA:** Require MFA for IAM users with administrative access.

## Updating Permissions

If you need to update the IAM user permissions (e.g., after adding new AWS services), you can use the helper script:

```bash
cd docs
./update-iam-permissions.sh skyfi-intellicheck-app
```

**Note:** This script requires IAM permissions to modify user policies. If your current IAM user doesn't have these permissions, you'll need to:
1. Have an AWS administrator run the script, OR
2. Manually update the policy in the AWS Console (IAM → Users → skyfi-intellicheck-app → Permissions → Add permissions → Create inline policy)

### Recent Permission Updates

**PR #17 (ECR Repository Setup):**
- `ec2:DescribeAddressesAttribute` - For reading EIP attributes
- `s3:GetBucketWebsite` - For reading S3 bucket website configuration
- `ecr:TagResource` - For tagging ECR repositories
- `ecr:UntagResource` - For untagging ECR repositories
- `ecr:SetRepositoryPolicy` - For setting ECR repository policies
- `ecr:GetRepositoryPolicy` - For reading ECR repository policies

**PR #18 (Backend Infrastructure Deployment):**
- `elasticloadbalancing:DescribeListenerAttributes` - For reading ALB listener attributes
- `logs:ListTagsForResource` - For listing tags on CloudWatch Logs resources
- `cloudwatch:ListTagsForResource` - For listing tags on CloudWatch alarms
- `application-autoscaling:RegisterScalableTarget` - For registering ECS auto-scaling targets
- `application-autoscaling:DeregisterScalableTarget` - For deregistering auto-scaling targets
- `application-autoscaling:DescribeScalableTargets` - For describing auto-scaling targets
- `application-autoscaling:PutScalingPolicy` - For creating auto-scaling policies
- `application-autoscaling:DeleteScalingPolicy` - For deleting auto-scaling policies
- `application-autoscaling:DescribeScalingPolicies` - For describing auto-scaling policies
- `application-autoscaling:TagResource` - For tagging auto-scaling resources
- `application-autoscaling:ListTagsForResource` - For listing tags on auto-scaling resources
- `cognito-idp:GetUserPoolMfaConfig` - For reading Cognito MFA configuration
- `cognito-idp:SetUserPoolMfaConfig` - For setting Cognito MFA configuration
- `lambda:ListVersionsByFunction` - For listing Lambda function versions

## Notes

- This policy is designed for Terraform/CDK infrastructure deployment
- ECS tasks and Lambda functions use separate IAM roles (defined in Terraform)
- Some actions may require additional permissions depending on your AWS account configuration
- Review and adjust based on your organization's security requirements

