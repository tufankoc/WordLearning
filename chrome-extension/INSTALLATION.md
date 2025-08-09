# 🚀 Kelime Chrome Extension Installation Guide

## Prerequisites

### 1. Django Backend Running
Ensure your Kelime Django app is running:
```bash
cd /path/to/kelime
python manage.py runserver 127.0.0.1:8000
```

### 2. Chrome Browser
- Chrome 88+ or any Chromium-based browser
- Developer mode capabilities

## 📦 Installation Steps

### Step 1: Prepare Extension Files

1. **Download/Clone the Extension**:
   ```bash
   # If you have the kelime project
   cd kelime/chrome-extension/
   
   # OR download just the extension folder
   ```

2. **Create Icon Files** (Optional but recommended):
   ```bash
   # Convert the SVG to PNG icons
   # See icons/create_icons.md for detailed instructions
   ```

### Step 2: Load Extension in Chrome

1. **Open Chrome Extensions Page**:
   - Type `chrome://extensions/` in address bar
   - OR: Menu → More Tools → Extensions

2. **Enable Developer Mode**:
   - Toggle "Developer mode" switch (top right)

3. **Load Unpacked Extension**:
   - Click "Load unpacked" button
   - Navigate to and select the `chrome-extension` folder
   - Click "Open"

4. **Verify Installation**:
   - Extension should appear in extensions list
   - Kelime icon should appear in browser toolbar
   - If no icon, click puzzle piece icon and pin Kelime

### Step 3: Configure Authentication

1. **Click Extension Icon**:
   - Beautiful purple gradient popup should appear

2. **Login to Kelime**:
   - Enter your Django app username/password
   - Click "Login" button
   - Should see "Welcome, [username]!" message

3. **Test Connection**:
   - Click "🚀 Open Kelime App"
   - Should open http://127.0.0.1:8000/ in new tab

## 🎯 Usage

### Method 1: Context Menu (Primary)

1. **Select Text**: Highlight any text on any webpage
2. **Right-Click**: Open context menu
3. **Choose**: "Add to Kelime Vocabulary"
4. **See Results**: Notification shows analysis (coverage %, new words)

### Method 2: Selection Tooltip

1. **Select Text**: Highlight text (3-500 characters)
2. **Auto Tooltip**: Popup appears below selection
3. **Click**: "📚 Add to Kelime" button
4. **Feedback**: Success/error notification

### Method 3: Keyboard Shortcut

1. **Enable Mode**: Press `Alt + K` for selection mode
2. **Select Text**: Crosshair cursor appears
3. **Auto Submit**: Selected text automatically adds to Kelime
4. **Exit Mode**: Press `Escape` or `Alt + K` again

## 🔧 Troubleshooting

### Common Issues

#### 🚫 **Extension Not Loading**
```
Error: "Could not load extension"
```
**Solutions**:
- Check folder contains `manifest.json`
- Ensure all files are present (popup.html, background.js, etc.)
- Look for syntax errors in console
- Try reloading extension

#### 🔒 **Login Failed**
```
Error: "Authentication failed" or "Connection error"
```
**Solutions**:
- Verify Django server is running: http://127.0.0.1:8000
- Check username/password in Django admin
- Clear extension storage: Extensions → Kelime → Storage
- Check browser console for network errors

#### 🚯 **Context Menu Missing**
```
Right-click doesn't show "Add to Kelime Vocabulary"
```
**Solutions**:
- Ensure text is selected before right-clicking
- Refresh the webpage (content script reloads)
- Check extension is enabled
- Verify permissions granted

#### 📱 **Notifications Not Showing**
```
No success/error messages appear
```
**Solutions**:
- Check Chrome notification permissions
- Look for blocked notifications (bell icon in address bar)
- Enable notifications for your site
- Check browser notification settings

#### 🌐 **CORS Errors**
```
"Access to fetch blocked by CORS policy"
```
**Solutions**:
Add to Django settings.py:
```python
CORS_ALLOWED_ORIGINS = [
    "chrome-extension://[your-extension-id]",
]

# OR for development
CORS_ALLOW_ALL_ORIGINS = True
```

### Debug Mode

#### 1. **Extension Console**
- `chrome://extensions/` → Kelime → "Service worker"
- Check for background script errors
- Monitor API calls and responses

#### 2. **Content Script Console**
- Open Developer Tools on webpage (`F12`)
- Console tab → look for "Kelime" messages
- Check for content script errors

#### 3. **Network Debugging**
- Developer Tools → Network tab
- Filter by your domain (127.0.0.1:8000)
- Monitor API requests/responses
- Check for failed requests

### Resetting Extension

If all else fails, reset completely:

1. **Remove Extension**:
   - `chrome://extensions/` → Kelime → "Remove"

2. **Clear Storage**:
   - Clear browser data for 127.0.0.1:8000
   - Chrome → Settings → Privacy → Clear browsing data

3. **Reinstall**:
   - Follow installation steps again
   - Start fresh with login

## 🔄 Development Updates

When you modify extension files:

### Quick Reload
- `chrome://extensions/` → Kelime → Refresh icon ↻
- No need to remove/re-add

### Full Restart (for manifest changes)
- Remove extension completely
- Reload unpacked from folder

### Testing Changes
1. **Background Script**: Requires reload
2. **Content Script**: Refresh webpage
3. **Popup**: Close/reopen popup
4. **Styles**: Refresh webpage for content styles

## 📋 Final Checklist

Before using the extension:

- [ ] Django server running on port 8000
- [ ] Extension loaded and enabled
- [ ] Icons present (optional)
- [ ] Login successful
- [ ] Context menu appears when text selected
- [ ] Notifications working
- [ ] API calls reaching Django backend

## 🎉 Success!

You should now be able to:
- ✅ Select text on any webpage
- ✅ Right-click → "Add to Kelime Vocabulary"
- ✅ See instant vocabulary analysis
- ✅ Track learning progress
- ✅ Build vocabulary from real content

**Happy Learning! 📚✨**

Transform any webpage into your personal vocabulary classroom with Kelime. 