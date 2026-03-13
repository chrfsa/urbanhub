#!/usr/bin/env python
"""
UrbanHub - API Server Launcher
Run this to start the FastAPI streaming server
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.api.server import run_server

if __name__ == "__main__":
    print("🚀 Starting UrbanHub API Server...")
    print("📡 API available at: http://localhost:8000")
    print("📚 Docs available at: http://localhost:8000/docs")
    run_server(host="0.0.0.0", port=8000)
