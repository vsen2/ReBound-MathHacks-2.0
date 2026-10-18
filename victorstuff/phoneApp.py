import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Ensure root directory is on sys.path so commands.py is imported directly
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

from commands import (
	NIGHT_SCROLL_MINUTES,
	SCROLL_MINUTES,
	DOPAMINE_ITEMS,
	MAX_DAILY_MINS,
	ReBoundState,
	calc_daily_goal,
	calc_psych_state,
	format_sim_time,
	generate_ai_suggestions,
	get_daily_goal_curve,
	get_sigmoid_curve,
)

# Shared calculation/state model from commands.py
state = ReBoundState()
popup_open = False
sim_paused = False
app_running = True
current_screen_name = 'home'
reel_counter = 1
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.png')
if not os.path.exists(LOGO_PATH):
	LOGO_PATH = os.path.join(ROOT_DIR, 'ReadMe', 'logo.png')


def load_logo_photo(target_size=72):
	"""Load and resize logo.png to target_size x target_size for Tkinter."""
	if not os.path.exists(LOGO_PATH):
		return None
	try:
		from PIL import Image, ImageTk
		img = Image.open(LOGO_PATH).convert('RGBA')
		resample = getattr(Image, 'Resampling', Image).LANCZOS
		img = img.resize((target_size, target_size), resample)
		return ImageTk.PhotoImage(img)
	except Exception:
		try:
			raw = tk.PhotoImage(file=LOGO_PATH)
			sx = max(1, round(raw.width() / target_size))
			sy = max(1, round(raw.height() / target_size))
			return raw.subsample(sx, sy)
		except Exception:
			return None


def safe_set_item_fill(cv, item, fill_color):
	try:
		if cv.winfo_exists():
			cv.itemconfig(item, fill=fill_color)
	except tk.TclError:
		pass


# --- UI Helper: Rounded Rectangle on Canvas ---
def draw_rounded_rect(canvas, x1, y1, x2, y2, r=18, **kwargs):
	points = [
		x1 + r, y1,
		x2 - r, y1,
		x2, y1,
		x2, y1 + r,
		x2, y2 - r,
		x2, y2,
		x2 - r, y2,
		x1 + r, y2,
		x1, y2,
		x1, y2 - r,
		x1, y1 + r,
		x1, y1,
	]
	return canvas.create_polygon(points, smooth=True, **kwargs)


def make_pill_button(
	parent,
	text,
	command,
	width=150,
	height=38,
	bg_parent='#eaf3f5',
	fill='#6c9ae2',
	hover_fill='#5c8bd8',
	fg='#214d5b',
	font=('Segoe UI', 10, 'bold'),
	radius=18,
):
	cv = tk.Canvas(
		parent, width=width, height=height, bg=bg_parent, highlightthickness=0, cursor='hand2'
	)
	shape = draw_rounded_rect(cv, 2, 2, width - 2, height - 2, r=radius, fill=fill, outline='')
	cv.create_text(width // 2, height // 2, text=text, fill=fg, font=font)
	cv.bind('<Enter>', lambda e: safe_set_item_fill(cv, shape, hover_fill))
	cv.bind('<Leave>', lambda e: safe_set_item_fill(cv, shape, fill))
	cv.bind('<ButtonRelease-1>', lambda e: command())
	return cv


# --- Main Phone Simulator Window ---
root = tk.Tk()
root.title('reBound')
root.geometry('430x790')
root.resizable(False, False)
root.configure(bg='#d1e0e6')

window_logo_img = load_logo_photo(64)
if window_logo_img is not None:
	root.iconphoto(True, window_logo_img)


def on_app_close():
	global app_running, popup_open
	app_running = False
	popup_open = False
	try:
		root.quit()
		root.destroy()
	except tk.TclError:
		pass


root.protocol('WM_DELETE_WINDOW', on_app_close)

chassis_canvas = tk.Canvas(root, width=430, height=790, bg='#d1e0e6', highlightthickness=0)
chassis_canvas.place(x=0, y=0)
draw_rounded_rect(
	chassis_canvas, 14, 24, 416, 766, r=44, fill='#bdd0d8', outline='#e2edf1', width=2
)
draw_rounded_rect(chassis_canvas, 20, 30, 410, 760, r=40, fill='#e1edf1', outline='')

screen_frame = tk.Frame(root, bg='#eaf3f5')
screen_frame.place(x=28, y=42, width=374, height=706)

# Top status bar
status_bar = tk.Frame(screen_frame, bg='#e1edf1', height=36)
status_bar.pack(fill='x', side='top')
status_bar.pack_propagate(False)

clock_status_lbl = tk.Label(
	status_bar, text='8:00 AM', fg='#214d5b', bg='#e1edf1', font=('Segoe UI', 9, 'bold')
)
clock_status_lbl.pack(side='left', padx=14)

island_cv = tk.Canvas(status_bar, width=104, height=22, bg='#e1edf1', highlightthickness=0)
draw_rounded_rect(island_cv, 2, 3, 102, 19, r=9, fill='#000000', outline='#f7fbfc')
island_cv.place(relx=0.5, rely=0.5, anchor='center')

day_status_lbl = tk.Label(
	status_bar, text='Day 1 • 5G', fg='#607b85', bg='#e1edf1', font=('Segoe UI', 8, 'bold')
)
day_status_lbl.pack(side='right', padx=14)

# Main content area & bottom bar
content_area = tk.Frame(screen_frame, bg='#eaf3f5')
content_area.pack(fill='both', expand=True)

nav_bar = tk.Frame(screen_frame, bg='#e1edf1', height=50)
nav_bar.pack(fill='x', side='bottom')
nav_bar.pack_propagate(False)

home_screen = tk.Frame(content_area, bg='#eaf3f5')
unscroll_screen = tk.Frame(content_area, bg='#eaf3f5')
instagram_screen = tk.Frame(content_area, bg='#121212')


def show_screen(target, name='home'):
	global current_screen_name
	current_screen_name = name
	for frame in (home_screen, unscroll_screen, instagram_screen):
		frame.pack_forget()
	target.pack(fill='both', expand=True)
	refresh_ui()


nav_btn_holder = tk.Frame(nav_bar, bg='#e1edf1')
nav_btn_holder.pack(pady=9)

home_pill = make_pill_button(
	nav_btn_holder,
	text='●  Home',
	command=lambda: show_screen(home_screen, 'home'),
	width=120,
	height=32,
	bg_parent='#e1edf1',
	fill='#f7fbfc',
	hover_fill='#cbdde3',
	fg='#214d5b',
	font=('Segoe UI', 9, 'bold'),
	radius=16,
)
home_pill.pack(side='left', padx=6)

pause_cv = tk.Canvas(
	nav_btn_holder, width=130, height=32, bg='#e1edf1', highlightthickness=0, cursor='hand2'
)
pause_shape = draw_rounded_rect(pause_cv, 2, 2, 128, 30, r=16, fill='#dce9fa', outline='')
pause_text_item = pause_cv.create_text(
	65, 16, text='⏸  Stop Time', fill='#214d5b', font=('Segoe UI', 9, 'bold')
)
pause_cv.pack(side='left', padx=6)


def toggle_sim_pause(_=None):
	global sim_paused
	sim_paused = not sim_paused
	if sim_paused:
		pause_cv.itemconfig(pause_shape, fill='#dcefe7')
		pause_cv.itemconfig(pause_text_item, text='▶  Start Time', fill='#214d5b')
		sim_speed_lbl.config(text='⏸ Paused', fg='#d79c58')
	else:
		pause_cv.itemconfig(pause_shape, fill='#dce9fa')
		pause_cv.itemconfig(pause_text_item, text='⏸  Stop Time', fill='#214d5b')
		sim_speed_lbl.config(text='⏱ 1 hr/s', fg='#528bdc')


pause_cv.bind('<ButtonRelease-1>', toggle_sim_pause)


# =====================================================================
# 1. HOME SCREEN (Widget + Next Day + Gemini AI Coach + App Icons)
# =====================================================================
header_row = tk.Frame(home_screen, bg='#eaf3f5')
header_row.pack(fill='x', padx=20, pady=(10, 4))
home_header_logo = load_logo_photo(28)
if home_header_logo is not None:
	home_logo_lbl = tk.Label(header_row, image=home_header_logo, bg='#eaf3f5')
	home_logo_lbl.image = home_header_logo
	home_logo_lbl.pack(side='left', padx=(0, 8))
tk.Label(
	header_row, text='reBound', font=('Segoe UI', 15, 'bold'), fg='#214d5b', bg='#eaf3f5'
).pack(side='left')

sim_speed_lbl = tk.Label(
	header_row,
	text='⏱ 1 hr/s',
	font=('Segoe UI', 8, 'bold'),
	fg='#528bdc',
	bg='#eaf3f5',
	cursor='hand2',
)
sim_speed_lbl.pack(side='right', pady=4)
sim_speed_lbl.bind('<ButtonRelease-1>', toggle_sim_pause)

widget_cv = tk.Canvas(
	home_screen, width=338, height=175, bg='#eaf3f5', highlightthickness=0, cursor='hand2'
)
widget_cv.pack(padx=18, pady=4)

draw_rounded_rect(widget_cv, 2, 2, 336, 173, r=24, fill='#f7fbfc', outline='#cbdde3', width=1.5)
widget_cv.create_line(26, 5, 312, 5, fill='#ffffff', width=1)
widget_cv.create_text(
	20, 22, text='REBOUND WIDGET', anchor='w', fill='#528bdc', font=('Segoe UI', 9, 'bold')
)
widget_risk_item = widget_cv.create_text(
	318, 22, text='Risk: 0.0%', anchor='e', fill='#c95353', font=('Segoe UI', 9, 'bold')
)
widget_clean_item = widget_cv.create_text(
	20, 56, text='Clean Streak: 1 🔥', anchor='w', fill='#5d9c86', font=('Segoe UI', 17, 'bold')
)
widget_status_item = widget_cv.create_text(
	20, 84,
	text='Clean from doomscrolling — keep it up!',
	anchor='w',
	fill='#4d6e7d',
	font=('Segoe UI', 8),
)
widget_scrolled_item = widget_cv.create_text(
	20, 118, text='Scrolled: 0 min', anchor='w', fill='#214d5b', font=('Segoe UI', 9, 'bold')
)
widget_limit_item = widget_cv.create_text(
	318, 118, text='Limit: 30 min', anchor='e', fill='#607b85', font=('Segoe UI', 9, 'bold')
)

draw_rounded_rect(widget_cv, 20, 138, 318, 152, r=7, fill='#eaf3f5', outline='')
widget_prog_fill = draw_rounded_rect(
	widget_cv, 20, 138, 28, 152, r=7, fill='#528bdc', outline=''
)
widget_cv.bind('<ButtonRelease-1>', lambda e: show_screen(unscroll_screen, 'rebound'))


def trigger_new_day():
	state.advance_to_next_day()
	sync_entries_from_state()
	refresh_ui()
	open_new_day_popup()


next_day_pill = make_pill_button(
	home_screen,
	text='☀️  Next Day (New Day Survey)',
	command=trigger_new_day,
	width=338,
	height=38,
	bg_parent='#eaf3f5',
	fill='#dcefe7',
	hover_fill='#c6e5d8',
	fg='#214d5b',
	font=('Segoe UI', 10, 'bold'),
	radius=19,
)
next_day_pill.pack(padx=18, pady=(6, 4))

# Home Screen Gemini-Powered Habit & Relapse Prevention Preview Card
home_ai_card = tk.Frame(home_screen, bg='#f7fbfc', padx=12, pady=8, highlightthickness=1, highlightbackground='#cbdde3')
home_ai_card.pack(fill='x', padx=18, pady=6)

home_ai_top = tk.Frame(home_ai_card, bg='#f7fbfc')
home_ai_top.pack(fill='x')
tk.Label(
	home_ai_top,
	text='✨ GEMINI HABIT & RELAPSE SUGGESTIONS',
	font=('Segoe UI', 8, 'bold'),
	fg='#528bdc',
	bg='#f7fbfc',
).pack(side='left')

home_ai_lbl = tk.Label(
	home_ai_card,
	text='Tap "✨ Refresh AI" in reBound or complete a survey for live Gemini coaching.',
	font=('Segoe UI', 8),
	fg='#355762',
	bg='#f7fbfc',
	justify='left',
	anchor='w',
	wraplength=310,
)
home_ai_lbl.pack(fill='x', pady=(4, 0))

tk.Label(
	home_screen, text='Apps', font=('Segoe UI', 10, 'bold'), fg='#607b85', bg='#eaf3f5'
).pack(anchor='w', padx=22, pady=(8, 4))

apps_grid = tk.Frame(home_screen, bg='#eaf3f5')
apps_grid.pack(fill='x', padx=22)


def make_app_icon(parent, icon_char, title, bg_color, hover_color, command, photo_image=None):
	holder = tk.Frame(parent, bg='#eaf3f5')
	cv = tk.Canvas(holder, width=84, height=84, bg='#eaf3f5', highlightthickness=0, cursor='hand2')
	bg_rect = draw_rounded_rect(cv, 4, 4, 80, 80, r=22, fill=bg_color, outline='#cbdde3', width=1)
	if photo_image is not None:
		cv.image = photo_image
		cv.create_image(42, 42, image=photo_image)
	else:
		cv.create_text(42, 42, text=icon_char, font=('Segoe UI Emoji', 26), fill='#214d5b')
	cv.pack()
	tk.Label(holder, text=title, font=('Segoe UI', 9, 'bold'), fg='#355762', bg='#eaf3f5').pack(
		pady=(5, 0)
	)
	cv.bind('<Enter>', lambda e: safe_set_item_fill(cv, bg_rect, hover_color))
	cv.bind('<Leave>', lambda e: safe_set_item_fill(cv, bg_rect, bg_color))
	cv.bind('<ButtonRelease-1>', lambda e: command())
	return holder


def open_instagram_app():
	state.record_instagram_scroll(SCROLL_MINUTES, is_night=(state.sim_minutes % 1440) >= 20 * 60)
	sync_entries_from_state()
	show_screen(instagram_screen, 'instagram')


unscroll_logo_img = load_logo_photo(72)
unscroll_icon = make_app_icon(
	apps_grid,
	'📈',
	'reBound',
	'#ffffff',
	'#355762',
	lambda: show_screen(unscroll_screen, 'rebound'),
	photo_image=unscroll_logo_img,
)
unscroll_icon.grid(row=0, column=0, padx=16, pady=4)

insta_icon = make_app_icon(apps_grid, '📸', 'Instagram', '#db2777', '#be185d', open_instagram_app)
insta_icon.grid(row=0, column=1, padx=16, pady=4)


# =====================================================================
# 2. REBOUND APP SCREEN (Tabs: Results & AI, Risk Sigmoid, Daily Goal)
# =====================================================================
unscroll_header = tk.Frame(unscroll_screen, bg='#eaf3f5', pady=6)
unscroll_header.pack(fill='x', padx=12)

unscroll_header_logo = load_logo_photo(26)
if unscroll_header_logo is not None:
	header_logo_lbl = tk.Label(unscroll_header, image=unscroll_header_logo, bg='#eaf3f5')
	header_logo_lbl.image = unscroll_header_logo
	header_logo_lbl.pack(side='left', padx=(0, 6))

tk.Label(
	unscroll_header, text='reBound Analytics', font=('Segoe UI', 12, 'bold'), fg='#214d5b', bg='#eaf3f5'
).pack(side='left')

new_day_top_pill = make_pill_button(
	unscroll_header,
	text='☀️ New Day',
	command=trigger_new_day,
	width=96,
	height=28,
	bg_parent='#eaf3f5',
	fill='#528bdc',
	hover_fill='#528bdc',
	fg='#214d5b',
	font=('Segoe UI', 8, 'bold'),
	radius=14,
)
new_day_top_pill.pack(side='right')

# 3-Tab Switcher Bar inside reBound App: Results & AI | Risk Graph | Goal Graph
tab_bar = tk.Frame(unscroll_screen, bg='#eaf3f5')
tab_bar.pack(fill='x', padx=12, pady=(2, 4))

results_tab_frame = tk.Frame(unscroll_screen, bg='#eaf3f5')
risk_tab_frame = tk.Frame(unscroll_screen, bg='#eaf3f5')
goal_tab_frame = tk.Frame(unscroll_screen, bg='#eaf3f5')

tab_results_cv = tk.Canvas(tab_bar, width=112, height=30, bg='#eaf3f5', highlightthickness=0, cursor='hand2')
tab_results_shape = draw_rounded_rect(tab_results_cv, 2, 2, 110, 28, r=13, fill='#dce9fa', outline='')
tab_results_txt = tab_results_cv.create_text(56, 15, text='✨ Results & AI', fill='#214d5b', font=('Segoe UI', 8, 'bold'))
tab_results_cv.pack(side='left', padx=(0, 4))

tab_risk_cv = tk.Canvas(tab_bar, width=112, height=30, bg='#eaf3f5', highlightthickness=0, cursor='hand2')
tab_risk_shape = draw_rounded_rect(tab_risk_cv, 2, 2, 110, 28, r=13, fill='#f7fbfc', outline='')
tab_risk_txt = tab_risk_cv.create_text(56, 15, text='📈 Risk Graph', fill='#607b85', font=('Segoe UI', 8, 'bold'))
tab_risk_cv.pack(side='left', padx=2)

tab_goal_cv = tk.Canvas(tab_bar, width=112, height=30, bg='#eaf3f5', highlightthickness=0, cursor='hand2')
tab_goal_shape = draw_rounded_rect(tab_goal_cv, 2, 2, 110, 28, r=13, fill='#f7fbfc', outline='')
tab_goal_txt = tab_goal_cv.create_text(56, 15, text='🎯 Goal Graph', fill='#607b85', font=('Segoe UI', 8, 'bold'))
tab_goal_cv.pack(side='left', padx=(4, 0))


def switch_unscroll_tab(tab_name):
	for f in (results_tab_frame, risk_tab_frame, goal_tab_frame):
		f.pack_forget()

	tab_results_cv.itemconfig(tab_results_shape, fill='#f7fbfc')
	tab_results_cv.itemconfig(tab_results_txt, fill='#607b85')
	tab_risk_cv.itemconfig(tab_risk_shape, fill='#f7fbfc')
	tab_risk_cv.itemconfig(tab_risk_txt, fill='#607b85')
	tab_goal_cv.itemconfig(tab_goal_shape, fill='#f7fbfc')
	tab_goal_cv.itemconfig(tab_goal_txt, fill='#607b85')

	if tab_name == 'results':
		results_tab_frame.pack(fill='both', expand=True)
		tab_results_cv.itemconfig(tab_results_shape, fill='#dce9fa')
		tab_results_cv.itemconfig(tab_results_txt, fill='#214d5b')
	elif tab_name == 'risk':
		risk_tab_frame.pack(fill='both', expand=True)
		tab_risk_cv.itemconfig(tab_risk_shape, fill='#dce9fa')
		tab_risk_cv.itemconfig(tab_risk_txt, fill='#214d5b')
	else:
		goal_tab_frame.pack(fill='both', expand=True)
		tab_goal_cv.itemconfig(tab_goal_shape, fill='#dcefe7')
		tab_goal_cv.itemconfig(tab_goal_txt, fill='#214d5b')
	refresh_ui()


tab_results_cv.bind('<ButtonRelease-1>', lambda e: switch_unscroll_tab('results'))
tab_risk_cv.bind('<ButtonRelease-1>', lambda e: switch_unscroll_tab('risk'))
tab_goal_cv.bind('<ButtonRelease-1>', lambda e: switch_unscroll_tab('goal'))

# --- TAB 0: CURRENT RESULTS & GEMINI AI HABIT COACH ---
results_card = tk.Frame(results_tab_frame, bg='#f7fbfc', padx=14, pady=10, highlightthickness=1, highlightbackground='#cbdde3')
results_card.pack(fill='x', padx=12, pady=(4, 6))

tk.Label(
	results_card, text='Current Results', font=('Segoe UI', 10, 'bold'), fg='#214d5b', bg='#f7fbfc'
).pack(anchor='w', pady=(0, 6))

metrics_row = tk.Frame(results_card, bg='#f7fbfc')
metrics_row.pack(fill='x')

limit_box = tk.Frame(metrics_row, bg='#eaf3f5', padx=10, pady=8, highlightthickness=1, highlightbackground='#cbdde3')
limit_box.pack(side='left', fill='both', expand=True, padx=(0, 4))
tk.Label(limit_box, text="TODAY'S DAILY LIMIT", font=('Segoe UI', 7, 'bold'), fg='#607b85', bg='#eaf3f5').pack(anchor='w')
results_daily_limit_lbl = tk.Label(limit_box, text='30.0 min', font=('Segoe UI', 15, 'bold'), fg='#5d9c86', bg='#eaf3f5')
results_daily_limit_lbl.pack(anchor='w', pady=(2, 0))

relapse_box = tk.Frame(metrics_row, bg='#eaf3f5', padx=10, pady=8, highlightthickness=1, highlightbackground='#cbdde3')
relapse_box.pack(side='left', fill='both', expand=True, padx=(4, 0))
tk.Label(relapse_box, text='RELAPSE PROBABILITY', font=('Segoe UI', 7, 'bold'), fg='#607b85', bg='#eaf3f5').pack(anchor='w')
results_relapse_lbl = tk.Label(relapse_box, text='50.0%', font=('Segoe UI', 15, 'bold'), fg='#528bdc', bg='#eaf3f5')
results_relapse_lbl.pack(anchor='w', pady=(2, 0))

# Gemini AI Coach Card inside Results Tab
ai_coach_card = tk.Frame(results_tab_frame, bg='#f7fbfc', padx=14, pady=10, highlightthickness=1, highlightbackground='#cbdde3')
ai_coach_card.pack(fill='both', expand=True, padx=12, pady=(2, 6))

ai_header_row = tk.Frame(ai_coach_card, bg='#f7fbfc')
ai_header_row.pack(fill='x', pady=(0, 6))

tk.Label(
	ai_header_row,
	text='✨ GEMINI HABIT & RELAPSE SUGGESTIONS',
	font=('Segoe UI', 8, 'bold'),
	fg='#528bdc',
	bg='#f7fbfc',
).pack(side='left')


def request_ai_suggestions():
	if not app_running:
		return
	ai_output_lbl.config(text='✨ Analyzing your reBound metrics with Gemini AI...')
	home_ai_lbl.config(text='✨ Analyzing your reBound metrics with Gemini AI...')

	snapshot = state.to_dict()

	def worker():
		res = generate_ai_suggestions(snapshot)
		text = res.get('suggestions', '')
		if app_running:
			try:
				root.after(0, lambda: _apply_ai_text(text))
			except Exception:
				pass

	threading.Thread(target=worker, daemon=True).start()


def _apply_ai_text(text):
	if not app_running:
		return
	try:
		ai_output_lbl.config(text=text)
		first_line = text.splitlines()[0] if text else ''
		home_ai_lbl.config(text=first_line)
	except tk.TclError:
		pass


make_pill_button(
	ai_header_row,
	text='✨ Refresh AI',
	command=request_ai_suggestions,
	width=92,
	height=24,
	bg_parent='#f7fbfc',
	fill='#dcefe7',
	hover_fill='#c6e5d8',
	fg='#214d5b',
	font=('Segoe UI', 8, 'bold'),
	radius=12,
).pack(side='right')

ai_output_holder = tk.Frame(ai_coach_card, bg='#eaf3f5', padx=10, pady=8, highlightthickness=1, highlightbackground='#cbdde3')
ai_output_holder.pack(fill='both', expand=True)

ai_output_lbl = tk.Label(
	ai_output_holder,
	text='Click "✨ Refresh AI" for personalized habit and relapse-prevention advice powered by commands.py.',
	font=('Segoe UI', 9),
	fg='#355762',
	bg='#eaf3f5',
	justify='left',
	anchor='nw',
	wraplength=296,
)
ai_output_lbl.pack(fill='both', expand=True)

results_btn_row = tk.Frame(ai_coach_card, bg='#f7fbfc')
results_btn_row.pack(fill='x', pady=(8, 0))

make_pill_button(
	results_btn_row,
	text='Beginning Survey',
	command=lambda: open_starting_survey(),
	width=145,
	height=28,
	bg_parent='#f7fbfc',
	fill='#e2edf1',
	hover_fill='#cbdde3',
	fg='#214d5b',
	font=('Segoe UI', 8, 'bold'),
	radius=14,
).pack(side='left', padx=(0, 6))

make_pill_button(
	results_btn_row,
	text='📊 View Graphs',
	command=lambda: switch_unscroll_tab('risk'),
	width=145,
	height=28,
	bg_parent='#f7fbfc',
	fill='#dce9fa',
	hover_fill='#c7ddf6',
	fg='#214d5b',
	font=('Segoe UI', 8, 'bold'),
	radius=14,
).pack(side='right')


# --- TAB 1: RISK SIGMOID + VARIABLES ---
fig = Figure(figsize=(3.5, 2.2), dpi=100, facecolor='#f7fbfc')
fig.subplots_adjust(left=0.16, right=0.95, top=0.85, bottom=0.20)
ax = fig.add_subplot(111)
ax.set_facecolor('#eaf3f5')

x_vals, y_vals, _ = get_sigmoid_curve(state.riskScore)
line_curve, = ax.plot(x_vals, y_vals, label='Sigmoid', color='#528bdc', linewidth=2.2)
point_risk, = ax.plot(
	[state.riskScore],
	[state.sigmoidRiskScore],
	marker='o',
	markersize=7,
	color='#6c9ae2',
	markeredgecolor='none',
	linestyle='None',
	zorder=5,
	label=f'Risk: {state.sigmoidRiskScore:.1%}',
)

ax.set_title('reBound — Doomscrolling Risk', fontsize=9.5, fontweight='bold', color='#214d5b')
ax.set_xlabel('Risk Score', fontsize=8, color='#4d6e7d')
ax.set_ylabel('Relapse Probability', fontsize=8, color='#4d6e7d')
ax.tick_params(colors='#607b85', labelsize=7.5)
for spine in ax.spines.values():
	spine.set_color('#cbdde3')
ax.grid(True, linestyle='--', alpha=0.3, color='#718790')
ax.legend(loc='upper left', fontsize=7.5, facecolor='#f7fbfc', edgecolor='#cbdde3', labelcolor='#214d5b')

canvas = FigureCanvasTkAgg(fig, master=risk_tab_frame)
canvas.get_tk_widget().pack(fill='x', padx=12, pady=(2, 4))

unscroll_clean_lbl = tk.Label(
	risk_tab_frame,
	text='Clean Streak: 1  •  Risk: 0.0%',
	font=('Segoe UI', 9, 'bold'),
	bg='#f7fbfc',
	fg='#528bdc',
	pady=4,
)
unscroll_clean_lbl.pack(fill='x', padx=12, pady=2)

inputs_panel = tk.Frame(
	risk_tab_frame,
	bg='#f7fbfc',
	padx=14,
	pady=6,
	highlightthickness=1,
	highlightbackground='#cbdde3',
)
inputs_panel.pack(fill='both', expand=True, padx=12, pady=(2, 6))

tk.Label(
	inputs_panel, text='Current Risk Score Factors', font=('Segoe UI', 10, 'bold'), bg='#f7fbfc', fg='#214d5b'
).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 3))

risk_field_defs = [
	('nightScrolling', 'Night Scrolling (min)', f'{state.nightScrolling:g}'),
	('psychState', 'Stress / Psych Level (0-1)', f'{state.psychState:g}'),
	('timeScrolling', 'Total Scrolling Today (min)', f'{state.timeScrolling:g}'),
	('dailyGoal', 'Daily Limit (min)', f'{state.dailyGoal:.1f}'),
	('timeBetweenLogins', 'Time Between Logins (min)', f'{state.timeBetweenLogins:g}'),
	('Dopamine', 'Healthy Dopamine (%)', f'{state.Dopamine:.0f}%'),
]

var_entries = {}
for idx, (key, label_text, default_v) in enumerate(risk_field_defs, start=1):
	tk.Label(
		inputs_panel, text=label_text, font=('Segoe UI', 9), bg='#f7fbfc', fg='#4d6e7d'
	).grid(row=idx, column=0, sticky='w', pady=2)
	ent = tk.Entry(
		inputs_panel,
		width=13,
		font=('Segoe UI', 9, 'bold'),
		bg='#eaf3f5',
		readonlybackground='#eaf3f5',
		fg='#214d5b',
		relief='flat',
		highlightthickness=1,
		highlightbackground='#cbdde3',
		highlightcolor='#cbdde3',
		justify='right',
	)
	ent.grid(row=idx, column=1, sticky='e', padx=(8, 0), pady=2, ipady=2)
	ent.insert(0, default_v)
	ent.config(state='readonly')
	var_entries[key] = ent

inputs_panel.columnconfigure(0, weight=1)

goal_entries = {}


def set_readonly_entry_value(entry, value):
	entry.config(state='normal')
	entry.delete(0, tk.END)
	entry.insert(0, value)
	entry.config(state='readonly')


def sync_risk_entries_from_state():
	values_map = {
		'nightScrolling': f'{state.nightScrolling:g}',
		'psychState': f'{state.psychState:.3f}'.rstrip('0').rstrip('.') if state.psychState else '0',
		'timeScrolling': f'{state.timeScrolling:g}',
		'dailyGoal': f'{state.dailyGoal:.1f}',
		'timeBetweenLogins': f'{state.timeBetweenLogins:g}',
		'Dopamine': f'{state.Dopamine:.0f}%',
	}
	for k, val in values_map.items():
		set_readonly_entry_value(var_entries[k], val)


def sync_entries_from_state():
	sync_risk_entries_from_state()
	if goal_entries:
		goal_values_map = {
			'day': f'{state.current_day:g}',
			'Tstart': f'{state.Tstart:g}',
			'Tgoal': f'{state.Tgoal:g}',
			'timeBetweenLogins': f'{state.timeBetweenLogins:g}',
			'relapseProbability': f'{state.sigmoidRiskScore:.3f}',
		}
		for k, val in goal_values_map.items():
			goal_entries[k].delete(0, tk.END)
			goal_entries[k].insert(0, val)
btn_row = tk.Frame(inputs_panel, bg='#f7fbfc')
btn_row.grid(row=len(risk_field_defs) + 1, column=0, columnspan=2, pady=(4, 2))

make_pill_button(
	btn_row,
	text='Beginning Survey',
	command=lambda: open_starting_survey(),
	width=130,
	height=30,
	bg_parent='#f7fbfc',
	fill='#e2edf1',
	hover_fill='#cbdde3',
	fg='#214d5b',
	font=('Segoe UI', 9),
	radius=15,
).pack(side='left', padx=6)


# --- TAB 2: DAILY GOAL DECAY CHART & PARAMETERS ---
fig_goal = Figure(figsize=(3.5, 2.2), dpi=100, facecolor='#f7fbfc')
fig_goal.subplots_adjust(left=0.17, right=0.95, top=0.85, bottom=0.20)
ax_goal = fig_goal.add_subplot(111)
ax_goal.set_facecolor('#eaf3f5')

days_arr, goals_arr, _ = get_daily_goal_curve(
	state.Tstart,
	state.Tgoal,
	state.current_day,
	state.timeBetweenLogins,
	state.sigmoidRiskScore,
)
line_goal_curve, = ax_goal.plot(
	days_arr, goals_arr, label='Daily Goal Curve', color='#5d9c86', linewidth=2.4
)
line_target_goal = ax_goal.axhline(
	state.Tgoal, color='#528bdc', linestyle='--', linewidth=1.3, label=f'Target: {state.Tgoal:.0f}m'
)
point_today_goal, = ax_goal.plot(
	[state.current_day],
	[state.dailyGoal],
	marker='o',
	markersize=7,
	color='#6c9ae2',
	markeredgecolor='none',
	linestyle='None',
	zorder=5,
	label=f'Day {state.current_day}: {state.dailyGoal:.1f}m',
)

ax_goal.set_title('reBound — Daily Goal Progression', fontsize=9.5, fontweight='bold', color='#214d5b')
ax_goal.set_xlabel('Day', fontsize=8, color='#4d6e7d')
ax_goal.set_ylabel('Goal Limit (min)', fontsize=8, color='#4d6e7d')
ax_goal.tick_params(colors='#607b85', labelsize=7.5)
for spine in ax_goal.spines.values():
	spine.set_color('#cbdde3')
ax_goal.grid(True, linestyle='--', alpha=0.3, color='#718790')
ax_goal.legend(loc='upper right', fontsize=7.5, facecolor='#f7fbfc', edgecolor='#cbdde3', labelcolor='#214d5b')

canvas_goal = FigureCanvasTkAgg(fig_goal, master=goal_tab_frame)
canvas_goal.get_tk_widget().pack(fill='x', padx=12, pady=(2, 4))

goal_stats_lbl = tk.Label(
	goal_tab_frame,
	text='',
	font=('Segoe UI', 9, 'bold'),
	fg='#5d9c86',
	bg='#f7fbfc',
	pady=4,
)
goal_stats_lbl.pack(fill='x', padx=12, pady=2)

goal_info_card = tk.Frame(
	goal_tab_frame,
	bg='#f7fbfc',
	padx=14,
	pady=6,
	highlightthickness=1,
	highlightbackground='#cbdde3',
)
goal_info_card.pack(fill='both', expand=True, padx=12, pady=(2, 6))

tk.Label(
	goal_info_card,
	text='Daily Goal Settings',
	font=('Segoe UI', 10, 'bold'),
	fg='#214d5b',
	bg='#f7fbfc',
).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 3))

goal_field_defs = [
	('day', 'Current Day', f'{state.current_day:g}'),
	('Tstart', 'Starting Time (min)', f'{state.Tstart:g}'),
	('Tgoal', 'Target Goal (min)', f'{state.Tgoal:g}'),
	('timeBetweenLogins', 'Time Between Logins (min)', f'{state.timeBetweenLogins:g}'),
	('relapseProbability', 'Relapse Risk (0-1)', f'{state.sigmoidRiskScore:.3f}'),
]

for idx, (key, label_text, default_v) in enumerate(goal_field_defs, start=1):
	tk.Label(
		goal_info_card, text=label_text, font=('Segoe UI', 9), bg='#f7fbfc', fg='#4d6e7d'
	).grid(row=idx, column=0, sticky='w', pady=2)
	ent = tk.Entry(
		goal_info_card,
		width=13,
		font=('Segoe UI', 9, 'bold'),
		bg='#eaf3f5',
		fg='#214d5b',
		insertbackground='#5d9c86',
		relief='flat',
		highlightthickness=1,
		highlightbackground='#cbdde3',
		highlightcolor='#5d9c86',
		justify='right',
	)
	ent.grid(row=idx, column=1, sticky='e', padx=(8, 0), pady=2, ipady=2)
	ent.insert(0, default_v)
	ent.bind('<ButtonRelease-1>', lambda e, w=ent: w.select_range(0, tk.END))
	ent.bind('<Return>', lambda e: apply_goal_inputs())
	goal_entries[key] = ent

goal_info_card.columnconfigure(0, weight=1)

goal_status_msg = tk.Label(goal_info_card, text='', font=('Segoe UI', 8), fg='#c95353', bg='#f7fbfc')
goal_status_msg.grid(row=len(goal_field_defs) + 1, column=0, columnspan=2)


def apply_goal_inputs():
	try:
		day_val = max(1, int(float(goal_entries['day'].get())))
		t_start_val = float(goal_entries['Tstart'].get())
		t_goal_val = float(goal_entries['Tgoal'].get())
		login_val = max(0.0, float(goal_entries['timeBetweenLogins'].get()))
		relapse_val = min(1.0, max(0.0, float(goal_entries['relapseProbability'].get())))
	except ValueError:
		goal_status_msg.config(text='Enter valid numbers in all fields.')
		return

	if t_start_val <= 0 or t_goal_val <= 0:
		goal_status_msg.config(text='Values must be greater than 0.')
		return
	if t_start_val > MAX_DAILY_MINS or t_goal_val > MAX_DAILY_MINS:
		goal_status_msg.config(text=f'Values cannot exceed {int(MAX_DAILY_MINS)} min.')
		return
	if t_goal_val > t_start_val:
		goal_status_msg.config(text='Target Goal cannot exceed Starting Time.')
		return

	state.current_day = day_val
	state.Tstart = t_start_val
	state.Tgoal = t_goal_val
	state.timeBetweenLogins = login_val
	state.sigmoidRiskScore = relapse_val
	state.dailyGoal = float(
		calc_daily_goal(
			state.current_day,
			state.Tstart,
			state.Tgoal,
			state.timeBetweenLogins,
			relapse_val,
		)
	)
	state.sync_to_storage()
	goal_status_msg.config(text='')
	sync_entries_from_state()
	refresh_ui(redraw_charts=True)


goal_btn_row = tk.Frame(goal_info_card, bg='#f7fbfc')
goal_btn_row.grid(row=len(goal_field_defs) + 2, column=0, columnspan=2, pady=(4, 2))

make_pill_button(
	goal_btn_row,
	text='Update Daily Goal',
	command=apply_goal_inputs,
	width=150,
	height=30,
	bg_parent='#f7fbfc',
	fill='#5d9c86',
	hover_fill='#4d8d78',
	fg='#214d5b',
	font=('Segoe UI', 9, 'bold'),
	radius=15,
).pack(side='left', padx=6)

results_tab_frame.pack(fill='both', expand=True)


# =====================================================================
# 3. INSTAGRAM APP SIMULATOR
# =====================================================================
insta_header = tk.Frame(instagram_screen, bg='#18181b', pady=10)
insta_header.pack(fill='x')
tk.Label(
	insta_header, text='📸  Instagram Reels', font=('Segoe UI', 12, 'bold'), fg='white', bg='#18181b'
).pack(side='left', padx=14)

insta_banner_lbl = tk.Label(
	instagram_screen,
	text='⏱ Scrolling Active — Stay within your Daily Limit to keep Clean Streak!',
	font=('Segoe UI', 9, 'bold'),
	bg='#1e3a8a',
	fg='#dbeafe',
	pady=6,
)
insta_banner_lbl.pack(fill='x', padx=16, pady=(12, 6))

reel_cv = tk.Canvas(instagram_screen, width=342, height=340, bg='#121212', highlightthickness=0)
reel_cv.pack(padx=16, pady=6)
draw_rounded_rect(reel_cv, 2, 2, 340, 338, r=24, fill='#27272a', outline='#3f3f46', width=1.5)

reel_title_item = reel_cv.create_text(
	171, 60, text='🎬  Infinite Reel #1', fill='white', font=('Segoe UI', 15, 'bold')
)
reel_stats_item = reel_cv.create_text(
	171,
	130,
	text='Scrolling live at 600x speed...\nStay under your Daily Limit to preserve Clean Streak.',
	fill='#d4d4d8',
	font=('Segoe UI', 10),
	justify='center',
)


def scroll_more_reels(minutes_added, is_night=False):
	global reel_counter
	reel_counter += 1
	night_now = is_night or ((state.sim_minutes % 1440) >= 20 * 60)
	state.record_instagram_scroll(minutes_added, is_night=night_now)
	sync_entries_from_state()
	effective_scrolled = max(state.timeScrolling, state.nightScrolling)
	reel_cv.itemconfig(reel_title_item, text=f'🎬  Infinite Reel #{reel_counter}')
	reel_cv.itemconfig(
		reel_stats_item,
		text=f'Scrolled +{minutes_added} min!\nTotal Today: {effective_scrolled:.0f} min (Limit: {state.dailyGoal:.1f} min)\nClean Streak: {state.cleanScore}',
	)
	refresh_ui()


make_pill_button(
	instagram_screen,
	text=f'⬇️  Scroll Next Reel (+{SCROLL_MINUTES} min)',
	command=lambda: scroll_more_reels(SCROLL_MINUTES, is_night=False),
	width=330,
	height=40,
	bg_parent='#121212',
	fill='#db2777',
	hover_fill='#be185d',
	fg='white',
	font=('Segoe UI', 10, 'bold'),
	radius=20,
).pack(pady=5)

make_pill_button(
	instagram_screen,
	text=f'🌙  Late-Night Doomscroll (+{NIGHT_SCROLL_MINUTES} min)',
	command=lambda: scroll_more_reels(NIGHT_SCROLL_MINUTES, is_night=True),
	width=330,
	height=40,
	bg_parent='#121212',
	fill='#4f46e5',
	hover_fill='#4338ca',
	fg='white',
	font=('Segoe UI', 10, 'bold'),
	radius=20,
).pack(pady=5)

make_pill_button(
	instagram_screen,
	text='Close Instagram & Return Home',
	command=lambda: show_screen(home_screen, 'home'),
	width=330,
	height=38,
	bg_parent='#121212',
	fill='#334155',
	hover_fill='#475569',
	fg='white',
	font=('Segoe UI', 9, 'bold'),
	radius=19,
).pack(pady=(6, 10))


# =====================================================================
# 4. POPUP SURVEYS (Starting Survey & New Day Dopamine + Psych Sliders)
# =====================================================================
def open_starting_survey():
	global popup_open
	if popup_open or not app_running:
		return
	try:
		if not root.winfo_exists():
			return
	except tk.TclError:
		return
	popup_open = True

	popup = tk.Toplevel(root)
	popup.title('reBound - Beginning Survey')
	popup.configure(bg='#eaf3f5')
	popup.resizable(False, False)
	popup.transient(root)
	try:
		popup.grab_set()
	except tk.TclError:
		pass
	popup.lift()
	popup.focus_force()

	entries = {}
	fields = (
		('Tstart', 'How many minutes a day do you currently spend doomscrolling? (Max: 1440)'),
		('Tgoal', 'How many minutes a day do you want to get your doomscrolling down to? (Max: 1440)'),
	)

	tk.Label(
		popup, text='reBound — Starting Survey', font=('Segoe UI', 14, 'bold'), fg='#214d5b', bg='#eaf3f5'
	).grid(row=0, column=0, padx=24, pady=(20, 12), sticky='w')

	current_row = 1
	for field, prompt in fields:
		tk.Label(popup, text=prompt, font=('Segoe UI', 10), fg='#4d6e7d', bg='#eaf3f5').grid(
			row=current_row, column=0, padx=24, pady=(8, 4), sticky='w'
		)
		entry = tk.Entry(
			popup,
			width=38,
			font=('Segoe UI', 10, 'bold'),
			bg='#f7fbfc',
			fg='#214d5b',
			insertbackground='#528bdc',
			relief='flat',
			highlightthickness=1,
			highlightbackground='#cbdde3',
			highlightcolor='#528bdc',
		)
		entry.grid(row=current_row + 1, column=0, padx=24, pady=(0, 8), sticky='w', ipady=4)
		entries[field] = entry
		current_row += 2

	entries['Tstart'].insert(0, str(int(min(MAX_DAILY_MINS, state.Tstart))))
	entries['Tgoal'].insert(0, str(int(min(state.Tstart, state.Tgoal))))
	entries['Tstart'].focus_set()

	def on_close():
		global popup_open
		popup_open = False
		try:
			popup.grab_release()
			popup.destroy()
		except tk.TclError:
			pass

	popup.protocol('WM_DELETE_WINDOW', on_close)

	def submit(_=None):
		global popup_open
		try:
			parsed = {field: float(entry.get()) for field, entry in entries.items()}
		except ValueError:
			messagebox.showerror('Invalid input', 'Enter a valid number in each field.', parent=popup)
			return
		ts, tg = parsed['Tstart'], parsed['Tgoal']
		if ts <= 0 or tg <= 0:
			messagebox.showerror('Invalid input', 'Minutes must be greater than 0.', parent=popup)
			return
		if ts > MAX_DAILY_MINS or tg > MAX_DAILY_MINS:
			messagebox.showerror(
				'Invalid input',
				f'Values cannot exceed {int(MAX_DAILY_MINS)} minutes (60 × 24).',
				parent=popup,
			)
			return
		if tg > ts:
			messagebox.showerror(
				'Invalid input',
				'Your goal cannot be higher than your current scrolling time.',
				parent=popup,
			)
			return

		state.set_starting_survey(ts, tg)
		sync_entries_from_state()
		refresh_ui(redraw_charts=True)
		request_ai_suggestions()
		popup_open = False
		try:
			popup.grab_release()
			popup.destroy()
		except tk.TclError:
			pass

	for ent in entries.values():
		ent.bind('<Return>', submit)

	make_pill_button(
		popup,
		text='Continue',
		command=submit,
		width=160,
		height=38,
		bg_parent='#eaf3f5',
		fill='#dce9fa',
		hover_fill='#c7ddf6',
		fg='#214d5b',
		font=('Segoe UI', 10, 'bold'),
		radius=19,
	).grid(row=current_row, column=0, padx=24, pady=(14, 22))


def open_new_day_popup():
	global popup_open
	if popup_open or not app_running:
		return
	try:
		if not root.winfo_exists():
			return
	except tk.TclError:
		return
	popup_open = True

	popup = tk.Toplevel(root)
	popup.title(f'reBound - Day {state.current_day} Survey')
	popup.configure(bg='#eaf3f5')
	popup.resizable(False, False)
	popup.transient(root)
	try:
		popup.grab_set()
	except tk.TclError:
		pass
	popup.lift()
	popup.focus_force()

	tk.Label(
		popup,
		text=f'Day {state.current_day} — New Day Survey',
		font=('Segoe UI', 14, 'bold'),
		fg='#214d5b',
		bg='#eaf3f5',
	).grid(row=0, column=0, padx=24, pady=(16, 8), sticky='w')

	tk.Label(
		popup,
		text='HEALTHY DOPAMINE HABITS',
		font=('Segoe UI', 9, 'bold'),
		fg='#528bdc',
		bg='#eaf3f5',
	).grid(row=1, column=0, padx=24, pady=(4, 4), sticky='w')

	check_vars = []
	current_row = 2
	for idx, (label_text, _) in enumerate(DOPAMINE_ITEMS):
		var = tk.BooleanVar(value=state.dopamine_selections[idx])
		check_vars.append(var)
		cb = tk.Checkbutton(
			popup,
			text=label_text,
			variable=var,
			font=('Segoe UI', 10),
			bg='#eaf3f5',
			fg='#355762',
			selectcolor='#f7fbfc',
			activebackground='#eaf3f5',
			activeforeground='#528bdc',
			wraplength=420,
			justify='left',
			anchor='w',
		)
		cb.grid(row=current_row, column=0, padx=24, pady=3, sticky='w')
		current_row += 1

	tk.Label(
		popup,
		text='PSYCHOLOGICAL STATE SLIDERS (0 – 5)',
		font=('Segoe UI', 9, 'bold'),
		fg='#528bdc',
		bg='#eaf3f5',
	).grid(row=current_row, column=0, padx=24, pady=(10, 4), sticky='w')
	current_row += 1

	slider_defs = [
		('craving', 'Craving', state.craving),
		('withdrawal', 'Withdrawal', state.withdrawal),
		('fomo', 'FOMO (Fear of Missing Out)', state.fomo),
		('stress', 'Stress', state.stress),
	]
	slider_vars = {}

	psych_preview_lbl = tk.Label(
		popup,
		text=f'Stress / Psych Level: {state.psychState:.2f} (0–1 scale)',
		font=('Segoe UI', 9, 'bold'),
		fg='#5d9c86',
		bg='#eaf3f5',
	)

	def update_psych_preview(_=None):
		p_val = calc_psych_state(
			slider_vars['craving'].get(),
			slider_vars['withdrawal'].get(),
			slider_vars['fomo'].get(),
			slider_vars['stress'].get(),
		)
		psych_preview_lbl.config(text=f'Stress / Psych Level: {p_val:.2f} (0–1 scale)')

	for key, label_text, init_val in slider_defs:
		row_frame = tk.Frame(popup, bg='#f7fbfc', padx=10, pady=4)
		row_frame.grid(row=current_row, column=0, padx=24, pady=3, sticky='ew')
		tk.Label(
			row_frame, text=label_text, font=('Segoe UI', 9, 'bold'), fg='#214d5b', bg='#f7fbfc', width=24, anchor='w'
		).pack(side='left')
		d_var = tk.DoubleVar(value=init_val)
		slider_vars[key] = d_var
		sc = tk.Scale(
			row_frame,
			variable=d_var,
			from_=0.0,
			to=5.0,
			resolution=0.5,
			orient='horizontal',
			length=180,
			bg='#f7fbfc',
			fg='#528bdc',
			troughcolor='#eaf3f5',
			highlightthickness=0,
			font=('Segoe UI', 8),
			command=update_psych_preview,
		)
		sc.pack(side='right')
		current_row += 1

	psych_preview_lbl.grid(row=current_row, column=0, padx=24, pady=(6, 2), sticky='w')
	current_row += 1

	def on_close():
		global popup_open
		popup_open = False
		try:
			popup.grab_release()
			popup.destroy()
		except tk.TclError:
			pass

	popup.protocol('WM_DELETE_WINDOW', on_close)

	def submit(_=None):
		global popup_open
		state.apply_dopamine_survey(
			[var.get() for var in check_vars],
			craving=slider_vars['craving'].get(),
			withdrawal=slider_vars['withdrawal'].get(),
			fomo=slider_vars['fomo'].get(),
			stress=slider_vars['stress'].get(),
		)
		sync_entries_from_state()
		refresh_ui(redraw_charts=True)
		request_ai_suggestions()
		popup_open = False
		try:
			popup.grab_release()
			popup.destroy()
		except tk.TclError:
			pass

	popup.bind('<Return>', submit)

	make_pill_button(
		popup,
		text='Continue',
		command=submit,
		width=160,
		height=38,
		bg_parent='#eaf3f5',
		fill='#dcefe7',
		hover_fill='#c6e5d8',
		fg='#214d5b',
		font=('Segoe UI', 10, 'bold'),
		radius=19,
	).grid(row=current_row, column=0, padx=24, pady=(10, 18))


# =====================================================================
# 5. UI & GRAPH REFRESH + 600x SIMULATED CLOCK
# =====================================================================
def refresh_ui(redraw_charts=True):
	if not app_running:
		return
	try:
		if not root.winfo_exists():
			return
	except tk.TclError:
		return

	state.recalculate()
	sync_risk_entries_from_state()
	clock_status_lbl.config(text=format_sim_time(state.sim_minutes))
	day_status_lbl.config(text=f'Day {state.current_day} • 5G')

	effective_scrolled = max(state.timeScrolling, state.nightScrolling)

	if redraw_charts:
		x_new, y_new, x_limit = get_sigmoid_curve(state.riskScore)
		line_curve.set_data(x_new, y_new)
		ax.set_xlim(-x_limit, x_limit)

		point_risk.set_data([state.riskScore], [state.sigmoidRiskScore])
		point_risk.set_label(f'Risk: {state.sigmoidRiskScore:.1%}')
		ax.legend(loc='upper left', fontsize=7.5, facecolor='#f7fbfc', edgecolor='#cbdde3', labelcolor='#214d5b')
		canvas.draw_idle()

		# Update Daily Goal Tab Chart
		days_arr, goals_arr, max_day = get_daily_goal_curve(
			state.Tstart,
			state.Tgoal,
			state.current_day,
			state.timeBetweenLogins,
			state.sigmoidRiskScore,
		)
		line_goal_curve.set_data(days_arr, goals_arr)
		line_target_goal.set_ydata([state.Tgoal, state.Tgoal])
		line_target_goal.set_label(f'Target: {state.Tgoal:.0f}m')
		point_today_goal.set_data([state.current_day], [state.dailyGoal])
		point_today_goal.set_label(f'Day {state.current_day}: {state.dailyGoal:.1f}m')
		ax_goal.set_xlim(0, max_day)
		y_min = max(0.0, min(state.Tgoal, state.Tstart) * 0.8)
		y_max = max(state.Tstart, state.Tgoal, state.dailyGoal, float(goals_arr.max())) * 1.1 + 5.0
		ax_goal.set_ylim(y_min, y_max)
		ax_goal.legend(loc='upper right', fontsize=7.5, facecolor='#f7fbfc', edgecolor='#cbdde3', labelcolor='#214d5b')
		canvas_goal.draw_idle()

	results_daily_limit_lbl.config(text=f'{state.dailyGoal:.1f} min')
	results_relapse_lbl.config(text=f'{state.sigmoidRiskScore:.1%}')

	goal_stats_lbl.config(
		text=f'Day {state.current_day} Goal: {state.dailyGoal:.1f} min  •  Target: {state.Tgoal:.0f} min'
	)

	unscroll_clean_lbl.config(
		text=f'Clean Streak: {state.cleanScore} 🔥  •  Risk: {state.sigmoidRiskScore:.1%}'
	)

	if effective_scrolled <= state.dailyGoal:
		insta_banner_lbl.config(
			text=f'⏱ Scrolled {effective_scrolled:.0f}/{state.dailyGoal:.1f} min — Within Daily Limit (Clean Streak: {state.cleanScore})',
			bg='#e2f0f8',
			fg='#365c68',
		)
	else:
		insta_banner_lbl.config(
			text='⚠️ Daily Limit Exceeded — Clean Streak Reset to 0!',
			bg='#7f1d1d',
			fg='#fecaca',
		)

	widget_cv.itemconfig(widget_risk_item, text=f'Risk: {state.sigmoidRiskScore:.1%}')
	if state.cleanScore > 0:
		widget_cv.itemconfig(widget_clean_item, text=f'Clean Streak: {state.cleanScore} 🔥', fill='#5d9c86')
		widget_cv.itemconfig(
			widget_status_item,
			text=f'Day {state.current_day} • {format_sim_time(state.sim_minutes)} — Keep avoiding doomscrolling!',
		)
	else:
		widget_cv.itemconfig(widget_clean_item, text='Clean Streak: 0 ⚠️', fill='#c95353')
		widget_cv.itemconfig(
			widget_status_item,
			text=f'Day {state.current_day} • {format_sim_time(state.sim_minutes)} — Clean streak reset!',
		)

	widget_cv.itemconfig(
		widget_scrolled_item,
		text=f'Scrolled: {effective_scrolled:.0f}m (Night: {state.nightScrolling:.0f}m)',
	)
	widget_cv.itemconfig(widget_limit_item, text=f'Limit: {state.dailyGoal:.1f}m')

	ratio = min(1.0, max(0.0, effective_scrolled / state.dailyGoal)) if state.dailyGoal > 0 else 1.0
	fill_w = max(12, int(298 * ratio))
	bar_color = '#528bdc' if effective_scrolled <= state.dailyGoal else '#cc5555'
	widget_cv.delete(widget_prog_fill)
	globals()['widget_prog_fill'] = draw_rounded_rect(
		widget_cv, 20, 138, 20 + fill_w, 152, r=7, fill=bar_color, outline=''
	)


def tick_clock():
	"""Advance simulated clock at 1 hour per second (6 simulated minutes every 100 ms)."""
	if not app_running:
		return
	try:
		if not root.winfo_exists():
			return
	except tk.TclError:
		return

	if not popup_open and not sim_paused:
		state.sim_minutes += 6
		is_insta = current_screen_name == 'instagram'
		if is_insta:
			state.record_instagram_scroll(6.0, is_night=(state.sim_minutes % 1440) >= 20 * 60)
			sync_entries_from_state()
			effective_scrolled = max(state.timeScrolling, state.nightScrolling)
			reel_cv.itemconfig(
				reel_stats_item,
				text=f'Scrolling live ({format_sim_time(state.sim_minutes)})...\nTotal Today: {effective_scrolled:.0f} min (Limit: {state.dailyGoal:.1f} min)\nClean Streak: {state.cleanScore}',
			)

		if state.sim_minutes >= 1440:
			trigger_new_day()
		else:
			refresh_ui(redraw_charts=is_insta)

	try:
		if app_running and root.winfo_exists():
			root.after(100, tick_clock)
	except tk.TclError:
		return


show_screen(home_screen, 'home')
request_ai_suggestions()
root.after(150, open_starting_survey)
root.after(200, tick_clock)
root.mainloop()
