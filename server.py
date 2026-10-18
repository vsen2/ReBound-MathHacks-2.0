import json
import asyncio
import websockets
import os

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

async def send_terminal_input():
    loop = asyncio.get_running_loop()

    while True:
        await loop.run_in_executor(None, input, "Press Enter to send variable > ")

        # Read fresh values from JSON every time you press Enter
        usage_log = load_log()
        total = usage_log.get("total", 0)
        daily_limit = usage_log.get("daily_limit", 0)

        my_variable = {
            "total": total,
            "daily_limit": daily_limit
        }

        payload = json.dumps(my_variable)

        if CONNECTED_CLIENTS:
            websockets.broadcast(CONNECTED_CLIENTS, payload)
            print(f"[+] Sent variable content: {payload}")
        else:
            print("[-] No Chrome extension connected to receive data.")

async def main():
    async with websockets.serve(handle_client, "127.0.0.1", 5000):
        print("WebSocket server listening on ws://127.0.0.1:5000")
        print("Press Enter in terminal to broadcast JSON variables to connected extensions.\n")
        await send_terminal_input()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shut down.")