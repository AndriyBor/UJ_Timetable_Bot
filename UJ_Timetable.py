import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import httpx
from datetime import datetime
import os
from dotenv import load_dotenv

class Subject:
    def __init__(self, code, semester, units, name, teachers):
        self.code = code
        self.sem = semester
        self.units = units
        self.name = name
        self.teachers = teachers

class Teacher:
    def __init__(self, allowed, first_name, last_name, class_type):
        self.allowed = allowed
        self.first_name = first_name
        self.last_name = last_name
        self.class_type = class_type

class Time:
    def __init__(self, day, start_time, end_time):
        self.day = day
        self.start_time = start_time
        self.end_time = end_time

def binar(arr, elem):
    left, right = -1, len(arr)
    while left < right - 1:
        mid = (left + right) // 2
        if arr[mid][0] > elem:
            right = mid
        else:
            left = mid
    return right


def generate_timetables(times, subjects, minim, maxim):
    ans = []
    perm = [[0 for ind_unit in range(len(subjects[ind_subject].units))] for ind_subject in range(len(subjects))]
    while True:
        curr = [[] for i in range(5)]
        good = True
        for ind_subject in range(len(perm)):
            name = subjects[ind_subject].name
            for ind_unit in range(len(perm[ind_subject])):
                form = times[name][ind_unit][-1]
                group = perm[ind_subject][ind_unit]
                for lesson in range(len(times[name][ind_unit][group])):
                    time = times[name][ind_unit][group][lesson]
                    day, start_time, end_time = time.day, time.start_time, time.end_time
                    ind = binar(curr[day], start_time)
                    if (ind == 0 or curr[day][ind - 1][3] == form == "Wykład" or minim <= start_time -
                        curr[day][ind - 1][1]) and (
                            ind == len(curr[day]) or curr[day][ind][3] == form == "Wykład" or minim <=
                            curr[day][ind][0] - end_time):
                        curr[day].insert(ind, [start_time, end_time, name, form])
                    else:
                        good = False
                        break
                if not good:
                    break
            if not good:
                break
        if good:
            for day in range(5):
                for lesson in range(1, len(curr[day])):
                    if curr[day][lesson][0] - curr[day][lesson - 1][1] > maxim and not (
                            curr[day][lesson][3] == curr[day][lesson - 1][3] == "Wykład"):
                        good = False
                        break
                if not good:
                    break
            if good:
                ans.append(curr)
        next_done = False
        for ind_subject in range(len(perm)):
            name = subjects[ind_subject].name
            for ind_unit in range(len(perm[ind_subject])):
                if perm[ind_subject][ind_unit] == len(times[name][ind_unit]) - 2:
                    perm[ind_subject][ind_unit] = 0
                else:
                    perm[ind_subject][ind_unit] += 1
                    next_done = True
                    break
            if next_done:
                break
        if not next_done:
            return ans


def print_timetable(chosen):
    text = ""
    days = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
    for day in range(5):
        text += days[day] + "\n"
        if not chosen[day]:
            text += "Nie ma zajęć!!!\n"
        else:
            for lesson in range(len(chosen[day])):
                start, end = chosen[day][lesson][0], chosen[day][lesson][1]
                time1 = f"{start // 60:02d}:{start % 60:02d}"
                time2 = f"{end // 60:02d}:{end % 60:02d}"
                text += str(lesson + 1) + ". " + chosen[day][lesson][2] + " " + chosen[day][lesson][
                    3] + " " + time1 + "-" + time2 + "\n"
        text += "\n"
    return text


load_dotenv()
token = os.getenv("TOKEN")
bot = Bot(token)
dp = Dispatcher()

class_types = dict()


class Form(StatesGroup):
    collect = State()
    ques = State()
    make = State()
    trans = State()


@dp.startup()
async def on_startup():
    global class_types
    async with httpx.AsyncClient() as client:
        response = await client.get("https://apps.usos.uj.edu.pl/services/courses/classtypes_index")
        class_types = response.json()


@dp.message(Command("start"))
async def st(message: types.Message):
    text = "Hello! This is a bot, which can help you make such a timetable of lessons at the Jagiellonian University, as you want!\n"
    text += "I ask you only the codes of your subjects, which you can take from the USOSWeb.\n"
    text += "Type /create if you want to start."
    await message.answer(text)


@dp.message(Command("create"))
async def create(message: types.Message, state: FSMContext):
    await message.answer(
        "Type the codes of the subjects you want to choose. If you want to cancel the last subject, type /del. If you mentioned all the courses you need, type /stop.")
    await state.update_data(subjects=[])
    await state.set_state(Form.collect)


@dp.message(Form.collect)
async def collect(message: types.Message, state: FSMContext):
    data = await state.get_data()
    subjects = data.get("subjects", [])
    if message.text == "/stop":
        await message.answer("What's the <b>minimum</b> break time you're OK with? Write in minutes.", parse_mode='HTML')
        await state.set_state(Form.ques)
    elif message.text == "/del":
        if not subjects:
            await message.answer("There's no subject to delete.")
        else:
            subjects.pop()
            await message.answer("Deleted")
            await state.update_data(subjects=subjects)
        await state.set_state(Form.collect)
    else:
        try:
            async with httpx.AsyncClient() as client:
                response1 = await client.get(
                    "https://apps.usos.uj.edu.pl/services/courses/course?course_id=" + message.text + "&fields=terms")
                sem = response1.json()["terms"][0]["id"]
                response2 = await client.get(
                    "https://apps.usos.uj.edu.pl/services/courses/course_edition?course_id=" + message.text + "&term_id=" + sem + "&fields=course_units_ids")
                units = response2.json()["course_units_ids"]
                response3 = await client.get(
                    "https://apps.usos.uj.edu.pl/services/courses/course?course_id=" + message.text)
                name = response3.json()["name"]["pl"]
                subjects.append(Subject(message.text, sem, units, name, []))
                teachers = []
                counts = []
                buttons = InlineKeyboardBuilder()
                for ind_unit in range(len(units)):
                    teachers.append(dict())
                    counts.append(0)
                    response = await client.get(
                        "https://apps.usos.uj.edu.pl/services/groups/group?course_unit_id=" + units[
                            ind_unit] + "&group_number=1&fields=class_type_id|lecturers")
                    info = response.json()
                    group = 1
                    while "message" not in info:
                        class_type = class_types[info["class_type_id"]]["name"]["pl"]
                        for teacher in info["lecturers"]:
                            prev_len = len(teachers[ind_unit])
                            teachers[ind_unit][teacher["id"]] = Teacher(True, teacher["first_name"], teacher["last_name"], class_type)
                            if len(teachers[ind_unit]) != prev_len:
                                counts[-1] += 1
                                buttons.add(types.InlineKeyboardButton(
                                    text="✅ " + teacher["first_name"] + " " + teacher["last_name"] + " (" + class_type + ")",
                                    callback_data=str(ind_unit) + " " + teacher["id"]))
                        group += 1
                        response = await client.get(
                            "https://apps.usos.uj.edu.pl/services/groups/group?course_unit_id=" + units[
                                ind_unit] + "&group_number=" + str(group) + "&fields=class_type_id|lecturers")
                        info = response.json()
                await state.update_data(subjects=subjects, teachers=teachers, counts=counts)
                buttons.add(types.InlineKeyboardButton(text="Choice done", callback_data="/stop"))
                buttons.adjust(1)
                await message.answer(
                    "Please, choose the teachers you're OK with. Note, that you have to choose at least one teacher for each type of the lesson.",
                    reply_markup=buttons.as_markup())
        except Exception as err:
            print(err)
            await message.answer(
                "Wrong subject code. Please, try again.")
            await state.set_state(Form.collect)


@dp.callback_query()
async def choosing(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if call.data == "Yes":
        await call.answer()
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer("What's the <b>minimum</b> break time you're OK with? Write in minutes.",
                             parse_mode='HTML')
        await state.set_state(Form.ques)
    elif call.data == "No":
        await call.answer()
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer(
            "Thank you for using this bot, I hope it was useful!\nIf you want to create a new timetable, type /create")
    elif call.data == "/stop":
        await call.answer()
        await call.message.edit_reply_markup(reply_markup=None)
        subjects, teachers = data.get("subjects", []), data.get("teachers", [])
        subjects[-1].teachers = teachers
        await state.update_data(subjects=subjects)
        await call.message.answer("Accepted. Please, continue.")
        await state.set_state(Form.collect)
    else:
        num, teacher_id = call.data.split()
        num = int(num)
        subjects, teachers, counts = data.get("subjects", []), data.get("teachers", []), data.get("counts", [])
        if not teachers[num][teacher_id].allowed:
            teachers[num][teacher_id].allowed = True
            counts[num] += 1
        elif counts[num] > 1:
            teachers[num][teacher_id].allowed = False
            counts[num] -= 1
        else:
            await call.answer("You can't delete all the teachers for a specific type of the lessons", show_alert=True)
            return
        await state.update_data(teachers=teachers, counts=counts)
        await call.answer()
        buttons = InlineKeyboardBuilder()
        for num in range(len(teachers)):
            for iden in teachers[num].keys():
                begin = "✅ "
                if not teachers[num][iden].allowed:
                    begin = "❌ "
                buttons.add(types.InlineKeyboardButton(
                    text=begin + teachers[num][iden].first_name + " " + teachers[num][iden].last_name + " (" + teachers[num][iden].class_type + ")",
                    callback_data=str(num) + " " + iden))
        buttons.add(types.InlineKeyboardButton(text="Choice done", callback_data="/stop"))
        buttons.adjust(1)
        await call.message.edit_reply_markup(reply_markup=buttons.as_markup())


@dp.message(Form.ques)
async def ques(message: types.Message, state: FSMContext):
    if not (message.text.isdigit()):
        await message.answer("Cannot recognise a number, please, try again.")
        await state.set_state(Form.ques)
    else:
        await message.answer("What's the <b>maximum</b> break time you're OK with? Write in minutes.", parse_mode='HTML')
        await state.update_data(minim=int(message.text))
        await state.set_state(Form.make)


@dp.message(Form.make)
async def make(message: types.Message, state: FSMContext):
    data = await state.get_data()
    subjects = data.get("subjects", [])
    minim = data.get("minim")
    if not (message.text.isdigit()):
        await message.answer("Cannot recognise a number, please, try again.")
        await state.set_state(Form.make)
    else:
        maxim = int(message.text)
        await message.answer("Your subjects:")
        for i in range(len(subjects)):
            await message.answer(str(i + 1) + ". " + subjects[i].name + " " + subjects[i].sem)
        await message.answer("Creating different timetables...")

        times = dict()
        try:
            async with httpx.AsyncClient() as client:
                for ind_subject in range(len(subjects)):
                    name = subjects[ind_subject].name
                    teachers = subjects[ind_subject].teachers
                    times[name] = []
                    date = "20" + subjects[ind_subject].sem[:2] + "-10-02"
                    if subjects[ind_subject].sem[-1] == 'L':
                        date = "20" + subjects[ind_subject].sem[3:5] + "-03-02"
                    for ind_unit in range(len(subjects[ind_subject].units)):
                        group = 1
                        unit = subjects[ind_subject].units[ind_unit]
                        times[name].append([])
                        response = await client.get(
                            "https://apps.usos.uj.edu.pl/services/tt/classgroup?unit_id=" + unit + "&group_number=" + str(
                                group) + "&start=" + date + "&fields=start_time|end_time|name|lecturer_ids")
                        info = response.json()
                        if not info:
                            response = await client.get(
                                "https://apps.usos.uj.edu.pl/services/tt/classgroup?unit_id=" + unit + "&group_number=" + str(
                                    group) + "&start=" + date[:-1] + "9&fields=start_time|end_time|name|lecturer_ids")
                            info = response.json()
                        while info:
                            good = True
                            for iden in info[0]["lecturer_ids"]:
                                if not teachers[ind_unit][str(iden)].allowed:
                                    good = False
                                    break
                            if good:
                                times[name][ind_unit].append([])
                                for lesson in range(len(info)):
                                    start, end = info[lesson]["start_time"], info[lesson]["end_time"]
                                    year, month, day = int(start[:4]), int(start[5:7]), int(start[8:10])
                                    num = datetime(year, month, day).weekday()
                                    start_time = int(start[11:13]) * 60 + int(start[14:16])
                                    end_time = int(end[11:13]) * 60 + int(end[14:16])
                                    times[name][ind_unit][-1].append(Time(num, start_time, end_time))
                            group += 1
                            response = await client.get(
                                "https://apps.usos.uj.edu.pl/services/tt/classgroup?unit_id=" + unit + "&group_number=" + str(
                                    group) + "&start=" + date + "&fields=start_time|end_time|name|lecturer_ids")
                            info = response.json()
                            if not info:
                                response = await client.get(
                                    "https://apps.usos.uj.edu.pl/services/tt/classgroup?unit_id=" + unit + "&group_number=" + str(
                                        group) + "&start=" + date[:-1] + "9&fields=start_time|end_time|name|lecturer_ids")
                                info = response.json()
                        response = await client.get(
                            "https://apps.usos.uj.edu.pl/services/tt/classgroup?unit_id=" + unit + "&group_number=1&start=" + date)
                        info = response.json()
                        if not info:
                            response = await client.get(
                                "https://apps.usos.uj.edu.pl/services/tt/classgroup?unit_id=" + unit + "&group_number=1&start=" + date[
                                    :-1] + "9")
                            info = response.json()
                        times[name][ind_unit].append(info[0]["name"]["pl"])
        except Exception as err:
            print(err)
            await message.answer("Something went wrong during the communication with the USOS API server, please, try again later.")

        timetables = generate_timetables(times, subjects, minim, maxim)
        if not timetables:
            buttons = InlineKeyboardBuilder()
            buttons.add(types.InlineKeyboardButton(text="Yes", callback_data="Yes"))
            buttons.add(types.InlineKeyboardButton(text="No", callback_data="No"))
            buttons.adjust(1)
            await message.answer(
                "Sorry, there's no timetable satisfied your criteria :(\nDo you want to change the break time range?",
                reply_markup=buttons.as_markup())
            return

        min_sum_breaks = []
        min_sum_days = []
        later_start = []
        for timetable in range(len(timetables)):
            sum_breaks = 0
            sum_days = 0
            start = 1440
            for day in range(5):
                sum_days += (len(timetables[timetable][day]) != 0)
                if len(timetables[timetable][day]) > 0 and timetables[timetable][day][0][-1] != "Wykład":
                    start = min(start, timetables[timetable][day][0][0])
                for lesson in range(1, len(timetables[timetable][day])):
                    sum_breaks += timetables[timetable][day][lesson][0] - timetables[timetable][day][lesson - 1][1]
                    if timetables[timetable][day][lesson][-1] != "Wykład":
                        start = min(start, timetables[timetable][day][lesson][0])
            min_sum_breaks.append([sum_breaks, timetables[timetable]])
            min_sum_days.append([sum_days, timetables[timetable]])
            later_start.append([start, timetables[timetable]])
        min_sum_breaks.sort(reverse=True)
        min_sum_days.sort(reverse=True)
        later_start.sort()

        buttons = ReplyKeyboardBuilder()
        buttons.add(types.KeyboardButton(text="Minimum sum of break times"))
        buttons.add(types.KeyboardButton(text="Minimum number of days"))
        buttons.add(types.KeyboardButton(text="Later start each day (lectures excluded)"))
        buttons.adjust(1)
        await message.answer("I generated " + str(
            len(timetables)) + " timetables for you! Which criteria of a timetable do you consider optimal?\nClicking the same button for several times will return you the next generated timetable.\nIf you want to stop generating, type /stop",
                          reply_markup=buttons.as_markup(resize_keyboard=True))
        await state.update_data(min_sum_breaks=min_sum_breaks, min_sum_days=min_sum_days, later_start=later_start)
        await state.set_state(Form.trans)


@dp.message(Form.trans)
async def trans(message: types.Message, state: FSMContext):
    data = await state.get_data()
    min_sum_breaks = data.get("min_sum_breaks", [])
    min_sum_days = data.get("min_sum_days", [])
    later_start = data.get("later_start", [])
    if message.text == "/stop":
        await message.answer(
            "Thank you for using this bot, I hope it was useful!\nIf you want to create a new timetable, type /create",
            reply_markup=types.ReplyKeyboardRemove())
    elif message.text == "Minimum sum of break times":
        if not min_sum_breaks:
            await message.answer("Sorry, there's no timetable left.")
        else:
            await message.answer(print_timetable(min_sum_breaks[-1][1]))
            min_sum_breaks.pop()
            await state.update_data(min_sum_breaks=min_sum_breaks)
        await state.set_state(Form.trans)
    elif message.text == "Minimum number of days":
        if not min_sum_days:
            await message.answer("Sorry, there's no timetable left.")
        else:
            await message.answer(print_timetable(min_sum_days[-1][1]))
            min_sum_days.pop()
            await state.update_data(min_sum_days=min_sum_days)
        await state.set_state(Form.trans)
    elif message.text == "Later start each day (lectures excluded)":
        if not later_start:
            await message.answer("Sorry, there's no timetable left.")
        else:
            await message.answer(print_timetable(later_start[-1][1]))
            later_start.pop()
            await state.update_data(later_start=later_start)
        await state.set_state(Form.trans)
    else:
        await message.answer("I have no such optimality criteria, try again.")
        await state.set_state(Form.trans)


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
