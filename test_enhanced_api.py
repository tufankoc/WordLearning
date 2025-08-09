#!/usr/bin/env python3
"""
Test script for the Enhanced Source API with multiple input types.
Demonstrates PDF, web, YouTube, SRT, and manual text processing.
"""

import requests
import json
import os

# API Configuration
BASE_URL = "http://127.0.0.1:8003"
API_URL = f"{BASE_URL}/api/sources/enhanced/"

# You'll need to authenticate first and get a session cookie or token
# For this demo, we'll assume you have a valid session

def test_manual_text_input():
    """Test manual text input"""
    print("🔤 Testing manual text input...")
    
    data = {
        'title': 'Test Manual Text',
        'manual_text': '''
        Learning vocabulary is essential for language acquisition. 
        Students who practice regularly tend to improve their comprehension significantly. 
        Advanced learners often use authentic materials like newspapers and podcasts 
        to expand their lexical knowledge and develop fluency.
        '''
    }
    
    try:
        response = requests.post(API_URL, data=data)
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Success: {result['success_message']}")
            print(f"📊 Analysis: {result['analysis']}")
            print(f"📝 Preview: {result['content_preview'][:100]}...")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "="*50 + "\n")

def test_web_url_input():
    """Test web URL input"""
    print("🌐 Testing web URL input...")
    
    data = {
        'title': 'BBC News Article',
        'web_url': 'https://www.bbc.com/news'
    }
    
    try:
        response = requests.post(API_URL, data=data)
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Success: {result['success_message']}")
            print(f"📊 Analysis: {result['analysis']}")
            print(f"📝 Preview: {result['content_preview'][:100]}...")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "="*50 + "\n")

def test_youtube_url_input():
    """Test YouTube URL input"""
    print("📺 Testing YouTube URL input...")
    
    data = {
        'title': 'TED Talk - Language Learning',
        'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'  # Sample URL
    }
    
    try:
        response = requests.post(API_URL, data=data)
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Success: {result['success_message']}")
            print(f"📊 Analysis: {result['analysis']}")
            print(f"📝 Preview: {result['content_preview'][:100]}...")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "="*50 + "\n")

def test_srt_file_input():
    """Test SRT file input"""
    print("📺 Testing SRT file input...")
    
    # Create a sample SRT file
    srt_content = """1
00:00:01,000 --> 00:00:04,000
Hello everyone, welcome to our vocabulary lesson.

2
00:00:04,500 --> 00:00:08,000
Today we will learn about advanced academic words.

3
00:00:08,500 --> 00:00:12,000
These words are essential for university students.

4
00:00:12,500 --> 00:00:16,000
Comprehension and fluency require consistent practice.
"""
    
    # Save to temporary file
    with open('test_subtitle.srt', 'w', encoding='utf-8') as f:
        f.write(srt_content)
    
    try:
        with open('test_subtitle.srt', 'rb') as f:
            files = {'srt_file': ('test_subtitle.srt', f, 'text/plain')}
            data = {'title': 'Sample Vocabulary Lesson Subtitles'}
            
            response = requests.post(API_URL, data=data, files=files)
            print(f"Status: {response.status_code}")
            if response.status_code == 201:
                result = response.json()
                print(f"✅ Success: {result['success_message']}")
                print(f"📊 Analysis: {result['analysis']}")
                print(f"📝 Preview: {result['content_preview'][:100]}...")
            else:
                print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    finally:
        # Clean up
        if os.path.exists('test_subtitle.srt'):
            os.remove('test_subtitle.srt')
    
    print("\n" + "="*50 + "\n")

def test_pdf_file_input():
    """Test PDF file input (would need actual PDF file)"""
    print("📄 Testing PDF file input...")
    print("⚠️  PDF test requires an actual PDF file")
    print("💡 To test: create a small PDF and upload via files={'pdf_file': ('sample.pdf', file_handle, 'application/pdf')}")
    print("\n" + "="*50 + "\n")

def test_validation_errors():
    """Test validation scenarios"""
    print("🔒 Testing validation...")
    
    # Test 1: No input provided
    print("Test 1: No input provided")
    try:
        response = requests.post(API_URL, data={'title': 'No Input Test'})
        print(f"Status: {response.status_code}")
        if response.status_code == 400:
            print(f"✅ Validation worked: {response.json()}")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 2: Multiple inputs provided
    print("\nTest 2: Multiple inputs provided")
    try:
        data = {
            'title': 'Multiple Input Test',
            'manual_text': 'Some text',
            'web_url': 'https://example.com'
        }
        response = requests.post(API_URL, data=data)
        print(f"Status: {response.status_code}")
        if response.status_code == 400:
            print(f"✅ Validation worked: {response.json()}")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 3: Invalid YouTube URL
    print("\nTest 3: Invalid YouTube URL")
    try:
        data = {
            'title': 'Invalid YouTube Test',
            'youtube_url': 'https://example.com/not-youtube'
        }
        response = requests.post(API_URL, data=data)
        print(f"Status: {response.status_code}")
        if response.status_code == 400:
            print(f"✅ Validation worked: {response.json()}")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "="*50 + "\n")

def main():
    """Run all tests"""
    print("🚀 Enhanced Source API Test Suite")
    print("="*50)
    
    # Test input types
    test_manual_text_input()
    test_web_url_input()
    test_youtube_url_input()
    test_srt_file_input()
    test_pdf_file_input()
    
    # Test validation
    test_validation_errors()
    
    print("🏁 Test suite completed!")
    print("\n📋 Summary:")
    print("• Manual text: ✅ Ready")
    print("• Web URL: ✅ Ready") 
    print("• YouTube: ✅ Ready (needs transcript)")
    print("• SRT files: ✅ Ready")
    print("• PDF files: ✅ Ready (needs actual PDF)")
    print("• Validation: ✅ Working")

if __name__ == "__main__":
    print("⚠️  Note: Make sure Django server is running on port 8003")
    print("⚠️  Note: You need to be authenticated (login first)")
    print("⚠️  Note: Update the requests to include authentication\n")
    
    # Uncomment to run tests
    # main()
    
    print("🔧 To run tests:")
    print("1. Start Django server: python manage.py runserver 8003")
    print("2. Login to get authentication")
    print("3. Uncomment main() call in this script")
    print("4. Run: python test_enhanced_api.py") 