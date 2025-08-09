# 📚 Kelime - Vocabulary Learning Chrome Extension

A powerful Chrome extension that seamlessly integrates with your Kelime vocabulary learning app, allowing you to capture and learn from any text on the web.

## 🌟 Features

### 🔍 **Smart Text Selection**
- Select any text on any webpage
- Right-click and choose "Add to Kelime Vocabulary"
- Automatic analysis shows your vocabulary coverage
- Visual feedback with notifications

### 📱 **Elegant Popup Interface**
- Beautiful gradient design with modern UI
- One-click login to your Kelime account
- Quick access to your learning dashboard
- Instant access to the main Kelime app

### 🚀 **Seamless Integration**
- Direct API integration with your Django backend
- Real-time vocabulary analysis
- Automatic word tokenization and frequency counting
- Smart skipping of words you already know

### ⌨️ **Keyboard Shortcuts**
- `Alt + K`: Toggle selection mode
- `Escape`: Cancel current selection
- `Ctrl/Cmd + Enter`: Quick login

### 🎯 **Visual Feedback**
- Success notifications with vocabulary stats
- Badge counter showing new words added
- Elegant tooltips for text selection
- Error handling with helpful messages

## 🔧 Installation

### Method 1: Load Unpacked (Development)

1. **Download the Extension**:
   ```bash
   # The extension files are in the chrome-extension/ directory
   ```

2. **Open Chrome Extensions**:
   - Navigate to `chrome://extensions/`
   - Enable "Developer mode" (top right)

3. **Load the Extension**:
   - Click "Load unpacked"
   - Select the `chrome-extension` folder
   - The extension icon should appear in your toolbar

### Method 2: From Chrome Web Store (Coming Soon)
*Extension will be available on the Chrome Web Store after review*

## 🚀 Quick Start

### 1. **Login to Your Account**
- Click the Kelime extension icon in your toolbar
- Enter your username and password
- Click "Login" to authenticate

### 2. **Start Learning from Any Website**
- Select any text on a webpage
- Right-click and choose "Add to Kelime Vocabulary"
- See instant analysis of your vocabulary coverage
- Continue reading and learning!

### 3. **Track Your Progress**
- Extension badge shows new words added
- Notifications display learning statistics
- Click "Open Kelime App" to see detailed progress

## 🎨 User Interface

### Popup Window
```
📚 Kelime
Vocabulary Learning Extension

[Username] [Password] [Login]

Welcome, username!
Ready to learn vocabulary

🚀 Open Kelime App
🚪 Logout

How to use:
1. Select any text on a webpage
2. Right-click and choose "Add to Kelime Vocabulary"
3. Watch your vocabulary grow! 📈
```

### Context Menu
```
Right-click menu:
- Copy
- Paste
- ...
- Add to Kelime Vocabulary  ← New option
```

### Selection Tooltip
```
┌─────────────────────────────────┐
│ Add "The quick brown fox..." to │
│ Kelime?                         │
│                                 │
│ [📚 Add to Kelime]  [✕]         │
└─────────────────────────────────┘
```

## 🔒 Privacy & Security

### 🛡️ **Data Handling**
- Only selected text is sent to your Kelime server
- Authentication data stored locally in Chrome
- No data shared with third parties
- HTTPS encryption for all API calls

### 🏠 **Local-First Design**
- Extension connects to your local Kelime instance
- Default: `http://127.0.0.1:8000`
- No external dependencies for core functionality
- Your vocabulary data stays on your server

### 🔐 **Authentication**
- Secure session-based authentication
- Automatic token refresh
- Safe logout clears all stored data
- CSRF protection enabled

## ⚙️ Configuration

### API Endpoints
The extension connects to these Django endpoints:

```javascript
const API_ENDPOINTS = {
  sources: 'http://127.0.0.1:8000/api/sources/',
  login: 'http://127.0.0.1:8000/auth/login/',
  logout: 'http://127.0.0.1:8000/auth/logout/'
};
```

### Permissions Required
```json
{
  "permissions": [
    "activeTab",      // Access current tab for text selection
    "storage",        // Store authentication data
    "contextMenus"    // Add right-click menu option
  ],
  "host_permissions": [
    "http://127.0.0.1:8000/*",  // Your local Django server
    "http://localhost:8000/*"   // Alternative localhost
  ]
}
```

## 🛠️ Development

### Project Structure
```
chrome-extension/
├── manifest.json      # Extension configuration
├── background.js      # Service worker (API calls, context menu)
├── popup.html         # Extension popup interface
├── popup.js          # Popup logic and authentication
├── content.js        # Injected script for text selection
├── styles.css        # Styling for content script elements
├── icons/           # Extension icons (16px, 32px, 48px, 128px)
└── README.md        # This file
```

### Key Components

#### 🔧 **Background Script** (`background.js`)
- Handles API communication with Django backend
- Manages user authentication and sessions
- Creates and manages context menus
- Processes text selection from content scripts

#### 🎨 **Popup Interface** (`popup.html` + `popup.js`)
- Beautiful login interface with gradient design
- Authentication status management
- Quick access to main application
- User-friendly error handling

#### 📝 **Content Script** (`content.js`)
- Detects text selection on web pages
- Shows elegant tooltips for quick actions
- Handles keyboard shortcuts
- Provides visual feedback

#### 🎭 **Styling** (`styles.css`)
- Modern glassmorphism design
- Responsive layout for all screen sizes
- Dark mode and high contrast support
- Smooth animations and transitions

### API Integration

#### Creating Sources
```javascript
// POST /api/sources/
{
  "title": "Selected from: Page Title",
  "source_type": "TEXT",
  "content": "Selected text content..."
}

// Response
{
  "id": 123,
  "title": "Selected from: Page Title",
  "analysis": {
    "coverage": 45.5,
    "total_words": 156,
    "unique_words": 89,
    "known_words": 40,
    "new_words": 49
  }
}
```

## 🚨 Troubleshooting

### Common Issues

#### **"Failed to connect to server"**
- Ensure your Django server is running on `http://127.0.0.1:8000`
- Check that CORS is properly configured
- Verify the server is accessible from the browser

#### **"Authentication failed"**
- Clear extension storage: Right-click extension → "Manage extensions" → "Storage"
- Try logging out and back in
- Check username/password on the main Kelime app

#### **"Context menu not appearing"**
- Ensure text is selected before right-clicking
- Try refreshing the page
- Check if extension is enabled

#### **"No response from content script"**
- Refresh the page to reload content scripts
- Check browser console for JavaScript errors
- Verify extension permissions are granted

### Debug Mode

1. **Open Extension Console**:
   - Go to `chrome://extensions/`
   - Find Kelime extension
   - Click "Service worker" or "Inspect views"

2. **View Content Script Logs**:
   - Open Developer Tools on any webpage (`F12`)
   - Check Console tab for Kelime logs

3. **Network Debugging**:
   - Open Network tab in Developer Tools
   - Filter by "kelime" or your server domain
   - Monitor API calls and responses

## 🌐 Browser Compatibility

- ✅ **Chrome 88+** (Manifest V3 support)
- ✅ **Chromium-based browsers** (Edge, Brave, Opera)
- ❌ **Firefox** (requires Manifest V2 adaptation)
- ❌ **Safari** (different extension format)

## 📈 Future Features

### 🎯 **Planned Enhancements**
- [ ] Word highlighting on pages (show known vs unknown words)
- [ ] Quick review popups for vocabulary practice
- [ ] Statistics dashboard within extension
- [ ] Export vocabulary lists
- [ ] Offline mode for text collection
- [ ] Multi-language support
- [ ] Custom vocabulary categories

### 🔮 **Advanced Features**
- [ ] AI-powered content recommendation
- [ ] Spaced repetition reminders
- [ ] Integration with other learning platforms
- [ ] Voice pronunciation features
- [ ] Progress sharing and social features

## 📞 Support

### 🆘 **Getting Help**
- Check the troubleshooting section above
- Review browser console for error messages
- Ensure Django backend is properly configured
- Verify all dependencies are installed

### 🐛 **Reporting Issues**
When reporting bugs, please include:
- Chrome version and operating system
- Extension version
- Steps to reproduce the issue
- Any console error messages
- Screenshots if applicable

### 💡 **Feature Requests**
We welcome suggestions for new features! Consider:
- How it would improve your learning experience
- Whether it fits with the extension's core purpose
- Technical feasibility and user privacy

## 📄 License

This Chrome extension is part of the Kelime vocabulary learning application.

---

**Happy Learning! 📚✨**

*Transform any webpage into your personal vocabulary classroom with Kelime Chrome Extension.* 