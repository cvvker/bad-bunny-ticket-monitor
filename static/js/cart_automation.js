/**
 * Bad Bunny Ticket Carting System
 * 
 * This module provides automatic ticket carting functionality for Ticketera.
 * It monitors for ticket availability and adds tickets to cart when they become available.
 * 
 * IMPORTANT: This system adds tickets to cart but DOES NOT complete the purchase.
 */

// Cart configuration - These settings can be modified through the UI
let cartConfig = {
    enabled: false,                // Master toggle for carting functionality
    ticketQuantity: 2,             // Number of tickets to add to cart (1-8)
    maxPrice: 500,                 // Maximum price willing to pay per ticket (in $)
    preferredSections: [],         // Preferred seating sections (empty means any section)
    fallbackToAnySection: true,    // If preferred sections unavailable, try any section
    autoRetryAttempts: 3,          // Number of retry attempts if carting fails
    notifications: true            // Show browser notifications for cart status
};

// Session storage to maintain cart attempts and prevent duplicate attempts
let cartingSession = {
    activeCarts: {},               // Currently active carting attempts by date
    completedCarts: {},            // Successfully completed carting attempts
    failedCarts: {},               // Failed carting attempts with reason
    lastStatus: {}                 // Last status by event ID
};

/**
 * Main function to start the carting process for a specific event
 * @param {string} eventId - Event ID in format "month-day" (e.g., "july-12")
 * @param {string} eventUrl - Direct URL to the event page
 * @param {string} eventName - Display name of the event
 */
function startAutomaticCarting(eventId, eventUrl, eventName) {
    // Don't attempt if carting is disabled
    if (!cartConfig.enabled) {
        console.log(`Automatic carting disabled for ${eventName}`);
        return;
    }
    
    // Don't attempt if already in our active or completed list
    if (cartingSession.activeCarts[eventId] || cartingSession.completedCarts[eventId]) {
        console.log(`Carting already in progress or completed for ${eventName}`);
        return;
    }
    
    // Log the start of carting process
    console.log(`Starting automatic carting for ${eventName} at ${eventUrl}`);
    
    // Track this carting attempt
    cartingSession.activeCarts[eventId] = {
        startTime: new Date().toISOString(),
        eventUrl: eventUrl,
        eventName: eventName,
        status: 'starting'
    };
    
    // Send Discord notification about carting attempt
    sendCartingNotification(eventId, eventName, 'Starting automatic carting process', false);
    
    // Show browser notification if enabled
    if (cartConfig.notifications) {
        showBrowserNotification(`Starting to cart ${eventName}`, 'Ticket carting process started');
    }
    
    // Start the carting process
    initiateCartProcess(eventId, eventUrl, eventName);
}

/**
 * Initiate the actual carting process by opening the event URL in a hidden iframe
 */
function initiateCartProcess(eventId, eventUrl, eventName) {
    // Update session status
    cartingSession.activeCarts[eventId].status = 'cartPage';
    
    // Create a hidden iframe to perform the carting
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.id = `cart-frame-${eventId}`;
    iframe.src = eventUrl;
    
    // Set up message listener for communication with the iframe
    window.addEventListener('message', function(event) {
        if (event.data.cartEventId === eventId) {
            handleCartingMessage(event.data, eventId, eventName);
        }
    });
    
    // Add iframe to page
    document.body.appendChild(iframe);
    
    // Set timeout for carting process (5 minutes max)
    setTimeout(function() {
        if (cartingSession.activeCarts[eventId] && 
            !cartingSession.completedCarts[eventId]) {
            // Carting timed out
            cartingFailed(eventId, eventName, 'Carting process timed out after 5 minutes');
        }
    }, 5 * 60 * 1000);
    
    // Send Discord notification
    sendCartingNotification(eventId, eventName, 'Accessing ticket page', false);
}

/**
 * Handle messages from the carting iframe
 */
function handleCartingMessage(message, eventId, eventName) {
    console.log(`Carting message received for ${eventName}:`, message);
    
    switch (message.status) {
        case 'ticketsFound':
            cartingSession.activeCarts[eventId].status = 'ticketsFound';
            sendCartingNotification(eventId, eventName, 
                `Tickets found! ${message.sectionName} - $${message.price}`, false);
            break;
            
        case 'addingToCart':
            cartingSession.activeCarts[eventId].status = 'addingToCart';
            sendCartingNotification(eventId, eventName, 
                `Adding ${cartConfig.ticketQuantity} tickets to cart`, false);
            break;
            
        case 'cartSuccess':
            cartingSuccess(eventId, eventName, message.checkoutUrl);
            break;
            
        case 'cartError':
            cartingFailed(eventId, eventName, message.error);
            break;
    }
}

/**
 * Handle successful carting
 */
function cartingSuccess(eventId, eventName, checkoutUrl) {
    // Update session status
    cartingSession.completedCarts[eventId] = {
        completedTime: new Date().toISOString(),
        checkoutUrl: checkoutUrl
    };
    
    // Remove from active carts
    delete cartingSession.activeCarts[eventId];
    
    // Send Discord notification with @everyone mention
    const successMessage = `🎫 **TICKETS ADDED TO CART!** 🎫\n` +
                          `Event: ${eventName}\n` +
                          `Quantity: ${cartConfig.ticketQuantity}\n` +
                          `[PROCEED TO CHECKOUT](${checkoutUrl})`;
    
    sendCartingNotification(eventId, eventName, successMessage, true);
    
    // Show browser notification
    if (cartConfig.notifications) {
        showBrowserNotification(
            'Tickets Added to Cart!', 
            `${cartConfig.ticketQuantity} tickets for ${eventName} are in your cart!`, 
            checkoutUrl
        );
    }
    
    // Clean up the iframe
    const iframe = document.getElementById(`cart-frame-${eventId}`);
    if (iframe) {
        iframe.remove();
    }
    
    // Open checkout window
    window.open(checkoutUrl, '_blank');
}

/**
 * Handle failed carting
 */
function cartingFailed(eventId, eventName, reason) {
    // Update session status
    cartingSession.failedCarts[eventId] = {
        failedTime: new Date().toISOString(),
        reason: reason
    };
    
    // Remove from active carts
    delete cartingSession.activeCarts[eventId];
    
    // Send Discord notification
    const failedMessage = `❌ **Carting Failed** ❌\n` +
                         `Event: ${eventName}\n` +
                         `Reason: ${reason}`;
    
    sendCartingNotification(eventId, eventName, failedMessage, false);
    
    // Show browser notification
    if (cartConfig.notifications) {
        showBrowserNotification(
            'Carting Failed', 
            `Could not add tickets for ${eventName}: ${reason}`
        );
    }
    
    // Clean up the iframe
    const iframe = document.getElementById(`cart-frame-${eventId}`);
    if (iframe) {
        iframe.remove();
    }
    
    // Retry if we have attempts left
    if (cartConfig.autoRetryAttempts > 0) {
        cartConfig.autoRetryAttempts--;
        setTimeout(() => {
            startAutomaticCarting(eventId, cartingSession.activeCarts[eventId].eventUrl, eventName);
        }, 30000); // Wait 30 seconds before retry
    }
}

/**
 * Send notification to Discord webhook
 */
function sendCartingNotification(eventId, eventName, message, useMentions) {
    // The server-side will handle this via the API
    fetch('/api/send-cart-notification', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            eventId: eventId,
            eventName: eventName,
            message: message,
            useMentions: useMentions
        })
    }).catch(error => {
        console.error('Error sending cart notification:', error);
    });
}

/**
 * Show browser notification
 */
function showBrowserNotification(title, message, url = null) {
    if (!("Notification" in window)) {
        console.log("Browser doesn't support notifications");
        return;
    }
    
    if (Notification.permission === "granted") {
        createNotification(title, message, url);
    } else if (Notification.permission !== "denied") {
        Notification.requestPermission().then(function (permission) {
            if (permission === "granted") {
                createNotification(title, message, url);
            }
        });
    }
}

/**
 * Create and display a notification
 */
function createNotification(title, message, url = null) {
    const notification = new Notification(title, {
        body: message,
        icon: '/static/img/notification-icon.png'
    });
    
    if (url) {
        notification.onclick = function() {
            window.open(url, '_blank');
            notification.close();
        };
    }
}

/**
 * Initialize the carting system
 */
function initCartingSystem() {
    console.log('Initializing Bad Bunny ticket carting system');
    
    // Load saved configuration if available
    const savedConfig = localStorage.getItem('cartConfig');
    if (savedConfig) {
        try {
            const parsedConfig = JSON.parse(savedConfig);
            cartConfig = {...cartConfig, ...parsedConfig};
            console.log('Loaded saved cart configuration:', cartConfig);
        } catch (e) {
            console.error('Error parsing saved cart configuration:', e);
        }
    }
    
    // Set up notification permission
    if (cartConfig.notifications && "Notification" in window) {
        if (Notification.permission !== "granted" && Notification.permission !== "denied") {
            Notification.requestPermission();
        }
    }
}

/**
 * Save carting configuration
 */
function saveCartingConfig() {
    localStorage.setItem('cartConfig', JSON.stringify(cartConfig));
    console.log('Saved cart configuration:', cartConfig);
}

/**
 * Update carting configuration
 */
function updateCartingConfig(newConfig) {
    cartConfig = {...cartConfig, ...newConfig};
    saveCartingConfig();
    
    // Update UI elements
    updateCartingUI();
    
    return cartConfig;
}

/**
 * Update UI elements based on current config
 */
function updateCartingUI() {
    // This will be called when the UI is initialized
    const enabledCheckbox = document.getElementById('cart-enabled');
    if (enabledCheckbox) {
        enabledCheckbox.checked = cartConfig.enabled;
    }
    
    const quantitySelect = document.getElementById('cart-quantity');
    if (quantitySelect) {
        quantitySelect.value = cartConfig.ticketQuantity;
    }
    
    const maxPriceInput = document.getElementById('cart-max-price');
    if (maxPriceInput) {
        maxPriceInput.value = cartConfig.maxPrice;
    }
    
    const notificationsCheckbox = document.getElementById('cart-notifications');
    if (notificationsCheckbox) {
        notificationsCheckbox.checked = cartConfig.notifications;
    }
}

// Initialize carting system
document.addEventListener('DOMContentLoaded', initCartingSystem);

// Expose functions to global scope for event handlers
window.cartSystem = {
    updateConfig: updateCartingConfig,
    startCarting: startAutomaticCarting,
    getConfig: () => cartConfig,
    getStatus: () => ({active: cartingSession.activeCarts, completed: cartingSession.completedCarts})
};
