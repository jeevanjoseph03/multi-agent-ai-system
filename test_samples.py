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
    with open(f"samples/emails/{filename}", 'r', encoding='utf-8') as f:
        email_content = f.read()
    
    # Send to API
    response = requests.post(f"{BASE_URL}/process/text", json={
        "content": email_content,
        "filename": filename
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Session ID: {result['session_id']}")
        print(f"   Format: {result['classification']['format_type']}") # Updated key
        print(f"   Intent: {result['classification']['intent']}")
        print(f"   Actions: {len(result['actions_taken'])} actions queued")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def test_json_sample(filename):
    """Test a JSON sample"""
    print(f"\n🧪 Testing JSON: {filename}")
    
    # Read JSON file
    with open(f"samples/jsons/{filename}", 'r', encoding='utf-8') as f:
        json_content = f.read() # Send as string
    
    # Send to API
    response = requests.post(f"{BASE_URL}/process/text", json={
        "content": json_content, # JSON content as a string
        "filename": filename
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Session ID: {result['session_id']}")
        print(f"   Format: {result['classification']['format_type']}") # Updated key
        print(f"   Intent: {result['classification']['intent']}")
        print(f"   Actions: {len(result['actions_taken'])} actions queued")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def test_pdf_text_sample(filename):
    """Test a PDF text sample"""
    print(f"\n🧪 Testing PDF text: {filename}")
    
    # Read PDF text file
    with open(f"samples/pdfs/{filename}", 'r', encoding='utf-8') as f:
        pdf_text_content = f.read()
    
    # Send to API
    response = requests.post(f"{BASE_URL}/process/text", json={
        "content": pdf_text_content,
        "filename": filename # Crucial for PDF classification from text
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Session ID: {result['session_id']}")
        print(f"   Format: {result['classification']['format_type']}") # Updated key
        print(f"   Intent: {result['classification']['intent']}")
        if "pdf_agent" in result.get("agent_results", {}):
            pdf_results = result["agent_results"]["pdf_agent"]
            print(f"   PDF Doc Type: {pdf_results.get('document_type')}")
            print(f"   PDF Flags: {pdf_results.get('flags')}")
            print(f"   PDF Suggested Action: {pdf_results.get('suggested_action')}")
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
            # Assuming your /status endpoint might not have these specific keys from the original script
            # Adjust if your /status provides more details like agents_active or uptime
            # print(f"   Agents active: {len(status.get('agents_active', []))}")
            # print(f"   Uptime: {status.get('uptime_seconds', 0):.1f} seconds")
            print(f"   Message: {status.get('message')}")
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

    # Test PDF text samples
    pdf_text_files = [f for f in os.listdir("samples/pdfs") if f.endswith('.txt')]
    for pdf_file in pdf_text_files:
        test_pdf_text_sample(pdf_file)
    
    print(f"\n🎉 Testing complete!")
    print(f"💡 Check your system at: {BASE_URL}")
    print(f"📚 API docs at: {BASE_URL}/docs")

if __name__ == "__main__":
    main()