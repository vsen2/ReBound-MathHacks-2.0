let trackerInterval = null;
let currentSecondsSpent = 0;
let dailyGoalMinutes = 30;
let requiredClicks = 1;
let currentClicks = 0;

// Array of motivational cards/quotes to break the doomscroll trance during friction
const frictionMessages = [
  {
    type: "quote",
    text: "“You are trading your long-term goals for short-term dopamine hits.”",
    sub: "Every swipe reinforces the loop."
  },
  {
    type: "quote",
    text: "“The master of the scroll is the servant of the feed.”",
    sub: "Take your time back."
  },
  {
    type: "quote",
    text: "“Discipline is choosing between what you want now and what you want most.”",
    sub: "Is this feed what you want most right now?"
  },
  {
    type: "quote",
    text: "“Your brain needs downtime to process and grow, not infinite algorithmic feeds.”",
    sub: "Protect your focus."
  }
];

// 1. Fetch live data from your Python backend / API
async function fetchReboundData() {
  try {
    const response = await fetch("http://127.0.0.1:5000/api/status");
    if (!response.ok) throw new Error("Server offline");
    return await response.json();
  } catch (err) {
    return {
      dailyGoal: 30,
      timeScrolling: 15,
      sigmoidRiskScore: 0.5
    };
  }
}

// 2. Format total seconds into a clean "Xm Ys" format
function formatTime(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins}m ${secs < 10 ? '0' : ''}${secs}s`;
}

// 3. Create or update the persistent top-right live counter banner
function updateTopBanner() {
  let banner = document.getElementById("rebound-top-banner");

  if (!banner) {
    banner = document.createElement("div");
    banner.id = "rebound-top-banner";
    banner.style.cssText = `
      position: fixed !important;
      top: 16px !important;
      right: 16px !important;
      z-index: 2147483646 !important;
      background: #1E293B !important;
      border: 1px solid #334155 !important;
      border-radius: 12px !important;
      padding: 10px 16px !important;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
      font-family: system-ui, -apple-system, sans-serif !important;
      display: flex !important;
      align-items: center !important;
      gap: 10px !important;
      color: #F8FAFC !important;
      font-size: 13px !important;
      font-weight: 600 !important;
      pointer-events: auto !important;
    `;
    document.documentElement.appendChild(banner);
  }

  const logoUrl = chrome.runtime.getURL("logo.png");

  banner.innerHTML = `
    <img src="${logoUrl}" style="width: 22px; height: 22px; object-fit: contain;" />
    <span>Time Spent: <strong style="color: #7DD3FC; font-variant-numeric: tabular-nums;">${formatTime(currentSecondsSpent)}</strong> / <span style="color: #FDE68A;">${dailyGoalMinutes}m limit</span></span>
  `;
}

// 4. Start live 1-second timer ticker
async function startBannerTracking() {
  const initialData = await fetchReboundData();
  currentSecondsSpent = Math.round((initialData.timeScrolling || 0) * 60);
  dailyGoalMinutes = initialData.dailyGoal || 30;

  updateTopBanner();

  if (!trackerInterval) {
    trackerInterval = setInterval(() => {
      currentSecondsSpent += 1;
      updateTopBanner();

      if (currentSecondsSpent % 30 === 0) {
        syncWithPythonServer();
      }
    }, 1000);
  }
}

async function syncWithPythonServer() {
  const latestData = await fetchReboundData();
  if (latestData && latestData.dailyGoal) {
    dailyGoalMinutes = latestData.dailyGoal;
  }
}

// 5. Full-Screen Blocker with Sigmoid-Calculated Friction
async function showReboundBlocker(domain) {
  if (document.getElementById("rebound-blocker")) return;

  const liveData = await fetchReboundData();
  currentSecondsSpent = Math.round((liveData.timeScrolling || 0) * 60);
  dailyGoalMinutes = liveData.dailyGoal || 30;
  
  // Mathematical friction calculation: Probability of relapse * 20 (minimum 1 click)
  const relapseProb = liveData.sigmoidRiskScore || 0.5;
  requiredClicks = Math.max(1, Math.round(relapseProb * 20));
  currentClicks = 0;

  const logoUrl = chrome.runtime.getURL("logo.png");

  const overlay = document.createElement("div");
  overlay.id = "rebound-blocker";
  overlay.style.cssText = `
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    z-index: 2147483647 !important;
    background-color: #0F172A !important;
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
      padding: 36px;
      border-radius: 24px;
      max-width: 480px;
      width: 100%;
      text-align: center;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
    ">
      <img src="${logoUrl}" alt="Rebound Logo" style="width: 72px; height: 72px; object-fit: contain; border-radius: 16px; padding: 4px; background: rgba(125, 211, 252, 0.1);" />
      
      <div>
        <h1 style="margin: 0; font-size: 24px; color: #7DD3FC; font-weight: 700;">Rebound</h1>
        <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 14px;">Access to <strong>${domain}</strong> is paused.</p>
      </div>

      <!-- Motivational Friction Card -->
      <div id="friction-container" style="
        background: #0F172A;
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 14px;
        width: 100%;
        box-sizing: border-box;
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 8px;
      ">
        <p id="friction-text" style="margin: 0; color: #F8FAFC; font-size: 15px; font-weight: 600; line-height: 1.4;">
          “${frictionMessages[0].text}”
        </p>
        <span id="friction-sub" style="color: #94A3B8; font-size: 12px;">
          ${frictionMessages[0].sub}
        </span>
      </div>

      <div style="font-size: 12px; color: #94A3B8;">
        Relapse Risk Factor: <strong style="color: #F87171;">${(relapseProb * 100).toFixed(1)}%</strong> 
        (Requires <span id="click-counter-display" style="color: #FDE68A; font-weight: bold;">${requiredClicks - currentClicks}</span> more confirmations)
      </div>

      <div style="display: flex; gap: 12px; width: 100%;">
        <button id="rebound-sure-btn" style="
          flex: 1;
          background: #334155;
          border: 1px solid #475569;
          color: #E2E8F0;
          padding: 12px;
          border-radius: 12px;
          cursor: pointer;
          font-weight: 600;
          font-size: 14px;
        ">Are you sure?</button>

        <button id="rebound-leave-btn" style="
          flex: 1;
          background: linear-gradient(135deg, #7DD3FC, #A7F3D0);
          border: none;
          color: #0F172A;
          padding: 12px;
          border-radius: 12px;
          cursor: pointer;
          font-weight: 700;
          font-size: 14px;
        ">Take a Break</button>
      </div>
    </div>
  `;

  document.documentElement.appendChild(overlay);

  const sureBtn = document.getElementById("rebound-sure-btn");
  const frictionText = document.getElementById("friction-text");
  const frictionSub = document.getElementById("friction-sub");
  const counterDisplay = document.getElementById("click-counter-display");

  sureBtn.addEventListener("click", () => {
    currentClicks++;
    const remaining = requiredClicks - currentClicks;

    if (remaining > 0) {
      counterDisplay.textContent = remaining;
      const nextMsg = frictionMessages[currentClicks % frictionMessages.length];
      frictionText.textContent = nextMsg.text;
      frictionSub.textContent = nextMsg.sub;
      
      sureBtn.style.transform = "scale(0.96)";
      setTimeout(() => sureBtn.style.transform = "scale(1)", 100);
    } else {
      // Threshold met! Remove overlay and start live counter banner in top right.
      overlay.remove();
      startBannerTracking();
    }
  });

  document.getElementById("rebound-leave-btn").addEventListener("click", () => {
    window.location.href = "https://www.google.com";
  });
}

function initReboundBlocker() {
  const hostname = window.location.hostname;
  if (hostname.includes("instagram.com") || hostname.includes("tiktok.com")) {
    showReboundBlocker(hostname);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initReboundBlocker);
} else {
  initReboundBlocker();
}