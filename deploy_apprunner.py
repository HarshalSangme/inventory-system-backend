#!/usr/bin/env python3
"""
One-click AWS App Runner deployment
"""
import subprocess
import json
import time
import sys

print("""
╔════════════════════════════════════════════════════════════════╗
║      AWS APP RUNNER - ONE-CLICK DEPLOYMENT (15 min)           ║
╚════════════════════════════════════════════════════════════════╝
""")

# Check if AWS CLI is installed
try:
    subprocess.run(["aws", "--version"], capture_output=True, check=True)
except:
    print("❌ AWS CLI not installed. Install it and try again.")
    sys.exit(1)

# GitHub repo details
REPO = "HarshalSangme/inventory-system-backend"
BRANCH = "main"
SERVICE_NAME = "inventory-backend"
REGION = "us-east-1"

print("📋 Configuration:")
print(f"   Repository: {REPO}")
print(f"   Branch: {BRANCH}")
print(f"   Service: {SERVICE_NAME}")
print(f"   Region: {REGION}")

# Get GitHub token from user
print("\n🔑 Authentication:")
token = input("   Enter your GitHub Personal Access Token\n   (Create at: https://github.com/settings/tokens)\n   Token: ").strip()

if not token:
    print("❌ Token required!")
    sys.exit(1)

print("\n⏳ Creating App Runner service...")

# Create the service
cmd = [
    "aws", "apprunner", "create-service",
    "--service-name", SERVICE_NAME,
    "--source-configuration",
    json.dumps({
        "CodeRepository": {
            "RepositoryUrl": f"https://github.com/{REPO}",
            "SourceCodeVersion": {
                "Type": "BRANCH",
                "Value": BRANCH
            },
            "AuthConnection": {
                "ConnectionArn": f"arn:aws:apprunner:{REGION}:TOKEN/{token}"
            }
        },
        "AutoDeploymentsEnabled": True
    }),
    "--instance-configuration",
    json.dumps({
        "Cpu": "0.25",
        "Memory": "512",
        "InstanceRoleArn": ""
    }),
    "--region", REGION
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    output = json.loads(result.stdout)
    service_arn = output["Service"]["ServiceArn"]
    
    print(f"✅ Service created: {service_arn}")
    print("\n⏳ Waiting for deployment (this takes 5-15 minutes)...")
    
    # Poll for status
    for i in range(60):
        time.sleep(10)
        check_cmd = [
            "aws", "apprunner", "describe-service",
            "--service-arn", service_arn,
            "--region", REGION
        ]
        
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        service = json.loads(result.stdout)["Service"]
        status = service["Status"]
        
        if status == "RUNNING":
            url = service["ServiceUrl"]
            print(f"\n✅ DEPLOYMENT COMPLETE!")
            print(f"🔗 API URL: {url}")
            print(f"\n📝 Update frontend .env.production:")
            print(f"   VITE_API_URL={url}")
            
            # Copy to clipboard (Windows)
            try:
                import pyperclip
                pyperclip.copy(url)
                print(f"\n✅ URL copied to clipboard!")
            except:
                pass
            
            break
        elif status == "OPERATION_IN_PROGRESS":
            print(f"   ⏳ Deploying... ({(i+1)*10} seconds elapsed)")
        else:
            print(f"   Status: {status}")

except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 Manual setup at: https://console.aws.amazon.com/apprunner/")
    sys.exit(1)
