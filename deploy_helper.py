#!/usr/bin/env python3
"""Deploy Falsifi to Render.com via API"""
import requests
import json
import sys

# Render API endpoint
RENDER_API = "https://api.render.com/v1"

# Try to deploy using the blueprint approach
# This requires a Render API key which we don't have

# Alternative: Print instructions for manual deployment
print("""
╔════════════════════════════════════════════════════════════════╗
║               Falsifi Deployment Instructions                   ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  1. Visit: https://dashboard.render.com/                       ║
║                                                                ║
║  2. Sign up with GitHub (use the-vec account)                  ║
║                                                                ║
║  3. Click "New +" → "Web Service"                              ║
║                                                                ║
║  4. Connect GitHub repo: the-vec/falsifi                       ║
║                                                                ║
║  5. Configure:                                                 ║
║     - Name: falsifi                                            ║
║     - Runtime: Python 3                                        ║
║     - Build Command: pip install -r requirements.txt           ║
║     - Start Command: gunicorn --bind 0.0.0.0:$PORT app:app     ║
║     - Plan: Free                                               ║
║                                                                ║
║  6. Add Environment Variables:                                 ║
║     - SECRET_KEY: (auto-generated)                             ║
║     - DATABASE_URL: sqlite:///instance/falsifi.db              ║
║                                                                ║
║  7. Click "Create Web Service"                                 ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
""")

# Or use the deploy button URL
print("\n📌 Quick Deploy URL:")
print("https://render.com/deploy?repo=https://github.com/the-vec/falsifi")
