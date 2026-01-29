#!/bin/bash

# Inventory System Backend - Lambda Deployment Script
# This script packages the FastAPI app for AWS Lambda deployment

set -e

ENVIRONMENT=${1:-dev}
AWS_REGION=${2:-us-east-1}
S3_BUCKET="${3:-inventory-system-deploy-${ENVIRONMENT}}"

echo "=== Inventory System Backend - Lambda Deployment ==="
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "S3 Bucket: $S3_BUCKET"
echo ""

# Create output directory
mkdir -p build/python_dependencies

# Install dependencies to layer
echo "Installing dependencies for Lambda layer..."
pip install -r requirements.txt --target build/python_dependencies/python/lib/python3.11/site-packages/ --upgrade

# Copy app code
echo "Copying application code..."
cp -r app build/

# Create deployment package
echo "Creating deployment package..."
cd build
zip -r ../inventory-backend-lambda.zip . -x "*.pyc" "__pycache__/*" ".pytest_cache/*"
cd ..

echo "Build completed: inventory-backend-lambda.zip"
echo ""
echo "Next steps:"
echo "1. Upload to S3: aws s3 cp inventory-backend-lambda.zip s3://$S3_BUCKET/"
echo "2. Deploy with SAM:"
echo "   sam deploy --template-file template.yaml --stack-name inventory-backend-$ENVIRONMENT --s3-bucket $S3_BUCKET --region $AWS_REGION --parameter-overrides EnvironmentName=$ENVIRONMENT"
echo ""
