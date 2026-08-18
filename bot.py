import logging
import os
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters, 
    ContextTypes
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === CONFIGURATION & ENVIRONMENT VARIABLES ===
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8617408271")) 
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "username_telegram_kamu") 
EXCEL_FILE = "Masterdata_bg.xlsx"

# Variabel Dinamis (Bisa diubah bebas dari Telegram)
PUBLIC_ACCESS = True 
MAINTENANCE_TEXT = (
    "⛔ <b>Bot Sedang Dalam Perbaikan / Privat!</b>\n\n"
    "Mohon maaf, layanan saat ini sedang tidak dapat diakses.\n"
    "Silakan hubungi Admin untuk info lebih lanjut."
)

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def get_data_by_term_id(tid_input: str):
    if not os.path.exists(EXCEL_FILE):
        return None, f"File database `{EXCEL_FILE}` tidak ditemukan di server."

    try:
        df = pd.read_excel(EXCEL_FILE, header=2, dtype=str)
        df = df.dropna(how='all')
        df.columns = df.columns.astype(str).str.strip()

        kolom_tid = "TERM ID" if "TERM ID" in df.columns else df.columns[1]

        filter_tid = df[kolom_tid].astype(str).str.strip().str.replace('.0', '', regex=False) == str(tid_input).strip()
        hasil = df[filter_tid]

        if not hasil.empty:
            row_data = hasil.iloc[0].to_dict()
            return row_data, None
        else:
            return None, f"Data dengan TERM ID `{tid_input}` tidak ditemukan."

    except Exception as e:
        logging.error(f"Error membaca Excel: {e}")
        return None, f"Terjadi kesalahan saat membaca database: {e}"

# Fungsi Mengirim Pesan Ditolak
async def send_access_denied_msg(update: Update):
    keyboard = [
        [InlineKeyboardButton("💬 Hubungi Admin", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(MAINTENANCE_TEXT, reply_markup=reply_markup, parse_mode="HTML")

# Handler /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not PUBLIC_ACCESS and not is_admin(user_id):
        await send_access_denied_msg(update)
        return

    status_role = "👑 <b>Admin</b>" if is_admin(user_id) else "👤 <b>User (Read-Only)</b>"
    
    msg = (
        f"👋 <b>Selamat Datang!</b>\n"
        f"Status Kamu: {status_role}\n\n"
        f"Ketik angka <b>TERM ID</b> secara langsung untuk mencari data.\n"
        f"Contoh: <code>379</code>, <code>503</code>, atau <code>561</code>"
    )
    
    if is_admin(user_id):
        msg += "\n\n⚙️ <b>Menu Admin:</b>\nKetik <b>edit</b> untuk membuka panel kontrol."

    await update.message.reply_text(msg, parse_mode="HTML")

# Tampilan Menu Edit
async def show_edit_menu(update: Update):
    status_saat_ini = "🌐 <b>Public</b>" if PUBLIC_ACCESS else "🔒 <b>Privat / Maintenance</b>"

    keyboard = [
        [
            InlineKeyboardButton("🌐 Set Public", callback_data="set_public"),
            InlineKeyboardButton("🔒 Set Privat", callback_data="set_private")
        ],
        [
            InlineKeyboardButton("✏️ Ubah Teks Maintenance", callback_data="set_text")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    pesan_menu = (
        f"⚙️ <b>PANEL KONTROL ADMIN</b>\n\n"
        f"• <b>Status Akses:</b> {status_saat_ini}\n"
        f"• <b>Pesan Maintenance Saat Ini:</b>\n\n{MAINTENANCE_TEXT}\n\n"
        f"Silakan pilih aksi di bawah:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(pesan_menu, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(pesan_menu, reply_markup=reply_markup, parse_mode="HTML")

# Command /edit
async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await send_access_denied_msg(update)
        return
    await show_edit_menu(update)

# Callback Handler Tombol Edit
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PUBLIC_ACCESS
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("Akses ditolak! Kamu bukan Admin.", show_alert=True)
        return

    await query.answer()

    if query.data == "set_public":
        PUBLIC_ACCESS = True
        await show_edit_menu(update)
    elif query.data == "set_private":
        PUBLIC_ACCESS = False
        await show_edit_menu(update)
    elif query.data == "set_text":
        context.user_data['waiting_for_maint_text'] = True
        await query.message.reply_text(
            "📝 <b>Mode Edit Teks Maintenance</b>\n\n"
            "Silakan ketik/balas pesan teks baru secara bebas.\n"
            "<i>Pesan ini yang akan langsung tampil ke pengguna saat bot dikunci.</i>",
            parse_mode="HTML"
        )

# Handler Pesan Teks
async def handle_direct_tid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MAINTENANCE_TEXT
    user_id = update.effective_user.id
    pesan_masuk = update.message.text.strip()

    # Cek jika Admin sedang menginput teks maintenance baru
    if is_admin(user_id) and context.user_data.get('waiting_for_maint_text'):
        MAINTENANCE_TEXT = pesan_masuk
        context.user_data['waiting_for_maint_text'] = False
        await update.message.reply_text("✅ <b>Pesan Maintenance Berhasil Diperbarui!</b>", parse_mode="HTML")
        await show_edit_menu(update)
        return

    # Jika Admin mengetik "edit"
    if pesan_masuk.lower() == "edit":
        if is_admin(user_id):
            await show_edit_menu(update)
        else:
            await send_access_denied_msg(update)
        return

    # Cek Mode Akses untuk User Umum
    if not PUBLIC_ACCESS and not is_admin(user_id):
        await send_access_denied_msg(update)
        return

    if pesan_masuk.startswith('/'):
        return

    data, error = get_data_by_term_id(pesan_masuk)

    if error:
        await update.message.reply_text(f"❌ {error}", parse_mode="HTML")
        return

    pesan = "📊 <u><b>Data Aset BG Bekasi</b></u>\n"
    pesan += "━━━━━━━━━━━━━━━━━━━\n"

    kolom_diabaikan = ["NO", "PAGU"]

    for kolom, nilai in data.items():
        kolom_clean = str(kolom).strip().upper()
        if any(ignore in kolom_clean for ignore in kolom_diabaikan) or "UNNAMED" in kolom_clean:
            continue
            
        val_str = "-" if pd.isna(nilai) or str(nilai).lower() == 'nan' else str(nilai)

        if kolom_clean == "DENOM" and val_str != "-":
            try:
                val_clean = float(val_str.replace(',', '').replace('.', ''))
                val_str = f"{int(val_clean):,}".replace(',', '.')
            except:
                pass
        
        pesan += f"• <b>{kolom}</b>: {val_str}\n"

    await update.message.reply_text(pesan, parse_mode="HTML")

if __name__ == '__main__':
    if not TOKEN:
        raise ValueError("Variabel BOT_TOKEN belum diatur di Railway Variables!")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("edit", edit_command))
    app.add_handler(CallbackQueryHandler(button_callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_direct_tid))

    print("Bot berjalan...")
    app.run_polling()