// Popup JavaScript for Kelime Chrome Extension

document.addEventListener('DOMContentLoaded', async () => {
    // DOM elements
    const loginSection = document.getElementById('loginSection');
    const dashboardSection = document.getElementById('dashboardSection');
    const loginForm = document.getElementById('loginForm');
    const logoutBtn = document.getElementById('logoutBtn');
    const openAppBtn = document.getElementById('openApp');
    const usernameDisplay = document.getElementById('usernameDisplay');
    const messageDiv = document.getElementById('message');
    const loginText = document.getElementById('loginText');
    const loginLoader = document.getElementById('loginLoader');

    // Initialize popup
    await checkAuthStatus();

    // Event listeners
    loginForm.addEventListener('submit', handleLogin);
    logoutBtn.addEventListener('click', handleLogout);
    openAppBtn.addEventListener('click', openKelimeApp);

    // Check authentication status
    async function checkAuthStatus() {
        try {
            const response = await sendMessage({action: 'checkAuth'});
            
            if (response.success && response.isLoggedIn) {
                showDashboard(response.username);
            } else {
                showLogin();
            }
        } catch (error) {
            console.error('Error checking auth status:', error);
            showLogin();
        }
    }

    // Handle login form submission
    async function handleLogin(event) {
        event.preventDefault();
        
        const formData = new FormData(loginForm);
        const credentials = {
            username: formData.get('username'),
            password: formData.get('password')
        };

        // Show loading state
        setLoginLoading(true);
        hideMessage();

        try {
            const response = await sendMessage({
                action: 'login',
                credentials: credentials
            });

            if (response.success) {
                showMessage('Login successful! 🎉', 'success');
                setTimeout(() => {
                    showDashboard(credentials.username);
                }, 1000);
            } else {
                showMessage(response.error || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            showMessage('Connection error. Please try again.', 'error');
        } finally {
            setLoginLoading(false);
        }
    }

    // Handle logout
    async function handleLogout() {
        try {
            logoutBtn.disabled = true;
            logoutBtn.textContent = 'Logging out...';

            const response = await sendMessage({action: 'logout'});
            
            if (response.success) {
                showMessage('Logged out successfully', 'success');
                setTimeout(() => {
                    showLogin();
                    loginForm.reset();
                }, 1000);
            } else {
                showMessage(response.error || 'Logout failed', 'error');
            }
        } catch (error) {
            console.error('Logout error:', error);
            showMessage('Logout error occurred', 'error');
        } finally {
            logoutBtn.disabled = false;
            logoutBtn.textContent = '🚪 Logout';
        }
    }

    // Open Kelime web app
    function openKelimeApp() {
        chrome.tabs.create({
            url: 'http://127.0.0.1:8000/'
        });
    }

    // UI state management
    function showLogin() {
        loginSection.classList.remove('hidden');
        dashboardSection.classList.add('hidden');
        document.getElementById('username').focus();
    }

    function showDashboard(username) {
        loginSection.classList.add('hidden');
        dashboardSection.classList.remove('hidden');
        usernameDisplay.textContent = username;
        hideMessage();
    }

    function setLoginLoading(isLoading) {
        if (isLoading) {
            loginText.classList.add('hidden');
            loginLoader.classList.remove('hidden');
            loginForm.querySelector('button').disabled = true;
        } else {
            loginText.classList.remove('hidden');
            loginLoader.classList.add('hidden');
            loginForm.querySelector('button').disabled = false;
        }
    }

    function showMessage(text, type = 'info') {
        messageDiv.textContent = text;
        messageDiv.className = `message ${type}`;
        messageDiv.classList.remove('hidden');
        
        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(hideMessage, 3000);
        }
    }

    function hideMessage() {
        messageDiv.classList.add('hidden');
    }

    // Helper to send messages to background script
    function sendMessage(message) {
        return new Promise((resolve, reject) => {
            chrome.runtime.sendMessage(message, (response) => {
                if (chrome.runtime.lastError) {
                    reject(chrome.runtime.lastError);
                } else {
                    resolve(response);
                }
            });
        });
    }

    // Handle Enter key in password field
    document.getElementById('password').addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            loginForm.dispatchEvent(new Event('submit'));
        }
    });

    // Add keyboard shortcuts
    document.addEventListener('keydown', (event) => {
        // Ctrl/Cmd + Enter to submit login
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            if (!loginSection.classList.contains('hidden')) {
                loginForm.dispatchEvent(new Event('submit'));
            }
        }
        
        // Escape to close popup
        if (event.key === 'Escape') {
            window.close();
        }
    });
}); 