// Content script for Kelime Chrome Extension

(function() {
    'use strict';

    // Configuration
    const KELIME_HIGHLIGHT_CLASS = 'kelime-highlight';
    const KELIME_TOOLTIP_CLASS = 'kelime-tooltip';

    // State
    let isSelectionMode = false;
    let currentTooltip = null;

    // Initialize content script
    function init() {
        addSelectionListener();
        addKeyboardShortcuts();
        console.log('Kelime content script loaded');
    }

    // Add text selection listener
    function addSelectionListener() {
        document.addEventListener('mouseup', handleTextSelection);
        document.addEventListener('keyup', handleTextSelection);
    }

    // Handle text selection events
    function handleTextSelection(event) {
        setTimeout(() => {
            const selectedText = window.getSelection().toString().trim();
            
            if (selectedText && selectedText.length > 0) {
                showSelectionTooltip(selectedText, event);
            } else {
                hideTooltip();
            }
        }, 100);
    }

    // Show tooltip for selected text
    function showSelectionTooltip(selectedText, event) {
        hideTooltip();

        // Don't show tooltip for very short or very long selections
        if (selectedText.length < 3 || selectedText.length > 500) {
            return;
        }

        // Create tooltip
        const tooltip = document.createElement('div');
        tooltip.className = KELIME_TOOLTIP_CLASS;
        tooltip.innerHTML = `
            <div class="kelime-tooltip-content">
                <div class="kelime-tooltip-text">
                    Add "${selectedText.substring(0, 50)}${selectedText.length > 50 ? '...' : ''}" to Kelime?
                </div>
                <div class="kelime-tooltip-actions">
                    <button class="kelime-btn kelime-btn-add" data-action="add">
                        📚 Add to Kelime
                    </button>
                    <button class="kelime-btn kelime-btn-close" data-action="close">
                        ✕
                    </button>
                </div>
            </div>
        `;

        // Position tooltip
        const selection = window.getSelection();
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        
        tooltip.style.left = `${rect.left + window.scrollX}px`;
        tooltip.style.top = `${rect.bottom + window.scrollY + 10}px`;

        // Add event listeners
        tooltip.querySelector('[data-action="add"]').addEventListener('click', () => {
            addTextToKelime(selectedText);
            hideTooltip();
        });

        tooltip.querySelector('[data-action="close"]').addEventListener('click', () => {
            hideTooltip();
        });

        // Add to page
        document.body.appendChild(tooltip);
        currentTooltip = tooltip;

        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (currentTooltip === tooltip) {
                hideTooltip();
            }
        }, 5000);
    }

    // Hide current tooltip
    function hideTooltip() {
        if (currentTooltip) {
            currentTooltip.remove();
            currentTooltip = null;
        }
    }

    // Add selected text to Kelime
    function addTextToKelime(selectedText) {
        console.log('Content script: Adding text to Kelime:', selectedText.substring(0, 50) + '...');
        
        // Create tab info object similar to background script
        const tabInfo = {
            title: document.title,
            url: window.location.href,
            id: null // Will be handled by background script
        };
        
        // Send message to background script to handle the API call
        chrome.runtime.sendMessage({
            action: 'handleTextSelection',
            selectedText: selectedText,
            tab: tabInfo
        }, (response) => {
            console.log('Background script response:', response);
            if (response && response.success) {
                showSuccessNotification(response.analysis);
            } else {
                showErrorNotification();
            }
        });
    }

    // Show success notification
    function showSuccessNotification(analysis) {
        const notification = createNotification(
            `✅ Added to Kelime! ${analysis ? `(${analysis.new_words} new words)` : ''}`,
            'success'
        );
        showNotification(notification);
    }

    // Show error notification
    function showErrorNotification() {
        const notification = createNotification(
            '❌ Failed to add to Kelime. Please try again.',
            'error'
        );
        showNotification(notification);
    }

    // Create notification element
    function createNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `kelime-notification kelime-notification-${type}`;
        notification.textContent = message;
        return notification;
    }

    // Show notification
    function showNotification(notification) {
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('kelime-notification-show');
        }, 100);

        // Auto-hide
        setTimeout(() => {
            notification.classList.remove('kelime-notification-show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }, 3000);
    }

    // Add keyboard shortcuts
    function addKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Alt + K to toggle selection mode
            if (event.altKey && event.key === 'k') {
                event.preventDefault();
                toggleSelectionMode();
            }

            // Escape to cancel
            if (event.key === 'Escape') {
                hideTooltip();
                if (isSelectionMode) {
                    toggleSelectionMode();
                }
            }
        });
    }

    // Toggle selection mode
    function toggleSelectionMode() {
        isSelectionMode = !isSelectionMode;
        
        if (isSelectionMode) {
            document.body.classList.add('kelime-selection-mode');
            showModeNotification('Selection mode enabled. Select text to add to Kelime!');
        } else {
            document.body.classList.remove('kelime-selection-mode');
            hideTooltip();
        }
    }

    // Show mode notification
    function showModeNotification(message) {
        const notification = createNotification(message, 'info');
        notification.classList.add('kelime-mode-notification');
        showNotification(notification);
    }

    // Highlight words (future feature)
    function highlightKnownWords() {
        // This could be implemented to highlight words the user already knows
        // Would require API call to get user's known words
    }

    // Clean up when page unloads
    window.addEventListener('beforeunload', () => {
        hideTooltip();
    });

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})(); 