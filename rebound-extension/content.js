function showReboundBanner(domain) {
  if (document.getElementById("rebound-banner")) return;

  const dailyLimitMinutes = 30;
  const timeUsedMinutes = 15;
  const timeRemaining = Math.max(0, dailyLimitMinutes - timeUsedMinutes);

  // Get the correct local URL for your logo image file inside the extension
  const logoUrl = chrome.runtime.getURL("logo.png");

  const banner = document.createElement("div");
  banner.id = "rebound-banner";
  banner.style.cssText = `
    position: fixed !important;
    top: 20px !important;
    right: 20px !important;
    z-index: 2147483647 !important;
    background-color: #0F172A !important;
    color: #F8FAFC !important;
    padding: 14px 20px !important;
    border-radius: 12px !important;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5) !important;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-size: 14px !important;
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
    border: 1px solid #334155 !important;
    pointer-events: auto !important;
  `;

  banner.innerHTML = `
    <img src="${logoUrl}" alt="Rebound Logo" style="width: 32px; height: 32px; object-fit: contain; border-radius: 6px;" />
    <div style="display: flex; flex-direction: column; gap: 2px;">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-weight: 700; color: #38BDF8; font-size: 15px;">Rebound</span>
        <span style="color: #94A3B8; font-size: 12px;">• ${domain}</span>
      </div>
      <span style="color: #E2E8F0; font-size: 13px;">
        ⏳ <strong>${timeRemaining} mins</strong> remaining of your ${dailyLimitMinutes} min limit.
      </span>
    </div>
    <button id="rebound-close-btn" style="
      background: #334155;
      border: none;
      color: #94A3B8;
      border-radius: 6px;
      padding: 6px 10px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      white-space: nowrap;
    ">Dismiss</button>
  `;

  document.documentElement.appendChild(banner);

  banner.addEventListener("click", (e) => {
    if (e.target && e.target.id === "rebound-close-btn") {
      banner.remove();
    }
  });
}

function initRebound() {
  const hostname = window.location.hostname;
  if (hostname.includes("instagram.com") || hostname.includes("tiktok.com")) {
    showReboundBanner(hostname);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initRebound);
} else {
  initRebound();
}

chrome.runtime.onMessage.addListener((message) => {
  if (message && message.type === "REBOUND_SITE_DETECTED") {
    showReboundBanner(message.domain);
  }
});