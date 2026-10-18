import json
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from commands import (
	BASE_DIR,
	STORAGE_FILE,
	compute_all_metrics,
	generate_ai_suggestions,
	read_storage,
	write_storage,
)

PORT = 8765


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
	allow_reuse_address = True


class ReBoundHandler(SimpleHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, directory=str(BASE_DIR), **kwargs)

	def end_headers(self):
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		self.send_header('Access-Control-Allow-Headers', 'Content-Type')
		super().end_headers()

	def _send_json(self, data, status=200):
		body = json.dumps(data, indent=4).encode('utf-8')
		self.send_response(status)
		self.send_header('Content-Type', 'application/json')
		self.send_header('Content-Length', str(len(body)))
		self.end_headers()
		self.wfile.write(body)

	def _read_json_body(self):
		length = int(self.headers.get('Content-Length', '0'))
		raw = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
		try:
			return json.loads(raw)
		except Exception:
			return {}

	def do_OPTIONS(self):
		self.send_response(204)
		self.end_headers()

	def do_GET(self):
		if self.path.startswith('/api/data_storage'):
			self._send_json(read_storage())
			return
		if self.path.startswith('/api/calculate'):
			self._send_json(compute_all_metrics())
			return
		if self.path.startswith('/api/ai_suggest'):
			self._send_json(generate_ai_suggestions())
			return
		super().do_GET()

	def do_POST(self):
		if self.path.startswith('/api/data_storage'):
			payload = self._read_json_body()
			updated = write_storage(payload)
			self._send_json(updated)
			return
		if self.path.startswith('/api/calculate'):
			payload = self._read_json_body()
			result = compute_all_metrics(payload)
			self._send_json(result)
			return
		if self.path.startswith('/api/ai_suggest'):
			payload = self._read_json_body()
			result = generate_ai_suggestions(payload)
			self._send_json(result)
			return
		self.send_response(404)
		self.end_headers()

	def log_message(self, format, *args):
		pass


def launch_rebound_browser(open_browser=True):
	"""Serve and open the reBound browser application with live data_storage.json syncing."""
	url = f'http://127.0.0.1:{PORT}/reBound_browser.html'
	server = ReusableThreadingHTTPServer(('127.0.0.1', PORT), ReBoundHandler)
	print(f'Launching reBound Browser App at {url} (syncing with {STORAGE_FILE.name})')
	if open_browser:
		webbrowser.open(url)
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		server.server_close()


if __name__ == '__main__':
	launch_rebound_browser(open_browser='--no-browser' not in sys.argv)
