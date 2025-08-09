# Enhanced Source API Guide

The Kelime Enhanced Source API supports multiple input types for extracting vocabulary from real-world content. This guide covers all supported input types, security measures, and usage examples.

## 🚀 Quick Start

### Endpoint
```
POST /api/sources/enhanced/
```

### Authentication
All requests require user authentication. Include session cookies or authorization headers.

### Basic Usage
Send one input type per request with a title:

```bash
curl -X POST http://localhost:8000/api/sources/enhanced/ \
  -H "Content-Type: application/json" \
  -d '{"title": "My Source", "manual_text": "Your content here..."}'
```

## 📋 Supported Input Types

### 1. 📄 PDF File Upload

Extract text from PDF documents with automatic text recognition.

**Parameters:**
- `title`: Source title (required)
- `pdf_file`: PDF file upload (required)

**Example:**
```python
import requests

with open('document.pdf', 'rb') as f:
    files = {'pdf_file': ('document.pdf', f, 'application/pdf')}
    data = {'title': 'Academic Paper on Language Learning'}
    
    response = requests.post(
        'http://localhost:8000/api/sources/enhanced/',
        data=data,
        files=files
    )
```

**Features:**
- ✅ Multi-page text extraction
- ✅ UTF-8 text normalization
- ✅ 10MB file size limit
- ✅ MIME type validation
- ✅ Metadata reporting (pages, word count)

---

### 2. 🌐 Website URL

Scrape and extract clean text from web pages.

**Parameters:**
- `title`: Source title (required)
- `web_url`: Valid HTTP/HTTPS URL (required)

**Example:**
```python
data = {
    'title': 'BBC News Article',
    'web_url': 'https://www.bbc.com/news/technology-12345'
}

response = requests.post(
    'http://localhost:8000/api/sources/enhanced/',
    data=data
)
```

**Features:**
- ✅ Automatic content area detection (`<main>`, `<article>`)
- ✅ Ad/navigation removal
- ✅ 15-second timeout
- ✅ Security URL validation
- ✅ Page title extraction

**Blocked URLs:**
- ❌ Private networks (127.x.x.x, 192.168.x.x, 10.x.x.x)
- ❌ Localhost access
- ❌ Non-HTTP(S) protocols

---

### 3. 📺 YouTube Video

Extract subtitles/transcripts from YouTube videos.

**Parameters:**
- `title`: Source title (required)
- `youtube_url`: YouTube video URL (required)

**Example:**
```python
data = {
    'title': 'TED Talk - The Power of Language',
    'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
}

response = requests.post(
    'http://localhost:8000/api/sources/enhanced/',
    data=data
)
```

**Supported URL Formats:**
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`

**Features:**
- ✅ Auto-detect available languages
- ✅ Prefer English transcripts
- ✅ Clean transcript formatting
- ✅ Remove timestamps and annotations
- ✅ Fallback to any available language

**Limitations:**
- ❌ Videos with disabled transcripts
- ❌ Private/unlisted videos without transcripts
- ❌ Videos without any captions

---

### 4. 📺 SRT Subtitle Files

Parse and extract text from subtitle files.

**Parameters:**
- `title`: Source title (required)
- `srt_file`: SRT subtitle file upload (required)

**Example:**
```python
with open('movie_subtitles.srt', 'rb') as f:
    files = {'srt_file': ('movie_subtitles.srt', f, 'text/plain')}
    data = {'title': 'Movie Dialogue for Language Learning'}
    
    response = requests.post(
        'http://localhost:8000/api/sources/enhanced/',
        data=data,
        files=files
    )
```

**Features:**
- ✅ Automatic timestamp removal
- ✅ HTML tag cleaning
- ✅ UTF-8 and Latin-1 encoding support
- ✅ Subtitle formatting removal
- ✅ 10MB file size limit

**Sample SRT Format:**
```srt
1
00:00:01,000 --> 00:00:04,000
Hello everyone, welcome to our lesson.

2
00:00:04,500 --> 00:00:08,000
Today we will learn advanced vocabulary.
```

---

### 5. 📝 Manual Text Input

Direct text input for custom content.

**Parameters:**
- `title`: Source title (required)
- `manual_text`: Text content (required, min 10 characters)

**Example:**
```python
data = {
    'title': 'Custom Vocabulary Text',
    'manual_text': '''
    Vocabulary acquisition is fundamental to language learning.
    Students benefit from exposure to authentic materials that
    challenge their lexical knowledge and promote retention.
    '''
}

response = requests.post(
    'http://localhost:8000/api/sources/enhanced/',
    data=data
)
```

**Features:**
- ✅ Direct content control
- ✅ No external dependencies
- ✅ Instant processing
- ✅ Perfect for custom materials

---

## 🔒 Security Features

### File Upload Security
- **Size Limits:** 10MB for PDFs/SRTs
- **MIME Type Validation:** When python-magic is available
- **Extension Validation:** .pdf, .srt extensions required
- **Content Scanning:** Basic malicious content detection

### URL Security
- **Protocol Restriction:** Only HTTP/HTTPS allowed
- **Network Blocking:** Private/local networks blocked
- **Timeout Protection:** 15-second request timeout
- **User Agent:** Proper browser headers to avoid blocking

### Input Validation
- **Single Input:** Exactly one input type per request
- **Title Validation:** 2-255 character limits
- **Content Minimum:** 10 character minimum for text
- **YouTube Validation:** Valid video ID extraction

---

## 📊 Response Format

### Success Response (201 Created)
```json
{
  "id": 123,
  "title": "My Source",
  "source_type": "TEXT",
  "created_at": "2025-01-23T10:30:00Z",
  "analysis": {
    "coverage": 65.5,
    "total_words": 1240,
    "unique_words": 287,
    "known_words": 188,
    "new_words": 99,
    "words_processed": 287,
    "processing_status": "success",
    "characters": 6543,
    "pages": 3
  },
  "content_preview": "Learning vocabulary is essential for language acquisition. Students who practice regularly tend to improve...",
  "success_message": "✅ 287 unique words extracted and processed successfully!"
}
```

### Error Response (400 Bad Request)
```json
{
  "error": "Exactly one input type must be provided: pdf_file, srt_file, web_url, youtube_url, or manual_text"
}
```

### Content Parsing Error
```json
{
  "error": "Content parsing failed: No transcript found for this video"
}
```

---

## 🧮 Analysis Metrics

Each successful response includes detailed analysis:

| Metric | Description |
|--------|-------------|
| `coverage` | Percentage of words user already knows |
| `total_words` | Total word instances in content |
| `unique_words` | Number of unique words found |
| `known_words` | Words user has already learned |
| `new_words` | New words added to learning queue |
| `words_processed` | Total words processed and stored |
| `characters` | Character count of extracted content |
| `processing_status` | `success` or `no_words_found` |

### Additional Metadata by Type

**PDF Files:**
- `total_pages`: Number of pages processed
- `characters`: Total character count

**Web Pages:**
- `url`: Final URL after redirects
- `title`: Page title from `<title>` tag
- `status_code`: HTTP response code

**YouTube Videos:**
- `video_id`: Extracted YouTube video ID
- `language`: Transcript language code
- `entries_count`: Number of transcript segments

**SRT Files:**
- `subtitles_count`: Number of subtitle entries
- `duration`: Total duration from first to last subtitle

---

## 🎯 User Flow Examples

### PDF Academic Paper
1. User uploads research paper PDF
2. System extracts text from all pages
3. Identifies 450 unique academic terms
4. Shows "127 new words added to your learning queue"
5. User starts reviewing unknown terminology

### YouTube Educational Video
1. User pastes TED Talk URL
2. System fetches English transcript
3. Extracts 89 unique words from 18-minute video
4. User learns vocabulary in context of presentation

### News Article
1. User pastes BBC News article URL
2. System scrapes clean content (removes ads/navigation)
3. Processes 156 current affairs vocabulary
4. User improves news comprehension skills

### Movie Subtitles
1. User uploads movie SRT file
2. System extracts dialogue (removes timestamps)
3. Finds 234 conversational expressions
4. User learns natural spoken language patterns

---

## 🔧 Integration Examples

### Frontend JavaScript
```javascript
// File upload example
const formData = new FormData();
formData.append('title', 'My PDF Document');
formData.append('pdf_file', fileInput.files[0]);

fetch('/api/sources/enhanced/', {
  method: 'POST',
  body: formData,
  headers: {
    'X-CSRFToken': getCSRFToken()
  }
})
.then(response => response.json())
.then(data => {
  console.log(`Success: ${data.success_message}`);
  console.log(`Analysis:`, data.analysis);
});
```

### Python Script
```python
import requests

def upload_content(title, content_type, content_data):
    """Upload content to Kelime API"""
    api_url = 'http://localhost:8003/api/sources/enhanced/'
    
    if content_type == 'text':
        data = {'title': title, 'manual_text': content_data}
        response = requests.post(api_url, data=data)
    
    elif content_type == 'url':
        data = {'title': title, 'web_url': content_data}
        response = requests.post(api_url, data=data)
    
    elif content_type == 'youtube':
        data = {'title': title, 'youtube_url': content_data}
        response = requests.post(api_url, data=data)
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ {result['success_message']}")
        return result
    else:
        print(f"❌ Error: {response.text}")
        return None

# Usage examples
upload_content("News Article", "url", "https://bbc.com/news/article")
upload_content("Custom Text", "text", "Your vocabulary content here...")
upload_content("TED Talk", "youtube", "https://youtube.com/watch?v=...")
```

---

## 🚨 Error Handling

### Common Error Scenarios

**File Too Large**
```json
{
  "error": "Content parsing failed: File too large. Maximum size: 10MB"
}
```

**Invalid YouTube URL**
```json
{
  "error": "Invalid YouTube URL format"
}
```

**Transcript Not Available**
```json
{
  "error": "Content parsing failed: No transcript found for this video"
}
```

**Website Blocked**
```json
{
  "error": "Content parsing failed: Private/local network URLs are not allowed"
}
```

**Multiple Inputs**
```json
{
  "error": "Exactly one input type must be provided: pdf_file, srt_file, web_url, youtube_url, or manual_text"
}
```

### Best Practices

1. **Always validate input** on frontend before sending
2. **Handle timeouts** for web scraping (15-second limit)
3. **Check file sizes** before upload (10MB limit)
4. **Provide user feedback** during processing
5. **Show analysis results** to user after success

---

## 📈 Performance Notes

- **PDF Processing:** ~2-5 seconds for typical documents
- **Web Scraping:** ~3-10 seconds depending on site speed
- **YouTube Transcripts:** ~1-3 seconds for most videos
- **SRT Processing:** ~1-2 seconds for typical files
- **Manual Text:** Instant processing

### Optimization Tips

1. **Cache results** when possible
2. **Process in background** for large files
3. **Show progress indicators** for slow operations
4. **Batch multiple small texts** if applicable

---

## 🔄 Legacy API Compatibility

The original `/api/sources/` endpoint remains available for backward compatibility:

```python
# Legacy endpoint (still works)
data = {
    'title': 'Manual Source',
    'source_type': 'TEXT', 
    'content': 'Your text content here...'
}

response = requests.post('/api/sources/', data=data)
```

**Migration Guide:**
- Replace `content` with `manual_text`
- Remove `source_type` (auto-detected)
- Use `/api/sources/enhanced/` endpoint
- Update response parsing for new analysis format

---

## 📞 Support & Troubleshooting

### Debug Mode
Enable Django debug mode to see detailed error traces:
```python
DEBUG = True  # In settings.py
```

### Logging
Check server logs for detailed parsing information:
```bash
tail -f logs/django.log
```

### Common Issues

1. **Missing Dependencies:** Install required packages from requirements.txt
2. **Authentication:** Ensure user is logged in before API calls  
3. **CSRF Tokens:** Include CSRF token for web requests
4. **File Permissions:** Check read permissions for uploaded files

For additional support, check the Django admin logs or contact the development team.

---

*Last updated: January 2025 - Enhanced Source API v1.0* 