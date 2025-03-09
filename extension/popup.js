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

// Default settings
const defaultSettings = {
    showNotifications: true
};

// Generate random phone number (Puerto Rico format)
function generateRandomPhone() {
    const areaCodes = ["787", "939"];
    const areaCode = areaCodes[Math.floor(Math.random() * areaCodes.length)];
    const middle = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
    const end = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
    return `${areaCode}-${middle}-${end}`;
}

// Generate random user info
function generateRandomUserInfo() {
    const getRandomItem = arr => arr[Math.floor(Math.random() * arr.length)];
    
    return {
        firstName: getRandomItem(sampleData.firstNames),
        lastName: getRandomItem(sampleData.lastNames),
        email: "", // Intentionally left blank for user to fill
        phone: generateRandomPhone(),
        street: `${getRandomItem(sampleData.streetNumbers)} ${getRandomItem(sampleData.streets)}`,
        city: getRandomItem(sampleData.cities),
        state: getRandomItem(sampleData.states),
        zip: getRandomItem(sampleData.zipCodes)
    };
}

// Save user info to Chrome storage
function saveUserInfo(userInfo) {
    chrome.storage.local.set({ userInfo: userInfo }, function() {
        console.log("User info saved to storage:", userInfo);
    });
}

// Save settings to Chrome storage
function saveSettings(settings) {
    chrome.storage.local.set({ settings: settings }, function() {
        console.log("Settings saved to storage:", settings);
    });
}

// Load user info from Chrome storage
function loadUserInfo(callback) {
    chrome.storage.local.get("userInfo", function(result) {
        if (result.userInfo) {
            callback(result.userInfo);
        } else {
            // Generate and save new user info if none exists
            const newUserInfo = generateRandomUserInfo();
            saveUserInfo(newUserInfo);
            callback(newUserInfo);
        }
    });
}

// Load settings from Chrome storage
function loadSettings(callback) {
    chrome.storage.local.get("settings", function(result) {
        if (result.settings) {
            callback(result.settings);
        } else {
            // Use default settings if none exists
            saveSettings(defaultSettings);
            callback(defaultSettings);
        }
    });
}

// Update the UI with user info
function updateUI(userInfo) {
    document.getElementById("firstName").value = userInfo.firstName || "";
    document.getElementById("lastName").value = userInfo.lastName || "";
    document.getElementById("email").value = userInfo.email || "";
    document.getElementById("phone").value = userInfo.phone || "";
    document.getElementById("street").value = userInfo.street || "";
    document.getElementById("city").value = userInfo.city || "";
    document.getElementById("state").value = userInfo.state || "";
    document.getElementById("zip").value = userInfo.zip || "";
}

// Update UI elements based on settings
function updateUIForSettings(settings) {
    document.getElementById("showNotificationsToggle").checked = settings.showNotifications;
}

// Fill the form on the current active tab
function fillForm() {
    // Get the stored user info
    chrome.storage.local.get("userInfo", function(result) {
        if (result.userInfo) {
            // Update with the current email value before filling
            result.userInfo.email = document.getElementById("email").value;
            
            // Save the updated user info
            saveUserInfo(result.userInfo);
            
            // Send message to content script
            chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                if (tabs[0]) {
                    chrome.tabs.sendMessage(tabs[0].id, {
                        action: "fill_form",
                        userInfo: result.userInfo
                    });
                } else {
                    alert("No active tab found. Please make sure you're on a Ticketera checkout page.");
                }
            });
        } else {
            alert("No user information available. Please generate random info first.");
        }
    });
}

// Initialize the popup
document.addEventListener("DOMContentLoaded", function() {
    // Load saved user info
    loadUserInfo(updateUI);
    
    // Load saved settings
    loadSettings(updateUIForSettings);
    
    // Generate new random info button
    document.getElementById("generateBtn").addEventListener("click", function() {
        const userInfo = generateRandomUserInfo();
        // Preserve the email if the user has entered one
        userInfo.email = document.getElementById("email").value;
        saveUserInfo(userInfo);
        updateUI(userInfo);
        
        // Show a notification
        const notification = document.createElement("div");
        notification.textContent = "New random information generated!";
        notification.style.backgroundColor = "#4CAF50";
        notification.style.color = "white";
        notification.style.padding = "10px";
        notification.style.borderRadius = "4px";
        notification.style.position = "fixed";
        notification.style.bottom = "10px";
        notification.style.left = "10px";
        notification.style.right = "10px";
        notification.style.textAlign = "center";
        notification.style.zIndex = "1000";
        document.body.appendChild(notification);
        
        setTimeout(function() {
            notification.style.opacity = "0";
            notification.style.transition = "opacity 0.5s";
            setTimeout(function() {
                notification.remove();
            }, 500);
        }, 2000);
    });
    
    // Fill form button
    document.getElementById("fillBtn").addEventListener("click", function() {
        fillForm();
    });
    
    // Save settings when notification toggle changes
    document.getElementById("showNotificationsToggle").addEventListener("change", function() {
        const settings = {
            showNotifications: this.checked
        };
        saveSettings(settings);
    });
});
