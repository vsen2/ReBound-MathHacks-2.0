<<<<<<<< HEAD:test_scripts/test_ocial_media_tracker.py
import time
import pygetwindow as gw

# Target platform keywords to track
TARGET_PLATFORMS = ["Instagram", "Tiktok"]
JSON_FILE = "usage_log.json"


def monitor_screen_time(interval=1):
    usage_log = {platform: 0 for platform in TARGET_PLATFORMS}

    while True:
        try:
            active_window = gw.getActiveWindow()
            if active_window and active_window.title:
                window_title = active_window.title.lower()
                
                for platform in TARGET_PLATFORMS:
                    if platform.lower() in window_title:
                        usage_log[platform] += interval
                        print(f"Logged {interval}s on {platform}. Total: {usage_log[platform]}s")
        except Exception:
            # Handle window focus transitions gracefully
            pass
            
        time.sleep(interval)

if __name__ == "__main__":
========
import time
import pygetwindow as gw

# Target platform keywords to track
TARGET_PLATFORMS = ["Instagram", "Tiktok"]

def monitor_screen_time(interval=1):
    usage_log = {platform: 0 for platform in TARGET_PLATFORMS}

    while True:
        try:
            active_window = gw.getActiveWindow()
            if active_window and active_window.title:
                window_title = active_window.title.lower()
                
                for platform in TARGET_PLATFORMS:
                    if platform.lower() in window_title:
                        usage_log[platform] += interval
                        print(f"Logged {interval}s on {platform}. Total: {usage_log[platform]}s")
        except Exception:
            # Handle window focus transitions gracefully
            pass
            
        time.sleep(interval)

if __name__ == "__main__":
>>>>>>>> 6cb7f3342e1f216f452b268841997f2e828f9aa4:social_media_tracker.py
    monitor_screen_time(interval=1)