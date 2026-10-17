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
	('I engaged in an offline, deep-focus hobby (e.g., reading a physical book, playing an instrument, sketching).', 25,
	),
]

def calc_daily_goal(day, Tstart, Tgoal, timeBetweenLogins=0.0, relapseProbability=0.5):
	"""Calculate the daily goal based on the starting survey values and behavioral/relapse state."""
	reasonableTimeBetweenLogins = 60.0
	dampingCoefficient = 0.1
	daily_goal = lambda d: Tgoal + (Tstart - Tgoal) * np.exp(-0.1 * d)

	behavioral_index = np.maximum(0.0, 1.0 - (timeBetweenLogins / reasonableTimeBetweenLogins))
	personal_state = dampingCoefficient * (relapseProbability + behavioral_index) * (Tstart - Tgoal)
	recommended_goal = daily_goal(day + 1) + personal_state
	return recommended_goal


def calc_sigmoid(z):
	"""Return the sigmoid function 1 / (1 + e^-z)."""
	return 1.0 / (1.0 + np.exp(-z))


def calc_risk(nightScrolling, psychState, timeScrolling, dailyGoal, timeBetweenLogins, Dopamine):
	"""Calculate riskScore and sigmoidRiskScore from the daily variables."""
	safe_goal = dailyGoal if dailyGoal != 0 else 1.0
	effective_scroll = max(float(timeScrolling), float(nightScrolling))
	riskScore = (
		w0
		+ w1 * ((effective_scroll - safe_goal) / safe_goal)
		+ w2 * psychState
		+ w3 * ((100.0 - Dopamine) / 100.0)
		+ w4 * (nightScrolling / safe_goal)
		- w5 * (timeBetweenLogins / 60.0)
	)
	sigmoidRiskScore = calc_sigmoid(riskScore)
	return riskScore, sigmoidRiskScore


def calc_dopamine_from_survey(selections):
	"""Sum the checked survey items to return the Dopamine percentage (0 to 100)."""
	return float(
		sum(pts for checked, (_, pts) in zip(selections, DOPAMINE_ITEMS) if checked)
	)


def calc_psych_state(craving=0.0, withdrawal=0.0, fomo=0.0, stress=0.0):
	"""Calculate psychState (0 to 1) from the 4 daily survey sliders (0 to 5 each)."""
	return float(craving) / 20.0 + float(withdrawal) / 20.0 + float(fomo) / 20.0 + float(stress) / 20.0


def get_sigmoid_curve(riskScore, num_points=200):
	"""Generate (x, y) arrays for plotting the sigmoid curve around riskScore."""
	x_limit = max(10.0, abs(riskScore) + 2.0)
	x_vals = np.linspace(-x_limit, x_limit, num_points)
	y_vals = calc_sigmoid(x_vals)
	return x_vals, y_vals, x_limit


def get_daily_goal_curve(
	Tstart,
	Tgoal,
	current_day=1,
	timeBetweenLogins=0.0,
	relapseProbability=0.5,
	min_days=30,
	num_points=200,
):
	"""Generate (days, goals) arrays showing how the daily goal decreases over time."""
	max_day = max(min_days, int(current_day) + 5)
	days = np.linspace(0, max_day, num_points)
	goals = calc_daily_goal(days, Tstart, Tgoal, timeBetweenLogins, relapseProbability)
	return days, goals, max_day


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


class ReBoundState:
	"""Holds all simulation variables and calls the calculation functions."""

	def __init__(self):
		# Pre-app survey values (Tstart saved for future equation)
		self.Tstart = 60.0
		self.Tgoal = 30.0
		self.Tduration = 0.0
		self.AppUsage = 0.0

		# Daily Risk Score variables
		self.nightScrolling = 0.0
		self.craving = 0.0
		self.withdrawal = 0.0
		self.fomo = 0.0
		self.stress = 0.0
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
		self.update_daily_goal()

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

	def update_daily_goal(self):
		"""Recalculate dailyGoal using calc_daily_goal with all 5 parameters."""
		self.dailyGoal = float(
			calc_daily_goal(
				self.current_day,
				self.Tstart,
				self.Tgoal,
				self.timeBetweenLogins,
				self.sigmoidRiskScore,
			)
		)
		self.recalculate()
		return self.dailyGoal

	def set_starting_survey(self, t_start, t_goal):
		"""Save pre-app Tstart and Tgoal (capped at 60*24 min and Tgoal <= Tstart) and calculate Day 1 dailyGoal."""
		max_mins = 60.0 * 24.0
		self.Tstart = min(max_mins, float(t_start))
		self.Tgoal = min(self.Tstart, max_mins, float(t_goal))
		self.timeScrolling = 0.0
		self.cleanScore = 1
		self.recalculate()
		self.update_daily_goal()

	def apply_dopamine_survey(self, selections, craving=None, withdrawal=None, fomo=None, stress=None):
		"""Save checkbox selections and psych sliders and recalculate Dopamine %, psychState, risk, and dailyGoal."""
		self.dopamine_selections = list(selections)
		self.Dopamine = calc_dopamine_from_survey(self.dopamine_selections)
		if all(v is not None for v in (craving, withdrawal, fomo, stress)):
			self.craving = float(craving)
			self.withdrawal = float(withdrawal)
			self.fomo = float(fomo)
			self.stress = float(stress)
			self.psychState = calc_psych_state(self.craving, self.withdrawal, self.fomo, self.stress)
		self.recalculate()
		self.update_daily_goal()

	def advance_to_next_day(self):
		"""Update clean streak based on whether scrolling stayed within dailyGoal, then update dailyGoal for the new day."""
		self.recalculate()
		prev_relapse_prob = self.sigmoidRiskScore
		if self.timeScrolling <= self.dailyGoal:
			self.cleanScore += 1
		else:
			self.cleanScore = 0
		self.timeScrolling = 0.0
		self.nightScrolling = 0.0
		self.current_day += 1
		self.sim_minutes = 8 * 60
		self.dailyGoal = float(
			calc_daily_goal(
				self.current_day,
				self.Tstart,
				self.Tgoal,
				self.timeBetweenLogins,
				prev_relapse_prob,
			)
		)
		self.recalculate()

	def record_instagram_scroll(self, minutes_added, is_night=False):
		"""Add scroll minutes from Instagram and reset cleanScore to 0."""
		self.cleanScore = 0
		self.timeScrolling += float(minutes_added)
		if is_night:
			self.nightScrolling += float(minutes_added)
		self.recalculate()


# Alias for backwards compatibility
UnscrollState = ReBoundState

