/**
 * Ticketera Checkout Form Autofill
 * This script automatically fills checkout form fields when a checkout page is detected
 */

// Saved user information (will be stored in localStorage)
let userInfo = {
    firstName: "",
    lastName: "",
    email: "",
    phone: "",
    address: {
        street: "",
        city: "",
        state: "",
        zip: ""
    }
};

// Load saved info from localStorage
function loadSavedInfo() {
    const savedInfo = localStorage.getItem('ticketeraUserInfo');
    if (savedInfo) {
        try {
            userInfo = JSON.parse(savedInfo);
            return true;
        } catch (e) {
            console.error("Error loading saved user info:", e);
            return false;
        }
    }
    return false;
}

// Save user info to localStorage
function saveUserInfo() {
    localStorage.setItem('ticketeraUserInfo', JSON.stringify(userInfo));
}

// Get form fields from the settings form
function getUserInfoFromForm() {
    const form = document.getElementById('autofill-settings-form');
    if (!form) return false;
    
    userInfo.firstName = form.querySelector('#autofill-firstname').value;
    userInfo.lastName = form.querySelector('#autofill-lastname').value;
    userInfo.email = form.querySelector('#autofill-email').value;
    userInfo.phone = form.querySelector('#autofill-phone').value;
    userInfo.address.street = form.querySelector('#autofill-street').value;
    userInfo.address.city = form.querySelector('#autofill-city').value;
    userInfo.address.state = form.querySelector('#autofill-state').value;
    userInfo.address.zip = form.querySelector('#autofill-zip').value;
    
    // Save to localStorage
    saveUserInfo();
    return true;
}

// Apply autofill to checkout page
function autofillCheckoutPage() {
    // This function will be injected into the checkout page via a content script approach
    // First, ensure we have user data
    if (loadSavedInfo()) {
        // Store fields to fill with corresponding values
        const fieldsToFill = {
            'input[name*="first"i]:not([type="hidden"])': userInfo.firstName,
            'input[name*="last"i]:not([type="hidden"])': userInfo.lastName,
            'input[type="email"]:not([name*="repeat"i]):not([name*="confirm"i])': userInfo.email,
            'input[name*="repeat"i][type="email"], input[name*="confirm"i][type="email"]': userInfo.email,
            'input[name*="phone"i]:not([type="hidden"])': userInfo.phone,
            'input[name*="street"i]:not([type="hidden"]), input[name*="address"i]:not([type="hidden"])': userInfo.address.street,
            'input[name*="city"i]:not([type="hidden"])': userInfo.address.city,
            'input[name*="state"i]:not([type="hidden"]), select[name*="state"i]': userInfo.address.state,
            'input[name*="zip"i]:not([type="hidden"]), input[name*="postal"i]:not([type="hidden"])': userInfo.address.zip
        };
        
        // Fill each matching field
        for (const selector in fieldsToFill) {
            const elements = document.querySelectorAll(selector);
            const value = fieldsToFill[selector];
            
            elements.forEach(element => {
                if (element.tagName === 'SELECT') {
                    // Handle dropdown select elements
                    const options = element.querySelectorAll('option');
                    for (const option of options) {
                        if (option.text.toLowerCase().includes(value.toLowerCase())) {
                            option.selected = true;
                            break;
                        }
                    }
                    // Trigger change event
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    // Handle input elements
                    element.value = value;
                    // Trigger input and change events to activate any form validation
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        }
        
        return true;
    }
    return false;
}

// Function to create a bookmarklet for manual autofill
function generateAutofillBookmarklet() {
    // Load the latest user data
    loadSavedInfo();
    
    // Create the JavaScript code that will be executed by the bookmarklet
    const bookmarkletCode = `
        (function() {
            const userInfo = ${JSON.stringify(userInfo)};
            
            // Store fields to fill with corresponding values
            const fieldsToFill = {
                'input[name*="first"i]:not([type="hidden"])': userInfo.firstName,
                'input[name*="last"i]:not([type="hidden"])': userInfo.lastName,
                'input[type="email"]:not([name*="repeat"i]):not([name*="confirm"i])': userInfo.email,
                'input[name*="repeat"i][type="email"], input[name*="confirm"i][type="email"]': userInfo.email,
                'input[name*="phone"i]:not([type="hidden"])': userInfo.phone,
                'input[name*="street"i]:not([type="hidden"]), input[name*="address"i]:not([type="hidden"])': userInfo.address.street,
                'input[name*="city"i]:not([type="hidden"])': userInfo.address.city,
                'input[name*="state"i]:not([type="hidden"]), select[name*="state"i]': userInfo.address.state,
                'input[name*="zip"i]:not([type="hidden"]), input[name*="postal"i]:not([type="hidden"])': userInfo.address.zip
            };
            
            // Fill each matching field
            for (const selector in fieldsToFill) {
                const elements = document.querySelectorAll(selector);
                const value = fieldsToFill[selector];
                
                elements.forEach(element => {
                    if (element.tagName === 'SELECT') {
                        // Handle dropdown select elements
                        const options = element.querySelectorAll('option');
                        for (const option of options) {
                            if (option.text.toLowerCase().includes(value.toLowerCase())) {
                                option.selected = true;
                                break;
                            }
                        }
                        // Trigger change event
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                    } else {
                        // Handle input elements
                        element.value = value;
                        // Trigger input and change events to activate any form validation
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
            }
            
            alert('Form autofilled successfully!');
        })();
    `;
    
    // Encode the code for a bookmarklet
    const encodedCode = encodeURIComponent(bookmarkletCode.replace(/\s+/g, ' '));
    return `javascript:${encodedCode}`;
}

// Function to update the bookmarklet link in settings
function updateBookmarkletLink() {
    const bookmarkletLink = document.getElementById('autofill-bookmarklet');
    if (bookmarkletLink) {
        bookmarkletLink.href = generateAutofillBookmarklet();
    }
}

// Initialize the autofill settings in the UI
function initAutofillSettings() {
    // Load saved info
    loadSavedInfo();
    
    // Populate the form fields with saved values
    const form = document.getElementById('autofill-settings-form');
    if (form) {
        form.querySelector('#autofill-firstname').value = userInfo.firstName || '';
        form.querySelector('#autofill-lastname').value = userInfo.lastName || '';
        form.querySelector('#autofill-email').value = userInfo.email || '';
        form.querySelector('#autofill-phone').value = userInfo.phone || '';
        form.querySelector('#autofill-street').value = userInfo.address.street || '';
        form.querySelector('#autofill-city').value = userInfo.address.city || '';
        form.querySelector('#autofill-state').value = userInfo.address.state || '';
        form.querySelector('#autofill-zip').value = userInfo.address.zip || '';
        
        // Add save button event listener
        const saveButton = document.getElementById('save-autofill-settings');
        if (saveButton) {
            saveButton.addEventListener('click', function() {
                getUserInfoFromForm();
                updateBookmarkletLink();
                alert('Your checkout information has been saved!');
            });
        }
    }
    
    // Set up the bookmarklet link
    updateBookmarkletLink();
}

// Wait for the DOM to be ready, then initialize
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the settings page
    if (document.getElementById('autofill-settings-form')) {
        initAutofillSettings();
    }
});
