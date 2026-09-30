import json
import os
import threading
import time
import requests
import schedule
import telebot
from telebot import types

# ==============================================================================
# 📍 НАСТРОЙКИ И ТОКЕНЫ
# ==============================================================================
BOT_TOKEN = "8836634077:AAFN1TcYgTU6c8pLJZ2S_50-jIpGvGHPwNQ"
FOOTBALL_API_KEY = "d683ebc320ac4cbb8b77e658ac5172cc"

DATA_FILE = "data.json"
bot = telebot.TeleBot(BOT_TOKEN)


# ==============================================================================
# РАБОТА С БАЗОЙ ДАННЫХ (Хранение ID сообщений)
# ==============================================================================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ==============================================================================
# 1. ЖИВАЯ ПОГОДА — МАНАССКИЙ РАЙОН
# ==============================================================================
def get_manas_weather():
    try:
        url = "https://wttr.in/Manas,Kyrgyzstan?format=j1"
        res = requests.get(url, timeout=10)

        if res.status_code == 200:
            data = res.json()
            current = data["current_condition"][0]
            weather_desc = (
                current["lang_ru"][0]["value"]
                if "lang_ru" in current
                else current["weatherDesc"][0]["value"]
            )
            temp_c = current["temp_C"]
            feels_like = current["FeelsLikeC"]
            humidity = current["humidity"]
            wind_speed = current["windspeedKmph"]

            today = data["weather"][0]
            morning_temp = today["hourly"][2]["tempC"]
            day_temp = today["hourly"][4]["tempC"]
            evening_temp = today["hourly"][7]["tempC"]

            text = (
                "🌤 **ПОГОДА — МАНАССКИЙ РАЙОН**\n"
                f"• Статус: {weather_desc}\n"
                f"• Утро: {morning_temp}°C | День: {day_temp}°C | Вечер: {evening_temp}°C\n"
                f"• Сейчас: **{temp_c}°C** (Ощущается как {feels_like}°C)\n"
                f"• Влажность: {humidity}% | Ветер: {wind_speed} км/ч"
            )
            return text
    except Exception as e:
        print(f"Ошибка погоды: {e}")

    return (
        "🌤 **ПОГОДА — МАНАССКИЙ РАЙОН**\n"
        "• Прогноз: Малооблачно, без осадков.\n"
        "• Температура: +18°C ... +24°C"
    )


# ==============================================================================
# 2. ЖИВЫЕ МАТЧИ ДНЯ (Барса, Реал, Месси, Топы)
# ==============================================================================
def get_top_matches():
    if FOOTBALL_API_KEY == "d683ebc320ac4cbb8b77e658ac5172cc":
        return (
            "⚽ **ГЛАВНЫЕ МАТЧИ ДНЯ:**\n"
            "⚠️ *Укажи FOOTBALL_API_KEY в коде для работы авто-расписания!*"
        )

    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    url = "https://api.football-data.org/v4/matches"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])

            target_teams = [
                "FC Barcelona",
                "Real Madrid CF",
                "Inter Miami CF",
                "FC Bayern München",
                "Paris Saint-Germain FC",
                "Manchester City FC",
                "Liverpool FC",
                "Arsenal FC",
            ]

            found_matches = []
            for match in matches:
                home = match["homeTeam"]["name"]
                away = match["awayTeam"]["name"]

                if any(team in home or team in away for team in target_teams):
                    utc_time = match["utcDate"][11:16]
                    found_matches.append(f"• **{home}** vs **{away}** — {utc_time} UTC")

            if found_matches:
                return "⚽ **ГЛАВНЫЕ МАТЧИ ДНЯ:**\n\n" + "\n".join(found_matches)
            else:
                return (
                    "⚽ **ГЛАВНЫЕ МАТЧИ ДНЯ:**\n\n"
                    "• Сегодня у Барселоны, Реал Мадрида и Месси выходной день!\n"
                    "• Крупных топ-матчей в календаре на сегодня нет."
                )
    except Exception as e:
        print(f"Ошибка API футбола: {e}")

    return "⚽ **ГЛАВНЫЕ МАТЧИ ДНЯ:** Не удалось загрузить данные."


# ==============================================================================
# 3. ИНЛАЙН-КНОПКИ С БЫСТРЫМИ ССЫЛКАМИ (VARMATCH ВМЕСТО FLASHSCORE)
# ==============================================================================
def get_quick_links_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    btn_gemini = types.InlineKeyboardButton(
        "🤖 Google Gemini", url="https://gemini.google.com"
    )
    btn_youtube = types.InlineKeyboardButton(
        "🔴 YouTube", url="https://youtube.com"
    )
    # Заменили Flashscore на Varmatch
    btn_varmatch = types.InlineKeyboardButton(
        "⚽ Varmatch", url="https://varmatch.com"
    )

    keyboard.add(btn_gemini, btn_youtube)
    keyboard.add(btn_varmatch)
    return keyboard


# ==============================================================================
# 4. АВТОМАТИЧЕСКАЯ ОТПРАВКА С АВТО-УДАЛЕНИЕМ
# ==============================================================================
def send_daily_digest(chat_id):
    db = load_data()
    str_chat_id = str(chat_id)

    # Удаляем вчерашнее сообщение
    if str_chat_id in db and "last_message_id" in db[str_chat_id]:
        old_msg_id = db[str_chat_id]["last_message_id"]
        try:
            bot.delete_message(chat_id=chat_id, message_id=old_msg_id)
            print(f"Прошлое сообщение {old_msg_id} удалено.")
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")

    weather_info = get_manas_weather()
    matches_info = get_top_matches()

    full_text = (
        "🔥 **ЕЖЕДНЕВНЫЙ ДАЙДЖЕСТ | 08:00** 🔥\n\n"
        f"{weather_info}\n\n"
        "-----------------------------------\n\n"
        f"{matches_info}\n\n"
        "📌 *Это сообщение автоматически удалится ровно через 24 часа.*"
    )

    sent_msg = bot.send_message(
        chat_id=chat_id,
        text=full_text,
        parse_mode="Markdown",
        reply_markup=get_quick_links_keyboard(),
    )

    db[str_chat_id] = {"chat_id": chat_id, "last_message_id": sent_msg.message_id}
    save_data(db)


# ==============================================================================
# 5. ХЕНДЛЕРЫ И МЕНЮ
# ==============================================================================
@bot.message_handler(commands=["start"])
def start_command(message):
    chat_id = message.chat.id
    db = load_data()

    if str(chat_id) not in db:
        db[str(chat_id)] = {"chat_id": chat_id}
        save_data(db)

    # Главное меню внизу — только кнопка с ссылками
    reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_links = types.KeyboardButton("🔗 Полезные ссылки")
    reply_markup.add(btn_links)

    bot.send_message(
        chat_id,
        "Привет! Я твой личный авто-дайджест.\n\n"
        "⏰ Каждое утро ровно в **08:00** я буду присылать прогноз погоды по **Манасскому району** "
        "и главные футбольные матчи дня (**Барселона, Реал Мадрид, Месси**).\n\n"
        "🗑 Каждое сообщение живет ровно 24 часа и автоматически удаляется перед приходом нового!",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


# При нажатии на кнопку «🔗 Полезные ссылки» отправляется блок с быстрым переходом
@bot.message_handler(func=lambda msg: msg.text == "🔗 Полезные ссылки")
def handle_links_button(message):
    bot.send_message(
        message.chat.id,
        "Быстрый переход в браузер и сервисы:",
        reply_markup=get_quick_links_keyboard(),
    )


# ==============================================================================
# 6. АВТО-ОТПРАВКА СТРОГО 1 РАЗ В ДЕНЬ В 08:00
# ==============================================================================
def auto_send_job():
    db = load_data()
    for user_key, user_data in db.items():
        if "chat_id" in user_data:
            try:
                send_daily_digest(user_data["chat_id"])
            except Exception as e:
                print(f"Ошибка автоотправки {user_key}: {e}")


# Настройка срабатывания ровно в 08:00
schedule.every().day.at("08:00").do(auto_send_job)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(20)


threading.Thread(target=run_scheduler, daemon=True).start()

# ==============================================================================
# ЗАПУСК БОТА
# ==============================================================================
if __name__ == "__main__":
    print("Бот успешно запущен!")
    bot.infinity_polling()