import os
import logging
import subprocess
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Environment variables
TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")  # e.g., https://yourapp.koyeb.app

# Telegram Bot and Flask App
bot = Bot(token=TOKEN)
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# Logging
logging.basicConfig(level=logging.INFO)

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a voice, audio, or video file, and I’ll convert it to MP3!")

# File handler
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or update.message.audio or update.message.video or update.message.voice
    if not file:
        await update.message.reply_text("Please send a supported voice/audio/video file.")
        return

    await update.message.reply_text("Downloading and converting to MP3...")

    telegram_file = await file.get_file()
    input_filename = f"{file.file_id}_input.ogg"
    output_filename = f"{file.file_id}.mp3"

    await telegram_file.download_to_drive(input_filename)

    # Convert to MP3 using FFmpeg
    subprocess.run([
        "ffmpeg", "-y", "-i", input_filename,
        "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", output_filename
    ], check=True)

    # Send MP3 back
    await update.message.reply_audio(audio=open(output_filename, "rb"))

    # Clean up
    os.remove(input_filename)
    os.remove(output_filename)

# Webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    print("Webhook received an update!")  # Debug log
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "ok"

# Health check route
@app.route("/", methods=["GET"])
def home():
    return "Bot is alive!"

# Start bot and Flask app
if __name__ == "__main__":
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_file))

    # Set webhook
    bot.delete_webhook()
    bot.set_webhook(url=f"{APP_URL}/{TOKEN}")

    # Run Flask
    app.run(host="0.0.0.0", port=8000)