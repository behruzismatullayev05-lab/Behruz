import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "7609784999:AAGyrg-db0Fnqmy6ZjtXkYC_BUd2rvfSYwo"
ADMIN_ID = 6939845092   # o'zingizning Telegram ID
CHANNEL_ID = -1002904540440  # kanal ID sini shu yerga yozing

# --- DATABASE ---
conn = sqlite3.connect("movies.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    file_id TEXT,
    info TEXT
)
""")
conn.commit()

adding = {}

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Salom! Bu *Kino Bot* 🎬\n\n"
        "ℹ️ Kodni yozing (masalan: `123`), men sizga kinoni yuboraman.\n\n"
        "📌 Foydali komandalar:\n"
        "• /help – bot haqida to‘liq ma’lumot\n"
        "• /add <kod> – yangi kino qo‘shish (faqat admin)\n"
        "• /delete <kod> – kinoni o‘chirish (faqat admin)\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# --- HELP ---
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🆘 *Bot haqida to‘liq ma’lumot:*\n\n"
        "🎥 Ushbu bot orqali siz kod orqali kinolarni olishingiz mumkin.\n"
        "➖ Kodni yozing (masalan: `123`), bot sizga kinoni yuboradi.\n\n"
        "👨‍💻 *Admin komandalar:*\n"
        "• /add <kod> — yangi kino qo‘shish\n"
        "• /delete <kod> — kinoni o‘chirish\n\n"
        "📂 Barcha kinolar bazada saqlanadi va kod orqali topiladi."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# --- ADMIN: /add 123 ---
async def add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Siz admin emassiz.")
    
    if len(context.args) < 1:
        return await update.message.reply_text("❗ Kod kiriting: /add 123")
    
    code = context.args[0]
    if not code.isdigit():
        return await update.message.reply_text("❗ Kod faqat raqam bo‘lishi kerak (masalan: 123).")
    
    adding[update.effective_user.id] = {"code": code}
    await update.message.reply_text("✅ Endi kinoni yuboring (video fayl).")

# --- ADMIN: Video qabul qilish ---
async def save_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and update.effective_user.id in adding:
        data = adding[update.effective_user.id]
        code = data["code"]
        file_id = update.message.video.file_id
        adding[update.effective_user.id]["file_id"] = file_id
        await update.message.reply_text("ℹ️ Kino haqida ma'lumot yozing (masalan: Format, davomiylik, janr).")
        adding[update.effective_user.id]["waiting_info"] = True
    else:
        await handle_message(update, context)

# --- ADMIN: Ma’lumot qabul qilish ---
async def save_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and update.effective_user.id in adding and "waiting_info" in adding[update.effective_user.id]:
        data = adding.pop(update.effective_user.id)
        code, file_id, info = data["code"], data["file_id"], update.message.text

        cursor.execute("INSERT OR REPLACE INTO movies (code, file_id, info) VALUES (?, ?, ?)", (code, file_id, info))
        conn.commit()

        # ✅ Adminga javob
        await update.message.reply_text(f"✅ Kino saqlandi!\nKod: {code}\nℹ️ {info}")

        # 📢 Kanalga yuborish
        caption = f"🎬 Yangi kino qo‘shildi!\n\n📌 Kod: {code}\nℹ️ {info}"
        await context.bot.send_video(CHANNEL_ID, file_id, caption=caption)
    else:
        await handle_message(update, context)

# --- ADMIN: Kino o‘chirish ---
async def delete_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Siz admin emassiz.")
    
    if len(context.args) < 1:
        return await update.message.reply_text("❗ Kod kiriting: /delete 123")
    
    code = context.args[0]
    cursor.execute("SELECT title, file_id FROM movies WHERE code = ?", (code,))
    row = cursor.fetchone()
    if not row:
        return await update.message.reply_text("❌ Bunday kod topilmadi.")
    
    cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
    conn.commit()

    # ✅ Adminga javob
    await update.message.reply_text(f"🗑 Kino o‘chirildi!\nKod: {code}")

    # 📢 Kanalga yuborish
    await context.bot.send_message(CHANNEL_ID, f"🗑 Kino o‘chirildi!\nKod: {code}")

# --- USER: Kod yuboradi ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    if code.isdigit():
        cursor.execute("SELECT file_id, info FROM movies WHERE code = ?", (code,))
        row = cursor.fetchone()
        if row:
            file_id, info = row
            await update.message.reply_video(file_id, caption=info)
        else:
            await update.message.reply_text("❌ Bunday kod topilmadi.")
    else:
        await update.message.reply_text("❌ Kod faqat raqam bo‘lishi kerak.")

# --- Botni ishga tushirish ---
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("add", add_movie))
app.add_handler(CommandHandler("delete", delete_movie))
app.add_handler(MessageHandler(filters.VIDEO, save_movie))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_info))

app.run_polling()