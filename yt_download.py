import yt_dlp
import os
import time
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def download_youtube_video(url, output_path="downloads"):
    """
    Downloads a YouTube video using yt-dlp.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading: {url}")
            info_dict = ydl.extract_info(url, download=True)
            video_title = info_dict.get('title', 'Unknown Title')
            print(f"Successfully downloaded: {video_title}")
            return True, video_title
    except Exception as e:
        print(f"Error downloading video: {e}")
        return False, str(e)

async def cmd_do_ytmp3cvt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    is_authorized = context.user_data.get("is_authorized", False)
    last_activity = context.user_data.get("last_activity", 0)
    current_time = time.time()

    # Check auth and 10-minute (600 seconds) timeout
    if not is_authorized or (current_time - last_activity > 600):
        logger.info("Access denied or session timed out for user_id=%s", update.effective_user.id if update.effective_user else None)
        context.user_data["is_authorized"] = False  # Reset auth state safely
        await update.message.reply_text("Unauthorized or session expired. Please authenticate using /do_auth first.")
        return

    # Update last activity to prevent timeout while active
    context.user_data["last_activity"] = current_time

    if not context.args:
        await update.message.reply_text("Please provide a YouTube URL. Example: /do_ytmp3cvt https://www.youtube.com/watch?v=...")
        return

    url = context.args[0]
    await update.message.reply_text("📥 Downloading video... Please wait.")

    loop = asyncio.get_running_loop()
    
    # Execute the synchronous download function in a separate thread so it doesn't block the bot
    success, result = await loop.run_in_executor(None, download_youtube_video, url)

    if success:
        await update.message.reply_text(f"✅ Successfully downloaded: {result}")
    else:
        await update.message.reply_text(f"❌ Error downloading video: {result}")

if __name__ == "__main__":
    # Test the download function
    test_url = input("Enter YouTube URL: ")
    download_youtube_video(test_url)
