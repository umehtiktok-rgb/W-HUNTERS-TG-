import logging
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN = "8683889309:AAFRStFSZVzoV_Wy1ai-FbInv_oB7iskizE"
ADMIN_CHAT_ID = 7139721940
PRIVATE_CHAT_ID = -1003818834337

# ─────────────────────────────────────────────
#  In-memory store: uid -> telegram user_id
# ─────────────────────────────────────────────
pending_users: dict[str, int] = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Welcome!\n\nPlease send me your UID to request access."
    )


async def receive_uid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    uid = update.message.text.strip()

    if not uid or len(uid) > 64:
        await update.message.reply_text("⚠️ Invalid UID. Please try again.")
        return

    pending_users[uid] = user.id

    admin_msg = (
        f"🔔 *New verification request*\n\n"
        f"👤 Name: {user.full_name}\n"
        f"🆔 Telegram ID: `{user.id}`\n"
        f"📋 UID: `{uid}`\n\n"
        f"To approve: `/approve {uid}`\n"
        f"To reject:  `/reject {uid}`"
    )
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_msg,
        parse_mode="Markdown",
    )

    await update.message.reply_text(
        "✅ Your UID has been submitted for review.\n"
        "You'll be notified once it's approved."
    )


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ You are not authorised to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /approve <uid>")
        return

    uid = context.args[0].strip()

    if uid not in pending_users:
        await update.message.reply_text(f"⚠️ No pending request found for UID: `{uid}`", parse_mode="Markdown")
        return

    telegram_user_id = pending_users.pop(uid)

    try:
        link = await context.bot.create_chat_invite_link(
            chat_id=PRIVATE_CHAT_ID,
            member_limit=1,
            name=f"invite-{uid}",
        )
        invite_url = link.invite_link
    except Exception as e:
        logger.error(f"Failed to create invite link: {e}")
        await update.message.reply_text(f"❌ Could not generate invite link: {e}")
        return

    await context.bot.send_message(
        chat_id=telegram_user_id,
        text=(
            f"🎉 Your UID has been verified!\n\n"
            f"Here is your one-time invite link:\n{invite_url}\n\n"
            f"⚠️ This link can only be used once."
        ),
    )

    await update.message.reply_text(f"✅ Approved and invite sent to UID: `{uid}`", parse_mode="Markdown")


async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ You are not authorised to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /reject <uid>")
        return

    uid = context.args[0].strip()

    if uid not in pending_users:
        await update.message.reply_text(f"⚠️ No pending request found for UID: `{uid}`", parse_mode="Markdown")
        return

    telegram_user_id = pending_users.pop(uid)

    await context.bot.send_message(
        chat_id=telegram_user_id,
        text="❌ Your UID could not be verified. Please contact support if you believe this is a mistake.",
    )

    await update.message.reply_text(f"🚫 Rejected UID: `{uid}`", parse_mode="Markdown")


async def pending_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ You are not authorised to use this command.")
        return

    if not pending_users:
        await update.message.reply_text("📭 No pending verification requests.")
        return

    lines = [f"• `{uid}` → TG ID: `{tg_id}`" for uid, tg_id in pending_users.items()]
    await update.message.reply_text(
        "📋 *Pending requests:*\n\n" + "\n".join(lines),
        parse_mode="Markdown",
    )


async def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CommandHandler("pending", pending_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_uid))

    logger.info("Bot is running...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
