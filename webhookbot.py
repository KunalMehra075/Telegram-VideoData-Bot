import os
import logging
from pymongo import MongoClient
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

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
    await update.message.reply_text('Hello! Send /newvid <title> <url> [description] to save a new video.')

# Command: /newvid
async def newvid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text('Usage: /newvid <title> <url> [description]')
        return

    title = args[0]
    url = args[1]
    description = ' '.join(args[2:]) if len(args) > 2 else ''

    video_data = {'title': title, 'url': url, 'description': description}
    result = video_collection.insert_one(video_data)
    await update.message.reply_text(f'✅ Video saved with ID: {result.inserted_id}')

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
    app.add_handler(CommandHandler('newvid', newvid))
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
