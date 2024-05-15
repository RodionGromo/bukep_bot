from bukepAPI import Bukep_API
from telegramAPI import TelegramPyAPI
from timeSecond import TimeSecondsSpan, formTime
import json, time, threading, sys, datetime
from urllib3.exceptions import MaxRetryError

key = open("key.txt", "r").read()
tgapi = TelegramPyAPI(key)

users = {}
user_mail = {}

alert_list = {}

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

print("[MAIN] Загрузка пользователей")
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

print("[MAIN] Загрузка оповещаемых пользователей")
# load alerts
file = json.loads(open("alert_list.json", "r").read())
for user, uid in file.items():
	alert_list[user] = uid
	print(f"[MAIN] Пользователь {user} восстановлен в список оповещения")

def save_alerts():
	file = open("alert_list.json", "w")
	file.write(json.dumps(alert_list))
	file.close()

def save_user():
	file = open("user_data.json", "w")
	endData = {}
	for user, api in users.items():
		endData[user] = [api.login, api.password]
	file.write(json.dumps(endData))
	file.close()

def compareEmails(newEmails, userid):
	new_ids = [i.mailID for i in newEmails]
	old_ids = [i.mailID for i in user_mail[userid]]
	return new_ids != old_ids

base_menu = to_inlinekb([["Расписания", "Почта"],["Сколько до звонка?", "Переключить оповещение о звонке"]])
lesson_getter_menu = to_inlinekb([["На сегодняшний день", "На завтрашний день"], ["На текущую неделю", "На следующую неделю"], ["На главную"]])
email_menu = to_inlinekb([["Обновить почту", "Показать ящик"],["Показать содержимое письма"], ["На главную"]])

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
		magicString = translateTiming(timeName) + "\nОсталось " + untilEndText.strftime("%H ч. %M мин. %S сек.")
		tgapi.sendMessageOnChannel(_channel, magicString)
		return

	if _userid not in users: return

	if "на главную" in _content:
		tgapi.sendKeyboard(_channel, "Домой!", base_menu)
		return

	if "расписания" in _content:
		# send kb
		tgapi.sendKeyboard(_channel, "Что смотрим?", lesson_getter_menu)
		return

	if "почта" in _content:
		tgapi.sendKeyboard(_channel, "Смотрим почту?", email_menu)

	if "переключить" in _content:
		# add to alert list, if already added remove
		username = message.user[0]
		if username in alert_list:
			del alert_list[username]
			tgapi.sendMessageOnChannel(_channel, "Удалил из списка оповещений!")
		else:
			alert_list[username] = _channel
			tgapi.sendMessageOnChannel(_channel, "Добавил в список оповещения!")
		save_alerts()

	if "обновить" in _content:
		tgapi.sendMessageOnChannel(_channel, "Обновляю ящик...")
		newEmails = users[_userid].parse_email()
		alerts = False
		if _userid in user_mail:
			if user_mail[_userid] != newEmails:
				alerts = compareEmails(newEmails, _userid)
		user_mail[_userid] = newEmails
		tgapi.sendMessageOnChannel(_channel, "Обновление успешно!" + (" У вас новые сообщения!" if alerts else "") + "\nВыберите \"Показать ящик\" чтоб увидеть сообщения в почте")

	if "ящик" in _content:
		if (_userid not in user_mail) or (not len(user_mail[_userid])):
			tgapi.sendMessageOnChannel(_channel, "У вас нет сообщений или вы еще не обновили их! Выберите \"Обновить почту\" и возвращайтесь!")
			return
		magicString = ""
		for mail in user_mail[_userid]:
			magicString += "Письмо от: `" + mail.sender + "`,\nТема: `" + mail.theme + "`\n"
			magicString += "Дата: `" + formTime(mail.date) + "`\n\n"
		magicString += "Чтоб прочитать содержимое, выберите \"Показать содержимое письма\"!"
		tgapi.sendMessageOnChannel(_channel, magicString, useMarkdown=True)

	if "содержимое" in _content:
		if (_userid not in user_mail) or (not len(user_mail[_userid])):
			tgapi.sendMessageOnChannel(_channel, "У вас нет сообщений или вы еще не обновили их! Выберите \"Обновить почту\" и возвращайтесь!")
			return
		args = _content.split(" ")
		if len(args) != 4:
			# no mail id supplied, ask for it
			tgapi.sendMessageOnChannel(_channel, "Укажите номер письма, которое хотите прочитать!")
			magicString = ""
			for i in range(len(user_mail[_userid])):
				magicString += f"{i+1}. `{user_mail[_userid][i].theme}` от `{user_mail[_userid][i].sender}`\n\n"
			magicString += "Добавьте к этой команде номер письма, и я достану его содержимое\nПример: Показать содержимое письма 3"
			tgapi.sendMessageOnChannel(_channel, magicString, useMarkdown=True) 
		else:
			if not args[3].isnumeric():
				tgapi.sendMessageOnChannel(_channel, "Неверно указан номер письма!")
				return
			mail_index = int(args[3])
			if (mail_index > len(user_mail[_userid])) or (mail_index < 1): 
				tgapi.sendMessageOnChannel(_channel, "Такого письма нет!")
				return
			mail_index -= 1
			# mail id supplied, get message content
			tgapi.sendMessageOnChannel(_channel, "Достаю содержимое письма...")
			mail = user_mail[_userid][mail_index]
			content = users[_userid].get_mail_content_by_id(mail.mailID)
			magicString = f"Письмо от `{mail.sender}`, дата: {formTime(mail.date)}, тема: `{mail.theme}\n\"{content}\"`"
			tgapi.sendMessageOnChannel(_channel, magicString, useMarkdown=True)

	stupidCommands = ["сегодняшний день", "завтрашний день", "текущую неделю", "следующую неделю"]
	for i in range(len(stupidCommands)):
		if stupidCommands[i] in _content:
			if i == 0 and datetime.datetime.now().weekday() == 6:
				tgapi.sendMessageOnChannel(_channel, "Сегодня воскресенье, пар нет!")
				break
			schedule_id = users[_userid].get_first_schedule()
			lessons = users[_userid].get_lessons_html_for_dateid(schedule_id, i)
			data = users[_userid].parse_lessons(lessons)
			if not data:
				tgapi.sendMessageOnChannel(_channel, "Ошибка в работе сайта, попробуйте позже...")
			tgapi.sendMessageOnChannel(_channel, convert_to_message(data), useMarkdown=True)

def update_cookies():
	print("[MAIN] Cookie updates: every 5 minutes, no checking")
	lastUpdate = TimeSecondsSpan.getCurrentSeconds();
	while running:
		if TimeSecondsSpan.getCurrentSeconds() - lastUpdate > 600:
			for user, api in users.items():
				try:
					api.logIn()
				except Exception as e:
					print(f"[MAIN] Update on user {user} failed: {e}")
			lastUpdate = TimeSecondsSpan.getCurrentSeconds();
		time.sleep(1)

def alert_users_thread():
	last_alert = ""
	lastUpdate = TimeSecondsSpan.getCurrentSeconds();
	print("[MAIN] Оповещение о звонках: проверка каждые 5 секунд")
	while running:
		if TimeSecondsSpan.getCurrentSeconds() - lastUpdate > 5:
			timeName = getCurrentLessonTiming()
			if not timeName:
				continue
			if timeName != last_alert:
				for user, chatid in alert_list.items():
					tgapi.sendMessageOnChannel(chatid, f"Звонок! Сейчас {translateTiming(timeName).lower()}")		
			last_alert = timeName
			lastUpdate = TimeSecondsSpan.getCurrentSeconds();
		time.sleep(1)

running = True

thr_alert = threading.Thread(target=alert_users_thread)
thr_alert.start()
thr = threading.Thread(target=update_cookies)
thr.start()

if __name__ == "__main__":
	while running:
		try:
			msg = tgapi.getSMparsed()
			if msg is None: continue
			newThread = threading.Thread(target=parse_message, args=(msg,))
			newThread.start()
		except KeyboardInterrupt:
			print("[MAIN] Stopping bot...")
			running = False
		except Exception as e:
			print("Error:", e)
