// Content script for Ticketera Autofill extension
// This script runs on Ticketera checkout pages but ONLY fills forms when requested

console.log("Ticketera Autofill: Content script loaded and ready");

// Global settings
let settings = { showNotifications: true };

// Listen for messages from the popup or background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log("Message received in content script:", message);
    
    if (message.action === "fill_form") {
        console.log("Fill form request received with data:", message.userInfo);
        fillCheckoutForm(message.userInfo);
    } else if (message.action === "update_settings") {
        settings = message.settings;
        console.log("Settings updated:", settings);
    }
    return true; // Keep the message channel open for async responses
});

// Add a floating autofill button
document.addEventListener("DOMContentLoaded", function() {
    console.log("Ticketera Autofill: Page loaded, checking for checkout form");
    
    if (isCheckoutPage()) {
        console.log("Checkout page detected!");
        addFloatingButton();
    }
});

// Check if we're on a checkout page
function isCheckoutPage() {
    const url = window.location.href.toLowerCase();
    if (url.includes('checkout') || url.includes('pago') || url.includes('payment')) {
        return true;
    }
    
    // Look for common checkout form elements
    const paymentForm = document.querySelector("form[id*='checkout'], form[id*='payment'], form[class*='checkout'], .checkout-form");
    const paymentFields = document.querySelector("input[name*='card'], input[name*='credit'], input[name*='tarjeta']");
    const addressFields = document.querySelector("input[name*='address'], input[name*='direccion']");
    
    return paymentForm || paymentFields || addressFields;
}

// Add a floating button for easy form filling
function addFloatingButton() {
    // Check if button already exists
    if (document.getElementById('ticketera-autofill-button')) {
        return;
    }
    
    const button = document.createElement("button");
    button.id = 'ticketera-autofill-button';
    button.innerHTML = "Autofill Form";
    button.style.position = "fixed";
    button.style.bottom = "20px";
    button.style.right = "20px";
    button.style.zIndex = "10000";
    button.style.backgroundColor = "#9c27b0";
    button.style.color = "white";
    button.style.border = "none";
    button.style.borderRadius = "4px";
    button.style.padding = "10px 15px";
    button.style.fontWeight = "bold";
    button.style.boxShadow = "0 2px 5px rgba(0,0,0,0.3)";
    button.style.cursor = "pointer";
    
    button.addEventListener("click", function() {
        chrome.storage.local.get("userInfo", function(result) {
            if (result.userInfo) {
                fillCheckoutForm(result.userInfo);
            } else {
                if (settings.showNotifications) {
                    showNotification("No user information found. Please open the extension popup and generate random info first.", "error");
                }
            }
        });
    });
    
    document.body.appendChild(button);
}

// Show notification in page
function showNotification(message, type = "info") {
    // Don't show if notifications are disabled
    if (!settings.showNotifications) {
        return;
    }
    
    // Remove any existing notifications
    const existingNotification = document.getElementById('ticketera-autofill-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    const notification = document.createElement("div");
    notification.id = 'ticketera-autofill-notification';
    notification.textContent = message;
    
    // Style based on notification type
    let bgColor = "#2196f3"; // Default blue for info
    if (type === "success") {
        bgColor = "#4CAF50"; // Green
    } else if (type === "error") {
        bgColor = "#f44336"; // Red
    } else if (type === "warning") {
        bgColor = "#ff9800"; // Orange
    }
    
    notification.style.position = "fixed";
    notification.style.top = "20px";
    notification.style.right = "20px";
    notification.style.backgroundColor = bgColor;
    notification.style.color = "white";
    notification.style.padding = "15px";
    notification.style.borderRadius = "4px";
    notification.style.zIndex = "10001";
    notification.style.boxShadow = "0 2px 10px rgba(0,0,0,0.3)";
    notification.style.maxWidth = "300px";
    
    document.body.appendChild(notification);
    
    // Remove the notification after 5 seconds
    setTimeout(() => {
        notification.style.opacity = "0";
        notification.style.transition = "opacity 0.5s";
        setTimeout(() => {
            notification.remove();
        }, 500);
    }, 5000);
}

// Fill the checkout form with user info
function fillCheckoutForm(userInfo) {
    console.log("Starting to fill checkout form with:", userInfo);
    let filledFields = 0;
    
    try {
        // First approach: Try common field selectors
        const fieldsMapping = [
            // First name
            { selectors: ["input[name*='first'i]:not([type='hidden'])", "input[name*='nombre'i]:not([type='hidden'])", 
                          "input#firstname", "input#firstName", "input#first_name", 
                          "input[placeholder*='first'i]", "input[placeholder*='nombre'i]"], 
              value: userInfo.firstName },
              
            // Last name
            { selectors: ["input[name*='last'i]:not([type='hidden'])", "input[name*='apellido'i]:not([type='hidden'])",
                          "input#lastname", "input#lastName", "input#last_name", 
                          "input[placeholder*='last'i]", "input[placeholder*='apellido'i]"], 
              value: userInfo.lastName },
              
            // Email (only fill if provided)
            { selectors: ["input[type='email']:not([type='hidden'])", "input[name*='email'i]:not([type='hidden'])",
                          "input#email", "input[placeholder*='email'i]", "input[placeholder*='correo'i]"], 
              value: userInfo.email },
              
            // Phone
            { selectors: ["input[name*='phone'i]:not([type='hidden'])", "input[name*='telefono'i]:not([type='hidden'])",
                          "input#phone", "input#phoneNumber", "input[type='tel']", 
                          "input[placeholder*='phone'i]", "input[placeholder*='telefono'i]"], 
              value: userInfo.phone },
              
            // Street
            { selectors: ["input[name*='street'i]:not([type='hidden'])", "input[name*='address'i]:not([type='hidden'])",
                          "input[name*='direccion'i]:not([type='hidden'])", 
                          "input#street", "input#address", "input#street-address",
                          "input[placeholder*='street'i]", "input[placeholder*='address'i]", "input[placeholder*='direccion'i]"], 
              value: userInfo.street },
              
            // City
            { selectors: ["input[name*='city'i]:not([type='hidden'])", "input[name*='ciudad'i]:not([type='hidden'])",
                          "input#city", "input[placeholder*='city'i]", "input[placeholder*='ciudad'i]"], 
              value: userInfo.city },
              
            // State
            { selectors: ["input[name*='state'i]:not([type='hidden'])", "input[name*='estado'i]:not([type='hidden'])",
                          "select[name*='state'i]", "select[name*='estado'i]", 
                          "input#state", "select#state", "select#estado"], 
              value: userInfo.state },
              
            // Zip code
            { selectors: ["input[name*='zip'i]:not([type='hidden'])", "input[name*='postal'i]:not([type='hidden'])",
                          "input[name*='codigo'i]:not([type='hidden'])", 
                          "input#zipcode", "input#zip", "input#postal", "input#postalCode",
                          "input[placeholder*='zip'i]", "input[placeholder*='postal'i]", "input[placeholder*='codigo'i]"], 
              value: userInfo.zip }
        ];
        
        // Try to fill each field using the selectors
        fieldsMapping.forEach(mapping => {
            // Skip if we don't have a value to fill (e.g., email might be empty)
            if (!mapping.value) return;
            
            let elementFound = false;
            
            // Try each selector until an element is found
            for (const selector of mapping.selectors) {
                if (elementFound) break;
                
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    elements.forEach(element => {
                        if (element.tagName === 'SELECT') {
                            // Handle dropdown elements
                            const options = element.querySelectorAll('option');
                            for (const option of options) {
                                if (option.text.toLowerCase().includes(mapping.value.toLowerCase())) {
                                    option.selected = true;
                                    elementFound = true;
                                    filledFields++;
                                    break;
                                }
                            }
                            element.dispatchEvent(new Event('change', { bubbles: true }));
                        } else {
                            // Only fill if the field is empty or if it's for testing
                            if (!element.value || element.value.length < 2 || window.location.href.includes('test')) {
                                element.value = mapping.value;
                                element.dispatchEvent(new Event('input', { bubbles: true }));
                                element.dispatchEvent(new Event('change', { bubbles: true }));
                                elementFound = true;
                                filledFields++;
                            }
                        }
                    });
                }
            }
        });
        
        // Second approach: Try to find fields by analyzing all inputs
        if (filledFields === 0) {
            console.log("First approach didn't find any fields, trying second approach...");
            
            // Get all input fields
            const allInputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"])');
            
            allInputs.forEach(input => {
                // Only fill if the field is empty
                if (input.value && input.value.length > 1) return;
                
                const name = (input.name || '').toLowerCase();
                const id = (input.id || '').toLowerCase();
                const placeholder = (input.placeholder || '').toLowerCase();
                const type = (input.type || '').toLowerCase();
                
                try {
                    // First name
                    if (name.includes('first') || name.includes('nombre') || id.includes('first') || id.includes('nombre') || 
                        placeholder.includes('first') || placeholder.includes('nombre')) {
                        input.value = userInfo.firstName;
                        filledFields++;
                    }
                    // Last name
                    else if (name.includes('last') || name.includes('apellido') || id.includes('last') || id.includes('apellido') || 
                            placeholder.includes('last') || placeholder.includes('apellido')) {
                        input.value = userInfo.lastName;
                        filledFields++;
                    }
                    // Email
                    else if ((name.includes('email') || id.includes('email') || placeholder.includes('email') || 
                            placeholder.includes('correo') || type === 'email') && userInfo.email) {
                        input.value = userInfo.email;
                        filledFields++;
                    }
                    // Phone
                    else if (name.includes('phone') || name.includes('telefono') || id.includes('phone') || id.includes('telefono') || 
                            placeholder.includes('phone') || placeholder.includes('telefono') || type === 'tel') {
                        input.value = userInfo.phone;
                        filledFields++;
                    }
                    // Street
                    else if (name.includes('street') || name.includes('address') || name.includes('direccion') || 
                            id.includes('street') || id.includes('address') || id.includes('direccion') || 
                            placeholder.includes('street') || placeholder.includes('address') || placeholder.includes('direccion')) {
                        input.value = userInfo.street;
                        filledFields++;
                    }
                    // City
                    else if (name.includes('city') || name.includes('ciudad') || id.includes('city') || id.includes('ciudad') || 
                            placeholder.includes('city') || placeholder.includes('ciudad')) {
                        input.value = userInfo.city;
                        filledFields++;
                    }
                    // State
                    else if (name.includes('state') || name.includes('estado') || id.includes('state') || id.includes('estado') || 
                            placeholder.includes('state') || placeholder.includes('estado')) {
                        input.value = userInfo.state;
                        filledFields++;
                    }
                    // Zip
                    else if (name.includes('zip') || name.includes('postal') || name.includes('codigo') || 
                            id.includes('zip') || id.includes('postal') || id.includes('codigo') || 
                            placeholder.includes('zip') || placeholder.includes('postal') || placeholder.includes('codigo')) {
                        input.value = userInfo.zip;
                        filledFields++;
                    }
                    
                    // Dispatch events if we filled this field
                    if (input.value) {
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                } catch (fallbackError) {
                    console.error("Error in fallback approach:", fallbackError);
                }
            });
        }
        
        // Show notification if enabled in settings
        if (settings.showNotifications) {
            if (filledFields > 0) {
                showNotification(`Form filled with ${filledFields} fields! ${!userInfo.email ? 'Remember to enter your email.' : ''}`, "success");
            } else {
                showNotification("No form fields were found to fill. You may need to fill the form manually.", "warning");
            }
        }
        
        return filledFields;
    } catch (error) {
        console.error("Error filling checkout form:", error);
        if (settings.showNotifications) {
            showNotification("Error filling form: " + error.message, "error");
        }
        return 0;
    }
}
