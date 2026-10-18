import json
import asyncio
import websockets

CONNECTED_CLIENTS = set()
JSON_FILE = "data_storage.json"

# Synchronous helper function to safely load JSON
def load_log(filename=JSON_FILE):
    log = {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return log

async def handle_client(websocket):
    
    CONNECTED_CLIENTS.add(websocket)
    print("\n[+] Chrome extension connected!")
    try:
        async for message in websocket:
            print(f"\n[Chrome]: {message}\nServer > ", end="")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CONNECTED_CLIENTS.remove(websocket)
        print("\n[-] Chrome extension disconnected.")

async def send_periodically(interval=1):
    """Reads JSON and broadcasts data to connected extensions every `interval` seconds."""
    while True:
        usage_log = load_log()
        payload_data = {
            "total": usage_log.get("total", 0),
            "daily_limit": usage_log.get("dailyGoal", 0)
        }

        payload = json.dumps(payload_data)

        if CONNECTED_CLIENTS:
            websockets.broadcast(CONNECTED_CLIENTS, payload)
            print(f"[+] Broadcasted: {payload}")

        # Wait for 1 second before reading and sending again
        await asyncio.sleep(interval)

async def main():
    async with websockets.serve(handle_client, "127.0.0.1", 5000):
        print("WebSocket server listening on ws://127.0.0.1:5000")
        print("Press Enter in terminal to broadcast JSON variables to connected extensions.\n")
        await send_periodically(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shut down.")