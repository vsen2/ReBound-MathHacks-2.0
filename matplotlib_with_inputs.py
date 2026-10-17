import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.widgets import TextBox, Button
import tkinter as tk
from tkinter import messagebox

from calculations import (
	DOPAMINE_ITEMS,
	UnscrollState,
	format_sim_time,
	get_sigmoid_curve,
)

# Shared calculation/state model from calculations.py
state = UnscrollState()
state.dailyGoal = 1.0
state.Dopamine = 0.0
state.recalculate()

popup_open = False
sim_paused = False


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
	width=160,
	height=38,
	bg_parent='#0f172a',
	fill='#3b82f6',
	hover_fill='#2563eb',
	fg='white',
	font=('Segoe UI', 10, 'bold'),
	radius=19,
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


# Create the polished plot figure in the background with space on the right for variable inputs
fig, ax = plt.subplots(figsize=(11, 6), facecolor='#0f172a')
fig.canvas.manager.set_window_title('Unscroll')
plt.subplots_adjust(left=0.07, right=0.58, top=0.86, bottom=0.14)
ax.set_facecolor('#1e293b')

right_card = FancyBboxPatch(
	(0.62, 0.08),
	0.35,
	0.84,
	boxstyle='round,pad=0.02,rounding_size=0.03',
	transform=fig.transFigure,
	facecolor='#1e293b',
	edgecolor='#334155',
	linewidth=1.5,
	zorder=0,
)
fig.add_artist(right_card)

x, y, _ = get_sigmoid_curve(state.riskScore)
line_curve, = ax.plot(x, y, label='Sigmoid Curve', color='#38bdf8', linewidth=2.5, linestyle='-')
point_risk, = ax.plot(
	[state.riskScore],
	[state.sigmoidRiskScore],
	marker='o',
	markersize=9,
	color='#f43f5e',
	linestyle='None',
	zorder=5,
	label=f'Your Risk: {state.sigmoidRiskScore:.2%} (score={state.riskScore:.2f})',
)

ax.set_title(
	'Unscroll — Doomscrolling Risk Score (Sigmoid)',
	fontsize=13,
	fontweight='bold',
	color='#f8fafc',
	pad=12,
)
ax.set_xlabel('Risk Score (z)', fontsize=11, color='#cbd5e1')
ax.set_ylabel('Risk Probability σ(z)', fontsize=11, color='#cbd5e1')
ax.tick_params(colors='#94a3b8')
for spine in ax.spines.values():
	spine.set_color('#334155')
ax.grid(True, linestyle='--', alpha=0.35, color='#64748b')
ax.legend(loc='upper left', facecolor='#0f172a', edgecolor='#334155', labelcolor='#f8fafc')

fig.text(0.65, 0.86, 'Risk Score Variables', fontsize=12, fontweight='bold', color='#f8fafc')
clock_text = fig.text(
	0.65,
	0.82,
	f'Day {state.current_day}  •  {format_sim_time(state.sim_minutes)}  (600x)',
	fontsize=9.5,
	fontweight='bold',
	color='#38bdf8',
)

risk_fields = [
	('nightScrolling', 'nightScrolling: ', f'{state.nightScrolling:g}'),
	('psychState', 'psychState: ', f'{state.psychState:g}'),
	('timeScrolling', 'timeScrolling: ', f'{state.timeScrolling:g}'),
	('dailyGoal', 'dailyGoal: ', f'{state.dailyGoal:g}'),
	('timeBetweenLogins', 'timeBetweenLogins: ', f'{state.timeBetweenLogins:g}'),
	('Dopamine', 'Dopamine (%): ', f'{state.Dopamine:.0f}%'),
]

text_boxes = {}


def pre_click(event):
	for tb in text_boxes.values():
		if tb.capturekeystrokes and not tb.ax.contains(event)[0]:
			tb.stop_typing()
			if event.canvas.mouse_grabber == tb.ax:
				event.canvas.release_mouse(tb.ax)


fig.canvas.mpl_connect('button_press_event', pre_click)

for i, (name, label_str, default_val) in enumerate(risk_fields):
	y_pos = 0.72 - i * 0.085
	box_ax = fig.add_axes([0.78, y_pos, 0.16, 0.055])
	for sp in box_ax.spines.values():
		sp.set_edgecolor('#475569')
		sp.set_linewidth(1.0)
	tb = TextBox(box_ax, label_str, initial=default_val, color='#0f172a', hovercolor='#1e293b')
	tb.label.set_color('#cbd5e1')
	tb.label.set_fontsize(9.5)
	tb.text_disp.set_color('#f8fafc')
	tb.text_disp.set_fontsize(9.5)
	text_boxes[name] = tb

status_text = fig.text(0.65, 0.10, '', color='#f87171', fontsize=9)


def update_graph(_=None):
	try:
		state.nightScrolling = float(text_boxes['nightScrolling'].text)
		state.psychState = float(text_boxes['psychState'].text)
		state.timeScrolling = float(text_boxes['timeScrolling'].text)
		state.dailyGoal = float(text_boxes['dailyGoal'].text)
		state.timeBetweenLogins = float(text_boxes['timeBetweenLogins'].text)
		dop_raw = text_boxes['Dopamine'].text.strip().rstrip('%').strip()
		state.Dopamine = float(dop_raw)
	except ValueError:
		status_text.set_text('Enter valid numbers in all fields.')
		fig.canvas.draw_idle()
		return

	if state.dailyGoal == 0:
		status_text.set_text('dailyGoal cannot be 0.')
		fig.canvas.draw_idle()
		return

	status_text.set_text('')
	state.recalculate()

	x_new, y_new, x_limit = get_sigmoid_curve(state.riskScore)
	line_curve.set_data(x_new, y_new)
	ax.set_xlim(-x_limit, x_limit)

	point_risk.set_data([state.riskScore], [state.sigmoidRiskScore])
	point_risk.set_label(f'Your Risk: {state.sigmoidRiskScore:.2%} (score={state.riskScore:.2f})')
	ax.legend(loc='upper left', facecolor='#0f172a', edgecolor='#334155', labelcolor='#f8fafc')
	fig.canvas.draw_idle()


for tb in text_boxes.values():
	tb.on_submit(update_graph)


def post_click(event):
	for tb in text_boxes.values():
		if tb.ax.contains(event)[0]:
			if hasattr(fig.canvas, 'get_tk_widget'):
				fig.canvas.get_tk_widget().focus_set()
			tb.begin_typing()
			tb.cursor_index = len(tb.text)
			tb._rendercursor()
			fig.canvas.draw_idle()
			break


fig.canvas.mpl_connect('button_press_event', post_click)


def open_starting_survey():
	global popup_open
	if popup_open:
		return
	parent = fig.canvas.manager.window
	try:
		if not parent.winfo_exists():
			return
	except tk.TclError:
		return
	popup_open = True

	popup = tk.Toplevel(parent)
	popup.title('Unscroll - Beginning Survey')
	popup.configure(bg='#0f172a')
	popup.resizable(False, False)
	popup.transient(parent)
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
			width=40,
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
		if parsed['Tgoal'] == 0:
			messagebox.showerror('Invalid input', 'Goal minutes cannot be 0.', parent=popup)
			return

		state.set_starting_survey(parsed['Tstart'], parsed['Tgoal'])
		text_boxes['dailyGoal'].set_val(f'{state.dailyGoal:.1f}')
		update_graph()
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
	).grid(row=current_row, column=0, padx=24, pady=(14, 20))


def open_new_day_popup(_=None):
	global popup_open
	if popup_open:
		return
	parent = fig.canvas.manager.window
	try:
		if not parent.winfo_exists():
			return
	except tk.TclError:
		return
	popup_open = True

	if _ is not None:
		state.advance_to_next_day()
		text_boxes['dailyGoal'].set_val(f'{state.dailyGoal:.1f}')
		text_boxes['timeScrolling'].set_val(f'{state.timeScrolling:g}')
		text_boxes['nightScrolling'].set_val(f'{state.nightScrolling:g}')
		clock_text.set_text(f'Day {state.current_day}  •  {format_sim_time(state.sim_minutes)}  (1 hr/s)')
		fig.canvas.draw_idle()

	popup = tk.Toplevel(parent)
	popup.title(f'Unscroll - Day {state.current_day} Survey')
	popup.configure(bg='#0f172a')
	popup.resizable(False, False)
	popup.transient(parent)
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
			wraplength=480,
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
		if 'Dopamine' in text_boxes:
			text_boxes['Dopamine'].set_val(f'{state.Dopamine:.0f}%')
		update_graph()
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
	).grid(row=current_row, column=0, padx=24, pady=(14, 20))


btn_ax = fig.add_axes([0.635, 0.14, 0.10, 0.065])
for sp in btn_ax.spines.values():
	sp.set_edgecolor('#3b82f6')
update_btn = Button(btn_ax, 'Update Risk', color='#2563eb', hovercolor='#1d4ed8')
update_btn.label.set_color('white')
update_btn.label.set_fontsize(8.5)
update_btn.label.set_fontweight('bold')
update_btn.on_clicked(update_graph)

pause_ax = fig.add_axes([0.745, 0.14, 0.10, 0.065])
for sp in pause_ax.spines.values():
	sp.set_edgecolor('#f59e0b')
pause_btn = Button(pause_ax, 'Stop Time', color='#f59e0b', hovercolor='#d97706')
pause_btn.label.set_color('#0f172a')
pause_btn.label.set_fontsize(8.5)
pause_btn.label.set_fontweight('bold')


def toggle_pause(_=None):
	global sim_paused
	sim_paused = not sim_paused
	if sim_paused:
		pause_btn.label.set_text('Start Time')
		clock_text.set_text(f'Day {state.current_day}  •  {format_sim_time(state.sim_minutes)}  (Paused)')
		clock_text.set_color('#f59e0b')
	else:
		pause_btn.label.set_text('Stop Time')
		clock_text.set_text(f'Day {state.current_day}  •  {format_sim_time(state.sim_minutes)}  (1 hr/s)')
		clock_text.set_color('#38bdf8')
	fig.canvas.draw_idle()


pause_btn.on_clicked(toggle_pause)

new_day_ax = fig.add_axes([0.855, 0.14, 0.10, 0.065])
for sp in new_day_ax.spines.values():
	sp.set_edgecolor('#10b981')
new_day_btn = Button(new_day_ax, 'New Day', color='#10b981', hovercolor='#059669')
new_day_btn.label.set_color('#06281e')
new_day_btn.label.set_fontsize(8.5)
new_day_btn.label.set_fontweight('bold')
new_day_btn.on_clicked(open_new_day_popup)


def tick_clock():
	"""Advance simulated clock at 1 hour per second (6 simulated minutes every 100 ms)."""
	win = fig.canvas.manager.window
	try:
		if not win.winfo_exists():
			return
	except tk.TclError:
		return

	if not popup_open and not sim_paused:
		state.sim_minutes += 6
		if state.sim_minutes >= 1440:
			state.advance_to_next_day()
			text_boxes['dailyGoal'].set_val(f'{state.dailyGoal:.1f}')
			text_boxes['timeScrolling'].set_val(f'{state.timeScrolling:g}')
			text_boxes['nightScrolling'].set_val(f'{state.nightScrolling:g}')
			clock_text.set_text(f'Day {state.current_day}  •  {format_sim_time(state.sim_minutes)}  (1 hr/s)')
			fig.canvas.draw_idle()
			open_new_day_popup(None)
		else:
			clock_text.set_text(f'Day {state.current_day}  •  {format_sim_time(state.sim_minutes)}  (1 hr/s)')
			fig.canvas.draw_idle()

	try:
		if win.winfo_exists():
			win.after(100, tick_clock)
	except tk.TclError:
		return


fig.canvas.manager.window.after(100, open_starting_survey)
fig.canvas.manager.window.after(200, tick_clock)
plt.show()