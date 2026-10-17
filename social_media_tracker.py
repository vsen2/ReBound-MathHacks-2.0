import time

import pygetwindow as gw

# Target platform keywords to track
TARGET_PLATFORMS = ["Instagram", "Tiktok"]

def monitor_screen_time(interval=1):
    usage_log = {platform: 0 for platform in TARGET_PLATFORMS}

    while True:
        active_window = gw.getActiveWindow()
        if active_window and active_window.title:
            window_title = active_window.title.lower()

            for platform in TARGET_PLATFORMS:
                if platform.lower() in window_title:
                    usage_log[platform] += interval
                    print(f"Logged {interval}s on {platform}. Total: {usage_log[platform]}s")

        time.sleep(interval)

if __name__ == "__main__":
    monitor_screen_time(interval=1)