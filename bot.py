import logging
import os
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Membaca TOKEN dari Environment Variables Railway
TOKEN = os.getenv("BOT_TOKEN")
EXCEL_FILE = "Masterdata_bg.xlsx"

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

# Handler /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Selamat Datang!</b>\n\n"
        "Silakan ketik angka <b>TERM ID</b> secara langsung untuk mencari data.\n\n"
        "Contoh: <code>379</code>, <code>503</code>, atau <code>561</code>",
        parse_mode="HTML"
    )

# Handler Pesan Teks Langsung
async def handle_direct_tid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid_query = update.message.text.strip()

    if tid_query.startswith('/'):
        return

    data, error = get_data_by_term_id(tid_query)

    if error:
        await update.message.reply_text(f"❌ {error}", parse_mode="HTML")
        return

    # KOP UNTUK PESAN
    pesan = "📊 <u><b>Data Aset BG Bekasi</b></u>\n"
    pesan += "━━━━━━━━━━━━━━━━━━━\n"

    kolom_diabaikan = ["NO", "PAGU"]

    for kolom, nilai in data.items():
        kolom_clean = str(kolom).strip().upper()
        
        # Abaikan kolom NO, PAGU, dan Unnamed
        if any(ignore in kolom_clean for ignore in kolom_diabaikan) or "UNNAMED" in kolom_clean:
            continue
            
        val_str = "-" if pd.isna(nilai) or str(nilai).lower() == 'nan' else str(nilai)

        # Format ribuan khusus untuk kolom DENOM
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
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_direct_tid))

    print("Bot berjalan...")
    app.run_polling()