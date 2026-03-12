import asyncio
import logging
import random
import base64
import sqlite3
import mercadopago
import os
from dotenv import load_dotenv # <--- Import the new library
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)
# Read the tokens securely
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MP_ACCESS_TOKEN = os.getenv('MERCADO_PAGO_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# 2. DATA STORAGE
active_users = set()
paid_users = set() # Users who have paid will be moved here

VIP_GROUP_LINK = "https://t.me/+kUgaXFWy31QyZDM5"

# 2. DATABASE SETUP
def init_db():
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, status TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, status="free"):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, status) VALUES (?, ?)", (user_id, status))
    conn.commit()
    conn.close()

def update_user_status(user_id, status):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
    conn.commit()
    conn.close()

def get_users_by_status(status):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE status = ?", (status,))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

# Initialize DB on startup
init_db()

# Your File IDs
VIDEO_IDS = [
   "BAACAgEAAxkBAAMPabIIvBdIxCDTmaeEpxVHbJq60qkAAl0HAAIjQpFFVqYFGvSIMtQ6BA",
   "BAACAgEAAxkBAAMNabIItjzRkIP0ZSVDzCibTEghBs8AAmAHAAIjQpFF_jRizylbOzI6BA",
   "BAACAgEAAxkBAAMLabIIr072DOYPywr6F0dBQwf2HkgAAmYHAAIjQpFF1A7uQPtTqPA6BA",
   "BAACAgEAAxkBAAMJabIIqoNn5_1-uRCCGHA_qcJLhz4AAmUHAAIjQpFF1b1dxj0EEJQ6BA",
   "BAACAgEAAxkBAAMHabIInxLXfh5OJrfYXmBNrdXctoMAAmQHAAIjQpFF_iVbT35f-Go6BA",
   "BAACAgEAAxkBAAMTabIJuKfRSJ8e7tBaPVmigWfQBQMAAmkHAAIjQpFFwu1QmrdyAqM6BA",
   "BAACAgEAAxkBAAMVabIJv_AqIznB0jO5ztyl-OXKY5sAAmoHAAIjQpFFaEOZuzLrJv06BA",
   "BAACAgEAAxkBAAMXabIJynSiJesNuPRP5ZbicMH0rhIAAmEHAAIjQpFFmmYqpcohUh06BA",
   "BAACAgEAAxkBAAMZabIJ0omin8OTZ9UJIPoLmnlrfEYAAl4HAAIjQpFFrGyfeP1zrUA6BA",
   "BAACAgEAAxkBAAMhabIK-C8FnmSEnPyfh2tS3klRRIsAAmsHAAIjQpFFlII6V9Y5i6s6BA",
   "BAACAgEAAxkBAAMjabILAslLasPir9hl2KOptwABYX3EAAJsBwACI0KRRds6tXtpXDEuOgQ",
   "BAACAgEAAxkBAAMrabILk0GvdOmL61oMeh9aQw25rVkAAm8HAAIjQpFFPg0yJK2Yj0Y6BA",
   "BAACAgEAAxkBAAMtabILmeOf3wjlHC2WDkYdxpV0fYoAAm4HAAIjQpFFtyBQO5vEk1k6BA",
   "BAACAgEAAxkBAAMxabIMN73_Q65AgrAkOUQ17n2wfhYAAnEHAAIjQpFFITlljbIVuqU6BA",
   "BAACAgEAAxkBAAMvabIMMSUAAQU7-tnYaJVWyWMrpe1jAAJwBwACI0KRRc0kTrcmZQtaOgQ",
   "BAACAgEAAxkBAAMzabIMVuODFafw2lou2g_gCS0u-XQAAnIHAAIjQpFFXchqsfQkQ4k6BA",
   "BAACAgEAAxkBAAM1abIMW-Q103ofk2hLVU4MxdbQ3Y8AAnMHAAIjQpFFPP195kRR1eM6BA"
]

# Edit your categories here! It's formatted in 7 rows of 2 columns, plus the 15th at the bottom.
CATEGORIES_LIST = (
    "🔥 Amadores ⠀⠀⠀ 🔥 N0vin44as\n"
    "🔥 Profissionais ⠀🔥 Esc0ndidos\n"
    "🔥 Fav3l4das ⠀⠀⠀⠀ 🔥 Faculdade\n"
    "🔥 C0rn03s ⠀⠀⠀ 🔥 VIP\n"
    "🔥 Vaz4d0ss ⠀⠀⠀⠀ 🔥 L3sbicas\n"
    "🔥 1nc3stxx ⠀⠀⠀ 🔥 H3ntai\n"
    "🔥 Pai e filha ⠀⠀⠀ 🔥 Onl4 F4ns\n"
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀🔥 Muito mais!🔥"
)

# 3. UI MENUS
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💎 Mensal - R$ 12,90", callback_data="buy_mensal"))
    builder.row(types.InlineKeyboardButton(text="👑 Vitalício - R$ 25,90", callback_data="buy_vitalicio"))
    builder.row(types.InlineKeyboardButton(text="ℹ️ Sobre o Premium", callback_data="about"))
    return builder.as_markup()

def payment_menu(pix_code, payment_id):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Verificar Pagamento", callback_data=f"check_{payment_id}"))
    builder.row(types.InlineKeyboardButton(text="📋 Copiar Código PIX", copy_text=types.CopyTextButton(text=pix_code)))
    return builder.as_markup()

# 4. HANDLERS

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    add_user(user_id, "free") # Saves to database
    
    welcome_text = "👋 Bem vindo ao nosso bot exclusivo para conteudos amadores e profissionais!"
    await message.answer(text=welcome_text)
    
    if VIDEO_IDS:
        amount_to_send = min(3, len(VIDEO_IDS)) 
        selected_videos = random.sample(VIDEO_IDS, amount_to_send)
        for video_id in selected_videos:
            await message.answer_video(video=video_id)
            await asyncio.sleep(0.5) 
            
    benefits_text = (
        "🚀 **Não perca e assine agora para ter acesso completo a todas essas categorias:**\n\n"
        f"{CATEGORIES_LIST}\n\n"
        "⭐ *Conteúdo original e exclusivo!*\n\n"
        "👇 Escolha o seu plano abaixo:"
    )
    await message.answer(text=benefits_text, reply_markup=main_menu(), parse_mode="Markdown")

@dp.message(F.video)
async def get_video_id(message: types.Message):
    await message.reply(f"`{message.video.file_id}`", parse_mode="Markdown")

# --- MERCADO PAGO INTEGRATION ---

@dp.callback_query(F.data.startswith("buy_"))
async def handle_payment(callback: types.CallbackQuery):
    await callback.message.answer("⏳ Gerando seu PIX, aguarde um momento...")
    
    price = 12.90 if callback.data == "buy_mensal" else 25.90
    title = "Premium Mensal" if callback.data == "buy_mensal" else "Premium Vitalício"

    payment_data = {
        "transaction_amount": price,
        "description": title,
        "payment_method_id": "pix",
        "payer": {"email": f"user_{callback.from_user.id}@telegrambot.com"}
    }

    result = await asyncio.to_thread(sdk.payment().create, payment_data)
    payment_info = result["response"]

    if "id" in payment_info:
        payment_id = payment_info["id"]
        pix_code = payment_info["point_of_interaction"]["transaction_data"]["qr_code"]
        
        # Extract base64 QR image and convert to bytes
        qr_b64 = payment_info["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        qr_bytes = base64.b64decode(qr_b64)
        photo = BufferedInputFile(qr_bytes, filename="pix_qr.png")

        await callback.message.answer_photo(
            photo=photo,
            caption=f"⚠️ **Pagamento PIX Gerado: {title}**\n\n💰 Valor: R$ {price:.2f}\n\nEscaneie o QR Code acima ou copie o código abaixo:",
            reply_markup=payment_menu(pix_code, payment_id),
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer("❌ Erro ao gerar PIX.")
    await callback.answer()

@dp.callback_query(F.data.startswith("check_"))
async def handle_check_pay(callback: types.CallbackQuery):
    payment_id = callback.data.split("_")[1] 
    
    result = await asyncio.to_thread(sdk.payment().get, payment_id)
    status = result["response"].get("status", "pending")

    if status == "approved":
        user_id = callback.from_user.id
        
        # Update user in Database to 'paid' so they stop getting the 10-minute loop
        update_user_status(user_id, "paid")

        # 1. Send VIP Link & Thank You
        await callback.message.answer(
            "✅ **Pagamento Aprovado!**\n\n"
            "Obrigado pelo pagamento!\n\n"
            f"🔗 **[CLIQUE AQUI PARA ENTRAR NO GRUPO VIP]({VIP_GROUP_LINK})**\n\n"
            "Enquanto você entra no grupo, aproveite essas prévias exclusivas:",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
        # 2. Send 10 Videos
        amount = min(10, len(VIDEO_IDS))
        selected_videos = random.sample(VIDEO_IDS, amount)
        for video_id in selected_videos:
            await bot.send_video(chat_id=user_id, video=video_id)
            await asyncio.sleep(0.5) 
            
    else:
        await callback.answer(f"Status: {status.upper()}. Pagamento ainda não identificado. Tente novamente em 10 segundos.", show_alert=True)

@dp.callback_query(F.data == "about")
async def handle_about(callback: types.CallbackQuery):
    await callback.message.answer("O Premium dá acesso a todos os vídeos completos sem cortes e atualizações diárias! Entre agora e veja todo conteudo completo")
    await callback.answer()

async def preview_loop():
    while True:
        await asyncio.sleep(600) 
        if not VIDEO_IDS:
            continue 
            
        free_users = get_users_by_status("free") # Pulls only free users from DB
        for user_id in free_users: 
            try:
                amount = min(2, len(VIDEO_IDS))
                selected_videos = random.sample(VIDEO_IDS, amount)
                for video_id in selected_videos:
                    await bot.send_video(chat_id=user_id, video=video_id)
                    await asyncio.sleep(0.5)
                
                loop_text = (
                    "🔥 **Você não vai querer perder!** Assine agora para ver o conteúdo completo, "
                    "veja todos os nossos grupos:\n\n"
                    f"{CATEGORIES_LIST}\n\n"
                    "👇 Escolha o seu plano abaixo:"
                )
                await bot.send_message(chat_id=user_id, text=loop_text, reply_markup=main_menu(), parse_mode="Markdown")
            except Exception:
                pass

async def main():
    asyncio.create_task(preview_loop())
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())