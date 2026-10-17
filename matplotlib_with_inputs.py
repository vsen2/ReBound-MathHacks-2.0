import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox, Button
import numpy as np
import tkinter as tk
from tkinter import messagebox

# Initial survey & dopamine calculator state
Tstart = 0.0
Tgoal = 1.0
Tduration = 0.0
AppUsage = 0.0

# weight coefficients for the risk score formula
w0 = -2.2 # Baseline intercept
w1 = 1.8 # Goal overshoot
w2 = 2.5 # Psych State (normalized data from the day(t) user survey to a 0 to 1 scale)
w3 = 2.5 # Dopamine Deficit
w4 = 0.8 # Past 8pm Scrolling
w5 = 0.4 # Login Interval Buffer

# other variables for risk score calc
nightScrolling = 0 # minutes per day
psychState = 0 
timeScrolling = 0 # minutes per day
dailyGoal = 1 # minutes scrolled per day
timeBetweenLogins = 0 # summation of different login differences
Dopamine = 0

def calc_risk(nightScrolling, psychState, timeScrolling, dailyGoal, timeBetweenLogins, Dopamine):
	riskScore = (
		w0
		+ w1 * ((timeScrolling - dailyGoal) / dailyGoal)
		+ w2 * psychState
		+ w3 * ((100 - Dopamine) / 100)
		+ w4 * (nightScrolling / 60)
		- w5 * (timeBetweenLogins / 60)
	)
	sigmoidRiskScore = 1 / (1 + np.exp(-riskScore))
	return riskScore, sigmoidRiskScore

riskScore, sigmoidRiskScore = calc_risk(
	nightScrolling, psychState, timeScrolling, dailyGoal, timeBetweenLogins, Dopamine
)

# Create the plot figure in the background with space on the right for variable inputs
fig, ax = plt.subplots(figsize=(10.5, 5.5))
fig.canvas.manager.set_window_title('Unscroll')
plt.subplots_adjust(left=0.08, right=0.62, top=0.90, bottom=0.14)

# Generate sigmoid curve data and plot the user's risk score on it
x = np.linspace(-10, 10, 200)
y = 1 / (1 + np.exp(-x))

line_curve, = ax.plot(x, y, label='Sigmoid Curve', color='royalblue', linewidth=2, linestyle='-')
point_risk, = ax.plot(
	[riskScore],
	[sigmoidRiskScore],
	marker='o',
	markersize=8,
	color='crimson',
	linestyle='None',
	zorder=5,
	label=f'Your Risk: {sigmoidRiskScore:.2%} (score={riskScore:.2f})',
)

# Add titles and axis labels
ax.set_title('Doomscrolling Risk Score (Sigmoid)', fontsize=14, fontweight='bold')
ax.set_xlabel('Risk Score (z)', fontsize=12)
ax.set_ylabel('Risk Probability σ(z)', fontsize=12)
ax.grid(True, linestyle='--', alpha=0.6)
legend = ax.legend(loc='upper left')

# Add input boxes on the graph interface for the risk score variables
fig.text(0.67, 0.88, 'Risk Score Variables', fontsize=12, fontweight='bold')

risk_fields = [
	('nightScrolling', nightScrolling),
	('psychState', psychState),
	('timeScrolling', timeScrolling),
	('dailyGoal', dailyGoal),
	('timeBetweenLogins', timeBetweenLogins),
	('Dopamine', Dopamine),
]

text_boxes = {}

def pre_click(event):
	# Release mouse grab when switching to another box or clicking buttons
	for tb in text_boxes.values():
		if tb.capturekeystrokes and not tb.ax.contains(event)[0]:
			tb.stop_typing()
			if event.canvas.mouse_grabber == tb.ax:
				event.canvas.release_mouse(tb.ax)

fig.canvas.mpl_connect('button_press_event', pre_click)

for i, (name, default_val) in enumerate(risk_fields):
	y_pos = 0.78 - i * 0.10
	box_ax = fig.add_axes([0.78, y_pos, 0.18, 0.06])
	tb = TextBox(box_ax, f'{name}: ', initial=str(default_val))
	text_boxes[name] = tb

status_text = fig.text(0.67, 0.06, '', color='crimson', fontsize=9)

def update_graph(_=None):
	global nightScrolling, psychState, timeScrolling, dailyGoal, timeBetweenLogins, Dopamine, riskScore, sigmoidRiskScore
	try:
		nightScrolling = float(text_boxes['nightScrolling'].text)
		psychState = float(text_boxes['psychState'].text)
		timeScrolling = float(text_boxes['timeScrolling'].text)
		dailyGoal = float(text_boxes['dailyGoal'].text)
		timeBetweenLogins = float(text_boxes['timeBetweenLogins'].text)
		Dopamine = float(text_boxes['Dopamine'].text)
	except ValueError:
		status_text.set_text('Enter valid numbers in all fields.')
		fig.canvas.draw_idle()
		return

	if dailyGoal == 0:
		status_text.set_text('dailyGoal cannot be 0.')
		fig.canvas.draw_idle()
		return

	status_text.set_text('')
	riskScore, sigmoidRiskScore = calc_risk(
		nightScrolling, psychState, timeScrolling, dailyGoal, timeBetweenLogins, Dopamine
	)

	x_limit = max(10, abs(riskScore) + 2)
	x_new = np.linspace(-x_limit, x_limit, 200)
	line_curve.set_data(x_new, 1 / (1 + np.exp(-x_new)))
	ax.set_xlim(-x_limit, x_limit)

	point_risk.set_data([riskScore], [sigmoidRiskScore])
	point_risk.set_label(f'Your Risk: {sigmoidRiskScore:.2%} (score={riskScore:.2f})')
	ax.legend(loc='upper left')
	fig.canvas.draw_idle()

for tb in text_boxes.values():
	tb.on_submit(update_graph)

def post_click(event):
	# Place cursor at the end of the number whenever clicking anywhere in a box
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
	parent = fig.canvas.manager.window
	popup = tk.Toplevel(parent)
	popup.title('Unscroll - Beginning Survey')
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

	tk.Label(popup, text='Starting survey', font=('Segoe UI', 14, 'bold')).grid(
		row=0, column=0, padx=24, pady=(20, 12), sticky='w'
	)

	current_row = 1
	for field, prompt in fields:
		tk.Label(popup, text=prompt, font=('Segoe UI', 10)).grid(
			row=current_row, column=0, padx=24, pady=(8, 2), sticky='w'
		)
		entry = tk.Entry(popup, width=40)
		entry.grid(row=current_row + 1, column=0, padx=24, pady=(0, 8), sticky='w')
		entries[field] = entry
		current_row += 2

	entries['Tstart'].focus_set()

	def submit():
		global Tstart, Tgoal
		try:
			parsed = {field: float(entry.get()) for field, entry in entries.items()}
		except ValueError:
			messagebox.showerror('Invalid input', 'Enter a number in each field.', parent=popup)
			return
		if parsed['Tgoal'] == 0:
			messagebox.showerror('Invalid input', 'Goal minutes cannot be 0.', parent=popup)
			return

		Tstart = parsed['Tstart']
		Tgoal = parsed['Tgoal']
		text_boxes['timeScrolling'].set_val(str(Tstart))
		text_boxes['dailyGoal'].set_val(str(Tgoal))
		update_graph()
		popup.destroy()

	tk.Button(popup, text='Continue', command=submit).grid(
		row=current_row, column=0, padx=24, pady=(14, 20)
	)


dopamine_items = [
	('I got 7+ hours of uninterrupted sleep last night.', 30),
	('I avoided looking at screens for at least 1 hour before bed.', 20),
	('I spent time outside in natural sunlight or exercised yesterday.', 25),
	(
		'I engaged in an offline, deep-focus hobby (e.g., reading a physical book, playing an instrument, sketching).',
		25,
	),
]
dopamine_selections = [False] * len(dopamine_items)


def open_new_day_popup(_=None):
	parent = fig.canvas.manager.window
	popup = tk.Toplevel(parent)
	popup.title('Unscroll - New Day Survey')
	popup.resizable(False, False)
	popup.transient(parent)
	popup.grab_set()
	popup.lift()
	popup.focus_force()

	tk.Label(popup, text='New Day Survey', font=('Segoe UI', 14, 'bold')).grid(
		row=0, column=0, padx=24, pady=(20, 12), sticky='w'
	)

	check_vars = []
	current_row = 1
	for idx, (label_text, _) in enumerate(dopamine_items):
		var = tk.BooleanVar(value=dopamine_selections[idx])
		check_vars.append(var)
		cb = tk.Checkbutton(
			popup,
			text=label_text,
			variable=var,
			font=('Segoe UI', 10),
			wraplength=480,
			justify='left',
			anchor='w',
		)
		cb.grid(row=current_row, column=0, padx=24, pady=6, sticky='w')
		current_row += 1

	def submit():
		global Dopamine
		for idx, var in enumerate(check_vars):
			dopamine_selections[idx] = var.get()
		Dopamine = sum(pts for var, (_, pts) in zip(check_vars, dopamine_items) if var.get())
		if 'Dopamine' in text_boxes:
			text_boxes['Dopamine'].set_val(str(Dopamine))
		update_graph()
		popup.destroy()

	tk.Button(popup, text='Continue', command=submit).grid(
		row=current_row, column=0, padx=24, pady=(14, 20)
	)


btn_ax = fig.add_axes([0.66, 0.14, 0.14, 0.07])
update_btn = Button(btn_ax, 'Update Risk')
update_btn.on_clicked(update_graph)

new_day_ax = fig.add_axes([0.82, 0.14, 0.14, 0.07])
new_day_btn = Button(new_day_ax, 'New Day')
new_day_btn.on_clicked(open_new_day_popup)

# Open the starting survey popup on top of the graph when first opened
fig.canvas.manager.window.after(100, open_starting_survey)

# Display the plot window
plt.show()