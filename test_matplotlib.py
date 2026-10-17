import matplotlib.pyplot as plt
import numpy as np

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