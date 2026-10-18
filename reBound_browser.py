import json
import os
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
STORAGE_FILE = BASE_DIR / 'data_storage.json'
PORT = 8765


def read_storage():
	if STORAGE_FILE.exists():
		try:
			with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
				return json.load(f)
		except Exception:
			pass
	return {
		'Instagram': 28,
		'Tiktok': 5,
		'Tstart': 60.0,
		'Tgoal': 30.0,
		'initial_goal': 30.0,
		'current_scrolling_min': 60.0,
		'nightScrolling': 0.0,
		'craving': 0.0,
		'withdrawal': 0.0,
		'fomo': 0.0,
		'stress': 0.0,
		'psychState': 0.0,
		'timeScrolling': 0.0,
		'dailyGoal': 30.0,
		'timeBetweenLogins': 0.0,
		'Dopamine': 50.0,
		'cleanScore': 1,
		'current_day': 1,
		'sim_minutes': 480,
		'riskScore': 0.0,
		'sigmoidRiskScore': 0.5,
	}


def write_storage(payload):
	data = read_storage()
	if isinstance(payload, dict):
		data.update(payload)
	with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
		json.dump(data, f, indent=4)
	return data


class ReBoundHandler(SimpleHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, directory=str(BASE_DIR), **kwargs)

	def end_headers(self):
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		self.send_header('Access-Control-Allow-Headers', 'Content-Type')
		super().end_headers()

	def do_OPTIONS(self):
		self.send_response(204)
		self.end_headers()

	def do_GET(self):
		if self.path.startswith('/api/data_storage'):
			data = read_storage()
			body = json.dumps(data, indent=4).encode('utf-8')
			self.send_response(200)
			self.send_header('Content-Type', 'application/json')
			self.send_header('Content-Length', str(len(body)))
			self.end_headers()
			self.wfile.write(body)
			return
		super().do_GET()

	def do_POST(self):
		if self.path.startswith('/api/data_storage'):
			length = int(self.headers.get('Content-Length', '0'))
			raw = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
			try:
				payload = json.loads(raw)
			except Exception:
				payload = {}
			updated = write_storage(payload)
			body = json.dumps(updated, indent=4).encode('utf-8')
			self.send_response(200)
			self.send_header('Content-Type', 'application/json')
			self.send_header('Content-Length', str(len(body)))
			self.end_headers()
			self.wfile.write(body)
			return
		self.send_response(404)
		self.end_headers()

	def log_message(self, format, *args):
		pass


def launch_rebound_browser(open_browser=True):
	"""Serve and open the reBound browser application with live data_storage.json syncing."""
	url = f'http://127.0.0.1:{PORT}/reBound_browser.html'
	server = ThreadingHTTPServer(('127.0.0.1', PORT), ReBoundHandler)
	print(f'Launching reBound Browser App at {url} (syncing with {STORAGE_FILE.name})')
	if open_browser:
		webbrowser.open(url)
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		server.server_close()


if __name__ == '__main__':
	launch_rebound_browser(open_browser='--no-browser' not in sys.argv)
