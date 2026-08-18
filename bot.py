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

# === CONFIGURATION ===
TOKEN = os.getenv("BOT_TOKEN")

# Daftar ID Telegram Admin (Bisa diisi beberapa ID jika ada lebih dari 1 Admin)
ADMIN_LIST = [8617408271] 

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "username_telegram_kamu") 
EXCEL_FILE = "Masterdata_bg.xlsx"

# === SYSTEM STATES ===
PUBLIC_ACCESS = True 

MAINTENANCE_TEXT = (
    "⛔ <b>Bot Sedang Dalam Perbaikan / Privat!</b>\n\n"
    "Mohon maaf, layanan saat ini sedang tidak dapat diakses.\n"
    "Silakan hubungi Admin untuk info lebih lanjut."
)

def is_admin(user_id: int) -> bool:
    return int(user_id) in ADMIN_LIST

def get_data_by_term_id(tid_input: str):
    if not os.path.exists(EXCEL_FILE):
        return None, f"File database `{EXCEL_FILE}` tidak ditemukan di server."

    try:
        df = pd.read_excel(EXCEL_FILE, header=2, dtype=str)
        df = df.dropna(how='all')
        df.columns = df.columns.astype(str).str.strip()

        kolom_tid = "TERM ID" if "TERM ID" in df.columns else df.columns[1]

        # Konversi ke UPPERCASE agar tidak sensitif terhadap huruf besar/kecil
        tid_target = str(tid_input).strip().upper()
        
        kolom_data_clean = (
            df[kolom_tid]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace('.0', '', regex=False)
        )

        filter_tid = kolom_data_clean == tid_target
        hasil = df[filter_tid]

        if not hasil.empty:
            row_data = hasil.iloc[0].to_dict()
            return row_data, None
        else:
            return None, f"Data dengan TERM ID `{tid_input}` tidak ditemukan."

    except Exception as e:
        logging.error(f"Error membaca Excel: {e}")
        return None, f"Terjadi kesalahan saat membaca database: {e}"

def render_edit_menu():
    status_saat_ini = "🌐 <b>Public</b> (Bisa diakses umum)" if PUBLIC_ACCESS else "🔒 <b>Privat</b> (Hanya Admin)"

    keyboard = [
        [
            InlineKeyboardButton("🌐 Set Public", callback_data="set_public"),
            InlineKeyboardButton("🔒 Set Privat", callback_data="set_private")
        ],
        [
            InlineKeyboardButton("✏️ Ubah Teks Maintenance", callback_data="set_text")
        ]
    ]
    
    pesan_menu = (
        f"⚙️ <b>PANEL KONTROL ADMIN</b>\n\n"
        f"• <b>Status Akses Bot:</b> {status_saat_ini}\n\n"
        f"• <b>Pesan Maintenance Saat Ini:</b>\n{MAINTENANCE_TEXT}\n\n"
        f"Silakan pilih tombol di bawah untuk mengubah pengaturan:"
    )
    
    return pesan_menu, InlineKeyboardMarkup(keyboard)

async def send_access_denied_msg(update: Update):
    keyboard = [
        [InlineKeyboardButton("💬 Hubungi Admin", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(MAINTENANCE_TEXT, reply_markup=reply_markup, parse_mode="HTML")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_admin(user_id):
        pesan = (
            f"👑 <b>Selamat Datang, Admin!</b>\n\n"
            f"• Ketik <b>edit</b> atau <b>/edit</b> untuk membuka Panel Kontrol Admin.\n"
            f"• Ketik angka/kode <b>TERM ID</b> untuk mencari data langsung."
        )
        await update.message.reply_text(pesan, parse_mode="HTML")
        return

    if not PUBLIC_ACCESS:
        await send_access_denied_msg(update)
        return

    msg = (
        f"👋 <b>Selamat Datang!</b>\n\n"
        f"Ketik angka <b>TERM ID</b> secara langsung untuk mencari data.\n"
        f"Contoh: <code>379</code>, <code>a131</code>, atau <code>A131</code>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def show_edit_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        pesan_menu, reply_markup = render_edit_menu()
        await update.message.reply_text(pesan_menu, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await send_access_denied_msg(update)

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
    elif query.data == "set_private":
        PUBLIC_ACCESS = False
    elif query.data == "set_text":
        context.user_data['waiting_for_maint_text'] = True
        await query.message.reply_text(
            "📝 <b>Mode Edit Teks Maintenance</b>\n\n"
            "Silakan ketik/balas pesan teks baru secara bebas.\n"
            "<i>Pesan ini yang akan langsung dikirim ke pengguna biasa saat bot dikunci (Privat).</i>",
            parse_mode="HTML"
        )
        return

    pesan_menu, reply_markup = render_edit_menu()
    await query.edit_message_text(pesan_menu, reply_markup=reply_markup, parse_mode="HTML")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MAINTENANCE_TEXT
    user_id = update.effective_user.id
    pesan_masuk = update.message.text.strip()

    if is_admin(user_id) and context.user_data.get('waiting_for_maint_text'):
        MAINTENANCE_TEXT = pesan_masuk
        context.user_data['waiting_for_maint_text'] = False
        await update.message.reply_text("✅ <b>Pesan Maintenance Berhasil Diperbarui!</b>", parse_mode="HTML")
        pesan_menu, reply_markup = render_edit_menu()
        await update.message.reply_text(pesan_menu, reply_markup=reply_markup, parse_mode="HTML")
        return

    if pesan_masuk.lower() in ["edit", "/edit"]:
        if is_admin(user_id):
            await show_edit_panel(update, context)
        else:
            await send_access_denied_msg(update)
        return

    if not is_admin(user_id) and not PUBLIC_ACCESS:
        await send_access_denied_msg(update)
        return

    if pesan_masuk.startswith('/'):
        return

    data, error = get_data_by_term_id(pesan_masuk)

    if error:
        await update.message.reply_text(f"❌ {error}", parse_mode="HTML")
        return

    pesan = "📊 <u><b>Data Aset BG Bekasi</b></u>\n━━━━━━━━━━━━━━━━━━━\n"
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

    # Penambahan Note di Akhir Pesan (Posisi Tengah + Tebal & Garis Bawah)
    pesan += "\n"
    pesan += "⠀" * 12 + "<b><u>Patuhi SOP jauhi Fraud</u></b>"

    await update.message.reply_text(pesan, parse_mode="HTML")

if __name__ == '__main__':
    if not TOKEN:
        raise ValueError("Variabel BOT_TOKEN belum diatur!")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("edit", show_edit_panel))
    app.add_handler(CallbackQueryHandler(button_callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_messages))

    print("Bot berjalan...")
    app.run_polling()