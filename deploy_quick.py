#!/usr/bin/env python3
"""
Quick Lambda deployment script - uses pre-built layer approach
"""
import subprocess
import os
import json
import shutil
import sys

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BACKEND_DIR, "build_lambda")
S3_BUCKET = "inventory-system-deploy-dev"
STACK_NAME = "inventory-backend-dev"
REGION = "us-east-1"

def run_cmd(cmd, cwd=None):
    """Run shell command"""
    print(f"▶ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return None
    return result.stdout.strip()

def build_lambda():
    """Build Lambda function with dependencies using Docker"""
    print("\n📦 Building Lambda package with Docker...")
    
    # Clean and create build dir
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)
    
    # Create Dockerfile for building dependencies
    dockerfile = """
FROM public.ecr.aws/lambda/python:3.11
WORKDIR /tmp/build
COPY requirements.txt .
RUN pip install -r requirements.txt -t python/lib/python3.11/site-packages/
"""
    
    dockerfile_path = os.path.join(BACKEND_DIR, "Dockerfile.build")
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile)
    
    # Build Docker image
    img_name = "lambda-build:latest"
    print(f"🐳 Building Docker image: {img_name}")
    run_cmd(f"docker build -f {dockerfile_path} -t {img_name} {BACKEND_DIR}")
    
    # Extract dependencies from container
    print("📥 Extracting dependencies...")
    run_cmd(f'docker run --rm -v {BUILD_DIR}:/output {img_name} cp -r python /output/')
    
    # Copy app code
    print("📄 Copying app code...")
    shutil.copy(os.path.join(BACKEND_DIR, "lambda_handler.py"), BUILD_DIR)
    shutil.copytree(os.path.join(BACKEND_DIR, "app"), os.path.join(BUILD_DIR, "app"))
    
    # Create ZIP
    print("🗜️  Creating ZIP file...")
    zip_path = os.path.join(BACKEND_DIR, "lambda.zip")
    os.chdir(BUILD_DIR)
    run_cmd(f"powershell -Command \"Compress-Archive -Path * -DestinationPath {zip_path} -Force\"")
    os.chdir(BACKEND_DIR)
    
    if os.path.exists(zip_path):
        size_mb = os.path.getsize(zip_path) / (1024*1024)
        print(f"✅ ZIP created: {size_mb:.2f} MB")
        return zip_path
    return None

def upload_to_s3(zip_path):
    """Upload ZIP to S3"""
    print(f"\n☁️  Uploading to S3...")
    run_cmd(f"aws s3 cp {zip_path} s3://{S3_BUCKET}/ --region {REGION}")
    print("✅ Uploaded to S3")

def delete_old_stack():
    """Delete old CloudFormation stack"""
    print(f"\n🗑️  Deleting old stack: {STACK_NAME}")
    run_cmd(f"aws cloudformation delete-stack --stack-name {STACK_NAME} --region {REGION}")
    # Wait for deletion
    for i in range(30):
        result = run_cmd(f"aws cloudformation describe-stacks --stack-name {STACK_NAME} --region {REGION} 2>&1")
        if result is None or "does not exist" in result:
            print("✅ Stack deleted")
            return True
        print(f"⏳ Waiting for deletion... ({i+1}/30)")
        import time
        time.sleep(2)
    return False

def deploy_lambda():
    """Deploy using SAM"""
    print(f"\n🚀 Deploying Lambda stack...")
    run_cmd(
        f"sam deploy --template-file template.yaml --stack-name {STACK_NAME} "
        f"--s3-bucket {S3_BUCKET} --region {REGION} --parameter-overrides EnvironmentName=dev "
        f"--capabilities CAPABILITY_NAMED_IAM",
        cwd=BACKEND_DIR
    )
    
    # Get outputs
    result = run_cmd(
        f"aws cloudformation describe-stacks --stack-name {STACK_NAME} --region {REGION} --query 'Stacks[0].Outputs'"
    )
    if result:
        outputs = json.loads(result)
        for output in outputs:
            if output["OutputKey"] == "ApiEndpoint":
                endpoint = output["OutputValue"]
                print(f"\n✅ DEPLOYMENT SUCCESSFUL!")
                print(f"🔗 API Endpoint: {endpoint}")
                return endpoint
    return None

def main():
    """Main deployment flow"""
    try:
        print("=" * 60)
        print("🚀 Lambda Deployment Script")
        print("=" * 60)
        
        # Build
        zip_path = build_lambda()
        if not zip_path:
            print("❌ Build failed")
            return False
        
        # Upload
        upload_to_s3(zip_path)
        
        # Delete old
        delete_old_stack()
        
        # Deploy
        endpoint = deploy_lambda()
        if endpoint:
            print("\n" + "=" * 60)
            print("✅ Deployment Complete!")
            print(f"API: {endpoint}")
            print("=" * 60)
            return True
        else:
            print("❌ Deployment failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
