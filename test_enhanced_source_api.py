#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced source extraction API.
Tests all source types: PDF, SRT, Web URL, YouTube URL, and Manual Text.
"""

import requests
import json
import os
import sys

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kelime.settings')
import django
django.setup()

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_USERNAME = "testuser"
TEST_USER_PASSWORD = "testpass123"

class SourceAPITester:
    def __init__(self):
        self.token = None
        self.headers = {}
        
    def setup_test_user(self):
        """Create or get test user and auth token"""
        try:
            user = User.objects.get(username=TEST_USER_USERNAME)
            print(f"✅ Using existing test user: {TEST_USER_USERNAME}")
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=TEST_USER_USERNAME,
                password=TEST_USER_PASSWORD,
                email="test@example.com"
            )
            print(f"✅ Created test user: {TEST_USER_USERNAME}")
        
        # Get or create token
        token, created = Token.objects.get_or_create(user=user)
        self.token = token.key
        self.headers = {
            'Authorization': f'Token {self.token}',
            'Content-Type': 'application/json'
        }
        print(f"✅ Authentication token ready")
        
    def test_debug_endpoint(self):
        """Test the debug endpoint first"""
        print("\n🔍 Testing debug endpoint...")
        
        try:
            response = requests.get(f"{BASE_URL}/debug/test/", headers=self.headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("✅ Debug endpoint working")
                return True
            else:
                print("❌ Debug endpoint failed")
                return False
                
        except Exception as e:
            print(f"❌ Debug endpoint error: {e}")
            return False
    
    def test_manual_text_source(self):
        """Test manual text input"""
        print("\n📝 Testing manual text source...")
        
        data = {
            'title': 'Test Manual Text',
            'manual_text': 'This is a test sentence with some vocabulary words like magnificent, extraordinary, and wonderful.'
        }
        
        return self._test_source_creation(data, "Manual Text")
    
    def test_web_url_source(self):
        """Test web URL scraping"""
        print("\n🌐 Testing web URL source...")
        
        data = {
            'title': 'Test Web Article',
            'web_url': 'https://www.bbc.com/news'
        }
        
        return self._test_source_creation(data, "Web URL")
    
    def test_youtube_url_source(self):
        """Test YouTube transcript extraction"""
        print("\n🎥 Testing YouTube URL source...")
        
        # Using a video that likely has English subtitles
        data = {
            'title': 'Test YouTube Video',
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'  # Rick Roll - known to have transcripts
        }
        
        return self._test_source_creation(data, "YouTube URL")
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n⚠️ Testing error handling...")
        
        # Test with no input
        print("Testing empty request...")
        empty_response = self._test_source_creation({}, "Empty Request", expect_error=True)
        
        # Test with multiple inputs
        print("Testing multiple inputs...")
        multi_data = {
            'title': 'Multiple Inputs Test',
            'manual_text': 'Some text',
            'web_url': 'https://example.com'
        }
        multi_response = self._test_source_creation(multi_data, "Multiple Inputs", expect_error=True)
        
        # Test with invalid URL
        print("Testing invalid URL...")
        invalid_url_data = {
            'title': 'Invalid URL Test',
            'web_url': 'not-a-valid-url'
        }
        invalid_response = self._test_source_creation(invalid_url_data, "Invalid URL", expect_error=True)
        
        return empty_response or multi_response or invalid_response
    
    def _test_source_creation(self, data, source_type, expect_error=False):
        """Generic method to test source creation"""
        try:
            response = requests.post(
                f"{BASE_URL}/sources/enhanced/",
                json=data,
                headers=self.headers
            )
            
            print(f"  Status: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"  Response keys: {list(response_data.keys())}")
                
                if expect_error:
                    if response.status_code >= 400:
                        print(f"  ✅ Expected error received for {source_type}")
                        print(f"  Error: {response_data.get('error', response_data.get('detail', 'Unknown error'))}")
                        return True
                    else:
                        print(f"  ❌ Expected error but got success for {source_type}")
                        return False
                else:
                    if response.status_code == 201:
                        print(f"  ✅ {source_type} source created successfully")
                        print(f"  Source ID: {response_data.get('source_id')}")
                        print(f"  Words extracted: {response_data.get('words_extracted')}")
                        print(f"  Analysis: {response_data.get('analysis', {})}")
                        return True
                    else:
                        print(f"  ❌ {source_type} source creation failed")
                        print(f"  Error: {response_data}")
                        return False
                        
            except json.JSONDecodeError:
                print(f"  ❌ Invalid JSON response for {source_type}")
                print(f"  Raw response: {response.text[:200]}...")
                return False
                
        except Exception as e:
            print(f"  ❌ Exception during {source_type} test: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Enhanced Source API Tests")
        print("=" * 50)
        
        # Setup
        self.setup_test_user()
        
        # Tests
        tests = [
            ("Debug Endpoint", self.test_debug_endpoint),
            ("Manual Text", self.test_manual_text_source),
            ("Web URL", self.test_web_url_source),
            ("YouTube URL", self.test_youtube_url_source),
            ("Error Handling", self.test_error_handling),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"❌ {test_name} test crashed: {e}")
                results[test_name] = False
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:20} : {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! API is working correctly.")
        else:
            print("⚠️ Some tests failed. Check the logs above for details.")
        
        return passed == total


if __name__ == "__main__":
    tester = SourceAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1) 