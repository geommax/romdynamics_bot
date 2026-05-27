import glob
import os
import time
import logging
import asyncio
import subprocess

from telegram import Update
from telegram.ext import ContextTypes

from yt_download import is_valid_youtube_url


logger = logging.getLogger(__name__)


def yt_download_mp4_save(url: str, output_path: str = os.path.expanduser("~/yt-dlp-mp4")):
	"""
	Downloads a YouTube video as MP4 using system yt-dlp and saves it to disk.
	"""
	if not os.path.exists(output_path):
		os.makedirs(output_path)

	try:
		output_template = os.path.join(output_path, "%(title)s.%(ext)s")
		command = [
			"yt-dlp",
			"-f", "mp4/best[ext=mp4]/best",
			"--merge-output-format", "mp4",
			"--no-playlist",
			"--cookies-from-browser", "chrome",
			"-o", output_template,
			"--print", "after_move:filepath",
			url,
		]

		logger.info("Running command: %s", " ".join(command))
		result = subprocess.run(command, capture_output=True, text=True, check=True)

		if result.stdout:
			logger.info("yt-dlp stdout:\n%s", result.stdout)
		if result.stderr:
			logger.info("yt-dlp stderr:\n%s", result.stderr)

		final_file_path = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
		if not final_file_path or not os.path.exists(final_file_path):
			mp4_files = glob.glob(os.path.join(output_path, "*.mp4"))
			if mp4_files:
				final_file_path = max(mp4_files, key=os.path.getmtime)
			else:
				logger.error("No .mp4 file found after yt-dlp finished.")
				return False, "yt-dlp ပြီးသွားသော်လည်း .mp4 ဖိုင်မတွေ့ပါ။ ffmpeg ထည့်သွင်းထားဖို့ လိုအပ်နိုင်သည်။"

		logger.info("Saved MP4 file: %s", final_file_path)
		return True, final_file_path
	except subprocess.CalledProcessError as error:
		error_msg = error.stderr if error.stderr else str(error)
		logger.error("yt-dlp command failed with code %s", error.returncode)
		logger.error("yt-dlp error output:\n%s", error_msg)
		return False, error_msg
	except Exception as error:
		logger.error("Error executing yt-dlp: %s", error)
		return False, str(error)


async def process_youtube_link_mp4_save(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
	await update.message.reply_text("📥 YouTube video ကို MP4 အဖြစ် ဒေါင်းလုပ်ဆွဲနေပါပြီ... ခဏစောင့်ပေးပါ။")

	loop = asyncio.get_running_loop()
	success, result = await loop.run_in_executor(None, yt_download_mp4_save, url)

	if success:
		file_path = result
		file_size = os.path.getsize(file_path)
		size_mb = file_size / (1024 * 1024)
		context.user_data["last_activity"] = time.time()
		logger.info("MP4 file saved (not sent): %s (%s bytes)", file_path, file_size)
		await update.message.reply_text(
			f"✅ MP4 file ကို အောင်မြင်စွာ ဒေါင်းလုပ်ဆွဲပြီး Folder မှာ သိမ်းထားပါပြီ။\n"
			f"📁 Path: {file_path}\n"
			f"📦 Size: {size_mb:.2f} MB"
		)
		return

	logger.error("MP4 download failed for %s: %s", url, result)
	await update.message.reply_text(f"❌ MP4 download မအောင်မြင်ပါ:\n{result}")


async def cmd_do_ytmp4save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		return

	is_authorized = context.user_data.get("is_authorized", False)
	last_activity = context.user_data.get("last_activity", 0)
	current_time = time.time()

	if not is_authorized or (current_time - last_activity > 600):
		logger.info(
			"Access denied or session timed out for user_id=%s",
			update.effective_user.id if update.effective_user else None,
		)
		context.user_data["is_authorized"] = False
		await update.message.reply_text("Unauthorized or session expired. Please authenticate using /do_auth first.")
		return

	context.user_data["last_activity"] = current_time

	if not context.args:
		context.user_data["awaiting_youtube_link_mp4_save"] = True
		await update.message.reply_text("ကျေးဇူးပြု၍ YouTube video link ကို ပို့ပေးပါ။ (MP4 အဖြစ် Folder မှာသာ သိမ်းမည်)")
		return

	url = context.args[0]
	if not is_valid_youtube_url(url):
		await update.message.reply_text("❌ မှားယွင်းသော URL ဖြစ်ပါသည်။ YouTube link သာ ပေးပို့နိုင်ပါသည်။")
		return

	await process_youtube_link_mp4_save(update, context, url)
