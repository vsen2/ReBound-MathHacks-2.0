import tkinter as tk
from tkinter import messagebox
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from calculations import (
	DOPAMINE_ITEMS,
	UnscrollState,
	format_sim_time,
	get_sigmoid_curve,
)

# Shared calculation/state model from calculations.py
state = UnscrollState()
popup_open = False
sim_paused = False
current_screen_name = 'home'
reel_counter = 1


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
	bg_parent='#0f172a',
	fill='#3b82f6',
	hover_fill='#2563eb',
	fg='white',
	font=('Segoe UI', 10, 'bold'),
	radius=18,
):
	cv = tk.Canvas(
		parent, width=width, height=height, bg=bg_parent, highlightthickness=0, cursor='hand2'
	)
	shape = draw_rounded_rect(cv, 2, 2, width - 2, height - 2, r=radius, fill=fill, outline='')
	cv.create_text(width // 2, height // 2, text=text, fill=fg, font=font)
	cv.bind('<Enter>', lambda e: cv.itemconfig(shape, fill=hover_fill))
	cv.bind('<Leave>', lambda e: cv.itemconfig(shape, fill=fill))
	cv.bind('<ButtonRelease-1>', lambda e: command())
	return cv


# --- Main Phone Simulator Window ---
root = tk.Tk()
root.title('Unscroll')
root.geometry('430x830')
root.resizable(False, False)
root.configure(bg='#090d16')

chassis_canvas = tk.Canvas(root, width=430, height=830, bg='#090d16', highlightthickness=0)
chassis_canvas.place(x=0, y=0)
draw_rounded_rect(
	chassis_canvas, 14, 10, 416, 820, r=44, fill='#272e3f', outline='#475569', width=2
)
draw_rounded_rect(chassis_canvas, 20, 16, 410, 814, r=40, fill='#0b1120', outline='')

screen_frame = tk.Frame(root, bg='#0f172a')
screen_frame.place(x=28, y=26, width=374, height=776)

# Top status bar
status_bar = tk.Frame(screen_frame, bg='#0b1120', height=36)
status_bar.pack(fill='x', side='top')
status_bar.pack_propagate(False)

clock_status_lbl = tk.Label(
	status_bar, text='8:00 AM', fg='#f8fafc', bg='#0b1120', font=('Segoe UI', 9, 'bold')
)
clock_status_lbl.pack(side='left', padx=14)

island_cv = tk.Canvas(status_bar, width=104, height=22, bg='#0b1120', highlightthickness=0)
draw_rounded_rect(island_cv, 2, 3, 102, 19, r=9, fill='#000000', outline='#1e293b')
island_cv.place(relx=0.5, rely=0.5, anchor='center')

day_status_lbl = tk.Label(
	status_bar, text='Day 1 • 5G', fg='#94a3b8', bg='#0b1120', font=('Segoe UI', 8, 'bold')
)
day_status_lbl.pack(side='right', padx=14)

# Main content area & bottom bar
content_area = tk.Frame(screen_frame, bg='#0f172a')
content_area.pack(fill='both', expand=True)

nav_bar = tk.Frame(screen_frame, bg='#0b1120', height=50)
nav_bar.pack(fill='x', side='bottom')
nav_bar.pack_propagate(False)

home_screen = tk.Frame(content_area, bg='#0f172a')
unscroll_screen = tk.Frame(content_area, bg='#0f172a')
instagram_screen = tk.Frame(content_area, bg='#121212')


def show_screen(target, name='home'):
	global current_screen_name
	current_screen_name = name
	for frame in (home_screen, unscroll_screen, instagram_screen):
		frame.pack_forget()
	target.pack(fill='both', expand=True)
	refresh_ui()


nav_btn_holder = tk.Frame(nav_bar, bg='#0b1120')
nav_btn_holder.pack(pady=9)

home_pill = make_pill_button(
	nav_btn_holder,
	text='●  Home',
	command=lambda: show_screen(home_screen, 'home'),
	width=120,
	height=32,
	bg_parent='#0b1120',
	fill='#1e293b',
	hover_fill='#334155',
	fg='#f8fafc',
	font=('Segoe UI', 9, 'bold'),
	radius=16,
)
home_pill.pack(side='left', padx=6)

pause_cv = tk.Canvas(
	nav_btn_holder, width=130, height=32, bg='#0b1120', highlightthickness=0, cursor='hand2'
)
pause_shape = draw_rounded_rect(pause_cv, 2, 2, 128, 30, r=16, fill='#f59e0b', outline='')
pause_text_item = pause_cv.create_text(
	65, 16, text='⏸  Stop Time', fill='#0f172a', font=('Segoe UI', 9, 'bold')
)
pause_cv.pack(side='left', padx=6)


def toggle_sim_pause(_=None):
	global sim_paused
	sim_paused = not sim_paused
	if sim_paused:
		pause_cv.itemconfig(pause_shape, fill='#10b981')
		pause_cv.itemconfig(pause_text_item, text='▶  Start Time', fill='#06281e')
		sim_speed_lbl.config(text='⏸ Paused', fg='#f59e0b')
	else:
		pause_cv.itemconfig(pause_shape, fill='#f59e0b')
		pause_cv.itemconfig(pause_text_item, text='⏸  Stop Time', fill='#0f172a')
		sim_speed_lbl.config(text='⏱ 1 hr/s', fg='#38bdf8')


pause_cv.bind('<ButtonRelease-1>', toggle_sim_pause)


# =====================================================================
# 1. HOME SCREEN (Widget + Next Day + App Icons)
# =====================================================================
header_row = tk.Frame(home_screen, bg='#0f172a')
header_row.pack(fill='x', padx=20, pady=(12, 4))
tk.Label(
	header_row, text='Unscroll', font=('Segoe UI', 14, 'bold'), fg='#f8fafc', bg='#0f172a'
).pack(side='left')

sim_speed_lbl = tk.Label(
	header_row,
	text='⏱ 1 hr/s',
	font=('Segoe UI', 8, 'bold'),
	fg='#38bdf8',
	bg='#0f172a',
	cursor='hand2',
)
sim_speed_lbl.pack(side='right', pady=4)
sim_speed_lbl.bind('<ButtonRelease-1>', toggle_sim_pause)

widget_cv = tk.Canvas(
	home_screen, width=338, height=185, bg='#0f172a', highlightthickness=0, cursor='hand2'
)
widget_cv.pack(padx=18, pady=6)

draw_rounded_rect(widget_cv, 2, 2, 336, 183, r=24, fill='#1e293b', outline='#334155', width=1.5)
widget_cv.create_text(
	20, 24, text='UNSCROLL WIDGET', anchor='w', fill='#38bdf8', font=('Segoe UI', 9, 'bold')
)
widget_risk_item = widget_cv.create_text(
	318, 24, text='Risk: 0.0%', anchor='e', fill='#f87171', font=('Segoe UI', 9, 'bold')
)
widget_clean_item = widget_cv.create_text(
	20, 62, text='Clean Streak: 1 🔥', anchor='w', fill='#4ade80', font=('Segoe UI', 18, 'bold')
)
widget_status_item = widget_cv.create_text(
	20, 92,
	text='Clean from doomscrolling — keep it up!',
	anchor='w',
	fill='#cbd5e1',
	font=('Segoe UI', 8),
)
widget_scrolled_item = widget_cv.create_text(
	20, 128, text='Scrolled: 0 min', anchor='w', fill='#f8fafc', font=('Segoe UI', 10, 'bold')
)
widget_limit_item = widget_cv.create_text(
	318, 128, text='Limit: 30 min', anchor='e', fill='#94a3b8', font=('Segoe UI', 10, 'bold')
)

draw_rounded_rect(widget_cv, 20, 148, 318, 162, r=7, fill='#0f172a', outline='')
widget_prog_fill = draw_rounded_rect(
	widget_cv, 20, 148, 28, 162, r=7, fill='#38bdf8', outline=''
)
widget_cv.bind('<ButtonRelease-1>', lambda e: show_screen(unscroll_screen, 'unscroll'))


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
	height=40,
	bg_parent='#0f172a',
	fill='#10b981',
	hover_fill='#059669',
	fg='#06281e',
	font=('Segoe UI', 10, 'bold'),
	radius=20,
)
next_day_pill.pack(padx=18, pady=(8, 4))

tk.Label(
	home_screen, text='Apps', font=('Segoe UI', 10, 'bold'), fg='#94a3b8', bg='#0f172a'
).pack(anchor='w', padx=22, pady=(14, 6))

apps_grid = tk.Frame(home_screen, bg='#0f172a')
apps_grid.pack(fill='x', padx=22)


def make_app_icon(parent, icon_char, title, bg_color, hover_color, command):
	holder = tk.Frame(parent, bg='#0f172a')
	cv = tk.Canvas(holder, width=84, height=84, bg='#0f172a', highlightthickness=0, cursor='hand2')
	bg_rect = draw_rounded_rect(cv, 4, 4, 80, 80, r=22, fill=bg_color, outline='')
	cv.create_text(42, 42, text=icon_char, font=('Segoe UI Emoji', 26), fill='white')
	cv.pack()
	tk.Label(holder, text=title, font=('Segoe UI', 9, 'bold'), fg='#e2e8f0', bg='#0f172a').pack(
		pady=(5, 0)
	)
	cv.bind('<Enter>', lambda e: cv.itemconfig(bg_rect, fill=hover_color))
	cv.bind('<Leave>', lambda e: cv.itemconfig(bg_rect, fill=bg_color))
	cv.bind('<ButtonRelease-1>', lambda e: command())
	return holder


def open_instagram_app():
	state.record_instagram_scroll(5.0, is_night=(state.sim_minutes % 1440) >= 20 * 60)
	sync_entries_from_state()
	show_screen(instagram_screen, 'instagram')


unscroll_icon = make_app_icon(
	apps_grid, '📈', 'Unscroll', '#2563eb', '#1d4ed8', lambda: show_screen(unscroll_screen, 'unscroll')
)
unscroll_icon.grid(row=0, column=0, padx=16, pady=6)

insta_icon = make_app_icon(apps_grid, '📸', 'Instagram', '#db2777', '#be185d', open_instagram_app)
insta_icon.grid(row=0, column=1, padx=16, pady=6)


# =====================================================================
# 2. UNSCROLL APP SCREEN (Graph + Risk Variable Inputs)
# =====================================================================
unscroll_header = tk.Frame(unscroll_screen, bg='#0f172a', pady=6)
unscroll_header.pack(fill='x', padx=12)
tk.Label(
	unscroll_header, text='Unscroll Analytics', font=('Segoe UI', 12, 'bold'), fg='#f8fafc', bg='#0f172a'
).pack(side='left')

new_day_top_pill = make_pill_button(
	unscroll_header,
	text='☀️ New Day',
	command=trigger_new_day,
	width=96,
	height=28,
	bg_parent='#0f172a',
	fill='#38bdf8',
	hover_fill='#0284c7',
	fg='#0f172a',
	font=('Segoe UI', 8, 'bold'),
	radius=14,
)
new_day_top_pill.pack(side='right')

fig = Figure(figsize=(3.5, 2.35), dpi=100, facecolor='#1e293b')
fig.subplots_adjust(left=0.16, right=0.95, top=0.85, bottom=0.20)
ax = fig.add_subplot(111)
ax.set_facecolor('#0f172a')

x_vals, y_vals, _ = get_sigmoid_curve(state.riskScore)
line_curve, = ax.plot(x_vals, y_vals, label='Sigmoid', color='#38bdf8', linewidth=2.2)
point_risk, = ax.plot(
	[state.riskScore],
	[state.sigmoidRiskScore],
	marker='o',
	markersize=8,
	color='#f43f5e',
	linestyle='None',
	zorder=5,
	label=f'Risk: {state.sigmoidRiskScore:.1%}',
)

ax.set_title('Doomscrolling Risk (Sigmoid)', fontsize=9.5, fontweight='bold', color='#f8fafc')
ax.set_xlabel('Risk Score (z)', fontsize=8, color='#cbd5e1')
ax.set_ylabel('Probability σ(z)', fontsize=8, color='#cbd5e1')
ax.tick_params(colors='#94a3b8', labelsize=7.5)
for spine in ax.spines.values():
	spine.set_color('#334155')
ax.grid(True, linestyle='--', alpha=0.3, color='#64748b')
ax.legend(loc='upper left', fontsize=7.5, facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

canvas = FigureCanvasTkAgg(fig, master=unscroll_screen)
canvas.get_tk_widget().pack(fill='x', padx=12, pady=(2, 4))

unscroll_clean_lbl = tk.Label(
	unscroll_screen,
	text='Clean Streak: 1  •  Risk: 0.0% (z=0.00)',
	font=('Segoe UI', 9, 'bold'),
	bg='#1e293b',
	fg='#38bdf8',
	pady=5,
)
unscroll_clean_lbl.pack(fill='x', padx=12, pady=2)

inputs_panel = tk.Frame(unscroll_screen, bg='#1e293b', padx=14, pady=8)
inputs_panel.pack(fill='both', expand=True, padx=12, pady=(4, 6))

tk.Label(
	inputs_panel, text='Risk Score Variables', font=('Segoe UI', 10, 'bold'), bg='#1e293b', fg='#f8fafc'
).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 4))

risk_field_defs = [
	('nightScrolling', 'nightScrolling (min)', f'{state.nightScrolling:g}'),
	('psychState', 'psychState (0-1)', f'{state.psychState:g}'),
	('timeScrolling', 'timeScrolling (min)', f'{state.timeScrolling:g}'),
	('dailyGoal', 'dailyGoal (min)', f'{state.dailyGoal:.1f}'),
	('timeBetweenLogins', 'timeBetweenLogins (min)', f'{state.timeBetweenLogins:g}'),
	('Dopamine', 'Dopamine (%)', f'{state.Dopamine:.0f}%'),
]

var_entries = {}
for idx, (key, label_text, default_v) in enumerate(risk_field_defs, start=1):
	tk.Label(
		inputs_panel, text=label_text, font=('Segoe UI', 9), bg='#1e293b', fg='#cbd5e1'
	).grid(row=idx, column=0, sticky='w', pady=3)
	ent = tk.Entry(
		inputs_panel,
		width=13,
		font=('Segoe UI', 9, 'bold'),
		bg='#0f172a',
		fg='#f8fafc',
		insertbackground='#38bdf8',
		relief='flat',
		highlightthickness=1,
		highlightbackground='#334155',
		highlightcolor='#38bdf8',
		justify='right',
	)
	ent.grid(row=idx, column=1, sticky='e', padx=(8, 0), pady=3, ipady=2)
	ent.insert(0, default_v)
	ent.bind('<ButtonRelease-1>', lambda e, w=ent: w.select_range(0, tk.END))
	ent.bind('<Return>', lambda e: apply_variable_inputs())
	var_entries[key] = ent

inputs_panel.columnconfigure(0, weight=1)

status_msg = tk.Label(inputs_panel, text='', font=('Segoe UI', 8), fg='#f87171', bg='#1e293b')
status_msg.grid(row=len(risk_field_defs) + 1, column=0, columnspan=2)


def sync_entries_from_state():
	values_map = {
		'nightScrolling': f'{state.nightScrolling:g}',
		'psychState': f'{state.psychState:g}',
		'timeScrolling': f'{state.timeScrolling:g}',
		'dailyGoal': f'{state.dailyGoal:.1f}',
		'timeBetweenLogins': f'{state.timeBetweenLogins:g}',
		'Dopamine': f'{state.Dopamine:.0f}%',
	}
	for k, val in values_map.items():
		var_entries[k].delete(0, tk.END)
		var_entries[k].insert(0, val)


def apply_variable_inputs():
	try:
		state.nightScrolling = float(var_entries['nightScrolling'].get())
		state.psychState = float(var_entries['psychState'].get())
		state.timeScrolling = float(var_entries['timeScrolling'].get())
		state.dailyGoal = float(var_entries['dailyGoal'].get())
		state.timeBetweenLogins = float(var_entries['timeBetweenLogins'].get())
		dop_raw = var_entries['Dopamine'].get().strip().rstrip('%').strip()
		state.Dopamine = float(dop_raw)
	except ValueError:
		status_msg.config(text='Enter valid numbers in all fields.')
		return

	if state.dailyGoal == 0:
		status_msg.config(text='dailyGoal cannot be 0.')
		return

	if state.timeScrolling > state.dailyGoal:
		state.cleanScore = 0

	state.recalculate()
	status_msg.config(text='')
	refresh_ui()


btn_row = tk.Frame(inputs_panel, bg='#1e293b')
btn_row.grid(row=len(risk_field_defs) + 2, column=0, columnspan=2, pady=(6, 2))

make_pill_button(
	btn_row,
	text='Update Risk',
	command=apply_variable_inputs,
	width=130,
	height=32,
	bg_parent='#1e293b',
	fill='#3b82f6',
	hover_fill='#2563eb',
	fg='white',
	font=('Segoe UI', 9, 'bold'),
	radius=16,
).pack(side='left', padx=6)

make_pill_button(
	btn_row,
	text='Beginning Survey',
	command=lambda: open_starting_survey(),
	width=130,
	height=32,
	bg_parent='#1e293b',
	fill='#475569',
	hover_fill='#334155',
	fg='white',
	font=('Segoe UI', 9),
	radius=16,
).pack(side='left', padx=6)


# =====================================================================
# 3. INSTAGRAM APP SIMULATOR
# =====================================================================
insta_header = tk.Frame(instagram_screen, bg='#18181b', pady=10)
insta_header.pack(fill='x')
tk.Label(
	insta_header, text='📸  Instagram Reels', font=('Segoe UI', 12, 'bold'), fg='white', bg='#18181b'
).pack(side='left', padx=14)

tk.Label(
	instagram_screen,
	text='⚠️ Doomscrolling Active — Clean Streak Reset to 0!',
	font=('Segoe UI', 9, 'bold'),
	bg='#7f1d1d',
	fg='#fecaca',
	pady=6,
).pack(fill='x', padx=16, pady=(12, 6))

reel_cv = tk.Canvas(instagram_screen, width=342, height=340, bg='#121212', highlightthickness=0)
reel_cv.pack(padx=16, pady=6)
draw_rounded_rect(reel_cv, 2, 2, 340, 338, r=24, fill='#27272a', outline='#3f3f46', width=1.5)

reel_title_item = reel_cv.create_text(
	171, 60, text='🎬  Infinite Reel #1', fill='white', font=('Segoe UI', 15, 'bold')
)
reel_stats_item = reel_cv.create_text(
	171,
	130,
	text='Scrolling live at 600x speed...\nYour Clean Streak has been reset to 0.',
	fill='#d4d4d8',
	font=('Segoe UI', 10),
	justify='center',
)


def scroll_more_reels(minutes_added, is_night=False):
	global reel_counter
	reel_counter += 1
	state.record_instagram_scroll(minutes_added, is_night=is_night)
	sync_entries_from_state()
	reel_cv.itemconfig(reel_title_item, text=f'🎬  Infinite Reel #{reel_counter}')
	reel_cv.itemconfig(
		reel_stats_item,
		text=f'Scrolled +{minutes_added} min!\nTotal Today: {state.timeScrolling:.0f} min (Limit: {state.dailyGoal:.0f} min)\nClean Streak: {state.cleanScore}',
	)
	refresh_ui()


make_pill_button(
	instagram_screen,
	text='⬇️  Scroll Next Reel (+5 min)',
	command=lambda: scroll_more_reels(5, is_night=False),
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
	text='🌙  Late-Night Doomscroll (+15 min)',
	command=lambda: scroll_more_reels(15, is_night=True),
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
# 4. POPUP SURVEYS
# =====================================================================
def open_starting_survey():
	global popup_open
	if popup_open:
		return
	popup_open = True

	popup = tk.Toplevel(root)
	popup.title('Unscroll - Beginning Survey')
	popup.configure(bg='#0f172a')
	popup.resizable(False, False)
	popup.transient(root)
	popup.grab_set()
	popup.lift()
	popup.focus_force()

	entries = {}
	fields = (
		('Tstart', 'How many minutes a day do you currently spend doomscrolling?'),
		('Tgoal', 'How many minutes a day do you want to get your doomscrolling down to?'),
	)

	tk.Label(
		popup, text='Starting survey', font=('Segoe UI', 14, 'bold'), fg='#f8fafc', bg='#0f172a'
	).grid(row=0, column=0, padx=24, pady=(20, 12), sticky='w')

	current_row = 1
	for field, prompt in fields:
		tk.Label(popup, text=prompt, font=('Segoe UI', 10), fg='#cbd5e1', bg='#0f172a').grid(
			row=current_row, column=0, padx=24, pady=(8, 4), sticky='w'
		)
		entry = tk.Entry(
			popup,
			width=38,
			font=('Segoe UI', 10, 'bold'),
			bg='#1e293b',
			fg='#f8fafc',
			insertbackground='#38bdf8',
			relief='flat',
			highlightthickness=1,
			highlightbackground='#334155',
			highlightcolor='#38bdf8',
		)
		entry.grid(row=current_row + 1, column=0, padx=24, pady=(0, 8), sticky='w', ipady=4)
		entries[field] = entry
		current_row += 2

	entries['Tstart'].insert(0, str(int(state.Tstart)))
	entries['Tgoal'].insert(0, str(int(state.Tgoal)))
	entries['Tstart'].focus_set()

	def on_close():
		global popup_open
		popup_open = False
		popup.destroy()

	popup.protocol('WM_DELETE_WINDOW', on_close)

	def submit():
		global popup_open
		try:
			parsed = {field: float(entry.get()) for field, entry in entries.items()}
		except ValueError:
			messagebox.showerror('Invalid input', 'Enter a number in each field.', parent=popup)
			return
		if parsed['Tgoal'] <= 0:
			messagebox.showerror('Invalid input', 'Goal minutes must be greater than 0.', parent=popup)
			return

		state.set_starting_survey(parsed['Tstart'], parsed['Tgoal'])
		sync_entries_from_state()
		refresh_ui()
		popup_open = False
		popup.destroy()

	make_pill_button(
		popup,
		text='Continue',
		command=submit,
		width=160,
		height=38,
		bg_parent='#0f172a',
		fill='#3b82f6',
		hover_fill='#2563eb',
		fg='white',
		font=('Segoe UI', 10, 'bold'),
		radius=19,
	).grid(row=current_row, column=0, padx=24, pady=(14, 22))


def open_new_day_popup():
	global popup_open
	if popup_open:
		return
	popup_open = True

	popup = tk.Toplevel(root)
	popup.title(f'Unscroll - Day {state.current_day} Survey')
	popup.configure(bg='#0f172a')
	popup.resizable(False, False)
	popup.transient(root)
	popup.grab_set()
	popup.lift()
	popup.focus_force()

	tk.Label(
		popup,
		text=f'Day {state.current_day} — New Day Survey',
		font=('Segoe UI', 14, 'bold'),
		fg='#f8fafc',
		bg='#0f172a',
	).grid(row=0, column=0, padx=24, pady=(20, 12), sticky='w')

	check_vars = []
	current_row = 1
	for idx, (label_text, _) in enumerate(DOPAMINE_ITEMS):
		var = tk.BooleanVar(value=state.dopamine_selections[idx])
		check_vars.append(var)
		cb = tk.Checkbutton(
			popup,
			text=label_text,
			variable=var,
			font=('Segoe UI', 10),
			bg='#0f172a',
			fg='#e2e8f0',
			selectcolor='#1e293b',
			activebackground='#0f172a',
			activeforeground='#38bdf8',
			wraplength=420,
			justify='left',
			anchor='w',
		)
		cb.grid(row=current_row, column=0, padx=24, pady=6, sticky='w')
		current_row += 1

	def on_close():
		global popup_open
		popup_open = False
		popup.destroy()

	popup.protocol('WM_DELETE_WINDOW', on_close)

	def submit():
		global popup_open
		state.apply_dopamine_survey([var.get() for var in check_vars])
		sync_entries_from_state()
		refresh_ui()
		popup_open = False
		popup.destroy()

	make_pill_button(
		popup,
		text='Continue',
		command=submit,
		width=160,
		height=38,
		bg_parent='#0f172a',
		fill='#10b981',
		hover_fill='#059669',
		fg='#06281e',
		font=('Segoe UI', 10, 'bold'),
		radius=19,
	).grid(row=current_row, column=0, padx=24, pady=(14, 22))


# =====================================================================
# 5. UI & GRAPH REFRESH + 600x SIMULATED CLOCK
# =====================================================================
def refresh_ui():
	state.recalculate()
	clock_status_lbl.config(text=format_sim_time(state.sim_minutes))
	day_status_lbl.config(text=f'Day {state.current_day} • 5G')

	x_new, y_new, x_limit = get_sigmoid_curve(state.riskScore)
	line_curve.set_data(x_new, y_new)
	ax.set_xlim(-x_limit, x_limit)

	point_risk.set_data([state.riskScore], [state.sigmoidRiskScore])
	point_risk.set_label(f'Risk: {state.sigmoidRiskScore:.1%} ({state.riskScore:.2f})')
	ax.legend(loc='upper left', fontsize=7.5, facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')
	canvas.draw_idle()

	unscroll_clean_lbl.config(
		text=f'Clean Streak: {state.cleanScore} 🔥  •  Risk: {state.sigmoidRiskScore:.1%} (z={state.riskScore:.2f})'
	)

	widget_cv.itemconfig(widget_risk_item, text=f'Risk: {state.sigmoidRiskScore:.1%}')
	if state.cleanScore > 0:
		widget_cv.itemconfig(widget_clean_item, text=f'Clean Streak: {state.cleanScore} 🔥', fill='#4ade80')
		widget_cv.itemconfig(
			widget_status_item,
			text=f'Day {state.current_day} • {format_sim_time(state.sim_minutes)} — Keep avoiding doomscrolling!',
		)
	else:
		widget_cv.itemconfig(widget_clean_item, text='Clean Streak: 0 ⚠️', fill='#f87171')
		widget_cv.itemconfig(
			widget_status_item,
			text=f'Day {state.current_day} • {format_sim_time(state.sim_minutes)} — Clean streak reset!',
		)

	widget_cv.itemconfig(widget_scrolled_item, text=f'Scrolled: {state.timeScrolling:.0f} min')
	widget_cv.itemconfig(widget_limit_item, text=f'Limit: {state.dailyGoal:.1f} min')

	ratio = min(1.0, max(0.0, state.timeScrolling / state.dailyGoal)) if state.dailyGoal > 0 else 1.0
	fill_w = max(12, int(298 * ratio))
	bar_color = '#38bdf8' if state.timeScrolling <= state.dailyGoal else '#ef4444'
	widget_cv.delete(widget_prog_fill)
	globals()['widget_prog_fill'] = draw_rounded_rect(
		widget_cv, 20, 148, 20 + fill_w, 162, r=7, fill=bar_color, outline=''
	)


def tick_clock():
	"""Advance simulated clock at 1 hour per second (6 simulated minutes every 100 ms)."""
	if not popup_open and not sim_paused:
		state.sim_minutes += 6
		if current_screen_name == 'instagram':
			state.record_instagram_scroll(6.0, is_night=(state.sim_minutes % 1440) >= 20 * 60)
			sync_entries_from_state()
			reel_cv.itemconfig(
				reel_stats_item,
				text=f'Scrolling live ({format_sim_time(state.sim_minutes)})...\nTotal Today: {state.timeScrolling:.0f} min (Limit: {state.dailyGoal:.0f} min)\nClean Streak: {state.cleanScore}',
			)

		if state.sim_minutes >= 1440:
			trigger_new_day()
		else:
			refresh_ui()

	root.after(100, tick_clock)


show_screen(home_screen, 'home')
root.after(150, open_starting_survey)
root.after(200, tick_clock)
root.mainloop()
