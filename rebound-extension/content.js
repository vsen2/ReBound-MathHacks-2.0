function showReboundBlocker(domain, timeUsedMinutes, dailyLimitMinutes) {
  // If blocker already exists, just update the text numbers
  const existingOverlay = document.getElementById("rebound-blocker");
  if (existingOverlay) {
    const textElement = document.getElementById("rebound-limit-text");
    if (textElement) {
      textElement.innerHTML = `⏳ Daily Limit Reached: <strong>${timeUsedMinutes}/${dailyLimitMinutes} mins</strong> used.`;
    }
    return;
  }

  const logoUrl = chrome.runtime.getURL("logo.png");

  // Create full-screen overlay container
  const overlay = document.createElement("div");
  overlay.id = "rebound-blocker";
  overlay.style.cssText = `
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    z-index: 2147483647 !important;
    background-color: #0B0F19 !important;
    color: #F8FAFC !important;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 24px !important;
    box-sizing: border-box !important;
  `;

  overlay.innerHTML = `
    <div style="
      background: #1E293B;
      border: 1px solid #334155;
      padding: 40px;
      border-radius: 20px;
      max-width: 480px;
      width: 100%;
      text-align: center;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 20px;
    ">
      <img src="${logoUrl}" alt="Rebound Logo" style="width: 64px; height: 64px; object-fit: contain; border-radius: 12px;" />
      
      <div>
        <h1 style="margin: 0 0 8px 0; font-size: 24px; color: #38BDF8; font-weight: 700;">Rebound</h1>
        <p style="margin: 0; color: #94A3B8; font-size: 14px;">Access to <strong>${domain}</strong> is paused.</p>
      </div>

      <div style="
        background: #0F172A;
        border: 1px solid #334155;
        padding: 16px;
        border-radius: 12px;
        width: 100%;
        box-sizing: border-box;
      ">
        <span id="rebound-limit-text" style="color: #E2E8F0; font-size: 14px; display: block;">
          ⏳ Daily Limit Reached: <strong>${timeUsedMinutes}/${dailyLimitMinutes} mins</strong> used.
        </span>
      </div>

      <div style="display: flex; gap: 12px; width: 100%; margin-top: 10px;">
        <button id="rebound-bypass-btn" style="
          flex: 1;
          background: #334155;
          border: 1px solid #475569;
          color: #E2E8F0;
          padding: 12px;
          border-radius: 10px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 600;
          transition: background 0.2s;
        ">Bypass (10 mins)</button>

        <button id="rebound-leave-btn" style="
          flex: 1;
          background: linear-gradient(135deg, #38BDF8, #34D399);
          border: none;
          color: #0F172A;
          padding: 12px;
          border-radius: 10px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 700;
        ">Take a Break</button>
      </div>
    </div>
  `;

  document.documentElement.appendChild(overlay);

  // Button actions
  document.getElementById("rebound-bypass-btn").addEventListener("click", () => {
    overlay.remove();
    console.log("[Rebound] User bypassed the block for this session.");
  });

  document.getElementById("rebound-leave-btn").addEventListener("click", () => {
    window.location.href = "https://www.google.com";
  });
}

function initReboundBlocker() {
  const hostname = window.location.hostname;
  if (hostname.includes("instagram.com") || hostname.includes("tiktok.com")) {
    
    // Fetch limits from storage first
    chrome.storage.local.get("usageData", (result) => {
      // Default to 0 / 30 if python server hasn't sent data yet
      const timeUsed = result.usageData?.total || 0;
      const dailyLimit = result.usageData?.daily_limit || 30;
      
      showReboundBlocker(hostname, timeUsed, dailyLimit);
    });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initReboundBlocker);
} else {
  initReboundBlocker();
}

// Listen for live updates sent from background.js (via the Python server)
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "UPDATE_UI" && message.data) {
    const hostname = window.location.hostname;
    
    // Updates the blocker live with new variables
    showReboundBlocker(hostname, message.data.total, message.data.daily_limit);
    
    // If you have a popup.html open, update that too
    const totalDisplay = document.getElementById('totalDisplay');
    const limitDisplay = document.getElementById('limitDisplay');
    if (totalDisplay) totalDisplay.textContent = `Total: ${message.data.total}`;
    if (limitDisplay) limitDisplay.textContent = `Limit: ${message.data.daily_limit}`;
  }
});