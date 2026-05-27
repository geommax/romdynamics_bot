import os
import logging
import time

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest



logging.basicConfig(
	format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
	level=logging.INFO,
)
logger = logging.getLogger(__name__)

USAGE_TEXT = (
	"🤖 RomDynamics Bot\n\n"
	"Available commands:\n"
	"/ping — Bot alive check\n"
	"/do_auth — Authenticate session\n"
	"/do_ytmp3cvt [url] — Download YouTube audio as MP3 & send\n"
	"/do_ytmp3save [url] — Download YouTube audio as MP3 & save to folder only\n"
	"/do_ytmp4save [url] — Download YouTube video as MP4 & save to folder only\n\n"
	"Session expires after 10 minutes of inactivity."
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if update.message:
		await update.message.reply_text(USAGE_TEXT)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if update.message:
		await update.message.reply_text(USAGE_TEXT)


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if update.message:
		logger.info(
			"/ping from user_id=%s chat_id=%s",
			update.effective_user.id if update.effective_user else None,
			update.effective_chat.id if update.effective_chat else None,
		)
		await update.message.reply_text("pong")


async def do_authentication(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		logger.warning("do_authentication called without message payload")
		return
	logger.info(
		"Auth flow started by user_id=%s chat_id=%s",
		update.effective_user.id if update.effective_user else None,
		update.effective_chat.id if update.effective_chat else None,
	)
	context.user_data["awaiting_auth_reply"] = True
	await update.message.reply_text("Who are you?")


async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message or not update.message.text:
		return

	# Handle Auth Flow
	if context.user_data.get("awaiting_auth_reply", False):
		provided_username = update.message.text.strip()
		context.user_data["awaiting_auth_reply"] = False
		logger.info(
			"Auth reply received user_id=%s provided_username=%s",
			update.effective_user.id if update.effective_user else None,
			provided_username,
		)

		if provided_username == context.bot_data.get("AUTHORIZED_USERNAME"):
			logger.info("Auth success for user_id=%s", update.effective_user.id if update.effective_user else None)
			context.user_data["is_authorized"] = True
			context.user_data["last_activity"] = time.time()
			await update.message.reply_text("Authorized. You can now use restricted commands.")
		else:
			logger.info("Auth failed for user_id=%s", update.effective_user.id if update.effective_user else None)
			context.user_data["is_authorized"] = False
			await update.message.reply_text("Unauthorized.")
		return

	# Handle YouTube Link Flow
	if context.user_data.get("awaiting_youtube_link", False):
		url = update.message.text.strip()
		context.user_data["awaiting_youtube_link"] = False

		# Verify auth inside this flow just to be safe
		is_authorized = context.user_data.get("is_authorized", False)
		last_activity = context.user_data.get("last_activity", 0)
		if not is_authorized or (time.time() - last_activity > 600):
			context.user_data["is_authorized"] = False
			await update.message.reply_text("Session expired. Please authenticate again.")
			return

		# Refresh session before the potentially long download starts
		context.user_data["last_activity"] = time.time()

		from yt_download import is_valid_youtube_url, process_youtube_link
		if not is_valid_youtube_url(url):
			await update.message.reply_text("❌ မှားယွင်းသော URL ဖြစ်ပါသည်။ YouTube link သာ ပေးပို့နိုင်ပါသည်။")
			return

		await process_youtube_link(update, context, url)
		return

	# Handle YouTube Save-Only Flow
	if context.user_data.get("awaiting_youtube_link_save", False):
		url = update.message.text.strip()
		context.user_data["awaiting_youtube_link_save"] = False

		is_authorized = context.user_data.get("is_authorized", False)
		last_activity = context.user_data.get("last_activity", 0)
		if not is_authorized or (time.time() - last_activity > 600):
			context.user_data["is_authorized"] = False
			await update.message.reply_text("Session expired. Please authenticate again.")
			return

		context.user_data["last_activity"] = time.time()

		from yt_download import is_valid_youtube_url, process_youtube_link_save_only
		if not is_valid_youtube_url(url):
			await update.message.reply_text("❌ မှားယွင်းသော URL ဖြစ်ပါသည်။ YouTube link သာ ပေးပို့နိုင်ပါသည်။")
			return

		await process_youtube_link_save_only(update, context, url)
		return

	# Handle YouTube MP4 Save-Only Flow
	if context.user_data.get("awaiting_youtube_link_mp4_save", False):
		url = update.message.text.strip()
		context.user_data["awaiting_youtube_link_mp4_save"] = False

		is_authorized = context.user_data.get("is_authorized", False)
		last_activity = context.user_data.get("last_activity", 0)
		if not is_authorized or (time.time() - last_activity > 600):
			context.user_data["is_authorized"] = False
			await update.message.reply_text("Session expired. Please authenticate again.")
			return

		context.user_data["last_activity"] = time.time()

		from yt_download import is_valid_youtube_url
		from yt_download_mp4 import process_youtube_link_mp4_save
		if not is_valid_youtube_url(url):
			await update.message.reply_text("❌ မှားယွင်းသော URL ဖြစ်ပါသည်။ YouTube link သာ ပေးပို့နိုင်ပါသည်။")
			return

		await process_youtube_link_mp4_save(update, context, url)
		return


def main() -> None:
	token = os.getenv("TELEGRAM_BOT_TOKEN")
	AUTHORIZED_USERNAME = os.getenv("AUTHORIZED_USERNAME")
	if not token:
		raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")
	if not AUTHORIZED_USERNAME:
		raise RuntimeError("AUTHORIZED_USERNAME environment variable is required")

	from yt_download import cmd_do_ytmp3cvt, cmd_do_ytmp3save
	from yt_download_mp4 import cmd_do_ytmp4save

	request = HTTPXRequest(
		read_timeout=300,
		write_timeout=300,
		connect_timeout=30,
	)
	application = Application.builder().token(token).request(request).build()
	application.bot_data["AUTHORIZED_USERNAME"] = AUTHORIZED_USERNAME
	logger.info("Starting Telegram bot and registering handlers")
	application.add_handler(CommandHandler("start", cmd_start))
	application.add_handler(CommandHandler("help", cmd_help))
	application.add_handler(CommandHandler("ping", cmd_ping))
	application.add_handler(CommandHandler("do_auth", do_authentication))
	application.add_handler(CommandHandler("do_ytmp3cvt", cmd_do_ytmp3cvt))
	application.add_handler(CommandHandler("do_ytmp3save", cmd_do_ytmp3save))
	application.add_handler(CommandHandler("do_ytmp4save", cmd_do_ytmp4save))
	application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
	logger.info("Bot polling started")
	application.run_polling(close_loop=False)


if __name__ == "__main__":
	main()
