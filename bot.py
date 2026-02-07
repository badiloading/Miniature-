 
import os
import subprocess
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# =====================
# CONFIG (Railway Safe)
# =====================
TOKEN = os.getenv("BOT_TOKEN")  # <-- مهم
BASE_DIR = os.getcwd()

INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
AUDIO_DIR = os.path.join(BASE_DIR, "audio")

LOGO_PATH = os.path.join(BASE_DIR, "logo.png")
BG_PATH = os.path.join(BASE_DIR, "BG.jpeg")

LOGO_WIDTH = 250
LOGO_MARGIN = 50

MAX_DURATION = 300
MAX_SIZE_MB = 200
DAILY_LIMIT = 3

for d in (INPUT_DIR, OUTPUT_DIR, AUDIO_DIR):
    os.makedirs(d, exist_ok=True)

# =====================
# USAGE LIMIT
# =====================
user_usage = {}

def can_use(user_id):
    today = str(date.today())
    if user_id not in user_usage or user_usage[user_id]["date"] != today:
        user_usage[user_id] = {"date": today, "count": 0}

    if user_usage[user_id]["count"] >= DAILY_LIMIT:
        return False, 0

    return True, DAILY_LIMIT - user_usage[user_id]["count"]

def increment_usage(user_id):
    user_usage[user_id]["count"] += 1

# =====================
# FFMPEG RUNNER
# =====================
async def run_ffmpeg(cmd):
    process = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    for _ in process.stderr:
        pass
    process.wait()

# =====================
# /start
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🚀 ابدأ", callback_data="start_bot")]]
    await update.message.reply_text(
        "🎬 مرحباً بك عند Pedro Loading لمعالجة الفيديو\n\n"
        "🆓 مجاني في فترة التطوير فقط\n\n"
        "اضغط 👇",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def start_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("⬇️ أرسل الفيديو الآن")

# =====================
# VIDEO RECEIVE
# =====================
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    allowed, remaining = can_use(user_id)

    if not allowed:
        await update.message.reply_text("❌ الحد اليومي خلص 😂 ارجع غدوة")
        return

    video = update.message.video

    if video.duration > MAX_DURATION:
        await update.message.reply_text("❌ الفيديو طويل")
        return

    if video.file_size / 1024 / 1024 > MAX_SIZE_MB:
        await update.message.reply_text("❌ الفيديو كبير")
        return

    context.user_data["file_id"] = video.file_id
    increment_usage(user_id)

    kb = [
        [
            InlineKeyboardButton("🌫 Blur", callback_data="blur"),
            InlineKeyboardButton("🟦 BG", callback_data="bg"),
            InlineKeyboardButton("✂️ Crop", callback_data="crop"),
        ],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await update.message.reply_text(
        f"✅ الفيديو مقبول\n🔁 المتبقي اليوم: {remaining - 1}\n\nاختر 👇",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# =====================
# BUTTON HANDLER
# =====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = q.data

    if q.data in ("blur", "bg"):
        await q.edit_message_text(
            "✍️ اكتب النسبة (100 – 150)\nمثال: 115"
        )
        return

    await process_video(q.message, context, 100)

# =====================
# TEXT HANDLER
# =====================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "mode" not in context.user_data:
        return

    try:
        percent = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ رقم فقط")
        return

    if not 100 <= percent <= 150:
        await update.message.reply_text("❌ بين 100 و 150")
        return

    await process_video(update.message, context, percent)

# =====================
# PROCESS VIDEO
# =====================
async def process_video(msg, context, percent):
    user_id = msg.from_user.id
    mode = context.user_data["mode"]

    inp = os.path.join(INPUT_DIR, f"in_{user_id}.mp4")
    out = os.path.join(OUTPUT_DIR, f"out_{user_id}.mp4")
    aud = os.path.join(AUDIO_DIR, f"aud_{user_id}.mp3")

    file = await context.bot.get_file(context.user_data["file_id"])
    await file.download_to_drive(inp)

    zoom = percent / 100

    if mode == "mp3":
        cmd = ["ffmpeg", "-y", "-i", inp, "-vn", "-ab", "192k", aud]
        await run_ffmpeg(cmd)
        await context.bot.send_audio(user_id, open(aud, "rb"))
        os.remove(aud)
        os.remove(inp)
        return

    if mode == "crop":
        vf = "crop=ih*9/16:ih,scale=1080:1920"
        inputs = ["-i", inp]
    elif mode == "blur":
        vf = (
            f"[0:v]scale=1080:1920,boxblur=25:1[bg];"
            f"[0:v]scale=iw*{zoom}:ih*{zoom}[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        inputs = ["-i", inp]
    else:
        vf = (
            f"[1:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920[bg];"
            f"[0:v]scale=iw*{zoom}:ih*{zoom}[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        inputs = ["-i", inp, "-i", BG_PATH]

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", LOGO_PATH,
        "-filter_complex",
        f"{vf}[base];[2:v]scale={LOGO_WIDTH}:-1[logo];[base][logo]overlay=W-w-{LOGO_MARGIN}:{LOGO_MARGIN}",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        out
    ]

    await run_ffmpeg(cmd)
    await context.bot.send_video(user_id, open(out, "rb"))

    os.remove(inp)
    os.remove(out)

# =====================
# RUN
# =====================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(start_button, pattern="start_bot"))
app.add_handler(MessageHandler(filters.VIDEO, video_handler))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("Bot is running...")
app.run_polling()