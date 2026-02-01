#!/usr/bin/env python3
"""
Ultra-fast Lambda deployment - uses manylinux wheels
"""
import subprocess
import os
import json
import shutil
import sys
import time
from pathlib import Path

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BACKEND_DIR, "lambda_build")
S3_BUCKET = "inventory-system-deploy-dev"
STACK_NAME = "inventory-backend-dev"
REGION = "us-east-1"

def run_cmd(cmd):
    """Run command"""
    print(f"  > {cmd[:80]}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=BACKEND_DIR)
    if result.returncode != 0 and "does not exist" not in result.stderr:
        if result.stderr:
            print(f"    ⚠️  {result.stderr[:150]}")
    return result.stdout.strip() if result.returncode == 0 else None

def build_with_manylinux():
    """Build using manylinux wheels"""
    print("\n📦 Building Lambda package...")
    
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    
    # Create structure: python/lib/python3.11/site-packages
    layer_dir = os.path.join(BUILD_DIR, "python", "lib", "python3.11", "site-packages")
    os.makedirs(layer_dir, exist_ok=True)
    
    # Install with manylinux wheels (--only-binary for compiled packages)
    print("  Installing dependencies for Linux...")
    cmd = f'pip install -r requirements.txt --only-binary :all: --platform manylinux2014_x86_64 --target "{layer_dir}" --python-version 311 --implementation cp --abi cp311'
    run_cmd(cmd)
    
    # Copy lambda handler and app
    print("  Copying application code...")
    shutil.copy("lambda_handler.py", BUILD_DIR)
    if os.path.exists(os.path.join(BUILD_DIR, "app")):
        shutil.rmtree(os.path.join(BUILD_DIR, "app"))
    shutil.copytree("app", os.path.join(BUILD_DIR, "app"))
    
    # Create ZIP at build root (not in subdirs)
    print("  Creating deployment package...")
    zip_file = os.path.join(BACKEND_DIR, "lambda-deploy.zip")
    
    # Use powershell to zip everything
    ps_cmd = f'Compress-Archive -Path "{BUILD_DIR}/*" -DestinationPath "{zip_file}" -Force'
    run_cmd(f'powershell -Command "{ps_cmd}"')
    
    if os.path.exists(zip_file):
        size = os.path.getsize(zip_file) / (1024*1024)
        print(f"✅ Package ready: {size:.1f} MB")
        return zip_file
    return None

def deploy():
    """Quick deploy"""
    print("\n🚀 Deploying Lambda...")
    
    zip_file = build_with_manylinux()
    if not zip_file:
        print("❌ Build failed")
        return False
    
    # Upload to S3
    print(f"  Uploading to S3...")
    run_cmd(f"aws s3 cp {zip_file} s3://{S3_BUCKET}/lambda-deploy.zip --region {REGION}")
    
    # Delete old stack
    print(f"  Cleaning up old stack...")
    run_cmd(f"aws cloudformation delete-stack --stack-name {STACK_NAME} --region {REGION}")
    
    # Wait for deletion
    for i in range(20):
        result = run_cmd(f"aws cloudformation describe-stacks --stack-name {STACK_NAME} --region {REGION}")
        if not result or "does not exist" in result:
            break
        time.sleep(1)
    
    # Deploy new stack
    print(f"  Creating new stack...")
    result = run_cmd(
        f"sam deploy --template-file template.yaml --stack-name {STACK_NAME} "
        f"--s3-bucket {S3_BUCKET} --region {REGION} --parameter-overrides EnvironmentName=dev "
        f"--capabilities CAPABILITY_NAMED_IAM --no-confirm-changeset"
    )
    
    # Get endpoint
    print(f"  Getting API endpoint...")
    time.sleep(5)
    result = run_cmd(
        f"aws cloudformation describe-stacks --stack-name {STACK_NAME} --region {REGION} --query \"Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue\" --output text"
    )
    
    if result and "execute-api" in result:
        print(f"\n{'='*60}")
        print(f"✅ SUCCESS!")
        print(f"🔗 API: {result}")
        print(f"{'='*60}")
        return result
    
    print("⚠️  Deployment may be in progress...")
    return None

if __name__ == "__main__":
    try:
        endpoint = deploy()
        sys.exit(0 if endpoint else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
