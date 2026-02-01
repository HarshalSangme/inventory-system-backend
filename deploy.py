#!/usr/bin/env python3
"""
Simple deployment script - Deploy to Render.com (Free)
"""
import subprocess
import webbrowser

print("""
╔════════════════════════════════════════════════════════════════╗
║         INVENTORY BACKEND - DEPLOYMENT TO RENDER.COM          ║
╚════════════════════════════════════════════════════════════════╝

✅ Docker files are ready!

DEPLOYMENT OPTIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  LOCAL TESTING (Free, instant)
   Command: docker-compose up
   URL: http://localhost:8000

2️⃣  RENDER.COM DEPLOYMENT (Free tier, 15 min startup)
   
   Steps:
   a) Go to: https://render.com
   b) Sign up/Login with GitHub
   c) Create New → Web Service
   d) Connect your repository: https://github.com/HarshalSangme/inventory-system-backend
   e) Environment: Python
   f) Build: pip install -r requirements.txt
   g) Start: python create_admin.py && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
   h) Click Deploy
   i) Your API endpoint will be: https://inventory-backend-XXXX.onrender.com

3️⃣  OR RAILWAY DEPLOYMENT (Free tier, 5GB/month)
   a) Go to: https://railway.app
   b) Connect GitHub repo
   c) Deploy automatically

4️⃣  OR FLY.IO DEPLOYMENT (Pay-as-you-go, ~$5/month)
   a) Go to: https://fly.io
   b) Get API key
   c) Run: flyctl launch

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 QUICK START (Test locally):
   
   $ docker-compose up
   
   Then open: http://localhost:8000/docs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ All necessary files are configured:
   • Dockerfile - Container configuration
   • docker-compose.yml - Local testing
   • render.yaml - Render.com deployment
   • Procfile - Heroku/Railway deployment
   • requirements.txt - Python dependencies

""")

choice = input("🚀 What would you like to do? (1-4 or 'q'): ").strip()

if choice == "1":
    print("\n▶️  Starting local development server...")
    print("   URL: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print("\n   Press Ctrl+C to stop\n")
    subprocess.run(["docker-compose", "up"], cwd=".")
    
elif choice == "2":
    print("\n📱 Opening Render.com...")
    webbrowser.open("https://render.com/dashboard")
    print("\n✅ Instructions:")
    print("   1. Click 'New +' → Web Service")
    print("   2. Connect GitHub repository")
    print("   3. Use the settings from render.yaml")
    print("   4. Deploy!")
    
elif choice == "3":
    print("\n📱 Opening Railway.app...")
    webbrowser.open("https://railway.app")
    print("\n✅ Railway will auto-detect and deploy!")
    
elif choice == "4":
    print("\n📱 Opening Fly.io...")
    webbrowser.open("https://fly.io")
    print("\n✅ Get started with Fly.io for $5/month hosting")
    
elif choice.lower() == "q":
    print("Goodbye!")
    
else:
    print("Invalid choice")
