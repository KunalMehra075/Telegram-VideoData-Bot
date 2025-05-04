import os
import logging
from pymongo import MongoClient
from telegram import Update,ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
ASK_URL, ASK_TITLE = range(2)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST')  # e.g., https://your-app.onrender.com
PORT = int(os.getenv('PORT', 10000))
WEBHOOK_PATH = f'/webhook/{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

# Setup MongoDB
client = MongoClient(MONGO_URI)
db = client['video_bot_db']
video_collection = db['video_data']

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['/newvid', '/videoslist'],
        ['/videoslength', '/flushdb']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        'Choose an option:',
        reply_markup=reply_markup
    )


# Start the /newvid conversation
async def newvid_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Please send the video URL.')
    return ASK_URL

# Handle URL input
async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['url'] = update.message.text
    await update.message.reply_text('Got the URL! Now send the video title.')
    return ASK_TITLE

# Handle title input and save to DB
async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    url = context.user_data.get('url')
    description = ''  # Optional: you can add another step if you want

    result = video_collection.insert_one({'title': title, 'url': url, 'description': description})
    await update.message.reply_text(f'✅ Video saved with ID: {result.inserted_id}')
    return ConversationHandler.END

# Handle cancel or fallback
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('❌ Video creation cancelled.')
    return ConversationHandler.END

# Command: /flushdb
async def flushdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = video_collection.delete_many({})
    await update.message.reply_text(f'🗑️ Flushed {result.deleted_count} videos from the database.')

# Command: /videoslist
async def videoslist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    videos = video_collection.find()
    titles = [video['title'] for video in videos]
    if titles:
        await update.message.reply_text('📺 Videos:\n' + '\n'.join(titles))
    else:
        await update.message.reply_text('No videos found.')

# Command: /videoslength
async def videoslength(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = video_collection.count_documents({})
    await update.message.reply_text(f'📊 Total videos: {count}')

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    # app.add_handler(CommandHandler('newvid', newvid))
    
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('newvid', newvid_start)],
    states={
        ASK_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)],
        ASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

    app.add_handler(conv_handler)   
    
    
    app.add_handler(CommandHandler('flushdb', flushdb))
    app.add_handler(CommandHandler('videoslist', videoslist))
    app.add_handler(CommandHandler('videoslength', videoslength))

    logger.info('🤖 Bot running with webhooks...')
    app.run_webhook(
        listen='0.0.0.0',
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL
    )
