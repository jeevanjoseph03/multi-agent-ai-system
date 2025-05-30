#!/usr/bin/env python3
"""
Test script to verify all sample data works correctly
Run this after starting your system to test everything
"""

import requests
import json
import os

# Base URL for your API
BASE_URL = "http://localhost:8000"

def test_email_sample(filename):
    """Test an email sample"""
    print(f"\n🧪 Testing email: {filename}")
    
    # Read email file
    with open(f"samples/emails/{filename}", 'r') as f:
        email_content = f.read()
    
    # Send to API
    response = requests.post(f"{BASE_URL}/process/text", json={
        "content": email_content,
        "filename": filename,
        "content_type": "email"
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Session ID: {result['session_id']}")
        print(f"   Format: {result['classification']['format']}")
        print(f"   Intent: {result['classification']['intent']}")
        print(f"   Actions: {len(result['actions_taken'])} actions queued")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def test_json_sample(filename):
    """Test a JSON sample"""
    print(f"\n🧪 Testing JSON: {filename}")
    
    # Read JSON file
    with open(f"samples/jsons/{filename}", 'r') as f:
        json_content = f.read()
    
    # Send to API
    response = requests.post(f"{BASE_URL}/process/text", json={
        "content": json_content,
        "filename": filename,
        "content_type": "json"
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Session ID: {result['session_id']}")
        print(f"   Format: {result['classification']['format']}")
        print(f"   Intent: {result['classification']['intent']}")
        print(f"   Actions: {len(result['actions_taken'])} actions queued")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def test_system_status():
    """Test if the system is running"""
    print("🔍 Checking system status...")
    
    try:
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ System is healthy!")
            print(f"   Agents active: {len(status['agents_active'])}")
            print(f"   Uptime: {status['uptime_seconds']:.1f} seconds")
            return True
        else:
            print(f"❌ System not responding: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to system. Is it running?")
        print("💡 Start it with: python start_system.py")
        return False

def main():
    """Run all tests"""
    print("🎯 Multi-Agent System - Sample Data Tester")
    print("=" * 50)
    
    # Check if system is running
    if not test_system_status():
        return
    
    # Test email samples
    email_files = [f for f in os.listdir("samples/emails") if f.endswith('.eml')]
    for email_file in email_files:
        test_email_sample(email_file)
    
    # Test JSON samples
    json_files = [f for f in os.listdir("samples/jsons") if f.endswith('.json')]
    for json_file in json_files:
        test_json_sample(json_file)
    
    print(f"\n🎉 Testing complete!")
    print(f"💡 Check your system at: {BASE_URL}")
    print(f"📚 API docs at: {BASE_URL}/docs")

if __name__ == "__main__":
    main()