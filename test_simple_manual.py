#!/usr/bin/env python3
import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kelime.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Source, Word, UserWordKnowledge
from core.serializers import EnhancedSourceSerializer
from rest_framework.test import APIRequestFactory

def test_manual_source():
    """Test manual source creation directly"""
    
    # Get test user
    try:
        user = User.objects.get(username='testuser')
        print(f"✅ Using user: {user.username}")
    except User.DoesNotExist:
        print("❌ Test user not found")
        return
    
    # Test data
    data = {
        'title': 'Test Manual Text',
        'manual_text': 'This is a test sentence with vocabulary words like magnificent, extraordinary, and wonderful.'
    }
    
    print(f"🧪 Testing with data: {data}")
    
    # Create serializer
    serializer = EnhancedSourceSerializer(data=data)
    
    if serializer.is_valid():
        print("✅ Serializer validation passed")
        print(f"Validated data: {serializer.validated_data}")
        
        try:
            # Try to save
            source = serializer.save(user=user)
            print(f"✅ Source created with ID: {source.id}")
            print(f"Source type: {source.source_type}")
            print(f"Content length: {len(source.content)}")
            
        except Exception as e:
            print(f"❌ Error saving source: {e}")
            import traceback
            traceback.print_exc()
            
    else:
        print(f"❌ Serializer validation failed: {serializer.errors}")

if __name__ == "__main__":
    test_manual_source() 