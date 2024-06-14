
import requests
import json

class Message():
	def __init__(self, message, user, isBot, channel, messageType):
		self.content = message
		self.user = [user,isBot]
		self.channel = channel
		self.messageType = messageType

	def __repr__(self):
		return "Сообщение от " + self.user[0] + (" (бот) " if self.user[1] else "") + ": " + self.content 

	def isBot(self):
		return self.user[1]

	def username(self):
		return self.user[0]

class ButtonQuery():
	def __init__(self,data,user,isBot,channel,qid):
		self.content = data
		self.user = [user,isBot]
		self.channel = channel
		self.id = qid

	def __repr__(self):
		return "Эвент кнопки от: {}".format(self.user[0]) + ", данные: {}".format(self.content)

class TelegramPyAPI():
	def __init__(self,botKey):
		self.botKey = botKey

		self._base = "https://api.telegram.org/bot" + self.botKey + "/"
		self._prefix = "[TelegramPyAPI]: " 
		self._lastUpdateInt = 0

		if self._validKey():
			self._p2rint("Ключ норм, стартуем")

		try:
			open("./botData.json","r").close()
			self._p2rint("Файл botData.json найден, загружаем данные...")
		except IOError:
			self._p2rint("Нет файла botData.json, создаем новый...")
			open("./botData.json","w").close()

		lastData = None
		lastDataFile = open("./botData.json","r")
		loadedData = lastDataFile.read()
		if(len(loadedData) == 0):
			self._p2rint("В файле botData.json нет данных, не загружаем...")
		else:
			lastData = json.loads(loadedData)
			self._lastUpdateInt = lastData["lui"]
			self._p2rint(f"Нашел последнее сообщение: {self._lastUpdateInt}")
		lastDataFile.close()

	def _validKey(self):
		test = self.pollCommand("getMe")
		if(test["ok"]):
			return True
		else:
			return False

	def _p2rint(self,message):
		print(self._prefix + message)

	@staticmethod
	def InlineButton(name,cb):
		return {"text":name,"callback_data":cb}

	@staticmethod
	def generateInlineKB(buttons: list):
		return {"inline_keyboard": buttons}

	@staticmethod
	def CButton(name):
		return {"text":name}

	def pollCommand(self,command):
		return json.loads(requests.get(self._base + command).content)

	def pollCommandAdvanced(self,command,args):
		return json.loads(requests.get(self._base + command,params=args).content)

	def saveUpdInt(self):
		file = open("./botData.json","w")
		file.write(json.dumps({"lui":self._lastUpdateInt}))
		file.close()
		self._p2rint("Сохранил update_id: " + str(self._lastUpdateInt))

	def getSingleMessage(self):
		if(self._lastUpdateInt != 0):
			res = self.pollCommandAdvanced("getUpdates",{"timeout":30,"offset":self._lastUpdateInt + 1})
		else:
			res = self.pollCommandAdvanced("getUpdates",{"timeout":30})
		if(len(res["result"]) > 0):
			self._lastUpdateInt = res["result"][len(res["result"])-1]["update_id"]
			self.saveUpdInt()
		return res

	def getSMparsed(self):
		msg = self.getSingleMessage()
		isButtonQuery = False
		isMessage = False
		tw = None
		if(msg["result"] != []):
			try:
				tw = msg["result"][0]["callback_query"]
			except Exception:
				pass
			else:
				return ButtonQuery(
					data=msg["result"][0]["callback_query"]["data"],
					user=msg["result"][0]["callback_query"]["message"]["from"]["first_name"],
					isBot=msg["result"][0]["callback_query"]["message"]["from"]["is_bot"],
					channel=msg["result"][0]["callback_query"]["message"]["chat"]["id"],
					qid=msg["result"][0]["callback_query"]["id"]
					)

			try:
				tw = msg["result"][0]["message"]
			except Exception:
				pass
			else:
				try:
					return Message(
						message=msg["result"][0]["message"]["text"],
						user=msg["result"][0]["message"]["from"]["first_name"] + " " + msg["result"][0]["message"]["from"]["last_name"],
						isBot=msg["result"][0]["message"]["from"]["is_bot"],
						channel=msg["result"][0]["message"]["chat"]["id"],
						messageType=msg["result"][0]["message"]["chat"]["type"]
					)
				except Exception:
					return Message(
						message=msg["result"][0]["message"]["text"],
						user=msg["result"][0]["message"]["from"]["first_name"],
						isBot=msg["result"][0]["message"]["from"]["is_bot"],
						channel=msg["result"][0]["message"]["chat"]["id"],
						messageType=msg["result"][0]["message"]["chat"]["type"]
					)
				
		return None

	@staticmethod
	def text_sanitization(text):
		charsToEscape = list(".:-=><!")
		clean = text
		for char in charsToEscape:
			clean = clean.replace(char, "\\"+char)
		return clean

	def sendMessageOnChannel(self,channel,string, useMarkdown=False, silent=False, returnMessageID=False):
		if(useMarkdown):
			res = self.pollCommandAdvanced("sendMessage", args={"chat_id":channel,"text":self.text_sanitization(string),"parse_mode":"MarkdownV2","disable_notification":silent})
		else:
			res = self.pollCommandAdvanced("sendMessage", args={"chat_id":channel,"text":string,"disable_notification":silent})

		if(not res["ok"]):
			print(res)

		if returnMessageID:
			return res["result"]["message_id"]
		else:
			return res["ok"]

	def editMessage(self, channel, message_id, string, useMarkdown=False):
		cntnt = {"chat_id": channel, "message_id": message_id, "text": string}
		if useMarkdown:
			cntnt["parse_mode"] = "MarkdownV2"
			cntnt["text"] = self.text_sanitization(string)
			res = self.pollCommandAdvanced("editMessageText", args=cntnt)
		else:
			res = self.pollCommandAdvanced("editMessageText", args=cntnt)

		if not res["ok"]:
			print("[TelegramPyAPI] Error on edit:", res)

		return res['ok']

	def sendKeyboard(self, channel, string, kb, silent=False, useMarkdown: bool=False):
		res = self.pollCommandAdvanced("sendMessage", args={
			"chat_id": channel,
			"text": self.text_sanitization(string) if useMarkdown else string,
			"reply_markup": kb,
			"disable_notification": silent,
			"parse_mode": "MarkdownV2" if useMarkdown else ""
		})
		if not res["ok"]:
			print(res)
		return res["ok"]

	def removeKeyboard(self, channel: str, string: str, silent: bool=False, useMarkdown: bool=False):
		res = self.pollCommandAdvanced("sendMessage", args={
			"chat_id": channel,
			"text": self.text_sanitization(string) if useMarkdown else string,
			"reply_markup": json.dumps({"remove_keyboard": True}),
			"disable_notification": silent,
			"parse_mode": "MarkdownV2" if useMarkdown else ""
		})
		if not res["ok"]:
			print(res)
		return res["ok"]

	def answerButton(self,channel,qid,string=None,showAlert=False):
		if(string is None):
			args = {"callback_query_id":qid}
		elif(string is not None):
			args = {"callback_query_id":qid,"text":string,"show_alert":showAlert}
		res = self.pollCommandAdvanced("answerCallbackQuery", args=args)
		return res["ok"]

	def answerButtonF(self,msg,string=None,showAlert=False):
		return self.answerButton(msg.channel,msg.id,string,showAlert)