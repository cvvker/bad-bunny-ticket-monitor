/**
 * Checkout link handling for Bad Bunny Ticket Monitor
 */

// Process checkout links in ticket status
function processCheckoutLink(statusText) {
    if (statusText.includes('CHECKOUT AVAILABLE')) {
        // Extract the link from the status text
        const linkMatch = statusText.match(/Link: (https?:\/\/[^\s]+)/);
        if (linkMatch && linkMatch[1]) {
            return linkMatch[1].replace('...', '');
        }
    }
    return null;
}

// Update UI with checkout button when available
function addCheckoutButton(card, checkoutLink) {
    // Remove any existing checkout buttons
    const existingButton = card.querySelector('.checkout-button-container');
    if (existingButton) {
        existingButton.remove();
    }
    
    // Create new checkout button
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'checkout-button-container text-center mt-3';
    
    const checkoutButton = document.createElement('a');
    checkoutButton.className = 'btn btn-danger checkout-button';
    checkoutButton.innerHTML = '<i class="fas fa-shopping-cart"></i> GO TO CHECKOUT';
    checkoutButton.href = checkoutLink;
    checkoutButton.target = '_blank';
    
    buttonContainer.appendChild(checkoutButton);
    card.appendChild(buttonContainer);
}

// Enhanced updateTicketUI function to handle checkout links
function enhancedUpdateTicketUI(eventId, event) {
    const eventCard = document.getElementById(eventId);
    if (!eventCard) {
        console.log(`Card for event ${eventId} not found`);
        return;
    }

    const statusElement = eventCard.querySelector('.status-badge');
    const updatedElement = eventCard.querySelector('.card-text');
    const statusAlert = eventCard.querySelector('.status-alert');
    
    // Store previous status for this event
    if (!previousStates[eventId]) {
        previousStates[eventId] = '';
    }

    // Update status text and apply styling
    if (event.status && statusElement) {
        statusElement.textContent = event.status;
        
        // Clear all existing classes first
        eventCard.classList.remove('shake', 'checkout-available');
        statusElement.className = 'badge status-badge';
        
        // Apply styling based on status
        if (event.status.includes('CHECKOUT AVAILABLE')) {
            // Special styling for checkout available
            eventCard.classList.add('checkout-available', 'shake');
            statusElement.className = 'badge checkout-status status-badge';
            statusAlert.className = 'status-alert alert-danger';
            
            // Add checkout button
            const checkoutLink = processCheckoutLink(event.status);
            if (checkoutLink) {
                addCheckoutButton(eventCard, checkoutLink);
                
                // Play special alert for checkout availability
                if (!previousStates[eventId].includes('CHECKOUT AVAILABLE') && isSoundEnabled()) {
                    console.log(`Checkout available for ${eventId}: ${previousStates[eventId]} → ${event.status}`);
                    // Play sound multiple times to indicate high priority
                    playAlertSound();
                    setTimeout(playAlertSound, 1000);
                    setTimeout(playAlertSound, 2000);
                }
            }
        } 
        else if (event.status.includes('Available')) {
            // Check if status has changed from unavailable to available
            if (!previousStates[eventId].includes('Available') && isSoundEnabled()) {
                console.log(`Status changed for ${eventId}: ${previousStates[eventId]} → ${event.status}`);
                playAlertSound();
            }
            statusElement.className = 'badge alert-success status-badge';
            statusAlert.className = 'status-alert alert-success';
            eventCard.classList.add('shake');
            
            // Remove checkout button if it exists
            const checkoutButtonContainer = eventCard.querySelector('.checkout-button-container');
            if (checkoutButtonContainer) {
                checkoutButtonContainer.remove();
            }
        } 
        else if (event.status.includes('Soon')) {
            statusElement.className = 'badge alert-warning status-badge';
            statusAlert.className = 'status-alert alert-warning';
            
            // Remove checkout button if it exists
            const checkoutButtonContainer = eventCard.querySelector('.checkout-button-container');
            if (checkoutButtonContainer) {
                checkoutButtonContainer.remove();
            }
        } 
        else if (event.status.includes('Sold Out')) {
            statusElement.className = 'badge alert-danger status-badge';
            statusAlert.className = 'status-alert alert-danger';
            
            // Remove checkout button if it exists
            const checkoutButtonContainer = eventCard.querySelector('.checkout-button-container');
            if (checkoutButtonContainer) {
                checkoutButtonContainer.remove();
            }
        } 
        else {
            statusElement.className = 'badge alert-info status-badge';
            statusAlert.className = 'status-alert alert-info';
            
            // Remove checkout button if it exists
            const checkoutButtonContainer = eventCard.querySelector('.checkout-button-container');
            if (checkoutButtonContainer) {
                checkoutButtonContainer.remove();
            }
        }
        
        // Save the current status as the previous status for next time
        previousStates[eventId] = event.status;
    }

    // Update last checked time
    if (updatedElement) {
        const now = new Date();
        updatedElement.textContent = `Last checked: ${new Date(event.lastChecked).toLocaleString()}`;
    }
}
