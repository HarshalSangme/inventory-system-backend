#!/usr/bin/env python3
"""
AWS Lambda Deployment Script for Inventory System Backend
Automates building, packaging, and deploying the FastAPI backend to AWS Lambda
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Configuration
PROJECT_ROOT = Path(__file__).parent
BUILD_DIR = PROJECT_ROOT / "build"
PYTHON_DIR = BUILD_DIR / "python" / "lib" / "python3.11" / "site-packages"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
LAMBDA_HANDLER = PROJECT_ROOT / "lambda_handler.py"
APP_DIR = PROJECT_ROOT / "app"
ZIP_FILE = PROJECT_ROOT / "inventory-backend-lambda.zip"
S3_BUCKET = "inventory-system-deploy-dev"
STACK_NAME = "inventory-backend-dev"
REGION = "us-east-1"
ENVIRONMENT = "dev"

# Color output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_step(text):
    print(f"{Colors.OKBLUE}▶ {text}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def run_command(cmd, description="", check=True):
    """Execute a shell command"""
    print_step(description or " ".join(cmd) if isinstance(cmd, list) else cmd)
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        
        if result.stdout:
            print(result.stdout.strip())
        if result.returncode == 0:
            print_success("Command completed successfully")
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def clean_build_directory():
    """Remove old build directory"""
    print_step("Cleaning old build directory")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print_success("Build directory removed")
    
    # Create new structure
    PYTHON_DIR.mkdir(parents=True, exist_ok=True)
    print_success("Created build directory structure")

def install_dependencies():
    """Install Python dependencies to build directory"""
    print_step("Installing Python dependencies")
    
    if not REQUIREMENTS_FILE.exists():
        print_error(f"Requirements file not found: {REQUIREMENTS_FILE}")
        sys.exit(1)
    
    cmd = [
        sys.executable, "-m", "pip", "install",
        "-r", str(REQUIREMENTS_FILE),
        "--target", str(PYTHON_DIR),
        "--no-cache-dir",
        "--platform", "manylinux2014_x86_64",
        "--implementation", "cp",
        "--python-version", "311",
        "--only-binary=:all:",
        "--upgrade"
    ]
    
    result = run_command(cmd, "Installing dependencies for Lambda")
    
    if result.returncode != 0:
        print_warning("Failed to install with platform-specific wheels. Attempting standard install...")
        # Fallback to standard install
        cmd = [
            sys.executable, "-m", "pip", "install",
            "-r", str(REQUIREMENTS_FILE),
            "--target", str(PYTHON_DIR),
            "--no-cache-dir"
        ]
        result = run_command(cmd, "Installing dependencies (fallback)")
    
    if result.returncode != 0:
        print_error("Dependency installation failed")
        sys.exit(1)

def copy_app_code():
    """Copy application code to build directory"""
    print_step("Copying application code")
    
    # Copy lambda handler
    if LAMBDA_HANDLER.exists():
        shutil.copy2(LAMBDA_HANDLER, BUILD_DIR / "lambda_handler.py")
        print_success(f"Copied lambda_handler.py")
    else:
        print_error(f"Lambda handler not found: {LAMBDA_HANDLER}")
        sys.exit(1)
    
    # Copy app directory
    if APP_DIR.exists():
        if (BUILD_DIR / "app").exists():
            shutil.rmtree(BUILD_DIR / "app")
        shutil.copytree(APP_DIR, BUILD_DIR / "app")
        print_success(f"Copied app directory")
    else:
        print_error(f"App directory not found: {APP_DIR}")
        sys.exit(1)

def create_zip_archive():
    """Create deployment ZIP file"""
    print_step("Creating deployment ZIP archive")
    
    if ZIP_FILE.exists():
        ZIP_FILE.unlink()
    
    # Change to build directory to maintain correct paths
    cwd = os.getcwd()
    try:
        os.chdir(BUILD_DIR.parent)
        
        cmd = [
            "powershell" if sys.platform == "win32" else "bash",
            "-Command" if sys.platform == "win32" else "-c",
            f"Compress-Archive -Path build/* -DestinationPath {ZIP_FILE.name} -Force" if sys.platform == "win32" else f"cd build && zip -r ../{ZIP_FILE.name} . && cd .."
        ]
        
        result = run_command(cmd, "Creating ZIP archive")
        
        if ZIP_FILE.exists():
            zip_size_mb = ZIP_FILE.stat().st_size / (1024 * 1024)
            print_success(f"ZIP archive created: {zip_size_mb:.2f} MB")
        else:
            print_error("ZIP archive creation failed")
            sys.exit(1)
    finally:
        os.chdir(cwd)

def upload_to_s3():
    """Upload ZIP to S3"""
    print_step(f"Uploading ZIP to S3 bucket: {S3_BUCKET}")
    
    cmd = [
        "aws", "s3", "cp",
        str(ZIP_FILE),
        f"s3://{S3_BUCKET}/"
    ]
    
    result = run_command(cmd, "Uploading to S3")
    
    if result.returncode == 0:
        print_success(f"Successfully uploaded to S3")
    else:
        print_error("S3 upload failed")
        sys.exit(1)

def check_cloudformation_stack():
    """Check if CloudFormation stack exists"""
    print_step(f"Checking CloudFormation stack: {STACK_NAME}")
    
    cmd = [
        "aws", "cloudformation", "describe-stacks",
        "--stack-name", STACK_NAME,
        "--region", REGION
    ]
    
    result = run_command(cmd, "Checking stack status", check=False)
    return result.returncode == 0

def delete_existing_stack():
    """Delete existing CloudFormation stack"""
    print_warning(f"Deleting existing stack: {STACK_NAME}")
    
    cmd = [
        "aws", "cloudformation", "delete-stack",
        "--stack-name", STACK_NAME,
        "--region", REGION
    ]
    
    run_command(cmd, "Deleting old CloudFormation stack")
    
    # Wait for deletion
    print_step("Waiting for stack deletion (this may take a minute)...")
    import time
    time.sleep(30)
    
    print_success("Stack deletion initiated")

def deploy_with_sam():
    """Deploy using AWS SAM"""
    print_header("DEPLOYING TO AWS LAMBDA")
    
    template_file = PROJECT_ROOT / "template.yaml"
    if not template_file.exists():
        print_error(f"SAM template not found: {template_file}")
        sys.exit(1)
    
    cmd = [
        "sam", "deploy",
        "--template-file", str(template_file),
        "--stack-name", STACK_NAME,
        "--s3-bucket", S3_BUCKET,
        "--region", REGION,
        "--parameter-overrides", f"EnvironmentName={ENVIRONMENT}",
        "--capabilities", "CAPABILITY_NAMED_IAM"
    ]
    
    result = run_command(cmd, "Deploying with AWS SAM")
    
    if result.returncode != 0:
        print_error("SAM deployment failed")
        sys.exit(1)

def get_api_endpoint():
    """Get the API Gateway endpoint from CloudFormation outputs"""
    print_step("Retrieving API endpoint")
    
    cmd = [
        "aws", "cloudformation", "describe-stacks",
        "--stack-name", STACK_NAME,
        "--region", REGION,
        "--query", "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue",
        "--output", "text"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout.strip():
        endpoint = result.stdout.strip()
        print_success(f"API Endpoint: {endpoint}")
        return endpoint
    else:
        print_error("Could not retrieve API endpoint")
        return None

def update_frontend_config(endpoint):
    """Update frontend environment configuration with new API endpoint"""
    print_step("Updating frontend configuration")
    
    env_file = PROJECT_ROOT.parent / "frontend" / ".env.production"
    
    try:
        with open(env_file, "w") as f:
            f.write(f"VITE_API_URL={endpoint}\n")
        print_success(f"Updated {env_file} with API endpoint")
    except Exception as e:
        print_warning(f"Could not update frontend config: {e}")

def main():
    """Main deployment flow"""
    print_header("INVENTORY SYSTEM BACKEND - AWS LAMBDA DEPLOYMENT")
    
    start_time = datetime.now()
    
    try:
        # Step 1: Clean and prepare
        print_header("STEP 1: PREPARING BUILD ENVIRONMENT")
        clean_build_directory()
        
        # Step 2: Install dependencies
        print_header("STEP 2: INSTALLING DEPENDENCIES")
        install_dependencies()
        
        # Step 3: Copy application code
        print_header("STEP 3: COPYING APPLICATION CODE")
        copy_app_code()
        
        # Step 4: Create ZIP archive
        print_header("STEP 4: CREATING DEPLOYMENT PACKAGE")
        create_zip_archive()
        
        # Step 5: Upload to S3
        print_header("STEP 5: UPLOADING TO AWS S3")
        upload_to_s3()
        
        # Step 6: Check for existing stack
        print_header("STEP 6: CHECKING CLOUDFORMATION STACK")
        if check_cloudformation_stack():
            delete_existing_stack()
        
        # Step 7: Deploy with SAM
        deploy_with_sam()
        
        # Step 8: Get API endpoint
        print_header("STEP 8: FINALIZING DEPLOYMENT")
        endpoint = get_api_endpoint()
        
        if endpoint:
            update_frontend_config(endpoint)
        
        # Summary
        elapsed_time = datetime.now() - start_time
        
        print_header("✓ DEPLOYMENT COMPLETE")
        print(f"{Colors.OKGREEN}Deployment Summary:{Colors.ENDC}")
        print(f"  Stack Name: {STACK_NAME}")
        print(f"  Region: {REGION}")
        print(f"  Environment: {ENVIRONMENT}")
        if endpoint:
            print(f"  API Endpoint: {endpoint}")
        print(f"  Elapsed Time: {elapsed_time.total_seconds():.1f} seconds")
        print(f"\n{Colors.OKGREEN}Next Steps:{Colors.ENDC}")
        print(f"  1. Wait for Amplify to build the frontend")
        print(f"  2. Test the application at the Amplify URL")
        print(f"  3. Verify API connectivity in browser DevTools")
        
        return 0
        
    except KeyboardInterrupt:
        print_error("\nDeployment cancelled by user")
        return 1
    except Exception as e:
        print_error(f"\nDeployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
