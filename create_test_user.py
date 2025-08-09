#!/usr/bin/env python3
"""
Create test user and get authentication token
"""

import os
import sys

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kelime.settings')
import django
django.setup()

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

def create_test_user():
    """Create test user and return token"""
    username = "testuser"
    password = "testpass123"
    email = "test@example.com"
    
    # Create or get user
    try:
        user = User.objects.get(username=username)
        print(f"✅ Using existing user: {username}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )
        print(f"✅ Created new user: {username}")
    
    # Get or create token
    token, created = Token.objects.get_or_create(user=user)
    
    if created:
        print(f"✅ Created new token for {username}")
    else:
        print(f"✅ Using existing token for {username}")
    
    print(f"\n🔑 Authentication Token: {token.key}")
    print(f"\n📝 Test Commands:")
    print(f"# Test debug endpoint")
    print(f'curl "http://localhost:8000/debug/test/"')
    print(f"\n# Test with authentication")
    print(f'curl -H "Authorization: Token {token.key}" "http://localhost:8000/debug/test/"')
    print(f"\n# Test manual text source")
    print(f"""curl -X POST "http://localhost:8000/sources/enhanced/" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Token {token.key}" \\
  -d '{{"title": "Test Text", "manual_text": "This is a test with words like magnificent and extraordinary."}}'""")
    
    return token.key

if __name__ == "__main__":
    token = create_test_user()
    print(f"\n🎯 Save this token for testing: {token}") 