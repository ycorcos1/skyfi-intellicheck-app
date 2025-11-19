#!/usr/bin/env bash
# Script to update IAM user permissions - split into very small policies
# Each policy is under 1500 bytes to stay well under the 2048 byte limit

set -euo pipefail

IAM_USER_NAME="${1:-skyfi-intellicheck-app}"

echo "Updating IAM permissions for user: ${IAM_USER_NAME}"
echo "Applying multiple small policies..."
echo ""

# Policy 1: VPC Management
POLICY1='{"Version":"2012-10-17","Statement":[{"Sid":"VPCManagement","Effect":"Allow","Action":["ec2:CreateVpc","ec2:DeleteVpc","ec2:DescribeVpcs","ec2:ModifyVpcAttribute","ec2:CreateSubnet","ec2:DeleteSubnet","ec2:DescribeSubnets","ec2:ModifySubnetAttribute","ec2:CreateInternetGateway","ec2:DeleteInternetGateway","ec2:AttachInternetGateway","ec2:DetachInternetGateway","ec2:DescribeInternetGateways","ec2:CreateNatGateway","ec2:DeleteNatGateway","ec2:DescribeNatGateways","ec2:AllocateAddress","ec2:ReleaseAddress","ec2:DescribeAddresses","ec2:DescribeAddressesAttribute","ec2:CreateRouteTable","ec2:DeleteRouteTable","ec2:DescribeRouteTables","ec2:CreateRoute","ec2:DeleteRoute","ec2:AssociateRouteTable","ec2:DisassociateRouteTable","ec2:CreateSecurityGroup","ec2:DeleteSecurityGroup","ec2:DescribeSecurityGroups","ec2:AuthorizeSecurityGroupIngress","ec2:AuthorizeSecurityGroupEgress","ec2:RevokeSecurityGroupIngress","ec2:RevokeSecurityGroupEgress","ec2:DescribeAvailabilityZones","ec2:DescribeAccountAttributes"],"Resource":"*"}]}'

# Policy 2: RDS Management
POLICY2='{"Version":"2012-10-17","Statement":[{"Sid":"RDSManagement","Effect":"Allow","Action":["rds:CreateDBInstance","rds:DeleteDBInstance","rds:DescribeDBInstances","rds:ModifyDBInstance","rds:CreateDBSubnetGroup","rds:DeleteDBSubnetGroup","rds:DescribeDBSubnetGroups","rds:CreateDBParameterGroup","rds:DeleteDBParameterGroup","rds:DescribeDBParameterGroups"],"Resource":"*"}]}'

# Policy 3: S3 Management
POLICY3='{"Version":"2012-10-17","Statement":[{"Sid":"S3Management","Effect":"Allow","Action":["s3:CreateBucket","s3:DeleteBucket","s3:ListBucket","s3:GetBucketLocation","s3:GetBucketVersioning","s3:PutBucketVersioning","s3:GetBucketPublicAccessBlock","s3:PutBucketPublicAccessBlock","s3:GetBucketCors","s3:PutBucketCors","s3:GetBucketEncryption","s3:PutBucketEncryption","s3:GetBucketLifecycleConfiguration","s3:PutBucketLifecycleConfiguration","s3:GetBucketWebsite","s3:PutObject","s3:GetObject","s3:DeleteObject","s3:ListBucketMultipartUploads","s3:AbortMultipartUpload"],"Resource":["arn:aws:s3:::skyfi-intellicheck-*","arn:aws:s3:::skyfi-intellicheck-*/*"]}]}'

# Policy 4: SQS Management
POLICY4='{"Version":"2012-10-17","Statement":[{"Sid":"SQSManagement","Effect":"Allow","Action":["sqs:CreateQueue","sqs:DeleteQueue","sqs:GetQueueUrl","sqs:GetQueueAttributes","sqs:SetQueueAttributes","sqs:SendMessage","sqs:ReceiveMessage","sqs:DeleteMessage","sqs:ListQueues"],"Resource":"*"}]}'

# Policy 5: Lambda Management
POLICY5='{"Version":"2012-10-17","Statement":[{"Sid":"LambdaManagement","Effect":"Allow","Action":["lambda:CreateFunction","lambda:DeleteFunction","lambda:GetFunction","lambda:UpdateFunctionCode","lambda:UpdateFunctionConfiguration","lambda:ListFunctions","lambda:AddPermission","lambda:RemovePermission","lambda:CreateEventSourceMapping","lambda:DeleteEventSourceMapping","lambda:ListEventSourceMappings","lambda:GetEventSourceMapping","lambda:InvokeFunction","lambda:TagResource","lambda:UntagResource","lambda:ListTags","lambda:PublishVersion","lambda:CreateAlias","lambda:DeleteAlias","lambda:UpdateAlias","lambda:GetAlias","lambda:ListAliases"],"Resource":"*"}]}'

# Policy 6: EC2 Instance Management
POLICY6='{"Version":"2012-10-17","Statement":[{"Sid":"EC2InstanceManagement","Effect":"Allow","Action":["ec2:RunInstances","ec2:TerminateInstances","ec2:DescribeInstances","ec2:DescribeInstanceStatus","ec2:StartInstances","ec2:StopInstances","ec2:CreateTags","ec2:DeleteTags","ec2:DescribeTags"],"Resource":"*","Condition":{"StringEquals":{"ec2:ResourceTag/Project":"skyfi-intellicheck"}}}]}'

# Policy 7: ECS Management
POLICY7='{"Version":"2012-10-17","Statement":[{"Sid":"ECSMangement","Effect":"Allow","Action":["ecs:CreateCluster","ecs:DeleteCluster","ecs:DescribeClusters","ecs:ListClusters","ecs:CreateService","ecs:DeleteService","ecs:DescribeServices","ecs:UpdateService","ecs:ListServices","ecs:RegisterTaskDefinition","ecs:DeregisterTaskDefinition","ecs:DescribeTaskDefinition","ecs:ListTaskDefinitions","ecs:RunTask","ecs:StopTask","ecs:DescribeTasks","ecs:ListTasks"],"Resource":"*"}]}'

# Policy 8: ELB Management
POLICY8='{"Version":"2012-10-17","Statement":[{"Sid":"ELBManagement","Effect":"Allow","Action":["elasticloadbalancing:CreateLoadBalancer","elasticloadbalancing:DeleteLoadBalancer","elasticloadbalancing:DescribeLoadBalancers","elasticloadbalancing:CreateTargetGroup","elasticloadbalancing:DeleteTargetGroup","elasticloadbalancing:DescribeTargetGroups","elasticloadbalancing:RegisterTargets","elasticloadbalancing:DeregisterTargets","elasticloadbalancing:DescribeTargetHealth","elasticloadbalancing:ModifyLoadBalancerAttributes","elasticloadbalancing:DescribeLoadBalancerAttributes"],"Resource":"*"}]}'

# Policy 9: Cognito Management
POLICY9='{"Version":"2012-10-17","Statement":[{"Sid":"CognitoManagement","Effect":"Allow","Action":["cognito-idp:CreateUserPool","cognito-idp:DeleteUserPool","cognito-idp:DescribeUserPool","cognito-idp:UpdateUserPool","cognito-idp:ListUserPools","cognito-idp:CreateUserPoolClient","cognito-idp:DeleteUserPoolClient","cognito-idp:DescribeUserPoolClient","cognito-idp:UpdateUserPoolClient","cognito-idp:ListUserPoolClients","cognito-idp:AdminCreateUser","cognito-idp:AdminDeleteUser","cognito-idp:AdminGetUser","cognito-idp:ListUsers"],"Resource":"*"}]}'

# Policy 10: Secrets Manager
POLICY10='{"Version":"2012-10-17","Statement":[{"Sid":"SecretsManagerManagement","Effect":"Allow","Action":["secretsmanager:CreateSecret","secretsmanager:DeleteSecret","secretsmanager:DescribeSecret","secretsmanager:GetSecretValue","secretsmanager:PutSecretValue","secretsmanager:UpdateSecret","secretsmanager:ListSecrets","secretsmanager:TagResource","secretsmanager:UntagResource"],"Resource":"*"}]}'

# Policy 11: IAM Role Management
POLICY11='{"Version":"2012-10-17","Statement":[{"Sid":"IAMRoleManagement","Effect":"Allow","Action":["iam:CreateRole","iam:DeleteRole","iam:GetRole","iam:ListRoles","iam:AttachRolePolicy","iam:DetachRolePolicy","iam:ListAttachedRolePolicies","iam:PutRolePolicy","iam:DeleteRolePolicy","iam:GetRolePolicy","iam:ListRolePolicies","iam:PassRole","iam:CreatePolicy","iam:DeletePolicy","iam:GetPolicy","iam:ListPolicies","iam:TagRole","iam:UntagRole"],"Resource":"*"}]}'

# Policy 12: CloudWatch Logs
POLICY12='{"Version":"2012-10-17","Statement":[{"Sid":"CloudWatchLogs","Effect":"Allow","Action":["logs:CreateLogGroup","logs:DeleteLogGroup","logs:DescribeLogGroups","logs:CreateLogStream","logs:DeleteLogStream","logs:DescribeLogStreams","logs:PutLogEvents","logs:PutRetentionPolicy"],"Resource":"*"}]}'

# Policy 13: CloudWatch Metrics
POLICY13='{"Version":"2012-10-17","Statement":[{"Sid":"CloudWatchMetrics","Effect":"Allow","Action":["cloudwatch:PutMetricData","cloudwatch:GetMetricStatistics","cloudwatch:ListMetrics","cloudwatch:PutMetricAlarm","cloudwatch:DeleteMetricAlarm","cloudwatch:DescribeAlarms"],"Resource":"*"}]}'

# Policy 14: API Gateway
POLICY14='{"Version":"2012-10-17","Statement":[{"Sid":"APIGatewayManagement","Effect":"Allow","Action":["apigateway:POST","apigateway:GET","apigateway:PUT","apigateway:DELETE","apigateway:PATCH"],"Resource":"*"}]}'

# Policy 15: CloudFront
POLICY15='{"Version":"2012-10-17","Statement":[{"Sid":"CloudFrontManagement","Effect":"Allow","Action":["cloudfront:CreateDistribution","cloudfront:DeleteDistribution","cloudfront:GetDistribution","cloudfront:UpdateDistribution","cloudfront:ListDistributions","cloudfront:CreateInvalidation","cloudfront:GetInvalidation","cloudfront:ListInvalidations"],"Resource":"*"}]}'

# Policy 16: ACM
POLICY16='{"Version":"2012-10-17","Statement":[{"Sid":"ACMManagement","Effect":"Allow","Action":["acm:RequestCertificate","acm:DeleteCertificate","acm:DescribeCertificate","acm:ListCertificates"],"Resource":"*"}]}'

# Policy 17: Route53
POLICY17='{"Version":"2012-10-17","Statement":[{"Sid":"Route53Management","Effect":"Allow","Action":["route53:CreateHostedZone","route53:DeleteHostedZone","route53:GetHostedZone","route53:ListHostedZones","route53:ChangeResourceRecordSets","route53:ListResourceRecordSets","route53:GetChange"],"Resource":"*"}]}'

# Policy 18: ECR Management (with new permissions)
POLICY18='{"Version":"2012-10-17","Statement":[{"Sid":"ECRManagement","Effect":"Allow","Action":["ecr:CreateRepository","ecr:DeleteRepository","ecr:DescribeRepositories","ecr:ListRepositories","ecr:PutLifecyclePolicy","ecr:GetLifecyclePolicy","ecr:DeleteLifecyclePolicy","ecr:PutImageScanningConfiguration","ecr:SetRepositoryPolicy","ecr:GetRepositoryPolicy","ecr:TagResource","ecr:UntagResource","ecr:GetAuthorizationToken","ecr:BatchCheckLayerAvailability","ecr:GetDownloadUrlForLayer","ecr:BatchGetImage","ecr:PutImage","ecr:InitiateLayerUpload","ecr:UploadLayerPart","ecr:CompleteLayerUpload"],"Resource":"*"}]}'

# Policy 19: STS
POLICY19='{"Version":"2012-10-17","Statement":[{"Sid":"STSAssumeRole","Effect":"Allow","Action":["sts:GetCallerIdentity","sts:AssumeRole"],"Resource":"*"}]}'

# Apply all policies
echo "Applying Policy 1: VPC Management..."
echo "${POLICY1}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-VPC" --policy-document file:///dev/stdin

echo "Applying Policy 2: RDS Management..."
echo "${POLICY2}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-RDS" --policy-document file:///dev/stdin

echo "Applying Policy 3: S3 Management..."
echo "${POLICY3}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-S3" --policy-document file:///dev/stdin

echo "Applying Policy 4: SQS Management..."
echo "${POLICY4}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-SQS" --policy-document file:///dev/stdin

echo "Applying Policy 5: Lambda Management..."
echo "${POLICY5}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-Lambda" --policy-document file:///dev/stdin

echo "Applying Policy 6: EC2 Instance Management..."
echo "${POLICY6}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-EC2" --policy-document file:///dev/stdin

echo "Applying Policy 7: ECS Management..."
echo "${POLICY7}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-ECS" --policy-document file:///dev/stdin

echo "Applying Policy 8: ELB Management..."
echo "${POLICY8}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-ELB" --policy-document file:///dev/stdin

echo "Applying Policy 9: Cognito Management..."
echo "${POLICY9}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-Cognito" --policy-document file:///dev/stdin

echo "Applying Policy 10: Secrets Manager..."
echo "${POLICY10}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-Secrets" --policy-document file:///dev/stdin

echo "Applying Policy 11: IAM Role Management..."
echo "${POLICY11}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-IAM" --policy-document file:///dev/stdin

echo "Applying Policy 12: CloudWatch Logs..."
echo "${POLICY12}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-Logs" --policy-document file:///dev/stdin

echo "Applying Policy 13: CloudWatch Metrics..."
echo "${POLICY13}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-Metrics" --policy-document file:///dev/stdin

echo "Applying Policy 14: API Gateway..."
echo "${POLICY14}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-APIGateway" --policy-document file:///dev/stdin

echo "Applying Policy 15: CloudFront..."
echo "${POLICY15}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-CloudFront" --policy-document file:///dev/stdin

echo "Applying Policy 16: ACM..."
echo "${POLICY16}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-ACM" --policy-document file:///dev/stdin

echo "Applying Policy 17: Route53..."
echo "${POLICY17}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-Route53" --policy-document file:///dev/stdin

echo "Applying Policy 18: ECR Management (with new permissions)..."
echo "${POLICY18}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-ECR" --policy-document file:///dev/stdin

echo "Applying Policy 19: STS..."
echo "${POLICY19}" | aws iam put-user-policy --user-name "${IAM_USER_NAME}" --policy-name "SkyFi-STS" --policy-document file:///dev/stdin

echo ""
echo "✅ All IAM policies updated successfully!"
echo ""
echo "To verify, run:"
echo "  aws iam list-user-policies --user-name ${IAM_USER_NAME}"

