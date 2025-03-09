/**
 * Bad Bunny Ticket Cart Content Script
 * 
 * This script injects into Ticketera pages to automatically add tickets to cart
 * when available. It communicates with the main application through window.postMessage.
 */

// Global cart settings
let cartSettings = {
    eventId: null,
    ticketQuantity: 2,
    maxPrice: 500,
    preferredSections: [],
    fallbackToAnySection: true
};

// Main initialization function
function initCartAutomation() {
    console.log('Cart automation content script loaded');
    
    // Get event ID from URL or data attributes if present
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('event_id')) {
        cartSettings.eventId = urlParams.get('event_id');
    }
    
    // Listen for messages from the parent window
    window.addEventListener('message', function(event) {
        // Validate origin (only accept messages from our extension or app)
        if (event.data.type === 'startCarting') {
            console.log('Received cart automation request:', event.data);
            cartSettings = {...cartSettings, ...event.data.settings};
            startTicketCartProcess();
        }
    });
    
    // If we're already on a Ticketera page, check if we should start carting
    if (window.location.href.includes('ticketera.com') || 
        window.location.href.includes('choli.pr')) {
        
        // Let parent window know we're ready
        window.parent.postMessage({
            type: 'cartContentScriptReady',
            url: window.location.href
        }, '*');
        
        // Check if this is already a cart or checkout page
        if (window.location.href.includes('/cart') || window.location.href.includes('/checkout')) {
            // We're already at checkout, notify parent
            window.parent.postMessage({
                cartEventId: cartSettings.eventId,
                status: 'cartSuccess',
                checkoutUrl: window.location.href
            }, '*');
        }
    }
}

// Main function to start the carting process
function startTicketCartProcess() {
    console.log('Starting ticket cart process with settings:', cartSettings);
    
    // Notify parent that we're starting
    window.parent.postMessage({
        cartEventId: cartSettings.eventId,
        status: 'starting'
    }, '*');
    
    // Check if we're on the event page or ticket selection page
    if (document.querySelector('.ticket-selection') || document.querySelector('.evento-info')) {
        console.log('On ticket selection page');
        findAndSelectTickets();
    } else {
        // We might be on the homepage or another page
        console.log('Not on ticket selection page');
        
        window.parent.postMessage({
            cartEventId: cartSettings.eventId,
            status: 'cartError',
            error: 'Not on ticket selection page'
        }, '*');
    }
}

// Function to find and select available tickets
function findAndSelectTickets() {
    console.log('Finding and selecting tickets');
    
    // Notify parent that we're looking for tickets
    window.parent.postMessage({
        cartEventId: cartSettings.eventId,
        status: 'findingTickets'
    }, '*');
    
    // Look for ticket sections
    const ticketSections = document.querySelectorAll('.section-item, .ticket-item');
    
    if (!ticketSections || ticketSections.length === 0) {
        console.log('No ticket sections found');
        
        window.parent.postMessage({
            cartEventId: cartSettings.eventId,
            status: 'cartError',
            error: 'No ticket sections found'
        }, '*');
        
        return;
    }
    
    console.log(`Found ${ticketSections.length} ticket sections`);
    
    // Filter sections based on preferences
    let selectedSection = null;
    let fallbackSection = null;
    
    // First try to find tickets in preferred sections
    if (cartSettings.preferredSections && cartSettings.preferredSections.length > 0) {
        for (const section of ticketSections) {
            const sectionName = section.querySelector('.section-name, .ticket-name').textContent.trim().toLowerCase();
            const sectionPrice = extractPrice(section);
            
            // Check if this section is in our preferred list
            const isPreferred = cartSettings.preferredSections.some(preferred => 
                sectionName.includes(preferred.toLowerCase())
            );
            
            // Check if price is within budget
            const isPriceOk = !sectionPrice || sectionPrice <= cartSettings.maxPrice;
            
            // Check if tickets are available
            const isAvailable = !section.classList.contains('disabled') && 
                               !section.classList.contains('sold-out');
            
            console.log(`Section: ${sectionName}, Price: ${sectionPrice}, Preferred: ${isPreferred}, Price OK: ${isPriceOk}, Available: ${isAvailable}`);
            
            if (isPreferred && isPriceOk && isAvailable) {
                selectedSection = section;
                break;
            }
            
            // Keep track of a fallback section
            if (isPriceOk && isAvailable && !fallbackSection) {
                fallbackSection = section;
            }
        }
    } else {
        // No preferred sections, just find any available section within budget
        for (const section of ticketSections) {
            const sectionName = section.querySelector('.section-name, .ticket-name').textContent.trim();
            const sectionPrice = extractPrice(section);
            
            // Check if price is within budget
            const isPriceOk = !sectionPrice || sectionPrice <= cartSettings.maxPrice;
            
            // Check if tickets are available
            const isAvailable = !section.classList.contains('disabled') && 
                               !section.classList.contains('sold-out');
            
            if (isPriceOk && isAvailable) {
                selectedSection = section;
                break;
            }
        }
    }
    
    // If no preferred section found, use fallback if enabled
    if (!selectedSection && fallbackSection && cartSettings.fallbackToAnySection) {
        console.log('No preferred section found, using fallback section');
        selectedSection = fallbackSection;
    }
    
    // If we found a section, select it
    if (selectedSection) {
        const sectionName = selectedSection.querySelector('.section-name, .ticket-name').textContent.trim();
        const sectionPrice = extractPrice(selectedSection);
        
        console.log(`Selected section: ${sectionName}, Price: ${sectionPrice}`);
        
        // Notify parent that we found tickets
        window.parent.postMessage({
            cartEventId: cartSettings.eventId,
            status: 'ticketsFound',
            sectionName: sectionName,
            price: sectionPrice
        }, '*');
        
        // Click on the section
        selectedSection.click();
        
        // Wait for ticket quantity selector to appear
        setTimeout(() => {
            selectTicketQuantity();
        }, 1000);
    } else {
        console.log('No suitable tickets found');
        
        window.parent.postMessage({
            cartEventId: cartSettings.eventId,
            status: 'cartError',
            error: 'No suitable tickets found within price range'
        }, '*');
    }
}

// Function to select ticket quantity
function selectTicketQuantity() {
    console.log('Selecting ticket quantity:', cartSettings.ticketQuantity);
    
    // Look for quantity selector
    const quantitySelector = document.querySelector('select.ticket-quantity');
    
    if (!quantitySelector) {
        console.log('Quantity selector not found');
        
        // Try to find "Add to Cart" button anyway
        addTicketsToCart();
        return;
    }
    
    // Set the quantity
    quantitySelector.value = cartSettings.ticketQuantity;
    
    // Trigger change event
    const event = new Event('change', { bubbles: true });
    quantitySelector.dispatchEvent(event);
    
    // Notify parent
    window.parent.postMessage({
        cartEventId: cartSettings.eventId,
        status: 'quantitySelected',
        quantity: cartSettings.ticketQuantity
    }, '*');
    
    // Proceed to add to cart
    setTimeout(() => {
        addTicketsToCart();
    }, 500);
}

// Function to add tickets to cart
function addTicketsToCart() {
    console.log('Adding tickets to cart');
    
    // Notify parent
    window.parent.postMessage({
        cartEventId: cartSettings.eventId,
        status: 'addingToCart'
    }, '*');
    
    // Find the "Add to Cart" button
    const addToCartButton = document.querySelector('.add-to-cart-btn, button[type="submit"]:not(.disabled)');
    
    if (!addToCartButton) {
        console.log('Add to cart button not found');
        
        window.parent.postMessage({
            cartEventId: cartSettings.eventId,
            status: 'cartError',
            error: 'Add to cart button not found'
        }, '*');
        
        return;
    }
    
    // Click the button
    addToCartButton.click();
    
    // Wait for cart page to load
    setTimeout(() => {
        checkCartStatus();
    }, 3000);
}

// Function to check if we've successfully added to cart
function checkCartStatus() {
    console.log('Checking cart status');
    
    // Check if we're on cart page
    if (window.location.href.includes('/cart') || 
        window.location.href.includes('/checkout') ||
        document.querySelector('.cart-summary, .checkout-summary')) {
        
        console.log('Successfully added to cart!');
        
        // Notify parent
        window.parent.postMessage({
            cartEventId: cartSettings.eventId,
            status: 'cartSuccess',
            checkoutUrl: window.location.href
        }, '*');
    } else {
        console.log('Not on cart page yet, waiting...');
        
        // Try again after a short delay
        setTimeout(() => {
            // Check if there are any error messages
            const errorMessages = document.querySelectorAll('.error-message, .alert-danger');
            if (errorMessages.length > 0) {
                const errorText = errorMessages[0].textContent.trim();
                console.log('Error adding to cart:', errorText);
                
                window.parent.postMessage({
                    cartEventId: cartSettings.eventId,
                    status: 'cartError',
                    error: errorText || 'Error adding to cart'
                }, '*');
                
                return;
            }
            
            // Keep checking
            checkCartStatus();
        }, 2000);
    }
}

// Helper function to extract price from a section element
function extractPrice(sectionElement) {
    const priceElement = sectionElement.querySelector('.price, .ticket-price');
    if (!priceElement) return null;
    
    const priceText = priceElement.textContent.trim();
    const priceMatch = priceText.match(/\$?(\d+(\.\d+)?)/);
    
    return priceMatch ? parseFloat(priceMatch[1]) : null;
}

// Initialize the cart automation
initCartAutomation();
