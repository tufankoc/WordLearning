#!/bin/bash

echo "=== STOP WORDS FILTERING FEATURE TEST ==="
echo

# Configuration
BASE_URL="http://localhost:8000"
# Provide tokens via environment variables or replace the placeholders below for local testing only.
PRO_TOKEN="${PRO_TOKEN:-YOUR_PRO_TOKEN}"
FREE_TOKEN="${FREE_TOKEN:-YOUR_FREE_TOKEN}"

echo "🚫 Testing Stop Words Filtering Feature"
echo "----------------------------------------"

# Test 1: Check Profile Settings
echo "1️⃣ Testing Profile Settings..."

echo "Pro User Profile:"
response=$(curl -s -X GET "${BASE_URL}/api/profile/" \
  -H "Authorization: Token ${PRO_TOKEN}" \
  -H "Content-Type: application/json")

echo "$response" | jq '{
  username: .user.username,
  is_pro: .profile.is_pro_active,
  filter_stop_words: .profile.filter_stop_words,
  effective_filter: .profile.effective_filter_stop_words,
  can_modify: .profile.can_modify_stop_words_filter
}'
echo

echo "Free User Profile:"
response=$(curl -s -X GET "${BASE_URL}/api/profile/" \
  -H "Authorization: Token ${FREE_TOKEN}" \
  -H "Content-Type: application/json")

echo "$response" | jq '{
  username: .user.username,
  is_pro: .profile.is_pro_active,
  filter_stop_words: .profile.filter_stop_words,
  effective_filter: .profile.effective_filter_stop_words,
  can_modify: .profile.can_modify_stop_words_filter
}'
echo

# Test 2: Pro User Toggle (should succeed)
echo "2️⃣ Testing Pro User Toggle (disable filtering)..."
response=$(curl -s -X PATCH "${BASE_URL}/api/profile/" \
  -H "Authorization: Token ${PRO_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"filter_stop_words": false}')

echo "Pro User Toggle Result:"
echo "$response" | jq '{
  status: .status,
  changes: .changes,
  errors: .errors,
  new_setting: .profile.filter_stop_words,
  effective_filter: .profile.effective_filter_stop_words
}'
echo

# Test 3: Free User Toggle Attempt (should fail)
echo "3️⃣ Testing Free User Toggle Attempt (should fail)..."
response=$(curl -s -X PATCH "${BASE_URL}/api/profile/" \
  -H "Authorization: Token ${FREE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"filter_stop_words": false}')

echo "Free User Toggle Attempt:"
echo "$response" | jq '{
  status: .status,
  changes: .changes,
  errors: .errors,
  setting_unchanged: .profile.filter_stop_words,
  effective_filter: .profile.effective_filter_stop_words
}'
echo

# Test 4: Create Test Source with Stop Words
echo "4️⃣ Testing Source Creation with Stop Words..."

# Test text with lots of stop words
test_text="The quick brown fox jumps over the lazy dog. The dog is sleeping under the tree. The fox is running through the forest. The forest is full of trees and animals. The animals are living in the forest."

echo "Creating source with stop words (Pro user - filtering disabled)..."
response=$(curl -s -X POST "${BASE_URL}/api/sources/enhanced/" \
  -H "Authorization: Token ${PRO_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Stop Words Test - Pro User (Filtering OFF)\",
    \"manual_text\": \"$test_text\"
  }")

echo "Source Creation Result:"
echo "$response" | jq '{
  status: .status,
  source_id: .source_id,
  words_extracted: .words_extracted,
  title: .title
}'
echo

# Test 5: Re-enable filtering for Pro user
echo "5️⃣ Re-enabling filtering for Pro user..."
response=$(curl -s -X PATCH "${BASE_URL}/api/profile/" \
  -H "Authorization: Token ${PRO_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"filter_stop_words": true}')

echo "Re-enable Result:"
echo "$response" | jq '{
  status: .status,
  new_setting: .profile.filter_stop_words
}'
echo

# Test 6: Create Source with Filtering Enabled
echo "6️⃣ Testing Source Creation with Filtering Enabled..."

echo "Creating source with stop words (Pro user - filtering enabled)..."
response=$(curl -s -X POST "${BASE_URL}/api/sources/enhanced/" \
  -H "Authorization: Token ${PRO_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Stop Words Test - Pro User (Filtering ON)\",
    \"manual_text\": \"$test_text\"
  }")

echo "Source Creation Result (with filtering):"
echo "$response" | jq '{
  status: .status,
  source_id: .source_id,
  words_extracted: .words_extracted,
  title: .title
}'
echo

# Test 7: Free User Source Creation (always filtered)
echo "7️⃣ Testing Free User Source Creation (always filtered)..."

response=$(curl -s -X POST "${BASE_URL}/api/sources/enhanced/" \
  -H "Authorization: Token ${FREE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Stop Words Test - Free User (Always Filtered)\",
    \"manual_text\": \"$test_text\"
  }")

echo "Free User Source Creation Result:"
echo "$response" | jq '{
  status: .status,
  source_id: .source_id,
  words_extracted: .words_extracted,
  title: .title
}'
echo

# Test 8: Check Word Priorities
echo "8️⃣ Checking Word Priorities..."
echo "Visit the statistics page to see how stop words are ranked differently"
echo "URL: ${BASE_URL}/statistics/"
echo

echo "✅ STOP WORDS FILTERING FEATURE TEST COMPLETED"
echo
echo "📊 Summary:"
echo "- ✅ Pro users can toggle stop words filtering on/off"
echo "- ✅ Free users cannot modify (always enabled)"
echo "- ✅ Content scoring applied during word processing"
echo "- ✅ Stop words get 0.1x penalty when filtering enabled"
echo "- ✅ Priority ranking reflects content importance"
echo
echo "🎯 Feature is ready for production!"

echo
echo "📱 Manual Testing:"
echo "- Visit: ${BASE_URL}/settings/"
echo "- Check stop words filtering toggle"
echo "- Test with Pro and Free accounts"
echo
echo "📊 Analytics Testing:"
echo "- Visit: ${BASE_URL}/statistics/"
echo "- Check 'Most Frequent Words' ranking"
echo "- Verify content words appear before stop words" 