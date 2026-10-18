import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
STORAGE_FILE = BASE_DIR / 'data_storage.json'
ENV_FILE = BASE_DIR / '.env'

# Weight coefficients for the risk score formula
w0 = -2.2  # Baseline intercept
w1 = 1.8   # Goal overshoot
w2 = 2.5   # Psych State (normalized data from the day(t) user survey to a 0 to 1 scale)
w3 = 2.5   # Dopamine Deficit
w4 = 0.8   # Past 8pm Scrolling
w5 = 0.4   # Login Interval Buffer

MAX_DAILY_MINS = 60.0 * 24.0

# Gemini model (override with GEMINI_MODEL=... in .env)
DEFAULT_GEMINI_MODEL = 'gemini-3.8-flash'

# Dopamine survey questions and point values (sums out of 100% with the automatic bedtime bonus)
DOPAMINE_ITEMS = [
	('I got 7+ hours of uninterrupted sleep last night.', 30),
	('I spent time outside in natural sunlight or exercised yesterday.', 25),
	(
		'I engaged in an offline, deep-focus hobby (e.g., reading a physical book, playing an instrument, sketching).',
		25,
	),
]

# "Avoided screens for 1 hour before bed" is no longer asked; it is True automatically
# when the previous day had no night scrolling (Late-Night Scroll button / scrolling after 8 PM).
NO_SCREENS_BEFORE_BED_PTS = 20

# Minutes added by the Scroll Reel and Late-Night Scroll buttons
SCROLL_MINUTES = 10
NIGHT_SCROLL_MINUTES = 10


def avoided_screens_before_bed(prev_night_scrolling):
	"""Return True if the user did not night-scroll the previous day."""
	return float(prev_night_scrolling) <= 0.0


def read_env_file():
	"""Parse the project-root .env file into a dict (re-read every call so edits apply live)."""
	values = {}
	if ENV_FILE.exists():
		try:
			with open(ENV_FILE, 'r', encoding='utf-8-sig') as f:
				for raw_line in f:
					line = raw_line.strip()
					if not line or line.startswith('#') or '=' not in line:
						continue
					k, v = line.split('=', 1)
					k = k.strip()
					if k.startswith('export '):
						k = k[len('export '):].strip()
					v = v.strip().strip('"').strip("'")
					if k:
						values[k] = v
		except Exception:
			pass
	return values


def load_env():
	"""Load .env values into os.environ (.env always overrides system variables)."""
	for k, v in read_env_file().items():
		os.environ[k] = v


def get_gemini_api_key():
	"""Return GEMINI_API_KEY, read only from the project-root .env file."""
	return read_env_file().get('GEMINI_API_KEY', '').strip()


# ---------------------------------------------------------------------------
# NumPy Calculation Functions
# ---------------------------------------------------------------------------

def calc_sigmoid(z):
	"""Return the sigmoid function 1 / (1 + e^-z) using NumPy."""
	return 1.0 / (1.0 + np.exp(-z))


def calc_psych_state(craving=0.0, withdrawal=0.0, fomo=0.0, stress=0.0):
	"""Calculate psychState (0 to 1) from the 4 daily survey sliders (0 to 5 each)."""
	sliders = np.array([craving, withdrawal, fomo, stress], dtype=float)
	return float(np.sum(sliders / 20.0))


def calc_dopamine_from_survey(selections, prev_night_scrolling=0.0):
	"""Sum the checked survey items plus the automatic no-night-scrolling bonus (0 to 100)."""
	total = sum(pts for checked, (_, pts) in zip(selections, DOPAMINE_ITEMS) if checked)
	if avoided_screens_before_bed(prev_night_scrolling):
		total += NO_SCREENS_BEFORE_BED_PTS
	return float(total)


def calc_dynamic_damping(cleanScore=0, relapseProbability=0.5):
	"""Calculate dynamic damping coefficient for the daily goal exponential taper.

	Base rate: 0.1.
	- Long clean streak (5+ days): increases damping (up to ~0.15) to taper faster
	  due to positive behavioral inertia.
	- High relapse risk (>60%): softens the drop (down to ~0.06) to prevent
	  overwhelming the user with an unrealistically aggressive target.
	"""
	k = 0.1
	score = float(cleanScore) if cleanScore is not None else 0.0
	relapse = float(np.mean(relapseProbability)) if np.iterable(relapseProbability) else float(relapseProbability)

	# If user maintains a long clean streak (5+ days), taper limit faster
	if score >= 5.0:
		# Gradually increase: 5 days = +0.01 (0.11), up to +0.05 (0.15) at 9+ days
		streak_boost = min(0.05, (score - 4.0) * 0.01)
		k += streak_boost

	# If relapse probability exceeds 60%, soften the drop
	if relapse > 0.60:
		# Gradually soften by up to 0.04 (e.g. dropping to ~0.06 at 100% risk)
		soften_amount = min(0.04, ((relapse - 0.60) / 0.40) * 0.04)
		k -= soften_amount

	return float(np.clip(k, 0.05, 0.18))


def calc_daily_goal(day, Tstart, Tgoal, timeBetweenLogins=0.0, relapseProbability=0.5, cleanScore=0):
	"""Calculate the daily goal using NumPy exponential decay with dynamic damping + personal state buffer."""
	reasonableTimeBetweenLogins = 60.0
	dampingCoefficient = calc_dynamic_damping(cleanScore, relapseProbability)
	daily_goal = lambda d: Tgoal + (Tstart - Tgoal) * np.exp(-dampingCoefficient * d)

	behavioral_index = np.maximum(0.0, 1.0 - (timeBetweenLogins / reasonableTimeBetweenLogins))
	personal_state = dampingCoefficient * (relapseProbability + behavioral_index) * (Tstart - Tgoal)
	recommended_goal = daily_goal(day + 1) + personal_state
	return np.minimum(Tstart, recommended_goal)


def calc_risk(nightScrolling, psychState, timeScrolling, dailyGoal, timeBetweenLogins, Dopamine):
	"""Calculate riskScore and sigmoidRiskScore from the daily variables using NumPy."""
	safe_goal = float(dailyGoal) if float(dailyGoal) != 0 else 1.0
	effective_scroll = float(np.maximum(float(timeScrolling), float(nightScrolling)))
	riskScore = float(
		w0
		+ w1 * ((effective_scroll - safe_goal) / safe_goal)
		+ w2 * float(psychState)
		+ w3 * ((100.0 - float(Dopamine)) / 100.0)
		+ w4 * (float(nightScrolling) / safe_goal)
		- w5 * (float(timeBetweenLogins) / 60.0)
	)
	sigmoidRiskScore = float(calc_sigmoid(riskScore))
	return riskScore, sigmoidRiskScore


def get_sigmoid_curve(riskScore, num_points=200):
	"""Generate (x, y) NumPy arrays for plotting the sigmoid curve around riskScore."""
	x_limit = float(max(10.0, abs(float(riskScore)) + 2.0))
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
	cleanScore=0,
):
	"""Generate (days, goals) NumPy arrays showing how the daily goal decreases over time with dynamic damping."""
	max_day = int(max(min_days, int(current_day) + 5))
	days = np.linspace(0, max_day, num_points)
	goals = calc_daily_goal(
		days,
		float(Tstart),
		float(Tgoal),
		float(timeBetweenLogins),
		float(relapseProbability),
		cleanScore=cleanScore,
	)
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


def compute_all_metrics(payload=None):
	"""Compute all NumPy metrics + curve arrays for a given state dictionary and save to storage."""
	data = read_storage()
	if isinstance(payload, dict):
		data.update(payload)

	t_start = float(np.clip(float(data.get('Tstart', data.get('current_scrolling_min', 60.0))), 1.0, MAX_DAILY_MINS))
	t_goal = float(np.clip(float(data.get('Tgoal', data.get('initial_goal', 30.0))), 1.0, t_start))
	current_day = max(1, int(data.get('current_day', 1)))
	night_scrolling = max(0.0, float(data.get('nightScrolling', 0.0)))
	time_scrolling = max(0.0, float(data.get('timeScrolling', 0.0)))
	time_between_logins = max(0.0, float(data.get('timeBetweenLogins', 0.0)))
	dopamine = float(np.clip(float(data.get('Dopamine', 50.0)), 0.0, 100.0))

	craving = float(np.clip(float(data.get('craving', 0.0)), 0.0, 5.0))
	withdrawal = float(np.clip(float(data.get('withdrawal', 0.0)), 0.0, 5.0))
	fomo = float(np.clip(float(data.get('fomo', 0.0)), 0.0, 5.0))
	stress = float(np.clip(float(data.get('stress', 0.0)), 0.0, 5.0))
	psych_state = calc_psych_state(craving, withdrawal, fomo, stress)

	# Determine clean streak before goal computation
	clean_score = int(data.get('cleanScore', 1))

	# First risk pass, then dailyGoal with dynamic damping, then final risk pass
	prev_daily_goal = float(data.get('dailyGoal', t_goal))
	_, prelim_sig = calc_risk(night_scrolling, psych_state, time_scrolling, prev_daily_goal, time_between_logins, dopamine)
	daily_goal = float(calc_daily_goal(current_day, t_start, t_goal, time_between_logins, prelim_sig, cleanScore=clean_score))
	risk_score, sig_risk = calc_risk(night_scrolling, psych_state, time_scrolling, daily_goal, time_between_logins, dopamine)
	damping_coefficient = calc_dynamic_damping(clean_score, sig_risk)

	if max(time_scrolling, night_scrolling) > daily_goal:
		clean_score = 0

	data.update({
		'Tstart': t_start,
		'Tgoal': t_goal,
		'initial_goal': t_goal,
		'current_scrolling_min': t_start,
		'current_day': current_day,
		'nightScrolling': night_scrolling,
		'timeScrolling': time_scrolling,
		'timeBetweenLogins': time_between_logins,
		'Dopamine': dopamine,
		'craving': craving,
		'withdrawal': withdrawal,
		'fomo': fomo,
		'stress': stress,
		'psychState': round(psych_state, 4),
		'dailyGoal': round(daily_goal, 4),
		'dampingCoefficient': round(damping_coefficient, 4),
		'riskScore': round(risk_score, 4),
		'sigmoidRiskScore': round(sig_risk, 4),
		'cleanScore': clean_score,
	})
	write_storage(data)

	sig_x, sig_y, x_lim = get_sigmoid_curve(risk_score)
	goal_days, goal_vals, max_day = get_daily_goal_curve(
		t_start, t_goal, current_day, time_between_logins, sig_risk, cleanScore=clean_score
	)

	return {
		'state': data,
		'curves': {
			'sigmoid': {'x': sig_x.tolist(), 'y': sig_y.tolist(), 'xLim': x_lim},
			'goal': {'days': goal_days.tolist(), 'goals': goal_vals.tolist(), 'maxDay': max_day},
		},
	}


# ---------------------------------------------------------------------------
# Storage Functions
# ---------------------------------------------------------------------------

def read_storage():
	"""Read all simulation & survey variables from data_storage.json."""
	if STORAGE_FILE.exists():
		try:
			with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
				return json.load(f)
		except Exception:
			pass
	return {
		'Instagram': 0,
		'Tiktok': 0,
		'Tstart': 60.0,
		'Tgoal': 30.0,
		'initial_goal': 30.0,
		'current_scrolling_min': 60.0,
		'nightScrolling': 0.0,
		'craving': 0.0,
		'withdrawal': 0.0,
		'fomo': 0.0,
		'stress': 0.0,
		'psychState': 0.0,
		'timeScrolling': 0.0,
		'dailyGoal': 30.0,
		'timeBetweenLogins': 0.0,
		'Dopamine': 50.0,
		'cleanScore': 1,
		'current_day': 1,
		'sim_minutes': 480,
		'riskScore': 0.0,
		'sigmoidRiskScore': 0.5,
	}


def write_storage(payload):
	"""Update and persist all simulation & survey variables into data_storage.json."""
	data = read_storage()
	if isinstance(payload, dict):
		data.update(payload)
	with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
		json.dump(data, f, indent=4)
	return data


# ---------------------------------------------------------------------------
# Gemini AI Coach Functions
# ---------------------------------------------------------------------------

def build_fallback_suggestions(state):
	"""Generate metric-driven habit & relapse prevention suggestions if Gemini is unreachable."""
	sig_risk = float(state.get('sigmoidRiskScore', 0.5))
	risk_pct = f'{sig_risk * 100:.1f}'
	time_scrolling = float(state.get('timeScrolling', 0.0))
	night_scrolling = float(state.get('nightScrolling', 0.0))
	effective_scrolled = max(time_scrolling, night_scrolling)
	current_day = int(state.get('current_day', 1))
	daily_goal = float(state.get('dailyGoal', 30.0))
	t_goal = float(state.get('Tgoal', 30.0))
	craving = float(state.get('craving', 0.0))
	withdrawal = float(state.get('withdrawal', 0.0))
	fomo = float(state.get('fomo', 0.0))
	stress = float(state.get('stress', 0.0))
	dopamine = float(state.get('Dopamine', 50.0))

	tips = []
	if sig_risk >= 0.6:
		tips.append(
			f'• High Relapse Risk ({risk_pct}%): Step away from short-form feeds for the next 45 minutes and set your phone in another room.'
		)
	elif sig_risk >= 0.3:
		tips.append(
			f'• Moderate Relapse Risk ({risk_pct}%): Space out your app check-ins to at least 60 minutes apart to keep your daily limit comfortable.'
		)
	else:
		tips.append(
			f"• Low Relapse Risk ({risk_pct}%): Great momentum! You are on track for Day {current_day}'s limit of {daily_goal:.1f} min (Target: {t_goal:.0f} min)."
		)

	if night_scrolling > 0:
		tips.append(
			f'• Late-Night Scrolling ({round(night_scrolling)} min): Enable grayscale mode or charge your phone outside the bedroom 1 hour before sleep.'
		)
	if craving >= 3 or withdrawal >= 3:
		tips.append(
			f'• Craving/Withdrawal ({craving:g}/5, {withdrawal:g}/5): Replace the urge to open Reels with a 5-minute physical reset (cold water, stretching, or a quick walk).'
		)
	if fomo >= 3 or stress >= 3:
		tips.append(
			f'• FOMO/Stress ({fomo:g}/5, {stress:g}/5): Try a 4-7-8 breathing cycle or message one friend directly instead of passively scrolling feeds.'
		)
	if dopamine < 50:
		tips.append(
			f'• Dopamine Recharge ({round(dopamine)}%): Prioritize 15 minutes of outdoor sunlight or an offline deep-focus hobby today to naturally lower your relapse risk.'
		)
	if effective_scrolled > daily_goal:
		tips.append(
			f"• Daily Limit Exceeded ({round(effective_scrolled)} / {daily_goal:.1f} min): Close social apps for the rest of today so tomorrow's taper curve stays achievable."
		)
	return '\n'.join(tips)


def generate_ai_suggestions(state=None):
	"""Call Gemini using GEMINI_API_KEY from .env to generate habit & relapse prevention suggestions."""
	if not isinstance(state, dict) or not state:
		state = read_storage()

	api_key = get_gemini_api_key()
	if api_key:
		current_day = state.get('current_day', 1)
		clean_score = state.get('cleanScore', 1)
		t_start = state.get('Tstart', 60)
		t_goal = state.get('Tgoal', 30)
		daily_goal = float(state.get('dailyGoal', 30.0))
		time_scrolling = float(state.get('timeScrolling', 0.0))
		night_scrolling = float(state.get('nightScrolling', 0.0))
		sig_risk = float(state.get('sigmoidRiskScore', 0.5))
		dopamine = state.get('Dopamine', 50)
		psych_state = float(state.get('psychState', 0.0))
		craving = state.get('craving', 0)
		withdrawal = state.get('withdrawal', 0)
		fomo = state.get('fomo', 0)
		stress = state.get('stress', 0)

		prompt = (
			'You are the reBound AI Habit Coach helping a user taper off doomscrolling.\n'
			'Give 3 concise, actionable, encouraging bullet-point suggestions tailored to their exact real-time metrics:\n'
			f'- Day: {current_day} (Clean Streak: {clean_score})\n'
			f'- Starting scrolling time: {t_start} min/day -> Target goal: {t_goal} min/day\n'
			f"- Today's Recommended Limit: {daily_goal:.1f} min\n"
			f'- Scrolled Today: {max(time_scrolling, night_scrolling)} min (Night scrolling: {night_scrolling} min)\n'
			f'- Relapse Probability: {sig_risk * 100:.1f}%\n'
			f'- Healthy Dopamine Score: {dopamine}%\n'
			f'- Psychological State ({psych_state * 100:.0f}%): Craving={craving}/5, Withdrawal={withdrawal}/5, FOMO={fomo}/5, Stress={stress}/5\n'
			'Keep the response under 110 words.'
		)

		model = read_env_file().get('GEMINI_MODEL', '').strip() or DEFAULT_GEMINI_MODEL
		url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
		req_body = json.dumps({'contents': [{'parts': [{'text': prompt}]}]}).encode('utf-8')
		req = urllib.request.Request(
			url,
			data=req_body,
			headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key},
			method='POST',
		)
		try:
			with urllib.request.urlopen(req, timeout=8) as resp:
				resp_data = json.loads(resp.read().decode('utf-8'))
				candidates = resp_data.get('candidates') or []
				if candidates:
					parts = candidates[0].get('content', {}).get('parts') or []
					if parts and parts[0].get('text'):
						return {'suggestions': parts[0]['text'].strip(), 'source': 'gemini'}
		except Exception:
			pass

	return {'suggestions': build_fallback_suggestions(state), 'source': 'fallback'}


# ---------------------------------------------------------------------------
# Shared ReBoundState Model (used by phoneApp.py and synced with data_storage.json)
# ---------------------------------------------------------------------------

class ReBoundState:
	"""Holds all simulation variables, calls commands.py calculation functions, and syncs with data_storage.json."""

	def __init__(self):
		stored = read_storage()
		self.Instagram = float(stored.get('Instagram', 28))
		self.Tiktok = float(stored.get('Tiktok', 5))
		self.Tstart = float(np.clip(float(stored.get('Tstart', stored.get('current_scrolling_min', 60.0))), 1.0, MAX_DAILY_MINS))
		self.Tgoal = float(np.clip(float(stored.get('Tgoal', stored.get('initial_goal', 30.0))), 1.0, self.Tstart))
		self.Tduration = 0.0
		self.AppUsage = 0.0

		# Daily Risk Score variables
		self.nightScrolling = max(0.0, float(stored.get('nightScrolling', 0.0)))
		self.craving = float(np.clip(float(stored.get('craving', 0.0)), 0.0, 5.0))
		self.withdrawal = float(np.clip(float(stored.get('withdrawal', 0.0)), 0.0, 5.0))
		self.fomo = float(np.clip(float(stored.get('fomo', 0.0)), 0.0, 5.0))
		self.stress = float(np.clip(float(stored.get('stress', 0.0)), 0.0, 5.0))
		self.psychState = calc_psych_state(self.craving, self.withdrawal, self.fomo, self.stress)
		self.timeScrolling = max(0.0, float(stored.get('timeScrolling', 0.0)))
		self.dailyGoal = float(stored.get('dailyGoal', 30.0))
		self.timeBetweenLogins = max(0.0, float(stored.get('timeBetweenLogins', 0.0)))
		self.Dopamine = float(np.clip(float(stored.get('Dopamine', 50.0)), 0.0, 100.0))

		# Streak & Clock state (600x speed; starts at 8:00 AM = 480 mins)
		self.cleanScore = max(0, int(stored.get('cleanScore', 1)))
		self.sim_minutes = int(stored.get('sim_minutes', 8 * 60))
		self.current_day = max(1, int(stored.get('current_day', 1)))
		self.dopamine_selections = [False] * len(DOPAMINE_ITEMS)
		self.prevNightScrolling = max(0.0, float(stored.get('prevNightScrolling', 0.0)))
		self.avoidedScreensBeforeBed = avoided_screens_before_bed(self.prevNightScrolling)

		# Calculated outputs
		self.riskScore = 0.0
		self.sigmoidRiskScore = 0.5
		self.recalculate()
		self.update_daily_goal()
		self.sync_to_storage()

	def to_dict(self):
		"""Return dictionary representation matching data_storage.json."""
		return {
			'Instagram': self.Instagram,
			'Tiktok': self.Tiktok,
			'Tstart': self.Tstart,
			'Tgoal': self.Tgoal,
			'initial_goal': self.Tgoal,
			'current_scrolling_min': self.Tstart,
			'nightScrolling': self.nightScrolling,
			'craving': self.craving,
			'withdrawal': self.withdrawal,
			'fomo': self.fomo,
			'stress': self.stress,
			'psychState': round(float(self.psychState), 4),
			'timeScrolling': self.timeScrolling,
			'dailyGoal': round(float(self.dailyGoal), 4),
			'timeBetweenLogins': self.timeBetweenLogins,
			'Dopamine': self.Dopamine,
			'cleanScore': self.cleanScore,
			'current_day': self.current_day,
			'sim_minutes': self.sim_minutes,
			'riskScore': round(float(self.riskScore), 4),
			'sigmoidRiskScore': round(float(self.sigmoidRiskScore), 4),
			'prevNightScrolling': self.prevNightScrolling,
			'avoidedScreensBeforeBed': self.avoidedScreensBeforeBed,
			'dampingCoefficient': round(float(getattr(self, 'dampingCoefficient', 0.1)), 4),
		}

	def sync_to_storage(self):
		"""Persist current state to data_storage.json."""
		write_storage(self.to_dict())

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
		"""Recalculate dailyGoal using calc_daily_goal with dynamic damping."""
		self.recalculate()
		self.dampingCoefficient = calc_dynamic_damping(self.cleanScore, self.sigmoidRiskScore)
		self.dailyGoal = float(
			calc_daily_goal(
				self.current_day,
				self.Tstart,
				self.Tgoal,
				self.timeBetweenLogins,
				self.sigmoidRiskScore,
				cleanScore=self.cleanScore,
			)
		)
		self.recalculate()
		return self.dailyGoal

	def set_starting_survey(self, t_start, t_goal):
		"""Save pre-app Tstart and Tgoal (capped at 60*24 min and Tgoal <= Tstart) and calculate Day 1 dailyGoal."""
		self.Tstart = float(np.clip(float(t_start), 1.0, MAX_DAILY_MINS))
		self.Tgoal = float(np.clip(float(t_goal), 1.0, self.Tstart))
		self.timeScrolling = 0.0
		self.cleanScore = 1
		self.update_daily_goal()
		self.sync_to_storage()

	def apply_dopamine_survey(self, selections, craving=None, withdrawal=None, fomo=None, stress=None):
		"""Save checkbox selections and psych sliders and recalculate Dopamine %, psychState, risk, and dailyGoal."""
		self.dopamine_selections = list(selections)
		self.Dopamine = calc_dopamine_from_survey(self.dopamine_selections, self.prevNightScrolling)
		if all(v is not None for v in (craving, withdrawal, fomo, stress)):
			self.craving = float(np.clip(float(craving), 0.0, 5.0))
			self.withdrawal = float(np.clip(float(withdrawal), 0.0, 5.0))
			self.fomo = float(np.clip(float(fomo), 0.0, 5.0))
			self.stress = float(np.clip(float(stress), 0.0, 5.0))
			self.psychState = calc_psych_state(self.craving, self.withdrawal, self.fomo, self.stress)
		self.update_daily_goal()
		self.sync_to_storage()

	def advance_to_next_day(self):
		"""Update clean streak based on whether scrolling stayed within dailyGoal, then update dailyGoal for the new day."""
		self.recalculate()
		prev_relapse_prob = self.sigmoidRiskScore
		if max(self.timeScrolling, self.nightScrolling) <= self.dailyGoal:
			self.cleanScore += 1
		else:
			self.cleanScore = 0
		# Remember yesterday's night scrolling for the automatic "avoided screens before bed" boolean
		self.prevNightScrolling = self.nightScrolling
		self.avoidedScreensBeforeBed = avoided_screens_before_bed(self.prevNightScrolling)
		self.timeScrolling = 0.0
		self.nightScrolling = 0.0
		self.current_day += 1
		self.sim_minutes = 8 * 60
		self.dampingCoefficient = calc_dynamic_damping(self.cleanScore, prev_relapse_prob)
		self.dailyGoal = float(
			calc_daily_goal(
				self.current_day,
				self.Tstart,
				self.Tgoal,
				self.timeBetweenLogins,
				prev_relapse_prob,
				cleanScore=self.cleanScore,
			)
		)
		self.recalculate()
		self.sync_to_storage()

	def record_instagram_scroll(self, minutes_added, is_night=False):
		"""Add scroll minutes from Instagram and only reset cleanScore to 0 if dailyGoal is exceeded."""
		self.timeScrolling += float(minutes_added)
		if is_night:
			self.nightScrolling += float(minutes_added)
		if max(self.timeScrolling, self.nightScrolling) > self.dailyGoal:
			self.cleanScore = 0
		self.recalculate()
		self.sync_to_storage()


# Alias for backwards compatibility
UnscrollState = ReBoundState

