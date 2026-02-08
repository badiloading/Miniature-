import os
import asyncio
import shutil
from uuid import uuid4
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    raise RuntimeError("ffmpeg not found")

WORKDIR = "/tmp/videos"
os.makedirs(WORKDIR, exist_ok=True)

# =========================
# FFmpeg Runner
# =========================
async def run_ffmpeg(cmd: list):
    cmd[0] = FFMPEG
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(stderr.decode())

# =========================
# HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 أرسل فيديو واختر طريقة المعالجة")

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = str(uuid4())
    input_path = f"{WORKDIR}/{file_id}.mp4"

    video = await update.message.video.get_file()
    await video.download_to_drive(input_path)

    context.user_data["video"] = input_path

    keyboard = [
        [
            InlineKeyboardButton("🔹 Blur", callback_data="blur"),
            InlineKeyboardButton("🔹 Crop", callback_data="crop"),
        ],
        [InlineKeyboardButton("⚙️ Auto", callback_data="auto")]
    ]

    await update.message.reply_text(
        "اختر نوع المعالجة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def process_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    input_path = context.user_data.get("video")
    if not input_path:
        await query.edit_message_text("❌ لا يوجد فيديو")
        return

    output_path = input_path.replace(".mp4", "_out.mp4")
    choice = query.data

    if choice == "blur":
        cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", "boxblur=10:1", output_path]
    elif choice == "crop":
        cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", "crop=iw*0.9:ih*0.9", output_path]
    else:  # auto
        cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", "scale=iw:ih", output_path]

    await query.edit_message_text("⏳ جارٍ المعالجة...")
    await run_ffmpeg(cmd)

    await query.message.reply_video(video=open(output_path, "rb"))

    os.remove(input_path)
    os.remove(output_path)
    context.user_data.clear()

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    app.add_handler(CallbackQueryHandler(process_choice))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
