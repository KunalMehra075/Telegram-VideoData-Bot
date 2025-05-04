import logging
from pymongo import MongoClient
from telegram import Update 
from dotenv import load_dotenv 
import os

from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
   
load_dotenv()
BotToken = os.environ.get('BOT_TOKEN')
MongoUri = os.environ.get('MONGO_URI')


# Set up logging to track bot events and errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# MongoDB connection setup (persistent client with connection pooling)
logger.info("Connecting to MongoDB...")
client = MongoClient(MongoUri)  # Replace with your MongoDB URI
db = client['video_bot_db']  # Database name
video_collection = db['videoData']  # Collection (table) name
logger.info("Connected to MongoDB and selected database 'video_bot_db'.")

# Command handler for /start to greet the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received /start command from user {update.effective_user.id}.")
    await update.message.reply_text('Hello! Send /newvid <title> <url> [description] to save a new video.')

# Command handler for /newvid to save video details
async def newvid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received /newvid command from user {update.effective_user.id} with args: {context.args}")
    try:
        args = context.args  # Get command arguments as a list

        if len(args) < 2:
            logger.warning("Insufficient arguments provided to /newvid command.")
            await update.message.reply_text('Usage: /newvid <title> <url> [description]')
            return

        title = args[0]
        url = args[1]
        description = ' '.join(args[2:]) if len(args) > 2 else ''

        logger.info(f"Preparing to insert video data: title='{title}', url='{url}', description='{description}'")

        videoData = {
            'title': title,
            'url': url,
            'description': description
        }

        result = video_collection.insert_one(videoData)
        logger.info(f"Inserted video document with ID: {result.inserted_id}")

        await update.message.reply_text(f'✅ Video saved with ID: {result.inserted_id}')

    except Exception as e:
        logger.error(f"Error in /newvid command: {e}", exc_info=True)
        await update.message.reply_text('❌ An error occurred while saving the video.')

# Command handler for /flushdb to delete all documents
async def flushdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received /flushdb command from user {update.effective_user.id}.")
    try:
        result = video_collection.delete_many({})
        logger.info(f"Deleted {result.deleted_count} documents from the collection.")
        await update.message.reply_text(f'🗑️ Cleared {result.deleted_count} documents from the database.')
    except Exception as e:
        logger.error(f"Error in /flushdb command: {e}", exc_info=True)
        await update.message.reply_text('❌ An error occurred while flushing the database.')

# Command handler for /videoslist to list all video titles
async def videoslist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received /videoslist command from user {update.effective_user.id}.")
    try:
        videos = video_collection.find({}, {'title': 1})
        titles = [video['title'] for video in videos]
        if titles:
            response = '🎥 Video Titles:\n' + '\n'.join(titles)
        else:
            response = 'No videos found in the database.'
        logger.info(f"Returning list of {len(titles)} videos.")
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in /videoslist command: {e}", exc_info=True)
        await update.message.reply_text('❌ An error occurred while fetching the video list.')

# Command handler for /videoslength to return total document count
async def videoslength(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received /videoslength command from user {update.effective_user.id}.")
    try:
        count = video_collection.count_documents({})
        logger.info(f"Database contains {count} documents.")
        await update.message.reply_text(f'📊 Total videos in database: {count}')
    except Exception as e:
        logger.error(f"Error in /videoslength command: {e}", exc_info=True)
        await update.message.reply_text('❌ An error occurred while counting the videos.')

if __name__ == '__main__':
    logger.info("Starting Telegram bot...")
    app = ApplicationBuilder().token(BotToken).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('newvid', newvid))
    app.add_handler(CommandHandler('flushdb', flushdb))
    app.add_handler(CommandHandler('videoslist', videoslist))
    app.add_handler(CommandHandler('videoslength', videoslength))

    logger.info("🤖 Bot is running and polling for updates...")
    app.run_polling()
