# bukep_bot
Этот бот парсит расписание с [my.bukep.ru](https://my.bukep.ru/), и так как я не нашел API, все данные идут с сайта

# Что именно он делает?
Бот может:
- показывать время до конца пары / перерыва / перерыва между полупарами
- показывать расписание на сегодня / завтра / текущую неделю / следующую неделю

# Чего не хватает для полноценной работы бота
В этой репе нет:
- паролей людей *(это значит нужно будет создать вручную файл user_data.json, в котором будет пустой json массив - это важно!)*
- и так же нет ключа Телеграмм бота *(нужно будет создать бота с помощью BotFather и получить с него код - он вносится в переменную key в `main.py`)*
