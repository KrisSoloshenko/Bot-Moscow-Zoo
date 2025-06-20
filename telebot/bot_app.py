from config import TOKEN, QUESTIONS, ANIMALS
import telebot
from telebot import types
from collections import Counter
import logging
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.parse


# Настройка логирования
logging.basicConfig(
    filename='bot_errors.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

bot = telebot.TeleBot(TOKEN)
user_data = {}

def generate_animal_image(animal_name, animal_image_path=None):
    """Генерация изображения с результатом"""
    if animal_image_path and os.path.exists(animal_image_path):
        try:
            # Открываем локальное изображение
            img = Image.open(animal_image_path)
            img = img.resize((800, 600))

            # Добавляем текст поверх изображения
            d = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()

            d.text((50, 20), "Ваше тотемное животное:", font=font, fill=(255, 255, 255))
            d.text((50, 70), animal_name, font=font, fill=(255, 215, 0))

            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return img_byte_arr
        except Exception as e:
            logging.error(f"Error loading animal image: {e}")

    # Если не удалось загрузить изображение, создаем свое
    img = Image.new('RGB', (800, 600), color=(53, 119, 107))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    d.text((100, 100), "Ваше тотемное животное:", font=font, fill=(255, 255, 255))
    d.text((100, 200), animal_name, font=font, fill=(255, 215, 0))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr


@bot.message_handler(commands=['start'])
def welcome(message):
    """Обработчик команды /start"""
    user_data[message.chat.id] = {
        'answers': [],
        'current_question': 0,
        'name': message.from_user.first_name
    }

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Начать викторину'))
    markup.add(types.KeyboardButton('О программе'))

    bot.send_message(
      message.chat.id,
      f"Привет, {message.from_user.first_name}!\n"
      "Я помогу тебе определить твое тотемное животное.\n"
      "Ответь на несколько вопросов, и я скажу, какой обитатель зоопарка тебе ближе всего!",
      reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == 'О программе')
def about_program(message):
    """Информация о программе опеки"""
    bot.send_message(
        message.chat.id,
        "🐾 *Программа опеки над животными Московского зоопарка*\n\n"
        "Вы можете стать опекуном одного из животных Московского зоопарка, помогая заботиться о нем.\n"
        "Контакты зоопарка:\n"
        "https://moscowzoo.ru/about/guardianship \n"
        "📞 +7 (962) 971-38-75\n"
        "📩 checking.notice.sf@yandex.ru",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == 'Начать викторину')
def start_quiz(message):
    """Начало викторины"""
    user_id = message.chat.id
    user_data[user_id]['current_question'] = 0
    user_data[user_id]['answers'] = []
    ask_question(message.chat.id)

def ask_question(chat_id):
    """Задаем вопрос пользователю"""
    question_num = user_data[chat_id]['current_question']

    if question_num >= len(QUESTIONS):
      finish_quiz(chat_id)
      return

    question_data = QUESTIONS[question_num]
    question_text = list(question_data.keys())[0]
    options = list(question_data.values())[0]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for option in options:
        option_text = list(option.keys())[0]
        markup.add(types.KeyboardButton(option_text))

    bot.send_message(
        chat_id,
        f"Вопрос {question_num + 1}/{len(QUESTIONS)}:\n{question_text}",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True)
def handle_answer(message):
    """Обработка ответов пользователя"""
    user_id = message.chat.id
    if user_id not in user_data:
      return

    question_num = user_data[user_id]['current_question']
    if question_num >= len(QUESTIONS):
      return

    question_data = QUESTIONS[question_num]
    options = list(question_data.values())[0]

    # Проверяем, что ответ соответствует одному из вариантов
    for option in options:
        if message.text in option:
            user_data[user_id]['answers'].append(option[message.text])
            user_data[user_id]['current_question'] += 1
            ask_question(user_id)
            return

    # Если ответ не распознан
    bot.send_message(user_id, "Пожалуйста, выберите один из предложенных вариантов.")

def finish_quiz(chat_id):
    """Завершение викторины и вывод результата"""
    answers = user_data[chat_id]['answers']
    all_animals = [animal for sublist in answers for animal in sublist]

    if not all_animals:
      bot.send_message(chat_id, "Не удалось определить ваше тотемное животное.")
      return

    # Находим самое частое животное
    counter = Counter(all_animals)
    most_common = counter.most_common(1)[0][0]
    animal = ANIMALS.get(most_common)

    if not animal:
        bot.send_message(chat_id, "Не удалось определить ваше тотемное животное.")
        return

    animal_name = animal["name"]
    animal_image_path = animal.get("image")
    full_image_path = os.path.join("images", animal_image_path) if animal_image_path else None
    img = generate_animal_image(animal_name, full_image_path)

    # Кодируем текст для URL
    share_text = urllib.parse.quote(f"Моё тотемное животное - {animal_name}! Узнай и своё!")
    bot.send_photo(
        chat_id,
        img,
        caption=f"🎉 *Поздравляем!*\n\nВаше тотемное животное - *{animal_name}*!\n\n"
                "Хотите узнать больше об этом животном или стать его опекуном? "
                "Напишите нам или посетите наш зоопарк!",
        parse_mode="Markdown"
    )
    share_markup = types.InlineKeyboardMarkup()
    share_markup.add(
        types.InlineKeyboardButton(
            "Поделиться в ВКонтакте",
            url=f"https://vk.com/share.php?url=https://t.me/ZooTotemBot&title={share_text}"
        )
    )
    bot.send_message(
        chat_id,
        "Расскажите друзьям о своем тотемном животном!",
        reply_markup=share_markup
    )

    restart_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    restart_markup.add(types.KeyboardButton('Начать викторину'))
    restart_markup.add(types.KeyboardButton('О программе'))
    bot.send_message(
        chat_id,
        "Хотите пройти викторину еще раз?",
        reply_markup=restart_markup
    )

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
