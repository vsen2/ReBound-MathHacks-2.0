const MONITORED_DOMAINS = ["tiktok.com", "instagram.com"];

// --- 1. Tab Monitoring & Logging ---
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab && tab.url) {
    const matchedDomain = MONITORED_DOMAINS.find((domain) =>
      tab.url.includes(domain)
    );

    if (matchedDomain) {
      console.log("[Rebound] Active session detected on " + matchedDomain);

      // Log session activity in local storage
      chrome.storage.local.get({ logs: [] }, (data) => {
        const newLog = {
          domain: matchedDomain,
          url: tab.url,
          timestamp: new Date().toISOString()
        };
        const updatedLogs = [...data.logs, newLog];
        chrome.storage.local.set({ logs: updatedLogs });
      });

      // Send site detection alert to tab content script
      chrome.tabs
        .sendMessage(tabId, {
          type: "REBOUND_SITE_DETECTED",
          domain: matchedDomain
        })
        .catch(() => {
          // Ignored if content script isn't ready or listening
        });
    }
  }
});

// --- 2. WebSocket Connection Logic ---
let socket = null;

function connect() {
  socket = new WebSocket("ws://127.0.0.1:5000");

  socket.onopen = () => {
    console.log("[Rebound Background] Connected to WebSocket server.");
  };

  // Prevent console errors when server is offline
  socket.onerror = () => {};

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      // Store latest Python data locally
      chrome.storage.local.set({ usageData: data });

      // Relay data to extension popup (if open)
      chrome.runtime
        .sendMessage({ type: "UPDATE_UI", data: data })
        .catch(() => {
          // Popup is closed, safe to ignore
        });

      // Relay data to the currently active tab
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]?.id) {
          chrome.tabs
            .sendMessage(tabs[0].id, { type: "UPDATE_UI", data: data })
            .catch(() => {
              // Content script not listening on this tab, safe to ignore
            });
        }
      });
    } catch (err) {
      console.error("[Rebound Background] Error parsing message from Python:", err);
    }
  };

  socket.onclose = () => {
    // Attempt reconnection every 3 seconds
    setTimeout(connect, 3000);
  };
}

connect();