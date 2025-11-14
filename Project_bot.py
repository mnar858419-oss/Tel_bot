import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = ""
BASE_PATH = os.getcwd()

# ---------------دیتابیس
def init_db():
    conn = sqlite3.connect("files.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            file_id TEXT
        )
    """)
    conn.commit()
    conn.close()

# def add_document(title, file_id):
#     conn = sqlite3.connect("files.db")
#     c = conn.cursor()
#     c.execute("INSERT INTO documents (title, file_id) VALUES (?, ?)", (title, file_id))
#     conn.commit()
#     conn.close()

def get_all_documents():
    conn = sqlite3.connect("files.db")
    c = conn.cursor()
    c.execute("SELECT id, title FROM documents")
    rows = c.fetchall()
    conn.close()
    return rows

def get_file_id_by_id(doc_id):
    conn = sqlite3.connect("files.db")
    c = conn.cursor()
    c.execute("SELECT file_id FROM documents WHERE id = ?", (doc_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# -------------------
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ارسال پروژه", callback_data="send_project")],
        [InlineKeyboardButton("لیست داکیومنت‌ها", callback_data="list_docs")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لطفاً نام و نام خانوادگی خود را وارد کنید:")

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_name = update.message.text.strip()
    safe_name = ""
    for c in full_name:
        if c in ['/', '|', ':', '*', '?', '"', '<', '>', '-']:
            safe_name += " "
        else:
            safe_name += c
    safe_name = safe_name.strip()
    user_folder = os.path.join(BASE_PATH, safe_name)
    os.makedirs(user_folder, exist_ok=True)
    context.user_data["user_folder"] = user_folder
    await update.message.reply_text("منوی اصلی:", reply_markup=main_menu_keyboard())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "send_project":
        context.user_data["awaiting_project"] = True
        await query.message.reply_text("لطفاً فایل پروژه‌ی خود را ارسال کنید:")

    elif query.data == "list_docs":
        docs = get_all_documents()
        if not docs:
            await query.message.reply_text("هنوز هیچ داکیومنتی ثبت نشده است.")
            return

        keyboard = [[InlineKeyboardButton(title, callback_data=f"doc_{doc_id}")] for doc_id, title in docs]
        keyboard.append([InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("لیست داکیومنت‌ها:", reply_markup=reply_markup)

    elif query.data.startswith("doc_"):
        doc_id = int(query.data.split("_")[1])
        file_id = get_file_id_by_id(doc_id)
        if file_id:
            await context.bot.send_document(chat_id=chat_id, document=file_id)
        else:
            await context.bot.send_message(chat_id=chat_id, text="فایل یافت نشد.")

    elif query.data == "main_menu":
        await query.message.reply_text("منوی اصلی:", reply_markup=main_menu_keyboard())

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_project"):
        return

    document = update.message.document
    if not document:
        return

    user_folder = context.user_data.get("user_folder", BASE_PATH)
    file_path = os.path.join(user_folder, document.file_name)

    new_file = await document.get_file()
    await new_file.download_to_drive(file_path)

    context.user_data["awaiting_project"] = False
    await update.message.reply_text(f"پروژه شما با نام '{document.file_name}' ذخیره شد!")

def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_name))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.run_polling()

if __name__ == "__main__":
    main()
