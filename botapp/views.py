import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from datetime import datetime, timedelta
import random
from .models import User, Task, Submission
from .utils import validate_wallet_address, validate_image, validate_audio, upload_to_gcs

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_API")
bot = Bot(token=TELEGRAM_BOT_TOKEN)
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def start(update: Update, context):
    """Handle /start command and wallet connection"""
    keyboard = [
        [InlineKeyboardButton("Connect Wallet", callback_data='connect_wallet')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to Stitch AI! Please connect your wallet to start earning.",
        reply_markup=reply_markup
    )

async def connect_wallet(update: Update, context):
    """Handle wallet connection callback"""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "Please send your Ethereum wallet address to connect."
    )
    context.user_data['awaiting_wallet'] = True

async def handle_wallet_message(update: Update, context):
    """Process wallet address submission"""
    if not context.user_data.get('awaiting_wallet'):
        return
    
    wallet_address = update.message.text
    if not validate_wallet_address(wallet_address):
        await update.message.reply_text("Invalid wallet address. Please try again.")
        return
    
    user, created = User.objects.get_or_create(
        telegram_id=update.effective_user.id,
        defaults={'wallet_address': wallet_address}
    )
    
    context.user_data['awaiting_wallet'] = False
    await update.message.reply_text(
        "Wallet connected successfully! Use /task to get your first task."
    )

async def get_task(update: Update, context):
    """Handle /task command"""
    user = User.objects.get(telegram_id=update.effective_user.id)
    
    # Check if user has a recent task
    if user.last_task_timestamp and \
       datetime.now() - user.last_task_timestamp < timedelta(hours=24):
        await update.message.reply_text(
            "Please wait 24 hours before requesting a new task."
        )
        return
    
    # Get random task
    tasks = Task.objects.filter(
        expires_at__gt=datetime.now()
    ).order_by('?')
    
    if not tasks:
        await update.message.reply_text("No tasks available at the moment.")
        return
    
    task = tasks[0]
    user.last_task_timestamp = datetime.now()
    user.save()
    
    await update.message.reply_text(
        f"Your task:\n{task.prompt}\n\n"
        f"Task type: {task.task_type}\n"
        "Send your submission as a reply to this message."
    )
    context.user_data['current_task'] = task.id

async def handle_submission(update: Update, context):
    """Process task submissions"""
    if 'current_task' not in context.user_data:
        await update.message.reply_text("Please request a task first using /task")
        return
    
    task = Task.objects.get(id=context.user_data['current_task'])
    user = User.objects.get(telegram_id=update.effective_user.id)
    
    if task.task_type == 'IMAGE':
        if not update.message.photo:
            await update.message.reply_text("Please submit an image.")
            return
        
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        if not validate_image(photo_bytes):
            await update.message.reply_text(
                "Image must be at least 400x400 pixels."
            )
            return
        
        file_url = upload_to_gcs(photo_bytes, 'jpg', user.id)
        
    elif task.task_type == 'AUDIO':
        if not update.message.voice:
            await update.message.reply_text("Please submit a voice message.")
            return
        
        voice_file = await update.message.voice.get_file()
        voice_bytes = await voice_file.download_as_bytearray()
        
        if not validate_audio(voice_bytes):
            await update.message.reply_text("Invalid audio submission.")
            return
        
        file_url = upload_to_gcs(voice_bytes, 'ogg', user.id)
        
    else:  # TEXT
        if not update.message.text:
            await update.message.reply_text("Please submit a text response.")
            return
        file_url = update.message.text
    
    Submission.objects.create(
        user=user,
        task=task,
        content=file_url,
        is_valid=True
    )
    
    del context.user_data['current_task']
    await update.message.reply_text(
        "Submission received! You can request a new task in 24 hours."
    )

def setup_handlers():
    """Setup all command and message handlers"""
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("task", get_task))
    app.add_handler(CallbackQueryHandler(connect_wallet, pattern='^connect_wallet$'))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE,
        handle_wallet_message
    ))
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.VOICE | filters.TEXT) & ~filters.COMMAND,
        handle_submission
    ))

@csrf_exempt
def telegram_webhook(request):
    """Handle incoming webhook requests"""
    if request.method == "POST":
        update = Update.de_json(request.json(), bot)
        app.process_update(update)
    return JsonResponse({"status": "ok"})
