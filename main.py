from bukepAPI import Bukep_API
from telegramAPI import TelegramPyAPI
from timeSecond import TimeSecondsSpan
import json, time, threading, sys

key = "***"
tgapi = TelegramPyAPI(key)

users = {}

lesson_timing = {
	"1.1": TimeSecondsSpan.FromTimeString("08:30.0", "09:15.0"),
	"p1": TimeSecondsSpan.FromTimeString("09:15.0", "09:20.0"),
	"1.2": TimeSecondsSpan.FromTimeString("09:20.0", "10:05.0"),
	"b1": TimeSecondsSpan.FromTimeString("10:05.0", "10:15.0"),

	"2.1": TimeSecondsSpan.FromTimeString("10:15.0", "11:00.0"),
	"p2": TimeSecondsSpan.FromTimeString("11:00.0", "11:05.0"),
	"2.2": TimeSecondsSpan.FromTimeString("11:05.0", "11:50.0"),
	"b2": TimeSecondsSpan.FromTimeString("11:50.0", "12:25.0"),

	"3.1": TimeSecondsSpan.FromTimeString("12:25.0", "13:10.0"),
	"p3": TimeSecondsSpan.FromTimeString("13:10.0", "13:15.0"),
	"3.2": TimeSecondsSpan.FromTimeString("13:15.0", "14:00.0"),
	"b3": TimeSecondsSpan.FromTimeString("14:00.0", "14:35.0"),

	"4.1": TimeSecondsSpan.FromTimeString("14:35.0", "15:20.0"),
	"p4": TimeSecondsSpan.FromTimeString("15:20.0", "15:25.0"),
	"4.2": TimeSecondsSpan.FromTimeString("15:25.0", "16:10.0"),
	"b4": TimeSecondsSpan.FromTimeString("16:10.0", "16:20.0"),

	"5.1": TimeSecondsSpan.FromTimeString("16:20.0", "17:05.0"),
	"p5": TimeSecondsSpan.FromTimeString("17:05.0", "17:10.0"),
	"5.2": TimeSecondsSpan.FromTimeString("17:10.0", "17:55.0"),
	"b5": TimeSecondsSpan.FromTimeString("17:55.0", "18:05.0"),

	"6.1": TimeSecondsSpan.FromTimeString("18:05.0", "18:50.0"),
	"p6": TimeSecondsSpan.FromTimeString("18:50.0", "18:55.0"),
	"6.2": TimeSecondsSpan.FromTimeString("18:55.0", "19:40.0"),
	"b6": TimeSecondsSpan.FromTimeString("19:40.0", "19:50.0"),

	"7.1": TimeSecondsSpan.FromTimeString("19:50.0", "20:35.0"),
	"p7": TimeSecondsSpan.FromTimeString("20:35.0", "20:40.0"),
	"7.2": TimeSecondsSpan.FromTimeString("20:40.0", "21:25.0"),

	"a": TimeSecondsSpan.FromTimeString("21:25.0", "23:59.59"),
	"s": TimeSecondsSpan.FromTimeString("0:00.00", "08:30.0"),
}

def translateTiming(string):
	if "b" in string:
		return f"Перерыв {string[1]}"
	if "p" in string:
		return f"Перерыв между парой {string[1]}"
	if "a" in string:
		return f"Пары окончены, до полночи"
	if "s" in string:
		return f"Еще спим, до начала пар"
	return f"Пара {string[0]}, полупара {string[2]}"

def getCurrentLessonTiming():
	currentSeconds = TimeSecondsSpan.getCurrentSeconds()
	for item, value in lesson_timing.items():
		if value.inSpan(currentSeconds):
			return item

def to_inlinekb(kb):
	return json.dumps({"keyboard": kb})

# load users
try:
	file = json.loads(open("user_data.json", "r").read())
	for user, api in file.items():
		users[user] = Bukep_API(api[0], api[1])
		print(f"[MAIN] Пользователь {user} загружен и залогинен...")
except MaxRetryError:
	print(f"[MAIN] Connection timeout on {user}")
except Exception as e:
	print(f"[MAIN] Error while loading users: {e}")

def save_user():
	file = open("user_data.json", "w")
	endData = {}
	for user, api in users.items():
		endData[user] = [api.login, api.password]
	file.write(json.dumps(endData))
	file.close()

base_menu = to_inlinekb([["Расписания"],["Сколько до звонка?"]])
lesson_getter_menu = to_inlinekb([["На сегодняшний день", "На завтрашний день"], ["На текущую неделю", "На следующую неделю"], ["На главную"]])

def convert_to_message(list_lessonDay):
	last_date = ""
	magicString = ""
	for lessonDay in list_lessonDay:
		if last_date != lessonDay.date:
			magicString += f"-- {lessonDay.date} --\n"
		#magicString += f"\\-\\- Дата: Не доступно на данный момент \\-\\-\n"
			last_date = lessonDay.date
		for lesson in lessonDay.lessons:
			magicString += f"\t`{lessonDay.lessons.index(lesson)+1}. {lesson.name} [кабинет {lesson.room}]\n\tПреподаватель: {lesson.lesson_teacher}`\n"
	return magicString

def parse_message(message):
	if message.user[1]: return
	_channel = message.channel
	_content = message.content.lower()
	_userid = message.user[0]

	if _content == "/start":
		if _userid in users: 
			tgapi.sendKeyboard(_channel, "Вы уже вошли в систему!", base_menu)
			return
		tgapi.sendMessageOnChannel(_channel, "Введите логин и пароль в таком формате: 'войти логин:пароль'\nПример: 'войти 123456:qwerty'")
		return
	elif "войти" in _content:
		if _userid in users: 
			tgapi.sendKeyboard(_channel, "Вы уже вошли в систему!", base_menu)
			return
		try:
			login, password = _content.split(" ")[1].split(":")
			print(login, password)
		except Exception:
			tgapi.sendMessageOnChannel(_channel, "Что-то пошло не так, проверьте введенные данные")
			return
		# try to log in
		bapi = Bukep_API(login, password)
		# check if cant get to any sites
		res = bapi.get_first_schedule()
		if not res:
			tgapi.sendMessageOnChannel(_channel, "Что-то не так, не могу зайти в систему, проверьте введенные данные")
			return
		# ok we're good save this bad boy
		users[message.user[0]] = bapi
		save_user()
		tgapi.sendKeyboard(_channel, "Вы успешно вошли!", base_menu)
		return

	if "до звонка" in _content:
		timeName = getCurrentLessonTiming()
		untilEndText = lesson_timing[timeName].untilEnd(TimeSecondsSpan.getCurrentSeconds()).toDatetime()
		print(untilEndText)
		magicString = translateTiming(timeName) + "\nОсталось " + untilEndText.strftime("%H ч. %M мин. %S сек.")
		tgapi.sendMessageOnChannel(_channel, magicString)
		return

	if _userid not in users: return

	if "на главную" in _content:
		tgapi.sendKeyboard(_channel, "Прошу!", base_menu)
		return

	if "расписания" in _content:
		# send kb
		tgapi.sendKeyboard(_channel, "Прошу!", lesson_getter_menu)
		return

	stupidCommands = ["сегодняшний день", "завтрашний день", "текущую неделю", "следующую неделю"]
	for i in range(len(stupidCommands)):
		if stupidCommands[i] in _content:
			schedule_id = users[_userid].get_first_schedule()
			lessons = users[_userid].get_lessons_html_for_dateid(schedule_id, i)
			data = users[_userid].parse_lessons(lessons)
			if not data:
				tgapi.sendMessageOnChannel(_channel, "Ошибка в работе сайта, попробуйте позже...")
			tgapi.sendMessageOnChannel(_channel, convert_to_message(data), useMarkdown=True)

def update_cookies():
	global running
	lastTime = TimeSecondsSpan.getCurrentSeconds()
	print("[MAIN] Cookie updates: every 5 minutes, no checking")
	while running:
		if abs(lastTime - TimeSecondsSpan.getCurrentSeconds()) > 600:
			for user, api in users.items():
				try:
					api.logIn()
				except Exception as e:
					print(f"[MAIN] Update on user {user} failed: {e}")

thr = threading.Thread(target=update_cookies)
thr.start()
running = True

if __name__ == "__main__":
	while running:
		try:
			msg = tgapi.getSMparsed()
			if msg is None: continue
			parse_message(msg)
		except KeyboardInterrupt:
			print("[MAIN] Stopping bot...")
			running = False
		except Exception as e:
			print(e)
