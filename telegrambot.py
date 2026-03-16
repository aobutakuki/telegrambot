import asyncio
import logging
import random
import base64
import sqlite3
import mercadopago
import os
import datetime # <--- NOVA BIBLIOTECA PARA LIDAR COM DATAS
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)
load_dotenv()

# Read the tokens securely
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MP_ACCESS_TOKEN = os.getenv('MERCADO_PAGO_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID') # <--- ID NUMÉRICO DO ADMIN PARA O RELATÓRIO

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# 1. EMOJIS PREMIUM (TAGS HTML)
# ==========================================
E_CIFRAO = '<tg-emoji emoji-id="5197434882321567830">💲</tg-emoji>'
E_RAIO = '<tg-emoji emoji-id="5456140674028019486">⚡</tg-emoji>'
E_SININHO = '<tg-emoji emoji-id="5458603043203327669">🔔</tg-emoji>'
E_DIAMANTE = '<tg-emoji emoji-id="5427168083074628963">💎</tg-emoji>'
E_FOGO = '<tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji>'
E_MEDALHA = '<tg-emoji emoji-id="5440539497383087970">🥇</tg-emoji>'
E_AVIAO = '<tg-emoji emoji-id="5201691993775818138">💸</tg-emoji>'
E_VERIFICADO = '<tg-emoji emoji-id="5251203410396458957">✅</tg-emoji>'
E_SALE = '<tg-emoji emoji-id="5406683434124859552">🛍️</tg-emoji>'

# ==========================================
# 2. DATA STORAGE & DATABASE (ATUALIZADO PARA MÉTRICAS)
# ==========================================
VIP_GROUP_LINK = "https://t.me/+kUgaXFWy31QyZDM5"

def init_db():
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, status TEXT)''')
    
    # Tenta adicionar as novas colunas caso o banco já exista com a versão antiga
    try:
        c.execute("ALTER TABLE users ADD COLUMN joined_date TEXT")
        c.execute("ALTER TABLE users ADD COLUMN payment_clicks INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Colunas já existem, segue o jogo
        
    conn.commit()
    conn.close()

def add_user(user_id, status="free"):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    today = datetime.date.today().isoformat()
    # Adiciona usuário salvando a data de hoje
    c.execute("INSERT OR IGNORE INTO users (user_id, status, joined_date, payment_clicks) VALUES (?, ?, ?, 0)", (user_id, status, today))
    conn.commit()
    conn.close()

def update_user_status(user_id, status):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
    conn.commit()
    conn.close()

def increment_payment_click(user_id):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    # Soma +1 nos cliques de pagamento desse usuário
    c.execute("UPDATE users SET payment_clicks = payment_clicks + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_users_by_status(status):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE status = ?", (status,))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_daily_stats():
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    today = datetime.date.today().isoformat()
    
    # Usuários que entraram HOJE
    c.execute("SELECT COUNT(*) FROM users WHERE joined_date = ?", (today,))
    new_users = c.fetchone()[0]
    
    # Total geral de usuários
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    # Total de usuários que já geraram algum PIX
    c.execute("SELECT COUNT(*) FROM users WHERE payment_clicks > 0")
    total_clicks = c.fetchone()[0]
    
    # Total de assinantes pagos
    c.execute("SELECT COUNT(*) FROM users WHERE status = 'paid'")
    paid_users = c.fetchone()[0]
    
    conn.close()
    return new_users, total_users, total_clicks, paid_users

init_db()

# ==========================================
# 3. CONTEÚDO (VÍDEOS E CATEGORIAS)
# ==========================================
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
   "BAACAgEAAxkBAAM1abIMW-Q103ofk2hLVU4MxdbQ3Y8AAnMHAAIjQpFFPP195kRR1eM6BA",
   "BAACAgEAAxkBAAIeVGm4M7EkInHKFuWd3pxzcJbJ_mEeAAKcBwACThTJRUl5MeTp3eGWOgQ",
   "BAACAgEAAxkBAAIeVmm4M9SxxmnjkXaYPcMe_Bzxv0TDAAKdBwACThTJRRq-SybBNY5EOgQ",
   "BAACAgEAAxkBAAIeWGm4M_PduKTUKo9nBz9HLa3N6iFTAAKfBwACThTJRVCyBZIEaTS9OgQ",
   "BAACAgEAAxkBAAIeWmm4NARVVIe400WONLx0QvYAAW7W0AACoAcAAk4UyUULSCi_3FzHoToE",
   "BAACAgEAAxkBAAIeXGm4NBkPVy2LcEef0XiuoStpmyABAAKhBwACThTJReNfVqvI3Yh5OgQ",
   "BAACAgEAAxkBAAIew2m4XFilPo1eVgaDW2NJvBMgkITBAAK5BwACThTJRWaWHWS1PlMkOgQ",
   "BAACAgEAAxkBAAIexWm4XG6WjRejXg8CKDa1C-s7dunWAAK6BwACThTJRQABVwo0rWHTbzoE",
   "BAACAgEAAxkBAAIex2m4XIJmKCovloEXEX5CHlqu4gGUAAK8BwACThTJRawsqJNTxLLpOgQ"
]

CATEGORIES_LIST = (
    f"{E_FOGO} Amadores\n"
    f"{E_FOGO} Profissionais\n"
    f"{E_FOGO} Fav3l4das\n"
    f"{E_FOGO} C0rn03s\n"
    f"{E_FOGO} Vaz4d0ss\n"
    f"{E_FOGO} N0vin44as\n"
    f"{E_FOGO} Esc0ndidos\n"
    f"{E_FOGO} Faculdade\n"
    f"{E_FOGO} VIP\n"
    f"{E_FOGO} ...e muito mais!"
)

# ==========================================
# 4. MENUS UI
# ==========================================
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💎 Mensal - R$ 12,90", callback_data="buy_mensal"))
    builder.row(types.InlineKeyboardButton(text="👑 3 Meses - R$ 25,90", callback_data="buy_trimestral"))
    builder.row(types.InlineKeyboardButton(text="ℹ️ Sobre o VIP / Dúvidas", callback_data="about"))
    return builder.as_markup()

def payment_menu(pix_code, payment_id):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Verificar Pagamento", callback_data=f"check_{payment_id}"))
    builder.row(types.InlineKeyboardButton(text="📋 Copiar Código PIX", copy_text=types.CopyTextButton(text=pix_code)))
    return builder.as_markup()

# ==========================================
# 5. HANDLERS
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    add_user(user_id, "free")
    
    welcome_text = f"<b>BEM VINDO AO BOT IMAGINE 24</b> {E_VERIFICADO}\n\nO seu bot exclusivo para conteúdos amadores e profissionais!"
    await message.answer(text=welcome_text, parse_mode="HTML")
    
    if VIDEO_IDS:
        amount_to_send = min(3, len(VIDEO_IDS)) 
        selected_videos = random.sample(VIDEO_IDS, amount_to_send)
        for video_id in selected_videos:
            await message.answer_video(video=video_id)
            await asyncio.sleep(0.5) 
            
    benefits_text = (
        f"{E_RAIO} <b>Não perca tempo e assine agora para ter acesso completo a todas as categorias:</b>\n\n"
        f"{CATEGORIES_LIST}\n\n"
        f"{E_SALE} <b>Promoção Ativa!</b> Preços reduzidos por tempo limitado.\n"
        f"{E_AVIAO} <b>Ganhe Dinheiro:</b> Receba R$ 1,00 por cada membro indicado!\n\n"
        f"👇 Escolha o seu plano abaixo:"
    )
    await message.answer(text=benefits_text, reply_markup=main_menu(), parse_mode="HTML")

@dp.message(F.video)
async def get_video_id(message: types.Message):
    await message.reply(f"`{message.video.file_id}`", parse_mode="Markdown")

@dp.message(F.entities)
async def get_emoji_id(message: types.Message):
    for entity in message.entities:
        if entity.type == "custom_emoji":
            await message.reply(
                f"🆔 **ID do Emoji Premium:**\n`{entity.custom_emoji_id}`\n\nBasta tocar no número acima para copiar!", 
                parse_mode="Markdown"
            )
            return

@dp.callback_query(F.data == "about")
async def handle_about(callback: types.CallbackQuery):
    about_text = (
        f"{E_DIAMANTE} <b>SOBRE O NOSSO VIP</b> {E_DIAMANTE}\n\n"
        f"Nosso sistema é <b>100% Automático</b> {E_RAIO}. Assim que você paga, a API libera seu acesso instantaneamente. Sem enrolação e sem precisar chamar atendente!\n\n"
        f"<b>Por que confiar na gente?</b> {E_VERIFICADO}\n"
        f"Não trabalhamos com modelo 'vitalício' falso. Em vez de roubar R$ 12,00 e sumir, a sua assinatura recorrente nos dá muito mais lucro a longo prazo. É um sistema onde você aproveita o conteúdo atualizado e nós aproveitamos também. Transparência total!\n\n"
        f"{E_AVIAO} <b>Sistema de Indicações (Ganhe Dinheiro):</b>\n"
        f"Membros podem convidar outros! A cada membro pagante que entrar, você ganha <b>R$ 1,00</b>. Junte o suficiente e tenha o seu VIP pago!\n\n"
        f"👇 <i>Selecione um plano acima para começar!</i>"
    )
    await callback.message.answer(text=about_text, parse_mode="HTML")
    await callback.answer()

# --- MERCADO PAGO INTEGRATION ---
@dp.callback_query(F.data.startswith("buy_"))
async def handle_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    increment_payment_click(user_id) # <--- REGISTRA QUE O USUÁRIO CLICOU EM COMPRAR
    
    await callback.message.answer("⏳ Gerando seu PIX, aguarde um momento...")
    
    price = 12.90 if callback.data == "buy_mensal" else 25.90
    title = "Premium Mensal" if callback.data == "buy_mensal" else "Premium 3 Meses"

    payment_data = {
        "transaction_amount": price,
        "description": title,
        "payment_method_id": "pix",
        "payer": {"email": f"user_{user_id}@telegrambot.com"}
    }

    result = await asyncio.to_thread(sdk.payment().create, payment_data)
    payment_info = result["response"]

    if "id" in payment_info:
        payment_id = payment_info["id"]
        pix_code = payment_info["point_of_interaction"]["transaction_data"]["qr_code"]
        
        qr_b64 = payment_info["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        qr_bytes = base64.b64decode(qr_b64)
        photo = BufferedInputFile(qr_bytes, filename="pix_qr.png")

        caption_text = (
            f"⚠️ <b>Pagamento PIX Gerado: {title}</b>\n\n"
            f"{E_CIFRAO} Valor: <b>R$ {price:.2f}</b>\n\n"
            f"{E_SININHO} {E_FOGO} <b>Falta pouco! Garanta sua vaga já e tenha acesso a mais de 1500 vídeos originais!</b> {E_RAIO}\n\n"
            f"Escaneie o QR Code acima ou copie o código abaixo:"
        )

        await callback.message.answer_photo(
            photo=photo,
            caption=caption_text,
            reply_markup=payment_menu(pix_code, payment_id),
            parse_mode="HTML"
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
        
        update_user_status(user_id, "paid")

        success_text = (
            f"{E_VERIFICADO} <b>PAGAMENTO APROVADO!</b> {E_VERIFICADO}\n\n"
            f"Muito obrigado pela compra! Seu acesso exclusivo foi liberado.\n\n"
            f"🔗 <b><a href='{VIP_GROUP_LINK}'>CLIQUE AQUI PARA ENTRAR NO GRUPO VIP</a></b>\n\n"
            f"{E_AVIAO} <b>Lembrete:</b> Você pode ganhar dinheiro! Indique o bot para amigos e ganhe R$ 1,00 por cada assinante novo.\n\n"
            f"Enquanto você entra no grupo, aproveite essas prévias exclusivas:"
        )
        
        await callback.message.answer(text=success_text, parse_mode="HTML", disable_web_page_preview=True)
        
        amount = min(10, len(VIDEO_IDS))
        selected_videos = random.sample(VIDEO_IDS, amount)
        for video_id in selected_videos:
            await bot.send_video(chat_id=user_id, video=video_id)
            await asyncio.sleep(0.5) 
            
    else:
        await callback.answer(f"Status: {status.upper()}. Pagamento ainda não identificado. Tente novamente em 10 segundos.", show_alert=True)

# ==========================================
# 6. RELATÓRIO DIÁRIO DO ADMIN
# ==========================================
async def daily_report_loop():
    if not ADMIN_ID:
        logging.warning("ADMIN_ID não configurado. Relatório diário desativado.")
        return
        
    while True:
        # Pausa de 24 horas (86400 segundos) entre os relatórios
        await asyncio.sleep(86400) 
        
        try:
            new_users, total_users, total_clicks, paid_users = get_daily_stats()
            
            report = (
                f"📊 <b>Relatório Diário do Bot</b> 📊\n\n"
                f"👤 <b>Novos leads hoje:</b> {new_users}\n"
                f"📈 <b>Total de usuários no bot:</b> {total_users}\n"
                f"💳 <b>Geraram código PIX:</b> {total_clicks}\n"
                f"✅ <b>Assinantes VIP Ativos:</b> {paid_users}\n\n"
                f"<i>Continue com o bom trabalho! 🚀</i>"
            )
            
            await bot.send_message(chat_id=int(ADMIN_ID), text=report, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Erro ao enviar relatório diário: {e}")

# ==========================================
# 7. LOOP DE RETENÇÃO (GRÁTIS)
# ==========================================
async def preview_loop():
    while True:
        await asyncio.sleep(7200) 
        if not VIDEO_IDS:
            continue 
            
        free_users = get_users_by_status("free")
        for user_id in free_users: 
            try:
                amount = min(2, len(VIDEO_IDS))
                selected_videos = random.sample(VIDEO_IDS, amount)
                for video_id in selected_videos:
                    await bot.send_video(chat_id=user_id, video=video_id)
                    await asyncio.sleep(0.5)
                
                loop_text = (
                    f"{E_FOGO} <b>Você não vai querer perder!</b> Assine agora para ver o conteúdo completo:\n\n"
                    f"{CATEGORIES_LIST}\n\n"
                    f"{E_SALE} <b>Aproveite a nossa promoção por tempo limitado!</b>\n\n"
                    f"👇 Escolha o seu plano abaixo:"
                )
                await bot.send_message(chat_id=user_id, text=loop_text, reply_markup=main_menu(), parse_mode="HTML")
            except Exception:
                pass

async def main():
    asyncio.create_task(preview_loop())
    asyncio.create_task(daily_report_loop()) # <--- INICIA O LOOP DO RELATÓRIO
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())