"""
Content parsers for different input types in Kelime vocabulary learning system.
Supports PDF, web URLs, YouTube videos, and SRT subtitle files.
"""

import re
import requests
from urllib.parse import urlparse, parse_qs
import fitz  # PyMuPDF
import pysrt
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
try:
    from youtube_transcript_api._errors import (
        TranscriptsDisabled, 
        NoTranscriptFound, 
        VideoUnavailable
    )
except ImportError:
    # Fallback for different versions
    try:
        from youtube_transcript_api.exceptions import (
            TranscriptsDisabled, 
            NoTranscriptFound, 
            VideoUnavailable
        )
    except ImportError:
        # Define custom exceptions if neither import works
        class TranscriptsDisabled(Exception):
            pass
        class NoTranscriptFound(Exception):
            pass
        class VideoUnavailable(Exception):
            pass

# Optional import for magic (MIME type detection)
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    
import tempfile
import os
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ContentParsingError(Exception):
    """Custom exception for content parsing errors"""
    pass

class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass


def validate_file_security(file_content: bytes, expected_mime_type: str, max_size_mb: int = 10) -> None:
    """
    Validate uploaded file for security.
    
    Args:
        file_content: File content as bytes
        expected_mime_type: Expected MIME type (e.g., 'application/pdf')
        max_size_mb: Maximum file size in MB
        
    Raises:
        SecurityError: If file fails security checks
    """
    # Check file size
    if len(file_content) > max_size_mb * 1024 * 1024:
        raise SecurityError(f"File too large. Maximum size: {max_size_mb}MB")
    
    # Check MIME type using python-magic if available
    if HAS_MAGIC:
        try:
            detected_mime = magic.from_buffer(file_content, mime=True)
            if not detected_mime.startswith(expected_mime_type.split('/')[0]):
                raise SecurityError(f"Invalid file type. Expected: {expected_mime_type}, Got: {detected_mime}")
        except Exception as e:
            logger.warning(f"MIME type detection failed: {e}")
            # Continue without strict MIME validation if magic fails
    else:
        logger.info("python-magic not available, skipping MIME type validation")


def validate_url_security(url: str) -> None:
    """
    Validate URL for security.
    
    Args:
        url: URL to validate
        
    Raises:
        SecurityError: If URL is not safe
    """
    parsed = urlparse(url)
    
    # Check scheme
    if parsed.scheme not in ['http', 'https']:
        raise SecurityError("Only HTTP and HTTPS URLs are allowed")
    
    # Block private/local networks
    if parsed.hostname:
        if (parsed.hostname.startswith('127.') or 
            parsed.hostname.startswith('10.') or
            parsed.hostname.startswith('192.168.') or
            parsed.hostname in ['localhost', '0.0.0.0']):
            raise SecurityError("Private/local network URLs are not allowed")


def parse_pdf_content(file_content: bytes) -> Tuple[str, Dict]:
    """
    Extract text content from PDF file.
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Tuple of (extracted_text, metadata)
        
    Raises:
        ContentParsingError: If PDF parsing fails
    """
    try:
        # Validate file security
        validate_file_security(file_content, 'application/pdf')
        
        # Create temporary file for PyMuPDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(temp_file_path)
            
            text_content = []
            total_pages = len(doc)
            
            # Extract text from each page
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():  # Only add non-empty pages
                    text_content.append(text)
            
            doc.close()
            
            # Combine all text
            full_text = '\n\n'.join(text_content)
            
            # Clean up text
            full_text = re.sub(r'\n+', '\n', full_text)  # Remove excessive newlines
            full_text = re.sub(r'\s+', ' ', full_text)   # Normalize whitespace
            
            metadata = {
                'total_pages': total_pages,
                'characters': len(full_text),
                'words': len(full_text.split()) if full_text else 0
            }
            
            if not full_text.strip():
                raise ContentParsingError("No readable text found in PDF")
            
            return full_text.strip(), metadata
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        if isinstance(e, (SecurityError, ContentParsingError)):
            raise
        raise ContentParsingError(f"Failed to parse PDF: {str(e)}")


def parse_web_content(url: str) -> Tuple[str, Dict]:
    """
    Extract text content from web page.
    
    Args:
        url: Web page URL
        
    Returns:
        Tuple of (extracted_text, metadata)
        
    Raises:
        ContentParsingError: If web scraping fails
    """
    try:
        # Validate URL security
        validate_url_security(url)
        
        # Set up headers to appear like a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Fetch the page with timeout
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
            element.decompose()
        
        # Try to find main content area
        main_content = None
        for selector in ['main', 'article', '[role="main"]', '.content', '#content']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # If no main content found, use body
        if not main_content:
            main_content = soup.find('body')
        
        if not main_content:
            raise ContentParsingError("No content found on the page")
        
        # Extract text
        text = main_content.get_text(separator=' ', strip=True)
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'\n+', '\n', text)  # Remove excessive newlines
        
        # Get page title
        title_tag = soup.find('title')
        page_title = title_tag.get_text().strip() if title_tag else 'Untitled'
        
        metadata = {
            'url': url,
            'title': page_title,
            'characters': len(text),
            'words': len(text.split()) if text else 0,
            'status_code': response.status_code
        }
        
        if not text.strip():
            raise ContentParsingError("No readable text found on the page")
        
        return text.strip(), metadata
        
    except requests.RequestException as e:
        raise ContentParsingError(f"Failed to fetch web page: {str(e)}")
    except Exception as e:
        if isinstance(e, (SecurityError, ContentParsingError)):
            raise
        raise ContentParsingError(f"Failed to parse web content: {str(e)}")


def parse_youtube_content(url: str) -> Tuple[str, Dict]:
    """
    Extract transcript from YouTube video.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Tuple of (transcript_text, metadata)
        
    Raises:
        ContentParsingError: If transcript extraction fails
    """
    try:
        # Extract video ID from URL
        video_id = extract_youtube_video_id(url)
        if not video_id:
            raise ContentParsingError("Invalid YouTube URL or video ID not found")
        
        # Try to get transcript
        try:
            # Get available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get English transcript first
            transcript = None
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            except NoTranscriptFound:
                # Try any available transcript
                available_transcripts = list(transcript_list)
                if available_transcripts:
                    transcript = available_transcripts[0]
                else:
                    raise ContentParsingError("No transcripts available for this video")
            
            # Fetch the transcript
            transcript_data = transcript.fetch()
            
            # Combine transcript entries
            text_parts = []
            for entry in transcript_data:
                text = entry.get('text', '').strip()
                if text:
                    # Clean up transcript text
                    text = re.sub(r'\[.*?\]', '', text)  # Remove [Music], [Applause], etc.
                    text = re.sub(r'\(.*?\)', '', text)  # Remove (speaking foreign language), etc.
                    text_parts.append(text)
            
            full_text = ' '.join(text_parts)
            
            # Clean up text
            full_text = re.sub(r'\s+', ' ', full_text)  # Normalize whitespace
            
            metadata = {
                'video_id': video_id,
                'url': url,
                'language': transcript.language_code,
                'characters': len(full_text),
                'words': len(full_text.split()) if full_text else 0,
                'entries_count': len(transcript_data)
            }
            
            if not full_text.strip():
                raise ContentParsingError("Transcript is empty or contains no readable text")
            
            return full_text.strip(), metadata
            
        except TranscriptsDisabled:
            raise ContentParsingError("Transcripts are disabled for this video")
        except NoTranscriptFound:
            raise ContentParsingError("No transcript found for this video")
        except VideoUnavailable:
            raise ContentParsingError("Video is unavailable or private")
            
    except Exception as e:
        if isinstance(e, ContentParsingError):
            raise
        raise ContentParsingError(f"Failed to extract YouTube transcript: {str(e)}")


def parse_srt_content(file_content: bytes) -> Tuple[str, Dict]:
    """
    Extract text content from SRT subtitle file.
    
    Args:
        file_content: SRT file content as bytes
        
    Returns:
        Tuple of (subtitle_text, metadata)
        
    Raises:
        ContentParsingError: If SRT parsing fails
    """
    try:
        # Validate file security (text files are generally safe, but check size)
        if len(file_content) > 10 * 1024 * 1024:  # 10MB limit for text files
            raise SecurityError("SRT file too large. Maximum size: 10MB")
        
        # Decode the file content
        try:
            # Try UTF-8 first
            text_content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # Try Latin-1 as fallback
                text_content = file_content.decode('latin-1')
            except UnicodeDecodeError:
                raise ContentParsingError("Unable to decode SRT file. Please ensure it's a valid text file.")
        
        # Create temporary file for pysrt
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(text_content)
            temp_file_path = temp_file.name
        
        try:
            # Parse SRT file
            subtitles = pysrt.open(temp_file_path, encoding='utf-8')
            
            if not subtitles:
                raise ContentParsingError("No subtitles found in SRT file")
            
            # Extract text from all subtitle entries
            text_parts = []
            for subtitle in subtitles:
                text = subtitle.text.strip()
                if text:
                    # Clean up subtitle text
                    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
                    text = re.sub(r'\{[^}]+\}', '', text)  # Remove subtitle formatting
                    text = re.sub(r'\[[^\]]+\]', '', text)  # Remove [sound effects], etc.
                    text_parts.append(text)
            
            full_text = ' '.join(text_parts)
            
            # Clean up text
            full_text = re.sub(r'\s+', ' ', full_text)  # Normalize whitespace
            
            metadata = {
                'subtitles_count': len(subtitles),
                'characters': len(full_text),
                'words': len(full_text.split()) if full_text else 0,
                'duration': str(subtitles[-1].end - subtitles[0].start) if subtitles else '00:00:00'
            }
            
            if not full_text.strip():
                raise ContentParsingError("No readable text found in SRT file")
            
            return full_text.strip(), metadata
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        if isinstance(e, (SecurityError, ContentParsingError)):
            raise
        raise ContentParsingError(f"Failed to parse SRT file: {str(e)}")


def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from various YouTube URL formats.
    
    Args:
        url: YouTube URL
        
    Returns:
        Video ID or None if not found
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([\w-]+)',
        r'(?:youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)',
        r'(?:youtube\.com\/v\/)([\w-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def get_content_preview(content: str, max_length: int = 200) -> str:
    """
    Get a preview of content for user feedback.
    
    Args:
        content: Full content text
        max_length: Maximum preview length
        
    Returns:
        Preview text with ellipsis if truncated
    """
    if len(content) <= max_length:
        return content
    
    # Find a good breaking point (end of sentence or word)
    preview = content[:max_length]
    last_period = preview.rfind('.')
    last_space = preview.rfind(' ')
    
    if last_period > max_length * 0.7:  # If period is reasonably close to end
        preview = preview[:last_period + 1]
    elif last_space > max_length * 0.8:  # If space is close to end
        preview = preview[:last_space]
    
    return preview + "..."


# Mapping of source types to parser functions
CONTENT_PARSERS = {
    'pdf': parse_pdf_content,
    'web': parse_web_content,
    'youtube': parse_youtube_content,
    'srt': parse_srt_content,
} 