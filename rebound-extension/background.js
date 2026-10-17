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