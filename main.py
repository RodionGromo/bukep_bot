import re

from bukepAPI import Bukep_API
from telegramAPI import TelegramPyAPI, Message
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

def arrInStr(string: str, array: list) -> bool:
	'''
		Возвращает True если хоть один из элементов есть в данной строке
	'''
	for test_string in array:
		if test_string in string:
			return True
	return False

def arrInStrIndexed(string: str, array: list) -> int:
	'''
		Возвращает индекс элемента массива, если он есть в данной строке
	'''
	for i in range(len(array)):
		if array[i] in string:
			return i
	return -1

def translateTiming(string) -> str:
	'''
		Преобразует сжатый формат оповещения в понятный
	'''
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

def to_inlinekb(kb) -> str:
	return json.dumps({"keyboard": kb})

def save_alerts() -> None:
	file = open("alert_list.json", "w")
	file.write(json.dumps(alert_list))
	file.close()

def save_user() -> None:
	file = open("user_data.json", "w")
	endData = {}
	for user, data in users.items():
		endData[user] = [data["api"].login, data["api"].password, data["state"]]
	file.write(json.dumps(endData))
	file.close()

print("[MAIN] Загрузка пользователей...")
# load users
file = json.loads(open("user_data.json", "r").read())
for user, data in file.items():
	try:
		users[user] = {"api": Bukep_API(data[0], data[1]), "state": data[2], "lastUse": datetime.datetime.now()}
		print(f"[MAIN]\t {user} - OK")
	except MaxRetryError:
		print(f"[MAIN]\t {user} - TIMEOUT")
	except Exception as e:
		print(f"[MAIN]\t {user} - ERROR {e}")

print("[MAIN] Загрузка оповещаемых пользователей")
# load alerts
file = json.loads(open("alert_list.json", "r").read())
for user, uid in file.items():
	alert_list[user] = uid
	print(f"[MAIN]\t {user} - OK")

base_menu = to_inlinekb(
	[["Расписания", "Почта"],["Сколько до звонка?", "Переключить оповещение о звонке"]])
lesson_getter_menu = to_inlinekb(
	[["На сегодняшний день", "На завтрашний день"], ["На текущую неделю", "На следующую неделю"], ["На главную"]])
email_menu = to_inlinekb(
	[["Обновить почту", "Показать ящик"],["Показать содержимое письма"], ["На главную"]])
kbs = {
	"main": [base_menu, "Возвращаемся на главную..."],
	"lessons": [lesson_getter_menu, "Открываем расписания..."],
	"mail": [email_menu, "Открываем почту..."]
}

def timedCookieRefresh(user):
	if user not in users:
		return

	if (datetime.datetime.now() - users[user]["lastUse"]).total_seconds() > 300:
		users[user]["api"].logIn()

def convert_to_message(list_lessonDay) -> str:
	last_date = ""
	magicString = ""
	for lessonDay in list_lessonDay:
		if last_date != lessonDay.date:
			magicString += f"-- {lessonDay.date} --\n"
		#magicString += f"\\-\\- Дата: Не доступно на данный момент \\-\\-\n"
			last_date = lessonDay.date
		for lesson in lessonDay.lessons:
			magicString += f"\t`{lesson.position}. {lesson.name} [кабинет {lesson.room}]\n\tПреподаватель: {lesson.lesson_teacher}`\n"
	if "<HTML>" in magicString:
		return "Ошибка bukepAPI, попросите разработчика перезагрузить..."
	return magicString

def parse_message(message: Message):
	if message.user[1]: return
	_channel: str = message.channel
	_content: str = message.content.lower()
	_userid: str = message.user[0]
	_isRegistered: bool = _userid in users

	def sendMessage(message: str, useMarkdown: bool=False, silent: bool=False, returnMessageID: bool=False):
		return tgapi.sendMessageOnChannel(_channel, message, useMarkdown, silent, returnMessageID)

	def sendKeyboard(msg: str, kb: list, silent: bool=False, useMarkdown: bool=False):
		return tgapi.sendKeyboard(_channel, msg, kb, silent, useMarkdown)

	def setUserState(state):
		users[_userid]["state"] = state

	def setUserState_Alert(state, silent: bool=False):
		setUserState(state)
		sendKeyboard(kbs[state][1], kbs[state][0], silent)

	def editMessage(msg_id: int, msg: str, useMarkdown: bool=False):
		return tgapi.editMessage(_channel, msg_id, msg, useMarkdown)

	# if not registered, do the login procedure
	if _userid not in users:
		if _content == "/start":
			if _isRegistered:
				sendKeyboard("Возвращаемся на главную...", base_menu)
			else:
				sendMessage("Добро пожаловать в бот личного кабинета MyBUKEP! Просьба при входе вводить только свои данные и следовать данному шаблону:")
				sendMessage("Введите логин и пароль таким образом: 'войти *логин*:*пароль*'", useMarkdown=True)
		else:
			match = re.match(r"войти ([a-zA-Z0-9]*):([a-zA-Z0-9]*)", _content)
			if match:
				login, passwd = match.groups()
				sendMessage("Проверяю...")
				newUser = Bukep_API(login, passwd)
				if not newUser.get_first_schedule():
					sendMessage("Не могу получить данные, проверьте логин/пароль")
				else:
					sendMessage("Вы успешно вошли!")
					users[_userid] = {"api": newUser, "state": "main"}
					save_user()
			else:
				sendMessage("Неправильно введены данные, попробуйте заново")
		return

	_userstate = users[_userid]["state"]
	_userapi = users[_userid]["api"]
	'''
		states:
			- main
			- lessons
			- mail
				- select
				- TODO: write
				- TODO: readall
	'''
	if "main" in _userstate:
		if "расписания" in _content:
			setUserState_Alert("lessons")
		elif "почта" in _content:
			setUserState_Alert("mail")

		elif "сколько" in _content:
			timeString = (
				lesson_timing[getCurrentLessonTiming()]
				.untilEnd(TimeSecondsSpan.getCurrentSeconds())
				.toDatetime()
			)
			sendMessage(
				translateTiming(getCurrentLessonTiming())
				+ f"\nОсталось {timeString.strftime('%H ч. %M мин. %S сек.')}"
			)

		elif "переключить" in _content:
			if _userid not in alert_list:
				alert_list[_userid] = _channel
				sendMessage("Добавил в список оповещения!")
			else:
				del alert_list[_userid]
				sendMessage("Убрал из списка оповещения!")
			save_alerts()

	elif "lessons" in _userstate:
		possible_lesson = ["сегодняшний", "завтрашний", "текущую", "следующую"]
		if arrInStr(_content, possible_lesson):

			msg_id = sendMessage("Понимаем день...", returnMessageID=True)
			if "сегодня" in _content:
				if datetime.datetime.now().weekday() == 6:
					sendMessage("На этот день выходной!")
					return
			if "завтра" in _content:
				if datetime.datetime.now().weekday() + 1 >= 6:
					sendMessage("На этот день выходной!")
					return

			editMessage(msg_id, "Обновляем куки, если необходимо...")
			timedCookieRefresh(_userid)

			editMessage(msg_id, "Получаем расписание...")
			lessons = _userapi.getSchedule(arrInStrIndexed(_content, possible_lesson))

			editMessage(msg_id, "Читаем расписание...")
			data = convert_to_message(lessons)

			if "<meta" in data:
				editMessage(msg_id, "На этот день расписания нет!")
				return
			editMessage(msg_id, data, useMarkdown=True)

		elif "главную" in _content:
			setUserState_Alert("main")

	elif "mail" in _userstate:
		if ".select" in _userstate:
			if _content.isnumeric():
				mailindex = int(_content) - 1
				if not -1 < mailindex < len(user_mail[_userid]):
					sendMessage("Такого письма нет, отмена...")
					setUserState("mail")
					return
				mail = user_mail[_userid][mailindex]
				content = _userapi.get_mail_content_by_id(mail.mailID)
				sendKeyboard(
					f"Письмо от `{mail.sender}`, дата: `{formTime(mail.date)}`\nТема: `{mail.theme}`\n\n`{content}`",
					useMarkdown=True, kb=email_menu
				)
				setUserState("mail")

		if "обновить" in _content:
			msg_id = sendMessage("Обновляю почту...", returnMessageID=True)
			#TODO: и тут тоже, сделай всё в одной функции в Bukep_API...
			if _userid in user_mail:
				user_mail[_userid], alerts = _userapi.refreshMail(user_mail[_userid])
			else:
				user_mail[_userid], alerts = _userapi.refreshMail([])
			editMessage(msg_id,
				"Обновление успешно!" +
				(" У вас новые сообщения!" if alerts else "") +
				"\nВыберите \"Показать почту\" для просмотра"
			)

		elif "ящик" in _content:
			if (_userid not in user_mail) or (not len(user_mail[_userid])):
				sendMessage(
					"Нет сообщений в ящике или вы не обновили их! " +
					"Выберите \"Обновить почту\" и возвращайтесь"
				)
				return

			magicString = ""
			for mail in user_mail[_userid]:
				magicString += (
					"Письмо от: `" + mail.sender + "`\n" +
					"Тема: `" + mail.theme + "`\n" +
					"Дата: `" + formTime(mail.date) + "`\n\n"
				)
			magicString += "Выберите \"Показать содержимое письма\" для просмотра содержимого!"
			sendMessage(magicString, useMarkdown=True)

		elif "содержимое" in _content:
			if (_userid not in user_mail) or (not len(user_mail[_userid])):
				sendMessage(
					"Нет сообщений в ящике или вы не обновили их! " +
					"Выберите \"Обновить почту\" и возвращайтесь"
				)
				return

			setUserState("mail.select")
			magicString = ""
			for i in range(len(user_mail[_userid])):
				mail = user_mail[_userid][i]
				magicString += f"{i+1}. `{mail.theme}`\nот `{mail.sender}`\n\n"
			magicString += "Введите номер письма для отображения содержимого:"
			tgapi.removeKeyboard(_channel, magicString, useMarkdown=True);

		elif "главную" in _content:
			setUserState_Alert("main")
	save_user()

'''
	Есть шанс что эта фича может вызвать кулдаун на айпи, 
	так что сейчас обновление куки будет по запросу
'''
# def update_cookies():
# 	print("[MAIN] Обновление куки: каждые 5 минут")
# 	lastUpdate = TimeSecondsSpan.getCurrentSeconds();
# 	while running:
# 		if TimeSecondsSpan.getCurrentSeconds() - lastUpdate > 600:
# 			for user, data in users.items():
# 				try:
# 					data["api"].logIn()
# 				except Exception as e:
# 					print(f"[MAIN] Обновление куки у {user} неудачно: {e}")
# 			lastUpdate = TimeSecondsSpan.getCurrentSeconds();
# 		time.sleep(1)

def alert_users_thread():
	last_alert = ""
	lastUpdate = TimeSecondsSpan.getCurrentSeconds();
	print("[MAIN] Оповещение о звонках: проверка каждые 5 секунд")
	while running:
		if TimeSecondsSpan.getCurrentSeconds() - lastUpdate > 5:
			lastUpdate = TimeSecondsSpan.getCurrentSeconds();
			timeName = getCurrentLessonTiming()
			if not timeName:
				continue
			if timeName != last_alert:
				for user, chatid in alert_list.items():
					tgapi.sendMessageOnChannel(chatid, f"Звонок! Сейчас {translateTiming(timeName).lower()}")
			last_alert = timeName		
		time.sleep(1)

running = True

thr_alert = threading.Thread(target=alert_users_thread)
thr_alert.start()
# thr = threading.Thread(target=update_cookies)
# thr.start()

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
		#except Exception as e:
			#print("Error:", e)
