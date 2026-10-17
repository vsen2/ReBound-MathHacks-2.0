import numpy as np

# Weight coefficients for the risk score formula
w0 = -2.2  # Baseline intercept
w1 = 1.8   # Goal overshoot
w2 = 2.5   # Psych State (normalized data from the day(t) user survey to a 0 to 1 scale)
w3 = 2.5   # Dopamine Deficit
w4 = 0.8   # Past 8pm Scrolling
w5 = 0.4   # Login Interval Buffer

# Dopamine survey questions and point values (sums out of 100%)
DOPAMINE_ITEMS = [
	('I got 7+ hours of uninterrupted sleep last night.', 30),
	('I avoided looking at screens for at least 1 hour before bed.', 20),
	('I spent time outside in natural sunlight or exercised yesterday.', 25),
	(
		'I engaged in an offline, deep-focus hobby (e.g., reading a physical book, playing an instrument, sketching).',
		25,
	),
]


def calc_sigmoid(z):
	"""Return the sigmoid function 1 / (1 + e^-z)."""
	return 1.0 / (1.0 + np.exp(-z))


def calc_risk(nightScrolling, psychState, timeScrolling, dailyGoal, timeBetweenLogins, Dopamine):
	"""Calculate riskScore and sigmoidRiskScore from the daily variables."""
	safe_goal = dailyGoal if dailyGoal != 0 else 1.0
	riskScore = (
		w0
		+ w1 * ((timeScrolling - safe_goal) / safe_goal)
		+ w2 * psychState
		+ w3 * ((100.0 - Dopamine) / 100.0)
		+ w4 * (nightScrolling / 60.0)
		- w5 * (timeBetweenLogins / 60.0)
	)
	sigmoidRiskScore = calc_sigmoid(riskScore)
	return riskScore, sigmoidRiskScore


def calc_dopamine_from_survey(selections):
	"""Sum the checked survey items to return the Dopamine percentage (0 to 100)."""
	return float(
		sum(pts for checked, (_, pts) in zip(selections, DOPAMINE_ITEMS) if checked)
	)


def get_sigmoid_curve(riskScore, num_points=200):
	"""Generate (x, y) arrays for plotting the sigmoid curve around riskScore."""
	x_limit = max(10.0, abs(riskScore) + 2.0)
	x_vals = np.linspace(-x_limit, x_limit, num_points)
	y_vals = calc_sigmoid(x_vals)
	return x_vals, y_vals, x_limit


def format_sim_time(total_mins):
	"""Convert total simulated minutes into 12-hour 'HH:MM AM/PM' string."""
	m = int(total_mins) % 1440
	hrs24 = m // 60
	mins = m % 60
	period = 'AM' if hrs24 < 12 else 'PM'
	hrs12 = hrs24 % 12
	if hrs12 == 0:
		hrs12 = 12
	return f'{hrs12}:{mins:02d} {period}'


class UnscrollState:
	"""Holds all simulation variables and calls the calculation functions."""

	def __init__(self):
		# Pre-app survey values (Tstart saved for future equation)
		self.Tstart = 60.0
		self.Tgoal = 30.0
		self.Tduration = 0.0
		self.AppUsage = 0.0

		# Daily Risk Score variables
		self.nightScrolling = 0.0
		self.psychState = 0.0
		self.timeScrolling = 0.0
		self.dailyGoal = 30.0
		self.timeBetweenLogins = 0.0
		self.Dopamine = 50.0

		# Streak & Clock state (600x speed; starts at 8:00 AM = 480 mins)
		self.cleanScore = 1
		self.sim_minutes = 8 * 60
		self.current_day = 1
		self.dopamine_selections = [False] * len(DOPAMINE_ITEMS)

		# Calculated outputs
		self.riskScore = 0.0
		self.sigmoidRiskScore = 0.5
		self.recalculate()

	def recalculate(self):
		"""Update riskScore and sigmoidRiskScore from current variables."""
		self.riskScore, self.sigmoidRiskScore = calc_risk(
			self.nightScrolling,
			self.psychState,
			self.timeScrolling,
			self.dailyGoal,
			self.timeBetweenLogins,
			self.Dopamine,
		)
		return self.riskScore, self.sigmoidRiskScore

	def set_starting_survey(self, t_start, t_goal):
		"""Save pre-app Tstart and set dailyGoal from Tgoal."""
		self.Tstart = float(t_start)
		self.Tgoal = float(t_goal)
		self.dailyGoal = float(t_goal)
		self.timeScrolling = 0.0
		self.cleanScore = 1
		self.recalculate()

	def apply_dopamine_survey(self, selections):
		"""Save checkbox selections and recalculate Dopamine % and risk."""
		self.dopamine_selections = list(selections)
		self.Dopamine = calc_dopamine_from_survey(self.dopamine_selections)
		self.recalculate()

	def advance_to_next_day(self):
		"""Update clean streak based on whether scrolling stayed within dailyGoal, then reset for new day."""
		if self.timeScrolling <= self.dailyGoal:
			self.cleanScore += 1
		else:
			self.cleanScore = 0
		self.timeScrolling = 0.0
		self.nightScrolling = 0.0
		self.current_day += 1
		self.sim_minutes = 8 * 60
		self.recalculate()

	def record_instagram_scroll(self, minutes_added, is_night=False):
		"""Add scroll minutes from Instagram and reset cleanScore to 0."""
		self.cleanScore = 0
		self.timeScrolling += float(minutes_added)
		if is_night:
			self.nightScrolling += float(minutes_added)
		self.recalculate()

