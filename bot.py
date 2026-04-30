import os
import logging
import time

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters



logging.basicConfig(
	format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
	level=logging.INFO,
)
logger = logging.getLogger(__name__)


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

		from yt_download import process_youtube_link
		await process_youtube_link(update, context, url)
		return


def main() -> None:
	token = os.getenv("TELEGRAM_BOT_TOKEN")
	AUTHORIZED_USERNAME = os.getenv("AUTHORIZED_USERNAME")
	if not token:
		raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")
	if not AUTHORIZED_USERNAME:
		raise RuntimeError("AUTHORIZED_USERNAME environment variable is required")

	from yt_download import cmd_do_ytmp3cvt

	application = Application.builder().token(token).build()
	application.bot_data["AUTHORIZED_USERNAME"] = AUTHORIZED_USERNAME
	logger.info("Starting Telegram bot and registering handlers")
	application.add_handler(CommandHandler("ping", cmd_ping))
	application.add_handler(CommandHandler("do_auth", do_authentication))
	application.add_handler(CommandHandler("do_ytmp3cvt", cmd_do_ytmp3cvt))
	application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
	logger.info("Bot polling started")
	application.run_polling(close_loop=False)


if __name__ == "__main__":
	main()
