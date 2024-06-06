import requests, datetime
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class Lesson:
	def __init__(self, lesson_name, lesson_type, lesson_teacher, room):
		self.name = lesson_name
		self.lesson_type = lesson_type
		self.lesson_teacher = lesson_teacher
		self.room = room

	def __repr__(self):
		return f"[Пара {self.name} в кабинете {self.room}, {self.lesson_type}, преподаватель {self.lesson_teacher}]"

class LessonDay:
	def __init__(self, date, lessons):
		self.lessons = lessons
		self.date = date

class Mail:
	def __init__(self, sender, theme, date, mid):
		self.sender = sender
		self.theme = theme
		self.date = datetime.datetime.strptime(date, "%d.%m.%y")
		self.mailID = mid

	def __repr__(self):
		return f"[Mail from {self.sender}, theme: {self.theme}, sent date: {self.date}]"

class Bukep_API:
	def __init__(self, login, password):
		'''
		Абсолютно угашеный апи который парсит данные из html
		'''
		self.login = login
		self.password = password
		self.lpdata = {"login": self.login, "password": self.password}
		self.logIn()

	def logIn(self):
		'''
		Логинимся испольуя логин/пароль что дал нам пользователь, обычно не вызывается снаружи
		'''
		rq = requests.post("https://my.bukep.ru/Login/Login", data=self.lpdata, verify=False, allow_redirects=False, timeout=10)
		if(rq.status_code != 302):
			print("[bukepAPI] ERROR login for", self.login, "status:", rq.status_code)
		# else:
		# 	print("[bukepAPI] Login for", self.login, "status:",rq.status_code)
		self.cookie = rq.cookies.get_dict()

	def get_first_schedule(self):
		'''
		Достаем ID первого расписания (если будет больше одного то с этим надо будет поработать)
		'''
		rq = requests.post("https://my.bukep.ru/Schedule/Schedule", cookies=self.cookie, verify=False)
		if "Неверное" in rq.text:
			return None
		data = rq.text
		first_schedule_id = data.find("/Schedule/Schedule/")
		data = data[first_schedule_id+19:first_schedule_id+24]
		return data

	def get_lessons_html_for_dateid(self, schedule_id, date_id):
		'''
		Возвращает HTML сайта расписания пар по данному ID даты

		БУКЭП имеет API в разработке, так что ждем его, а пока парсим все с HTML
		А ну да, чтоб получить расписание нужно подать одну из этих цифер
		0 - расписание на сегодня
		1 - на завтра
		2 - на текущуюю неделю
		3 - на следующую неделю
		4 - полное расписание на неделю
		'''
		rq = requests.post("https://my.bukep.ru/Schedule/Schedule/" + schedule_id, cookies=self.cookie, data={"ddlConfig": int(date_id)}, verify=False)
		return rq.text

	def parse_lessons(self, raw_data):
		raw_data = raw_data.strip()
		lessons_start = raw_data.find('<div class="row-rasp raspDayDiv">')
		raw_data = raw_data[lessons_start+33:].split('<div class="row-rasp raspDayDiv">')
		del lessons_start
		lessonday_list = []
		for raw_data_part in raw_data:
			data = raw_data_part.replace("\r", "").strip()
			# достаем день + дату
			str_date_start = data.find('<td colspan="3"')
			str_date_end = data.find('</td>')
			day_date = data[str_date_start+15:str_date_end]
			del str_date_start, str_date_end
			# достаем дату, а по ней уже будем день недели доставать
			raw_date_start = day_date.find('25px;">')
			raw_date_end = day_date.rfind('</div>')
			raw_date = day_date[raw_date_start+7:raw_date_end]
			date_1 = raw_date
			del raw_date_start, raw_date_end, day_date
			# пары..
			lessons = []
			for lesson in data.split('<div style="color:black;">'):
				lesson_end = lesson.find("</td>")
				lesson_data = lesson[:lesson_end].replace("\n                ", "")
				if("raspDayTable" in lesson_data):
					continue
				lesson_name = lesson_data[:lesson_data.find("</div>")]
				lesson_type = lesson_data[lesson_data.find("</div><div>")+11:lesson_data.find(" <span")]
				lesson_teacher = lesson_data[lesson_data.find("</div>    <div>")+15:lesson_data.find("</div>\n")].replace("</div>    <div>", "/")
				lesson_room = lesson_data[lesson_data.find('black;">')+8:lesson_data.find("</span>")]
				lessons.append(Lesson(lesson_name, lesson_type, lesson_teacher, lesson_room))
			lessonday_list.append(LessonDay(date_1, lessons))
		return lessonday_list


	def parse_email(self, page=1):
		raw_data = requests.get("https://my.bukep.ru/MailBukep/Incoming?PageNumber="+str(page), cookies=self.cookie, verify=False, allow_redirects=False).text
		mail_table_start = raw_data.find('<table class="table table-bordered table-hover table-striped small">')
		mail_table_end = raw_data[mail_table_start:].rfind('</table>')
		rd_1 = raw_data[mail_table_start:mail_table_end+mail_table_start]
		r_mails = rd_1.split('<td class="col-lg-1 col-md-2 col-sm-1 col-xs-3 " align="center" valign="middle">')
		mails = []
		for m in r_mails:
			# id
			mail_id = m[m.find("Incoming/")+9:m.find("?PageNumber=1&")]
			if not mail_id.isnumeric():
				continue
			m = m[m.find("?PageNumber=1&"):]
			# sender
			snd_i1 = m.find('<span style="font-size: small">')
			snd_i2 = m[snd_i1:].find("</span>")
			sender = m[snd_i1+31:snd_i2+snd_i1]
			if sender == "":
				continue
			m = m[snd_i2+snd_i1:]
			# theme
			th_i1 = m.find('<div style="font-size: small; font-size: 9px">')
			th_i2 = m[th_i1+46:].find("</div>")
			theme = m[th_i1+46:th_i2+th_i1+46].replace("\n","").strip()
			if theme == "":
				continue
			m = m[th_i2+th_i1+46:]
			# date
			dt_i1 = m.find('<span style="font-size: small">')
			dt_i2 = m.find("</span>")
			date = m[dt_i1+31:dt_i2]
			mails.append(Mail(sender, theme, date, mail_id))
		return mails

	def get_mail_content_by_id(self, mailid):
		link = "https://my.bukep.ru/MailBukep/Incoming/" + str(mailid) + "?PageNumber=1&isDetail=False"
		html = requests.get(link, cookies=self.cookie, verify=False, allow_redirects=False).text
		cnt_id1 = html.rfind('<span style="border: none; white-space: pre-wrap;">')+51
		cnt_id2 = html[cnt_id1:].find('</span>')
		raw_content = html[cnt_id1:cnt_id2+cnt_id1].replace("\r", "")
		return raw_content