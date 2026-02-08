import os
import asyncio
import subprocess
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =====================
# CONFIG
# =====================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

# =====================
# FFMPEG (Railway SAFE)
# =====================
async def run_ffmpeg(cmd: list):
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(stderr.decode())

# =====================
# HANDLERS
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 البوت شغّال، ابعث فيديو 🎥")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 ابعث فيديو فقط")

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    video = await msg.video.get_file()

    input_path = "input.mp4"
    output_path = "output.mp4"

    await video.download_to_drive(input_path)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vf", "scale=iw:ih",
        output_path
    ]

    try:
        await run_ffmpeg(cmd)
        await msg.reply_video(video=open(output_path, "rb"))
    except Exception as e:
        await msg.reply_text(f"❌ خطأ ffmpeg:\n{str(e)}")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

# =====================
# RUN
# =====================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
