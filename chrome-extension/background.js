// Background service worker for Kelime Chrome Extension

// API Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';
const API_ENDPOINTS = {
  sources: `${API_BASE_URL}/api/sources/`,
  login: `${API_BASE_URL}/accounts/login/`,
  logout: `${API_BASE_URL}/accounts/logout/`
};

// Create context menu when extension is installed
chrome.runtime.onInstalled.addListener(() => {
  // Remove any existing context menus first
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "addToKelime",
      title: "Add to Kelime Vocabulary",
      contexts: ["selection"]
    }, () => {
      if (chrome.runtime.lastError) {
        console.error('Context menu creation error:', chrome.runtime.lastError);
      } else {
        console.log("Kelime extension installed and context menu created successfully");
      }
    });
  });
});

// Also recreate context menu on startup
chrome.runtime.onStartup.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "addToKelime", 
      title: "Add to Kelime Vocabulary",
      contexts: ["selection"]
    });
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "addToKelime" && info.selectionText) {
    handleTextSelection(info.selectionText, tab);
  }
});

// Handle text selection and send to API
async function handleTextSelection(selectedText, tab) {
  try {
    console.log('Context menu triggered with text:', selectedText.substring(0, 50) + '...');
    
    // Get stored authentication data
    const authData = await getStoredAuth();
    console.log('Auth data found:', !!authData?.isLoggedIn);
    
    if (!authData || !authData.isLoggedIn) {
      // Show notification to log in
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'Kelime - Login Required',
        message: 'Please log in through the extension popup to add vocabulary.'
      });
      return;
    }

    // Get fresh CSRF token
    const csrfResponse = await fetch(`${API_BASE_URL}/accounts/login/`, {
      method: 'GET',
      credentials: 'include'
    });
    
    const csrfText = await csrfResponse.text();
    const csrfMatch = csrfText.match(/name=['"']csrfmiddlewaretoken['"'] value=['"']([^'"]+)['"]/);
    const csrfToken = csrfMatch ? csrfMatch[1] : authData.csrfToken;

    // Prepare source data
    const sourceData = {
      title: tab.title,
      source_type: 'EXTENSION',
      content: selectedText.trim()
    };

    console.log('Sending to API:', API_ENDPOINTS.sources);
    console.log('Source data:', sourceData);

    // Send to API
    const response = await fetch(API_ENDPOINTS.sources, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        'Referer': API_BASE_URL,
      },
      credentials: 'include',
      body: JSON.stringify(sourceData)
    });

    console.log('API response status:', response.status);

    if (response.ok) {
      const result = await response.json();
      const analysis = result.analysis;
      
      console.log('Success! Analysis:', analysis);
      
      // Show success notification with analysis
      const wordsProcessed = analysis.words_processed || analysis.unique_words;
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'Kelime - Text Added Successfully! 🎉',
        message: `${wordsProcessed} words processed | Coverage: ${analysis.coverage}% | New: ${analysis.new_words} | Known: ${analysis.known_words}`
      });
      
      // Update badge with total processed word count (including known words)
      chrome.action.setBadgeText({
        text: wordsProcessed > 0 ? wordsProcessed.toString() : '',
        tabId: tab.id
      });
      chrome.action.setBadgeBackgroundColor({color: '#4F46E5'});
      
    } else if (response.status === 401 || response.status === 403) {
      // Authentication failed
      await clearStoredAuth();
      const errorText = await response.text();
      console.log('Auth error response:', errorText);
      
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'Kelime - Authentication Failed',
        message: 'Please log in again through the extension popup.'
      });
    } else {
      const errorText = await response.text();
      console.error('API error:', response.status, errorText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

  } catch (error) {
    console.error('Error adding text to Kelime:', error);
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'Kelime - Error',
      message: `Failed to add text: ${error.message}`
    });
  }
}

// Storage helpers
async function getStoredAuth() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['kelimeAuth'], (result) => {
      resolve(result.kelimeAuth || {});
    });
  });
}

async function clearStoredAuth() {
  return new Promise((resolve) => {
    chrome.storage.local.remove(['kelimeAuth'], resolve);
  });
}

// Handle messages from popup/content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'login') {
    handleLogin(request.credentials)
      .then(result => sendResponse(result))
      .catch(error => sendResponse({success: false, error: error.message}));
    return true; // Keep message channel open for async response
  }
  
  if (request.action === 'logout') {
    handleLogout()
      .then(result => sendResponse(result))
      .catch(error => sendResponse({success: false, error: error.message}));
    return true;
  }
  
  if (request.action === 'checkAuth') {
    getStoredAuth()
      .then(auth => sendResponse({success: true, isLoggedIn: auth.isLoggedIn || false, username: auth.username}))
      .catch(error => sendResponse({success: false, error: error.message}));
    return true;
  }
  
  if (request.action === 'handleTextSelection') {
    // Handle text selection from content script
    const tab = request.tab || sender.tab;
    handleTextSelection(request.selectedText, tab)
      .then(() => sendResponse({success: true}))
      .catch(error => {
        console.error('Text selection error:', error);
        sendResponse({success: false, error: error.message});
      });
    return true;
  }
});

// Login handler
async function handleLogin(credentials) {
  try {
    console.log('Starting login process...');
    
    // Get CSRF token first
    const csrfResponse = await fetch(`${API_BASE_URL}/accounts/login/`, {
      method: 'GET',
      credentials: 'include'
    });
    
    console.log('CSRF response status:', csrfResponse.status);
    
    const csrfText = await csrfResponse.text();
    const csrfMatch = csrfText.match(/name=['"']csrfmiddlewaretoken['"'] value=['"']([^'"]+)['"]/);
    const csrfToken = csrfMatch ? csrfMatch[1] : '';
    
    console.log('CSRF token found:', !!csrfToken);

    // Attempt login
    const loginData = new URLSearchParams({
      username: credentials.username,
      password: credentials.password,
      csrfmiddlewaretoken: csrfToken
    });
    
    console.log('Attempting login with username:', credentials.username);

    const loginResponse = await fetch(API_ENDPOINTS.login, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': csrfToken,
      },
      credentials: 'include',
      body: loginData
    });

    console.log('Login response status:', loginResponse.status);
    console.log('Login response URL:', loginResponse.url);

    if (loginResponse.ok) {
      const responseText = await loginResponse.text();
      const isLoginPage = responseText.includes('csrfmiddlewaretoken') && responseText.includes('password');
      
      if (!isLoginPage) {
        // Login successful - store auth data
        const cookies = loginResponse.headers.get('set-cookie') || '';
        const sessionMatch = cookies.match(/sessionid=([^;]+)/);
        const sessionId = sessionMatch ? sessionMatch[1] : '';

        const authData = {
          isLoggedIn: true,
          username: credentials.username,
          csrfToken: csrfToken,
          sessionId: sessionId,
          cookies: cookies,
          loginTime: Date.now()
        };

        await new Promise((resolve) => {
          chrome.storage.local.set({kelimeAuth: authData}, resolve);
        });

        console.log('Login successful!');
        return {success: true, message: 'Login successful!'};
      } else {
        console.log('Login failed - returned to login page');
        return {success: false, error: 'Invalid username or password'};
      }
    } else {
      console.log('Login response not OK:', loginResponse.status, loginResponse.statusText);
      return {success: false, error: `Server error: ${loginResponse.status}`};
    }

  } catch (error) {
    console.error('Login error:', error);
    return {success: false, error: `Connection error: ${error.message}`};
  }
}

// Logout handler
async function handleLogout() {
  try {
    const authData = await getStoredAuth();
    
    if (authData.csrfToken) {
      // Attempt server logout
      await fetch(API_ENDPOINTS.logout, {
        method: 'POST',
        headers: {
          'X-CSRFToken': authData.csrfToken,
        },
        credentials: 'include'
      });
    }

    // Clear stored auth regardless of server response
    await clearStoredAuth();
    
    // Clear any badge text
    chrome.action.setBadgeText({text: ''});
    
    return {success: true, message: 'Logged out successfully'};

  } catch (error) {
    console.error('Logout error:', error);
    // Still clear local auth even if server logout fails
    await clearStoredAuth();
    return {success: true, message: 'Logged out locally'};
  }
} 