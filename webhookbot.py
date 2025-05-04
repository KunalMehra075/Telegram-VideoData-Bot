import os
import logging
from pymongo import MongoClient
from telegram import Update,ReplyKeyboardMarkup,InlineKeyboardButton, InlineKeyboardMarkup
from gemini import getResponseFromGemini
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)
# Conversation states
SELECTING_VIDEO, DELETING_VIDEO = range(2)
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
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST')  
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
        ['/start', '/cancel'],
        ['/newvid', '/videoslist'],
        ['/videoslength', '/flushdb']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        'Choose an option:',
        reply_markup=reply_markup
    )
    
async def handlehello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'Hi Kunal! Your Annovator Bot is ready for action! 🥳🍸')


async def handle_any_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    try:
        reply =  getResponseFromGemini(prompt=user_text)
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("❌ Sorry, something went wrong while talking to Gemini.")

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

# /delete command handler
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Fetch all video titles from the database
    video_docs = video_collection.find()
    video_buttons = []
    
    for doc in video_docs:
        title = doc.get('title')
        video_buttons.append([InlineKeyboardButton(title, callback_data=title)])

    # If no videos, notify the user
    if not video_buttons:
        await update.message.reply_text("❌ No videos found in the database.")
        return

    # Send video titles as inline buttons
    reply_markup = InlineKeyboardMarkup(video_buttons)
    await update.message.reply_text("Select a video to delete:", reply_markup=reply_markup)
    
    return SELECTING_VIDEO

# Handler for when a video button is clicked
async def handle_video_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    video_title = query.data  # Get the title of the selected video
    
    # Find and delete the video from the database
    video = video_collection.find_one_and_delete({'title': video_title})
    
    if video:
        # Confirm deletion to the user
        await query.answer()
        await query.edit_message_text(f"✅ Video '{video_title}' has been deleted.")
    else:
        await query.answer()
        await query.edit_message_text(f"❌ Failed to delete video '{video_title}'.")
    
    return ConversationHandler.END

# Conversation handler for deleting videos
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled.")
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

# Command: Unknown commands
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Sorry, I don’t recognize that command. Please use /start to see available commands.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('newvid', newvid_start)],
    states={
        ASK_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)],
        ASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
    )
        # Setting up the conversation handler
    delete_conversation = ConversationHandler(
        entry_points=[CommandHandler('delete', delete)],  # Start with /delete command
        states={
            SELECTING_VIDEO: [CallbackQueryHandler(handle_video_selection)],  # Handle video selection
        },
        fallbacks=[CommandHandler('cancel', cancel)]  # Handle cancellation
    )

    
    

    app.add_handler(conv_handler)   
    app.add_handler(delete_conversation)   
    
    
    app.add_handler(CommandHandler('hello', handlehello))
    app.add_handler(CommandHandler('flushdb', flushdb))
    app.add_handler(CommandHandler('videoslist', videoslist))
    app.add_handler(CommandHandler('videoslength', videoslength))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_text))



    logger.info('🤖 Bot running with webhooks...')
    app.run_webhook(
        listen='0.0.0.0',
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL
    )



if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(e)
 