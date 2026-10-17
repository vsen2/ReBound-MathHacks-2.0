import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox, Button
import numpy as np
import tkinter as tk
from tkinter import messagebox

def collect_inputs():
	root = tk.Tk()
	root.title('App Usage Inputs')
	root.resizable(False, False)

	entries = {}
	fields = ('Tstart', 'Tgoal', 'Tduration', 'AppUsage')

	tk.Label(root, text='Enter your values', font=('Segoe UI', 14, 'bold')).grid(
		row=0, column=0, columnspan=2, padx=24, pady=(20, 12), sticky='w'
	)

	for row, field in enumerate(fields, start=1):
		tk.Label(root, text=field).grid(row=row, column=0, padx=24, pady=7, sticky='w')
		entry = tk.Entry(root, width=24)
		entry.grid(row=row, column=1, padx=(12, 24), pady=7)
		entries[field] = entry

	values = {}

	def submit():
		try:
			values.update({field: float(entry.get()) for field, entry in entries.items()})
		except ValueError:
			messagebox.showerror('Invalid input', 'Enter a number in each field.', parent=root)
			return
		root.destroy()

	tk.Button(root, text='Continue', command=submit).grid(
		row=len(fields) + 1, column=0, columnspan=2, padx=24, pady=(14, 20)
	)
	root.mainloop()

	if not values:
		raise SystemExit
	return values


inputs = collect_inputs()
Tstart = inputs['Tstart']
Tgoal = inputs['Tgoal']
Tduration = inputs['Tduration']
AppUsage = inputs['AppUsage']

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

# Create the plot figure with space on the right for variable inputs
fig, ax = plt.subplots(figsize=(10.5, 5.5))
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
for i, (name, default_val) in enumerate(risk_fields):
	y_pos = 0.78 - i * 0.10
	box_ax = fig.add_axes([0.78, y_pos, 0.18, 0.06])
	tb = TextBox(box_ax, f'{name}: ', initial=str(default_val))
	text_boxes[name] = tb

status_text = fig.text(0.67, 0.08, '', color='crimson', fontsize=9)

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

btn_ax = fig.add_axes([0.74, 0.15, 0.16, 0.07])
update_btn = Button(btn_ax, 'Update Risk')
update_btn.on_clicked(update_graph)

# Display the plot window
plt.show()