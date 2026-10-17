import os
import webbrowser
from pathlib import Path


def launch_rebound_browser():
	"""Open the reBound browser application (reBound_browser.html) in the default web browser."""
	html_path = Path(os.path.dirname(os.path.abspath(__file__))) / 'reBound_browser.html'
	url = html_path.as_uri()
	print(f'Launching reBound Browser App: {url}')
	webbrowser.open(url)


if __name__ == '__main__':
	launch_rebound_browser()

