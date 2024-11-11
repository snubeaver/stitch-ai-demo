from django.shortcuts import render

# Create your views here.
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_API")
bot = Bot(token=TELEGRAM_BOT_TOKEN)
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def start(update: Update, context):
    await update.message.reply_text("Welcome to the Stitch AI bot!")

app.add_handler(CommandHandler("start", start))

@csrf_exempt
def telegram_webhook(request):
    if request.method == "POST":
        update = Update.de_json(request.json(), bot)
        app.process_update(update)
    return JsonResponse({"status": "ok"})