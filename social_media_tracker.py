import json
import time
import pygetwindow as gw

# Target platform keywords to track
TARGET_PLATFORMS = ["Instagram", "Tiktok"]
JSON_FILE = "data_storage.json"


def load_log(filename=JSON_FILE):
    """Loads existing usage log if available, otherwise initializes zeroed counts."""
    log = {platform: 0 for platform in TARGET_PLATFORMS}
    try:
        with open(filename, "r") as f:
            saved_data = json.load(f)
            log.update(saved_data)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return log


def save_log(data, filename=JSON_FILE):
    """Reads current file contents, updates only the changed keys, and saves back."""
    existing_data = {}
    try:
        with open(filename, "r") as f:
            existing_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Merge new updates into existing JSON data
    existing_data.update(data)

    with open(filename, "w") as f:
        json.dump(existing_data, f, indent=4)


def monitor_screen_time(interval=1):
    usage_log = load_log()

    try:
        while True:
            try:
                active_window = gw.getActiveWindow()

                if active_window and active_window.title:
                    window_title = active_window.title.lower()
                    for platform in TARGET_PLATFORMS:
                        if platform.lower() in window_title:
                            usage_log[platform] = usage_log.get(platform, 0) + interval
                            print(
                                f"Logged {interval}s on {platform}. Total: "
                                f"{usage_log[platform]}s"
                            )

                    # Update total screen time calculated from tracked platforms
                    usage_log["total"] = sum(
                        usage_log.get(p, 0) for p in TARGET_PLATFORMS
                    )

                    save_log(usage_log)

            except Exception:
                # Handle window focus transitions gracefully
                pass

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopping monitor. Final data saved.")
        save_log(usage_log)


if __name__ == "__main__":
    monitor_screen_time(interval=1)