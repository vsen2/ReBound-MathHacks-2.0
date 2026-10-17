import matplotlib.pyplot as plt
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

# Generate sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create the plot figure
plt.figure(figsize=(8, 4.5))

# Plot data with custom styling
plt.plot(x, y, label='sin(x)', color='royalblue', linewidth=2, linestyle='-')

# Add titles and axis labels
plt.title('Sine Wave Example', fontsize=14, fontweight='bold')
plt.xlabel('X Values', fontsize=12)
plt.ylabel('Y Values', fontsize=12)

# Enable grid lines and legend
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(loc='upper right')

# Display the plot window
plt.show()