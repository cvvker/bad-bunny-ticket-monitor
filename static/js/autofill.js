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

// Sample data for random generation
const sampleData = {
    firstNames: ["Juan", "Luis", "Carlos", "Miguel", "José", "Pedro", "Antonio", "Manuel", "Francisco", "Roberto", "Fernando", "Rafael", "Javier", "Sergio", "Ricardo", "Daniel", "Eduardo", "Mario", "Jorge", "Alberto", "Alejandro"],
    lastNames: ["Rodríguez", "González", "Hernández", "López", "Martínez", "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera", "Gómez", "Díaz", "Reyes", "Cruz", "Morales", "Ortiz", "Vázquez", "Castillo", "Mendoza", "Jiménez", "García", "Rosario", "Figueroa", "Acosta", "Ayala", "Medina", "Santiago", "Colón", "Delgado", "Rivera", "Nieves", "Vega"],
    streets: ["Calle Sol", "Avenida Fernández Juncos", "Calle Luna", "Avenida Ashford", "Calle Loíza", "Calle Fortaleza", "Calle San Francisco", "Avenida Ponce de León", "Avenida Roosevelt", "Calle 31 SO", "Calle San Sebastián", "Avenida Jesús T. Piñero", "Calle Recinto Sur", "Avenida Constitución", "Calle Tanca", "Avenida Luis Muñoz Rivera"],
    streetNumbers: ["100", "200", "300", "400", "500", "600", "700", "800", "900", "1000", "1100", "1200", "1300", "1400", "1500", "1600", "1700", "1800", "1900", "2000"],
    cities: ["San Juan", "Bayamón", "Carolina", "Ponce", "Caguas", "Guaynabo", "Mayagüez", "Trujillo Alto", "Fajardo", "Arecibo", "Vega Baja", "Humacao", "Aguadilla", "Isabela", "Dorado", "Hatillo", "Manatí", "Cayey", "Guayama", "Río Grande", "Coamo", "Rincón"],
    states: ["PR"],
    zipCodes: ["00901", "00902", "00906", "00907", "00909", "00911", "00913", "00917", "00920", "00921", "00923", "00926", "00927", "00934", "00936", "00949", "00950", "00959", "00961", "00965", "00966", "00969", "00976", "00979"]
};

// Generate random phone number (Puerto Rico format)
function generateRandomPhone() {
    const areaCodes = ["787", "939"];
    const areaCode = areaCodes[Math.floor(Math.random() * areaCodes.length)];
    const middle = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
    const end = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
    return `${areaCode}-${middle}-${end}`;
}

// Generate random data for everything except email
function generateRandomUserInfo() {
    const getRandomItem = arr => arr[Math.floor(Math.random() * arr.length)];
    
    userInfo.firstName = getRandomItem(sampleData.firstNames);
    userInfo.lastName = getRandomItem(sampleData.lastNames);
    userInfo.phone = generateRandomPhone();
    userInfo.address.street = `${getRandomItem(sampleData.streetNumbers)} ${getRandomItem(sampleData.streets)}`;
    userInfo.address.city = getRandomItem(sampleData.cities);
    userInfo.address.state = getRandomItem(sampleData.states);
    userInfo.address.zip = getRandomItem(sampleData.zipCodes);
    
    // Email is intentionally left blank for the user to fill in
    userInfo.email = "";
    
    return userInfo;
}

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

// Function to add a random autofill button
function addRandomAutofillButton() {
    const form = document.getElementById('autofill-settings-form');
    if (form) {
        const actionDiv = form.querySelector('.autofill-actions');
        if (actionDiv) {
            // Create random fill button
            const randomButton = document.createElement('button');
            randomButton.type = 'button';
            randomButton.id = 'random-autofill-settings';
            randomButton.className = 'btn btn-secondary';
            randomButton.innerHTML = '<i class="fas fa-dice"></i> Generate Random Info';
            
            // Add click event
            randomButton.addEventListener('click', function() {
                // Generate random info
                generateRandomUserInfo();
                
                // Update form with random data (except email)
                document.getElementById('autofill-firstname').value = userInfo.firstName;
                document.getElementById('autofill-lastname').value = userInfo.lastName;
                document.getElementById('autofill-phone').value = userInfo.phone;
                document.getElementById('autofill-street').value = userInfo.address.street;
                document.getElementById('autofill-city').value = userInfo.address.city;
                document.getElementById('autofill-state').value = userInfo.address.state;
                document.getElementById('autofill-zip').value = userInfo.address.zip;
                
                // Save to localStorage
                saveUserInfo();
                
                // Update bookmarklet
                updateBookmarkletLink();
                
                // Notify user
                alert('Random information generated! Email field left empty for your own list.');
            });
            
            // Insert before the save button
            actionDiv.insertBefore(randomButton, actionDiv.firstChild);
        }
    }
}

// Initialize the autofill settings in the UI
function initAutofillSettings() {
    // Load saved info, if none exists, generate random
    const hasUserInfo = loadSavedInfo();
    if (!hasUserInfo) {
        generateRandomUserInfo();
    }
    
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
    
    // Add random autofill button
    addRandomAutofillButton();
    
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
