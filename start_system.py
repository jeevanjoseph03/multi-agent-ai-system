#!/usr/bin/env python3
"""
Startup script for Multi-Agent AI System
"""

import subprocess
import sys
import os

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'fastapi', 'uvicorn', 'PyPDF2', 'pydantic', 'requests'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("📦 Installing missing packages...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
        print("✅ All packages installed!")

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting Multi-Agent AI System...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API Documentation at: http://localhost:8000/docs")
    print("💡 Health Check at: http://localhost:8000/status")
    print("\n" + "="*50)
    print("Press Ctrl+C to stop the server")
    print("="*50)
    
    try:
        subprocess.run([
            sys.executable, '-m', 'uvicorn', 
            'multi_agent_system.main:app',
            '--reload',
            '--host', '127.0.0.1',
            '--port', '8000'
        ])
    except KeyboardInterrupt:
        print("\n🛑 System stopped by user")
    except Exception as e:
        print(f"❌ Error starting system: {e}")
        print("💡 Try running directly: python -m uvicorn multi_agent_system.main:app --reload")

if __name__ == "__main__":
    print("🎯 Multi-Agent AI System Startup")
    print("=" * 40)
    
    # Check dependencies
    check_dependencies()
    
    # Start the server
    start_server()