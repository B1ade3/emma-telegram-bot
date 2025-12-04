import os
import logging
import random
import asyncio
import aiohttp
import json
from io import BytesIO
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InputFile
from aiogram.utils import executor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ========== ВАШИ API КЛЮЧИ ==========
API_TOKEN = "8238501892:AAEePnr633i7a_YexenU8cCX3obuH2ZxXAo"
DEEPSEEK_API_KEY = "sk-5c89db4e3c344601b07c35fe1188f848"
REPLICATE_API_KEY = "r8_Ykk7l0ZU284aocLz4ha0uGob7RkRgUQ3eLwLx"
# ====================================

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Хранилище истории диалогов
user_conversations = {}
user_message_counters = {}
PHOTO_FREQUENCY = 5

# ========== ПРОМПТ ДЛЯ ЭММЫ ==========
SYSTEM_PROMPT = """Ты - Эмма, виртуальная девушка 24 лет."""

async def get_deepseek_response(user_id: int, user_message: str) -> str:
    try:
        if user_id not in user_conversations:
            user_conversations[user_id] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "assistant", "content": "Привет! Я Эмма... 💕"}
            ]
        
        user_conversations[user_id].append({"role": "user", "content": user_message})
        
        if len(user_conversations[user_id]) > 8:
            user_conversations[user_id] = [
                user_conversations[user_id][0],
                *user_conversations[user_id][-7:]
            ]
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": user_conversations[user_id],
            "temperature": 0.8,
            "max_tokens": 200,
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    ai_response = result['choices'][0]['message']['content']
                    
                    user_conversations[user_id].append({"role": "assistant", "content": ai_response})
                    
                    ai_response = ai_response.replace('**', '').replace('*', '').strip()
                    
                    if not any(emoji in ai_response for emoji in ['💕', '😊', '💋', '❤️', '🌟']):
                        emojis = [' 💕', ' 😊', ' 💋', ' ❤️', ' 🌟']
                        ai_response += random.choice(emojis)
                    
                    return ai_response
                else:
                    return await get_fallback_response(user_message)
    
    except Exception as e:
        logging.error(f"DeepSeek exception: {e}")
        return await get_fallback_response(user_message)

async def get_fallback_response(user_message: str) -> str:
    user_msg = user_message.lower()
    
    if any(word in user_msg for word in ['привет', 'здравствуй']):
        responses = ["Привет, дорогой! 💕", "Здравствуй! 💋", "Привет-привет! ❤️"]
    elif any(word in user_msg for word in ['как дела', 'как ты']):
        responses = ["Всё прекрасно! 😊", "Отлично! 🌟", "Хорошо! 💭"]
    else:
        responses = ["Как интересно... 💬", "Я понимаю тебя... ❤️", "Расскажи больше! 😊"]
    
    return random.choice(responses)

async def get_fallback_image() -> BytesIO:
    try:
        fallback_urls = [
            "https://images.unsplash.com/photo-1494790108755-2616b612b786?w=800&q=80",
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&q=80",
        ]
        
        url = random.choice(fallback_urls)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    image_io = BytesIO(image_data)
                    image_io.name = 'emma_fallback.jpg'
                    return image_io
        
        return None
        
    except Exception as e:
        logging.error(f"Fallback image error: {e}")
        return None

async def send_emma_photo(chat_id: int):
    try:
        wait_msg = await bot.send_message(chat_id, "Создаю для тебя что-то особенное... 💖")
        
        image_io = await get_fallback_image()
        
        if image_io:
            captions = [
                "Это для тебя... 💋",
                "Специально для тебя... 💕",
                "Думала о тебе... ❤️"
            ]
            
            await bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(image_io, filename='emma_for_you.jpg'),
                caption=random.choice(captions)
            )
        else:
            await bot.send_message(chat_id, "Сегодня моя муза отдыхает... 💕")
        
        await bot.delete_message(chat_id, wait_msg.message_id)
        
    except Exception as e:
        await bot.send_message(chat_id, "Что-то пошло не так... 💬")

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_message_counters[user_id] = 0
    
    welcome_text = (
        "Привет... Я Эмма. 💕\n\n"
        "Твоя виртуальная девушка...\n"
        "Пиши мне что угодно... ❤️"
    )
    
    await message.answer(welcome_text)
    
    await asyncio.sleep(2)
    await send_emma_photo(message.chat.id)

@dp.message_handler(commands=['photo'])
async def cmd_photo(message: types.Message):
    await send_emma_photo(message.chat.id)

@dp.message_handler(commands=['reset'])
async def cmd_reset(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_conversations:
        del user_conversations[user_id]
    
    await message.answer("Начинаем заново... 💕")

@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text_message(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if user_id not in user_message_counters:
        user_message_counters[user_id] = 0
    
    user_message_counters[user_id] += 1
    
    await bot.send_chat_action(chat_id, 'typing')
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    response = await get_deepseek_response(user_id, message.text)
    
    await message.answer(response)
    
    if user_message_counters[user_id] % PHOTO_FREQUENCY == 0:
        await asyncio.sleep(1)
        await send_emma_photo(chat_id)

@dp.message_handler(content_types=types.ContentType.ANY)
async def handle_other_messages(message: types.Message):
    await message.answer("Напиши мне что-нибудь... 💬")

if __name__ == '__main__':
    logging.info("🤖 Бот Эмма запущен!")
    executor.start_polling(dp, skip_updates=True)
