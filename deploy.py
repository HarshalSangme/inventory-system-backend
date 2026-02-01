#!/usr/bin/env python3
"""
Inventory System Backend - AWS Lambda Deployment Script
Deploys FastAPI backend to AWS Lambda with API Gateway
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path

class LambdaDeployer:
    def __init__(self):
        self.backend_dir = Path(__file__).parent
        self.build_dir = self.backend_dir / "build"
        self.zip_file = self.backend_dir / "lambda-package.zip"
        self.s3_bucket = "inventory-system-deploy-dev"
        self.stack_name = "inventory-backend-dev"
        self.region = "us-east-1"
        self.env_name = "dev"
        
    def log(self, message, status="INFO"):
        """Print colored log messages"""
        colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m",
            "ERROR": "\033[91m",
            "WARNING": "\033[93m"
        }
        reset = "\033[0m"
        print(f"{colors.get(status, '')}{status}{reset} | {message}")
    
    def run_command(self, cmd, check=True, shell=False):
        """Run shell command and return output"""
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                check=check,
                shell=shell
            )
            return result.stdout.strip(), result.returncode
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e.stderr}", "ERROR")
            raise
    
    def clean_build(self):
        """Remove old build artifacts"""
        self.log("Cleaning old build artifacts...")
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        if self.zip_file.exists():
            self.zip_file.unlink()
        self.log("Cleaned", "SUCCESS")
    
    def setup_build_directory(self):
        """Create build directory structure"""
        self.log("Setting up build directory...")
        self.build_dir.mkdir(exist_ok=True)
        
        # Copy lambda handler
        shutil.copy(self.backend_dir / "lambda_handler.py", self.build_dir / "lambda_handler.py")
        
        # Copy app code
        app_src = self.backend_dir / "app"
        app_dst = self.build_dir / "app"
        if app_dst.exists():
            shutil.rmtree(app_dst)
        shutil.copytree(app_src, app_dst)
        
        self.log("Build directory prepared", "SUCCESS")
    
    def install_dependencies_docker(self):
        """Use Docker to install Linux-compatible dependencies"""
        self.log("Installing dependencies with Docker...")
        
        # Check if Docker is available
        docker_check, _ = self.run_command("docker --version", check=False)
        if not docker_check:
            self.log("Docker not found. Installing dependencies locally (may not work on Lambda)...", "WARNING")
            self.install_dependencies_local()
            return
        
        # Create requirements for pip in Docker
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.build_dir}:/var/task",
            "public.ecr.aws/lambda/python:3.11",
            "pip", "install", "-r", "/var/task/../requirements.txt",
            "-t", "/var/task"
        ]
        
        try:
            self.log("Running Docker container for dependency installation...")
            subprocess.run(docker_cmd, check=True)
            self.log("Dependencies installed via Docker", "SUCCESS")
        except subprocess.CalledProcessError:
            self.log("Docker installation failed, trying local install...", "WARNING")
            self.install_dependencies_local()
    
    def install_dependencies_local(self):
        """Fallback: install dependencies locally"""
        self.log("Installing dependencies locally...")
        
        pip_cmd = [
            sys.executable, "-m", "pip", "install",
            "-r", str(self.backend_dir / "requirements.txt"),
            "-t", str(self.build_dir),
            "--upgrade"
        ]
        
        subprocess.run(pip_cmd, check=True)
        self.log("Dependencies installed locally", "SUCCESS")
    
    def create_zip(self):
        """Create deployment ZIP file"""
        self.log("Creating deployment package...")
        
        # Use PowerShell on Windows, zip on Unix
        if sys.platform == "win32":
            ps_cmd = f"""
            $compress = @{{
                Path = '{self.build_dir}/*'
                DestinationPath = '{self.zip_file}'
                CompressionLevel = 'Optimal'
            }}
            Compress-Archive @compress -Force
            """
            subprocess.run(["powershell", "-Command", ps_cmd], check=True)
        else:
            os.chdir(self.build_dir)
            subprocess.run(["zip", "-r", str(self.zip_file), "."], check=True)
            os.chdir(self.backend_dir)
        
        zip_size_mb = self.zip_file.stat().st_size / (1024 * 1024)
        self.log(f"Created {self.zip_file.name} ({zip_size_mb:.2f} MB)", "SUCCESS")
    
    def upload_to_s3(self):
        """Upload ZIP to S3"""
        self.log("Uploading to S3...")
        
        cmd = [
            "aws", "s3", "cp",
            str(self.zip_file),
            f"s3://{self.s3_bucket}/",
            "--region", self.region
        ]
        
        output, _ = self.run_command(cmd, shell=False)
        self.log(output, "SUCCESS")
    
    def delete_old_stack(self):
        """Delete old CloudFormation stack if exists"""
        self.log("Checking for existing stack...")
        
        cmd = [
            "aws", "cloudformation", "describe-stacks",
            "--stack-name", self.stack_name,
            "--region", self.region
        ]
        
        _, code = self.run_command(cmd, check=False)
        
        if code == 0:
            self.log(f"Deleting old stack: {self.stack_name}...")
            del_cmd = [
                "aws", "cloudformation", "delete-stack",
                "--stack-name", self.stack_name,
                "--region", self.region
            ]
            self.run_command(del_cmd)
            self.log("Stack deletion initiated", "SUCCESS")
            
            # Wait for deletion
            import time
            self.log("Waiting for stack deletion (this may take a minute)...")
            time.sleep(30)
        else:
            self.log("No existing stack found", "INFO")
    
    def deploy_with_sam(self):
        """Deploy using SAM CLI"""
        self.log("Deploying with AWS SAM...")
        
        cmd = [
            "sam", "deploy",
            "--template-file", str(self.backend_dir / "template.yaml"),
            "--stack-name", self.stack_name,
            "--s3-bucket", self.s3_bucket,
            "--region", self.region,
            "--parameter-overrides", f"EnvironmentName={self.env_name}",
            "--capabilities", "CAPABILITY_NAMED_IAM"
        ]
        
        try:
            subprocess.run(cmd, check=True, cwd=str(self.backend_dir))
            self.log("SAM deployment completed", "SUCCESS")
            self.get_api_endpoint()
        except subprocess.CalledProcessError as e:
            self.log(f"SAM deployment failed: {e}", "ERROR")
            raise
    
    def get_api_endpoint(self):
        """Retrieve API endpoint from CloudFormation outputs"""
        self.log("Retrieving API endpoint...")
        
        cmd = [
            "aws", "cloudformation", "describe-stacks",
            "--stack-name", self.stack_name,
            "--region", self.region,
            "--query", "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue",
            "--output", "text"
        ]
        
        endpoint, _ = self.run_command(cmd)
        
        if endpoint:
            self.log(f"API Endpoint: {endpoint}", "SUCCESS")
            
            # Update frontend .env.production
            env_file = self.backend_dir.parent / "frontend" / ".env.production"
            with open(env_file, "w") as f:
                f.write(f"VITE_API_URL={endpoint}\n")
            self.log(f"Updated frontend .env.production", "SUCCESS")
            
            return endpoint
        else:
            self.log("Could not retrieve API endpoint", "WARNING")
            return None
    
    def deploy(self):
        """Execute full deployment"""
        try:
            self.log("=" * 60)
            self.log("Starting Lambda Deployment", "INFO")
            self.log("=" * 60)
            
            self.clean_build()
            self.setup_build_directory()
            self.install_dependencies_docker()
            self.create_zip()
            self.upload_to_s3()
            self.delete_old_stack()
            self.deploy_with_sam()
            
            self.log("=" * 60)
            self.log("Deployment Complete! ✅", "SUCCESS")
            self.log("=" * 60)
            
        except Exception as e:
            self.log(f"Deployment failed: {str(e)}", "ERROR")
            sys.exit(1)

if __name__ == "__main__":
    deployer = LambdaDeployer()
    deployer.deploy()
