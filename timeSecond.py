import datetime

def formTime(time: datetime.datetime) -> str:
	return time.strftime("%d.%m.%Y")

class TimeSeconds:
	def __init__(self, seconds):
		self.seconds = seconds

	def toDatetime(self):
		return datetime.datetime.min + datetime.timedelta(seconds=self.seconds - 1)

	def __repr__(self):
		return f"[TimeSeconds: {self.seconds}]"

	@staticmethod
	def FromDatetime(dt):
		seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
		return TimeSeconds(seconds)

	@staticmethod
	def FromTimeString(ts):
		time = datetime.datetime.strptime(ts, "%H:%M.%S")
		seconds = time.hour * 3600 + time.minute * 60 + time.second
		return TimeSeconds(seconds)

	def __eq__(self, x):
		return self.seconds == x.seconds

	def __ne__(self, x):
		return not self.__eq__(x)

	def __gt__(self, x):
		return self.seconds > x.seconds

	def __ge__(self, x):
		return self.seconds >= x.seconds

	def __lt__(self, x):
		return self.seconds < x.seconds

	def __le__(self, x):
		return self.seconds <= x.seconds

	def __add__(self, x):
		return self.seconds + x.seconds

	def __sub__(self, x):
		return self.seconds - x.seconds

class TimeSecondsSpan:
	def __init__(self, s1, s2):
		self.start = TimeSeconds(s1)
		self.end = TimeSeconds(s2)

	@staticmethod
	def getCurrentSeconds():
		dt1 = datetime.datetime.now()
		return dt1.hour * 3600 + dt1.minute * 60 + dt1.second

	def inSpan(self, seconds):
		return self.start.seconds < seconds < self.end.seconds

	def untilEnd(self, seconds):
		return TimeSeconds(self.end.seconds - seconds)

	def __repr__(self):
		return f"[TimeSecondsSpan: from {self.start.seconds} to {self.end.seconds}]"

	@staticmethod
	def FromDatetime(dt1, dt2):
		seconds = dt1.hour * 3600 + dt1.minute * 60 + dt1.second
		seconds2 = dt2.hour * 3600 + dt2.minute * 60 + dt2.second
		return TimeSecondsSpan(seconds, seconds2)

	def FromTimeString(ts1, ts2):
		time = datetime.datetime.strptime(ts1, "%H:%M.%S")
		seconds = time.hour * 3600 + time.minute * 60 + time.second
		time2 = datetime.datetime.strptime(ts2, "%H:%M.%S")
		seconds2 = time2.hour * 3600 + time2.minute * 60 + time2.second
		return TimeSecondsSpan(seconds, seconds2)