This is a Telegram Bot, which can create different timetables of your subjects in the Jagiellonian University!

To run the code of this bot on your device you have to:
 - Create your own Telegram Bot by BotFather
 - Download a Python Interpreter of the newest version
 - Clone the project from GitHub
 - Install aiogram, httpx and python-dotenv libraries
 - Add a .env file to the project (the name of the file should be exactly .env, without any additional letters at the beginning)
 - Write TOKEN=... in the .env file, where ... means the code of your Telegram Bot given by BotFather
 - Run the code!

To run the code in the terminal:
```commandline
git clone https://github.com/AndriyBor/UJ_Timetable_Bot.git
cd UJ_Timetable_Bot
python -m venv .venv
source .venv/bin/activate
pip install aiogram httpx python-dotenv
python UJ_Timetable.py
```

In order to start the bot, type /start. Pay attention, that you should give the **codes** of the subjects, not their names. The codes are available on the USOSWeb. Have fun!

Technical notes:
 - Written on Python 3.13 with the usage of aiogram, httpx and python-dotenv
 - Time complexity of the timetable generation algorithm: $O(\prod_{i=1}^{s}\prod_{j=1}^{c_i}g_{ij}*\sum_{k=1}^{s}c_k)$, where $s$ is the number of subjects, $c_i$ - number of class types in the $i$-th subject, $g_{ij}$ - number of groups of $j$-th class type in the $i$-th subject. Considering the easiest case, when each subject has one lecture and $g$ practice groups, time complexity becomes $O(g^s*s)$
 - Binary search used. However, the logarithmic complexity of it was not used in the time complexity above, because it is only used, when we want to find an index where to insert a lesson in a particular day, while the number of lessons at the day is usually not greater than 4, so as a result the time complexity of binary search tends to $O(1)$.
 - Communication with USOS API used. Currently, massive usage of the bot can cause ban of the server IP, because of the Rate Limit.