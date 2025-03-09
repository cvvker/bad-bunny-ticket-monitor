// Background script for Ticketera Autofill extension

// Listen for extension installation or update
chrome.runtime.onInstalled.addListener(function(details) {
    console.log("Ticketera Autofill extension installed or updated:", details.reason);
    
    // Initialize default user info if it's a new installation
    if (details.reason === "install") {
        const defaultUserInfo = {
            firstName: "Juan",
            lastName: "Rodríguez",
            email: "",
            phone: "787-555-1234",
            street: "100 Calle Sol",
            city: "San Juan",
            state: "PR",
            zip: "00901"
        };
        
        const defaultSettings = {
            showNotifications: true
        };
        
        chrome.storage.local.set({ 
            userInfo: defaultUserInfo,
            settings: defaultSettings 
        }, function() {
            console.log("Default user info and settings initialized");
        });
    }
});
