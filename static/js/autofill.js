/**
 * Ticketera Checkout Form Autofill
 * This script provides a bookmarklet for auto-filling checkout forms
 */

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

// Generate random user info object
function generateRandomUserInfo() {
    const getRandomItem = arr => arr[Math.floor(Math.random() * arr.length)];
    
    return {
        firstName: getRandomItem(sampleData.firstNames),
        lastName: getRandomItem(sampleData.lastNames),
        email: "", // Intentionally left blank
        phone: generateRandomPhone(),
        address: {
            street: `${getRandomItem(sampleData.streetNumbers)} ${getRandomItem(sampleData.streets)}`,
            city: getRandomItem(sampleData.cities),
            state: getRandomItem(sampleData.states),
            zip: getRandomItem(sampleData.zipCodes)
        }
    };
}

// Generate bookmarklet code - UPDATED VERSION with more robust selectors
function generateBookmarkletCode(userInfo) {
    const code = `
    (function() {
        try {
            console.log("Autofill bookmarklet started");
            const userInfo = ${JSON.stringify(userInfo)};
            
            // More comprehensive set of selectors for form fields
            const fieldsToFill = {
                // First name - try multiple variations
                'input[name*="first"i]:not([type="hidden"]), input[name*="nombre"i]:not([type="hidden"]), input#firstname, input#firstName, input#first_name, input[placeholder*="first"i], input[placeholder*="nombre"i]': userInfo.firstName,
                
                // Last name - try multiple variations
                'input[name*="last"i]:not([type="hidden"]), input[name*="apellido"i]:not([type="hidden"]), input#lastname, input#lastName, input#last_name, input[placeholder*="last"i], input[placeholder*="apellido"i]': userInfo.lastName,
                
                // Phone
                'input[name*="phone"i]:not([type="hidden"]), input[name*="telefono"i]:not([type="hidden"]), input#phone, input#phoneNumber, input[placeholder*="phone"i], input[placeholder*="telefono"i], input[type="tel"]': userInfo.phone,
                
                // Address/Street
                'input[name*="street"i]:not([type="hidden"]), input[name*="address"i]:not([type="hidden"]), input[name*="direccion"i]:not([type="hidden"]), input#street, input#address, input[placeholder*="street"i], input[placeholder*="address"i], input[placeholder*="direccion"i]': userInfo.address.street,
                
                // City
                'input[name*="city"i]:not([type="hidden"]), input[name*="ciudad"i]:not([type="hidden"]), input#city, input[placeholder*="city"i], input[placeholder*="ciudad"i]': userInfo.address.city,
                
                // State
                'input[name*="state"i]:not([type="hidden"]), input[name*="estado"i]:not([type="hidden"]), select[name*="state"i], select[name*="estado"i], input#state, select#state, select#estado': userInfo.address.state,
                
                // Zip code
                'input[name*="zip"i]:not([type="hidden"]), input[name*="postal"i]:not([type="hidden"]), input[name*="codigo"i]:not([type="hidden"]), input#zipcode, input#zip, input#postal, input#postalCode, input[placeholder*="zip"i], input[placeholder*="postal"i]': userInfo.address.zip
            };
            
            console.log("Attempting to fill fields with:", userInfo);
            
            // Count of fields found
            let fieldsFound = 0;
            
            // Fill fields
            for (const selector in fieldsToFill) {
                const elements = document.querySelectorAll(selector);
                const value = fieldsToFill[selector];
                
                console.log(\`Found \${elements.length} elements matching selector: \${selector}\`);
                
                elements.forEach(element => {
                    try {
                        fieldsFound++;
                        if (element.tagName === 'SELECT') {
                            // Handle dropdown select elements
                            const options = element.querySelectorAll('option');
                            for (const option of options) {
                                if (option.text.toLowerCase().includes(value.toLowerCase())) {
                                    option.selected = true;
                                    break;
                                }
                            }
                            element.dispatchEvent(new Event('change', { bubbles: true }));
                        } else {
                            // Handle input elements
                            element.value = value;
                            element.dispatchEvent(new Event('input', { bubbles: true }));
                            element.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        console.log(\`Successfully filled field: \${element.name || element.id || 'unnamed'} with value: \${value}\`);
                    } catch (fieldError) {
                        console.error("Error filling field:", fieldError);
                    }
                });
            }
            
            // Try a different approach for fields that might be in iframes or have unusual structures
            setTimeout(function() {
                // Get all input elements
                const allInputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"])');
                
                allInputs.forEach(input => {
                    const name = (input.name || '').toLowerCase();
                    const id = (input.id || '').toLowerCase();
                    const placeholder = (input.placeholder || '').toLowerCase();
                    const type = (input.type || '').toLowerCase();
                    
                    // Skip if already filled
                    if (input.value) return;
                    
                    try {
                        // First name
                        if (name.includes('first') || name.includes('nombre') || id.includes('first') || id.includes('nombre') || 
                            placeholder.includes('first') || placeholder.includes('nombre')) {
                            input.value = userInfo.firstName;
                        }
                        // Last name
                        else if (name.includes('last') || name.includes('apellido') || id.includes('last') || id.includes('apellido') || 
                                placeholder.includes('last') || placeholder.includes('apellido')) {
                            input.value = userInfo.lastName;
                        }
                        // Phone
                        else if (name.includes('phone') || name.includes('telefono') || id.includes('phone') || id.includes('telefono') || 
                                placeholder.includes('phone') || placeholder.includes('telefono') || type === 'tel') {
                            input.value = userInfo.phone;
                        }
                        // Street
                        else if (name.includes('street') || name.includes('address') || name.includes('direccion') || 
                                id.includes('street') || id.includes('address') || id.includes('direccion') || 
                                placeholder.includes('street') || placeholder.includes('address') || placeholder.includes('direccion')) {
                            input.value = userInfo.address.street;
                        }
                        // City
                        else if (name.includes('city') || name.includes('ciudad') || id.includes('city') || id.includes('ciudad') || 
                                placeholder.includes('city') || placeholder.includes('ciudad')) {
                            input.value = userInfo.address.city;
                        }
                        // State
                        else if (name.includes('state') || name.includes('estado') || id.includes('state') || id.includes('estado') || 
                                placeholder.includes('state') || placeholder.includes('estado')) {
                            input.value = userInfo.address.state;
                        }
                        // Zip
                        else if (name.includes('zip') || name.includes('postal') || name.includes('codigo') || 
                                id.includes('zip') || id.includes('postal') || id.includes('codigo') || 
                                placeholder.includes('zip') || placeholder.includes('postal') || placeholder.includes('codigo')) {
                            input.value = userInfo.address.zip;
                        }
                        
                        // Dispatch events
                        if (input.value) {
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            fieldsFound++;
                        }
                    } catch (fallbackError) {
                        console.error("Error in fallback approach:", fallbackError);
                    }
                });
                
                if (fieldsFound > 0) {
                    alert(\`Form autofilled with \${fieldsFound} fields! Email field left blank for your list.\`);
                } else {
                    alert("No form fields were found to autofill. Please check if you're on a checkout page.");
                }
            }, 500);
            
        } catch (error) {
            console.error("Autofill bookmarklet error:", error);
            alert("Error running autofill: " + error.message);
        }
    })();
    `;
    
    return 'javascript:' + encodeURIComponent(code.replace(/\s+/g, ' '));
}

// Update the bookmarklet URL
function updateBookmarkletURL() {
    const userInfo = generateRandomUserInfo();
    const bookmarkletURL = generateBookmarkletCode(userInfo);
    
    const bookmarkletLink = document.getElementById('autofill-bookmarklet');
    if (bookmarkletLink) {
        bookmarkletLink.href = bookmarkletURL;
    }
    
    // Also update the display fields if they exist
    displayUserInfo(userInfo);
    
    return userInfo;
}

// Display user info in the form
function displayUserInfo(userInfo) {
    const fields = {
        'autofill-firstname': userInfo.firstName,
        'autofill-lastname': userInfo.lastName,
        'autofill-email': userInfo.email,
        'autofill-phone': userInfo.phone,
        'autofill-street': userInfo.address.street,
        'autofill-city': userInfo.address.city,
        'autofill-state': userInfo.address.state,
        'autofill-zip': userInfo.address.zip
    };
    
    for (const id in fields) {
        const element = document.getElementById(id);
        if (element) {
            element.value = fields[id];
        }
    }
}

// Set up the autofill button
function setupAutofillButton() {
    const generateButton = document.getElementById('generate-autofill');
    if (generateButton) {
        generateButton.addEventListener('click', function() {
            const userInfo = updateBookmarkletURL();
            alert('Random identity generated! Drag the bookmarklet to your bookmarks bar.');
        });
    }
}

// Initialize immediately when the script loads
function init() {
    console.log('Autofill script initializing');
    updateBookmarkletURL();
    setupAutofillButton();
}

// Initialize
document.addEventListener('DOMContentLoaded', init);

// Also initialize if DOM is already loaded
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    console.log('DOM already loaded - initializing autofill');
    setTimeout(init, 100);
}

// Force initialization when the autofill settings container becomes visible
const toggleInterval = setInterval(function() {
    const container = document.getElementById('autofill-settings-container');
    if (container && container.classList.contains('visible')) {
        init();
    }
}, 500);

// Call init right away
init();
