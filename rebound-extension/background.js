const MONITORED_DOMAINS = ["tiktok.com", "instagram.com"];

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab && tab.url) {
    const matchedDomain = MONITORED_DOMAINS.find(domain => tab.url.includes(domain));
    
    if (matchedDomain) {
      console.log("[Rebound] Active session detected on " + matchedDomain);
      
      chrome.storage.local.get({ logs: [] }, (data) => {
        const newLog = {
          domain: matchedDomain,
          url: tab.url,
          timestamp: new Date().toISOString()
        };
        const updatedLogs = [...data.logs, newLog];
        chrome.storage.local.set({ logs: updatedLogs });
      });

      chrome.tabs.sendMessage(tabId, {
        type: "REBOUND_SITE_DETECTED",
        domain: matchedDomain
      }).catch(() => {
        // Ignored if content script isn't listening yet
      });
    }
  }
});

// --- 2. WebSocket Server Connection Logic ---
let socket = null;

function connect() {
  socket = new WebSocket('ws://127.0.0.1:5000');

  // Silently catch socket errors to prevent console spam when server is off
  socket.onerror = () => {};
socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      
      // Save usage limits to storage
      chrome.storage.local.set({ usageData: data });

      // 1. Relay to popup (if open)
      chrome.runtime.sendMessage({ type: "UPDATE_UI", data: data }).catch(() => {});
      
      // 2. Relay to active tab so content.js can update the screen live
      chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        if (tabs[0]) {
          chrome.tabs.sendMessage(tabs[0].id, { type: "UPDATE_UI", data: data }).catch(() => {});
        }
      });
    } catch (err) {
      console.error("Error parsing message from Python:", err);
    }
  };

  socket.onclose = () => {
    setTimeout(connect, 3000); // Attempt reconnection every 3 seconds
  };
}

connect();