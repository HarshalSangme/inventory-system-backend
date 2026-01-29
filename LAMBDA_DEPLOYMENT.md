# AWS Lambda Deployment for Inventory System Backend

## Prerequisites
- AWS CLI configured with credentials
- SAM CLI installed (`pip install aws-sam-cli`)
- Python 3.11 runtime available locally

## Quick Start

### 1. Deploy Backend to Lambda

```bash
cd backend

# For development environment
./deploy.sh dev us-east-1

# For production environment
./deploy.sh prod us-east-1
```

This will:
- Package dependencies into a Lambda layer
- Bundle the FastAPI application
- Output `inventory-backend-lambda.zip`
- Provide SAM deployment command

### 2. Deploy with AWS SAM

```bash
sam deploy \
  --template-file template.yaml \
  --stack-name inventory-backend-dev \
  --s3-bucket inventory-system-deploy-dev \
  --region us-east-1 \
  --parameter-overrides EnvironmentName=dev \
  --capabilities CAPABILITY_NAMED_IAM
```

### 3. Get API Endpoint

After deployment, CloudFormation outputs will show the API Gateway endpoint:

```bash
aws cloudformation describe-stacks \
  --stack-name inventory-backend-dev \
  --query 'Stacks[0].Outputs[0].OutputValue' \
  --region us-east-1
```

## Configuration

### Environment Variables

Set these in Lambda environment or in `template.yaml`:
- `ENVIRONMENT`: dev or prod
- `DATABASE_URL`: Path to inventory.db (Lambda uses `/tmp` for temporary storage)

### Database

For Lambda, SQLite database file is stored in `/tmp/inventory.db` (ephemeral storage).
For production, migrate to:
- AWS RDS PostgreSQL (relational data)
- Amazon DynamoDB (serverless NoSQL)

Currently kept as SQLite for dev/demo.

## Monitoring

```bash
# View Lambda logs
aws logs tail /aws/lambda/inventory-system-backend-dev --follow

# View API Gateway access logs
aws logs tail /aws/apigateway/inventory-system-api-dev --follow
```

## Cost Estimation

- **Lambda**: Free tier: 1M requests/month + 400,000 GB-seconds/month
- **API Gateway**: Free tier: 1M requests/month
- **S3**: Minimal for deployment artifacts (~$0.02/GB stored)
- **Total**: ~$5-10/month after free tier (depending on usage)

## Cleanup

To delete the stack and stop incurring charges:

```bash
aws cloudformation delete-stack \
  --stack-name inventory-backend-dev \
  --region us-east-1
```
