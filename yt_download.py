import glob
import os
import re
import time
import logging
import asyncio
import subprocess
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

YOUTUBE_URL_PATTERN = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+', re.IGNORECASE
)
TELEGRAM_AUDIO_SIZE_LIMIT = 50 * 1024 * 1024  # 50 MB


def is_valid_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_URL_PATTERN.match(url))


def download_youtube_video(url, output_path=os.path.expanduser("~/yt-dlp-mp3")):
    """
    Downloads a YouTube video as MP3 using system yt-dlp.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    try:
        print(f"Downloading: {url}")

        # YouTube title ကို filename အနေနဲ့ use မယ်
        # %(title)s က yt-dlp ကိုယ်တိုင် sanitize လုပ်ပေးတယ်
        output_template = os.path.join(output_path, "%(title)s.%(ext)s")

        command = [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--no-playlist",                   # playlist ဆိုရင် ပထမ video တစ်ပုဒ်ကိုသာ ဆွဲ
            "--cookies-from-browser", "chrome",
            "-o", output_template,
            "--print", "after_move:filepath",
            url
        ]

        logger.info(f"Running command: {' '.join(command)}")

        result = subprocess.run(command, capture_output=True, text=True, check=True)

        if result.stdout:
            logger.info(f"yt-dlp stdout:\n{result.stdout}")
        if result.stderr:
            logger.info(f"yt-dlp stderr:\n{result.stderr}")

        # --print after_move:filepath က final path ကို stdout မှာ ထုတ်ပေးတယ်
        final_file_path = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None

        # stdout မရရင် output_path ထဲမှ အသစ်ဆုံး .mp3 ဖိုင်ကိုယူ
        if not final_file_path or not os.path.exists(final_file_path):
            mp3_files = glob.glob(os.path.join(output_path, "*.mp3"))
            if mp3_files:
                final_file_path = max(mp3_files, key=os.path.getmtime)
            else:
                logger.error("No .mp3 file found after yt-dlp finished.")
                return False, "yt-dlp ပြီးသွားသော်လည်း .mp3 ဖိုင်မတွေ့ပါ။ ffmpeg ထည့်သွင်းထားဖို့ လိုအပ်နိုင်သည်။"

        logger.info(f"Using file: {final_file_path}")
        print(f"Successfully downloaded: {final_file_path}")
        return True, final_file_path

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        logger.error(f"yt-dlp command failed with code {e.returncode}")
        logger.error(f"yt-dlp error output:\n{error_msg}")
        print(f"Error downloading video: {error_msg}")
        return False, error_msg
    except Exception as e:
        logger.error(f"Error executing yt-dlp: {e}")
        print(f"Error executing yt-dlp: {e}")
        return False, str(e)

async def process_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    await update.message.reply_text("📥 ယူကျု့ဗီဒီယို ဒေါင်းလုပ်ဆွဲနေပါပြီ... ခဏစောင့်ပေးပါ။")

    loop = asyncio.get_running_loop()
    
    # Execute the synchronous download function in a separate thread so it doesn't block the bot
    success, result = await loop.run_in_executor(None, download_youtube_video, url)

    if success:
        file_path = result

        # Telegram bot file size limit is 50 MB
        file_size = os.path.getsize(file_path)
        if file_size > TELEGRAM_AUDIO_SIZE_LIMIT:
            os.remove(file_path)
            size_mb = file_size // (1024 * 1024)
            await update.message.reply_text(
                f"❌ ဖိုင်ဆိုဒ် ({size_mb} MB) သည် Telegram ၏ 50MB ကန့်သတ်ချက်ကို ကျော်လွန်ပါသည်။"
            )
            return

        await update.message.reply_text("✅ အောင်မြင်စွာ ဆွဲပြီးပါပြီ။ ဖိုင်ပို့ပေးနေပါပြီ...")
        logger.info(f"Sending audio file to user: {file_path} ({file_size} bytes)")

        try:
            with open(file_path, "rb") as audio_file:
                await update.message.reply_audio(
                    audio=audio_file,
                    write_timeout=300,   # 5 min — file upload အတွက်
                    read_timeout=300,    # 5 min — Telegram processing + response အတွက်
                    connect_timeout=30,
                )
            context.user_data["last_activity"] = time.time()
            logger.info("Audio sent successfully.")
        except Exception as e:
            logger.error(f"Error sending audio to Telegram: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Telegram သို့ဖိုင်ပို့ရာတွင် အခက်အခဲရှိနေပါသည်။\n{e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Temp file deleted: {file_path}")
    else:
        logger.error(f"Download failed for {url}: {result}")
        await update.message.reply_text(f"❌ Download မအောင်မြင်ပါ:\n{result}")


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
        context.user_data["awaiting_youtube_link"] = True
        await update.message.reply_text("ကျေးဇူးပြု၍ YouTube video link ကို ပို့ပေးပါ။")
        return

    url = context.args[0]
    if not is_valid_youtube_url(url):
        await update.message.reply_text("❌ မှားယွင်းသော URL ဖြစ်ပါသည်။ YouTube link သာ ပေးပို့နိုင်ပါသည်။")
        return
    await process_youtube_link(update, context, url)

if __name__ == "__main__":
    # Test the download function
    test_url = input("Enter YouTube URL: ")
    download_youtube_video(test_url)
