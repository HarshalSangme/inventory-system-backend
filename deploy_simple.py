#!/usr/bin/env python3
import subprocess
import os
import json
import shutil
import sys
import time
from pathlib import Path

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BACKEND_DIR, "lambda_build_final")
S3_BUCKET = "inventory-system-deploy-dev"
STACK_NAME = "inventory-backend-dev"
REGION = "us-east-1"

def run(cmd):
    """Run command silently"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=BACKEND_DIR)
    return result.stdout.strip() if result.returncode == 0 else None

print("\n📦 Building Lambda package...")

# Clean and create build dir
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
os.makedirs(BUILD_DIR)

# Install dependencies to site-packages directly in build root
site_packages = os.path.join(BUILD_DIR, "site-packages")
os.makedirs(site_packages, exist_ok=True)

print("  Installing dependencies...")
run(f'pip install -r requirements.txt --only-binary :all: --platform manylinux2014_x86_64 --target "{site_packages}" --python-version 311 --implementation cp --abi cp311')

# Move site-packages contents to root (so Lambda can find them)
print("  Organizing package structure...")
for item in os.listdir(site_packages):
    src = os.path.join(site_packages, item)
    dst = os.path.join(BUILD_DIR, item)
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)
        
shutil.rmtree(site_packages)

# Copy lambda handler and app
print("  Copying app code...")
shutil.copy(os.path.join(BACKEND_DIR, "lambda_handler.py"), BUILD_DIR)
if os.path.exists(os.path.join(BUILD_DIR, "app")):
    shutil.rmtree(os.path.join(BUILD_DIR, "app"))
shutil.copytree(os.path.join(BACKEND_DIR, "app"), os.path.join(BUILD_DIR, "app"))

# Create ZIP
print("  Creating ZIP...")
zip_file = os.path.join(BACKEND_DIR, "lambda.zip")
ps_cmd = f'Compress-Archive -Path "{BUILD_DIR}/*" -DestinationPath "{zip_file}" -Force'
run(f'powershell -Command "{ps_cmd}"')

if os.path.exists(zip_file):
    size = os.path.getsize(zip_file) / (1024*1024)
    print(f"✅ Package: {size:.1f} MB")
else:
    print("❌ ZIP creation failed")
    sys.exit(1)

# Upload to S3
print("  Uploading to S3...")
run(f"aws s3 cp {zip_file} s3://{S3_BUCKET}/ --region {REGION}")

# Delete old stack
print("  Cleaning up...")
run(f"aws cloudformation delete-stack --stack-name {STACK_NAME} --region {REGION}")

# Wait for deletion
for i in range(20):
    result = run(f"aws cloudformation describe-stacks --stack-name {STACK_NAME} --region {REGION}")
    if not result or "does not exist" in result:
        break
    time.sleep(1)

# Deploy new stack
print("  Deploying...")
run(f"sam deploy --template-file template.yaml --stack-name {STACK_NAME} --s3-bucket {S3_BUCKET} --region {REGION} --parameter-overrides EnvironmentName=dev --capabilities CAPABILITY_NAMED_IAM --no-confirm-changeset")

# Get endpoint
time.sleep(5)
result = run(f"aws cloudformation describe-stacks --stack-name {STACK_NAME} --region {REGION} --query \"Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue\" --output text")

if result and "execute-api" in result:
    print(f"\n{'='*60}")
    print(f"✅ SUCCESS!")
    print(f"🔗 API: {result}")
    print(f"{'='*60}\n")
else:
    print("⚠️  Deployment in progress...")
