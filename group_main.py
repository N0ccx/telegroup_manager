from telethon import TelegramClient, events, functions, types
import asyncio
import os
import logging
from telethon.errors import FloodWaitError, ChatAboutNotModifiedError
import time
from datetime import datetime
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_group.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_name = os.getenv("SESSION_NAME")

client = TelegramClient(session_name, api_id, api_hash)

BANNED_KEYWORDS = [
    "scam",
    "airdrop",
    "giveaway",
    "free crypto",
    "dm me",
    "wallet seed",
    "recovery phrase",
    "porn",
    "rug",
    "hentai",
    "safu",
    "fud",
    "pamp",
    "send btc",
    "admin here",
    "investment tip",
    "nsfw",
    "naked",
    "pajeet",
    "moonboy",
    "buy this now",
    "click this",
    "onlyfans",
    "telegrammod",
    "pump it",
    "cashapp",
    "mod dm",
    "crypto god",
    "binance hack",
    "metamask help"
]

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

BOT_USERNAMES = [
    "@MissRose_bot",
    "@safeguard",
    "@cherrys",
    "@MajorBuyBot"
]

# Bot-specific admin rights
BOT_ADMIN_RIGHTS = {
    "@MissRose_bot": {
        "post_messages": True,
        "edit_messages": True,
        "delete_messages": True,
        "ban_users": True,
        "invite_users": True,
        "pin_messages": True,
        "add_admins": False,
        "manage_call": True,
        "anonymous": False,
        "manage_topics": True
    },
    "@safeguard": {
        "post_messages": True,
        "edit_messages": True,
        "delete_messages": True,
        "ban_users": True,
        "invite_users": True,
        "pin_messages": True,
        "add_admins": False,
        "manage_call": False,
        "anonymous": False,
        "manage_topics": True
    },
    "@cherrys": {
        "post_messages": True,
        "edit_messages": True,
        "delete_messages": True,
        "ban_users": True,
        "invite_users": True,
        "pin_messages": True,
        "add_admins": False,
        "manage_call": False,
        "anonymous": False,
        "manage_topics": True
    }
}



async def resolve_users(usernames):
    entities = []
    for username in usernames:
        try:
            entity = await client.get_entity(username)
            entities.append(entity)
            logger.info(f"Successfully resolved user: {username}")
        except Exception as e:
            logger.error(f"Could not resolve {username}: {e}")
    return entities

async def safe_telegram_call(call_func, *args, retries=3, delay=1):
    if DRY_RUN:
        logger.info(f"[DryRun] Would call {call_func.__name__} with args: {args}")
        return None

    for attempt in range(retries):
        try:
            return await call_func(*args)
        except FloodWaitError as e:
            wait_time = e.seconds
            logger.warning(f"[Rate Limit] Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
        except Exception as ex:
            logger.error(f"[Attempt {attempt+1}] Error calling {call_func.__name__}: {ex}")
            if attempt + 1 == retries:
                raise
            sleep_time = delay * (attempt + 1)
            time.sleep(sleep_time)

async def create_basic_group(title, about=""):
    result = await client(functions.channels.CreateChannelRequest(
        title=title,
        about=about,
        megagroup=True
    ))
    return result.chats[0].id


async def upgrade_to_supergroup(chat_id):
    res = await client(functions.messages.MigrateChatRequest(chat_id))
    return res.chats[0].id

async def upload_and_set_photo(chat_id, photo_path):
    try:
        if photo_path and os.path.exists(photo_path):
            file = await client.upload_file(photo_path)
            await client(functions.channels.EditPhotoRequest(
                channel=chat_id,
                photo=types.InputChatUploadedPhoto(file)
            ))
            logger.info("Group photo updated successfully")
    except Exception as e:
        logger.error(f"Failed to update photo: {e}")

async def set_public_link(chat_id, base_username):
    if base_username.endswith("ONSOL"):
        username = base_username
    else:
        username = base_username + "ONSOLL"

    try:
        await client(functions.channels.UpdateUsernameRequest(
            channel=chat_id,
            username=username
        ))
        return f"https://t.me/{username}"
    except Exception as e:
        print(f"Failed to set public username {username}: {e}")
        return None

async def invite_users(chat_id, users):
    for user in users:
        try:
            await client(functions.channels.InviteToChannelRequest(
                channel=chat_id,
                users=[user]
            ))
        except Exception as e:
            print(f"Could not invite {user.username}: {e}")

async def promote_bots(chat_id, bot_usernames):
    for username in bot_usernames:
        try:
            user = await client.get_entity(username)
            admin_rights = BOT_ADMIN_RIGHTS.get(username, {
                "post_messages": True,
                "edit_messages": True,
                "delete_messages": True,
                "ban_users": True,
                "invite_users": True,
                "pin_messages": True,
                "add_admins": False,
                "manage_call": True,
                "anonymous": False,
                "manage_topics": True
            })
            
            await client(functions.channels.EditAdminRequest(
                channel=chat_id,
                user_id=user,
                admin_rights=types.ChatAdminRights(**admin_rights),
                rank="Bot"
            ))
            logger.info(f"Successfully promoted {username} to admin")
        except Exception as e:
            logger.error(f"Could not promote {username}: {e}")

async def post_and_pin_welcome(chat_id, message):
    try:
        sent_msg = await client.send_message(chat_id, message)
        await client(functions.messages.UpdatePinnedMessageRequest(
            peer=chat_id,
            id=sent_msg.id,
            silent=False
        ))
    except Exception as e:
        print(f"Failed to pin welcome message: {e}")

async def execute(client_func, *args):
    if DRY_RUN:
        print(f"[DryRun] Would call {client_func.__name__} with {args}")
    else:
        return await safe_telegram_call(client_func, *args) 

def setup_keyword_moderation(chat_id):
    @client.on(events.NewMessage(chats=chat_id))
    async def handler(event):
        try:
            sender = await event.get_sender()
            if sender.bot or getattr(sender, "admin_rights", None):
                return

            msg = event.message.message.lower()
            matched_keywords = [kw for kw in BANNED_KEYWORDS if kw in msg]

            if matched_keywords:
                await event.delete()
                logger.info(f"Deleted message containing banned keywords: {matched_keywords}")
                warning_msg = (
                    "⚠️ *Message Deleted*\n\n"
                    f"Your message contained banned content.\n"
                    f"*Keywords:* `{', '.join(matched_keywords)}`"
                )
                try:
                    await event.respond(warning_msg, parse_mode='markdown')
                except Exception:
                    await event.respond(f"⚠️ Message removed. Keywords: {', '.join(matched_keywords)}")
        except Exception as e:
            logger.error(f"Error in keyword moderation: {e}")
            try:
                await event.respond("⚠️ Error processing message. Contact an admin.")
            except Exception as notify_error:
                logger.error(f"Failed to notify user: {notify_error}")


def format_description_from_community(community: dict) -> str:
    parts = []

    if "welcome_message" in community:
        parts.append(community["welcome_message"])

    if "closing" in community:
        parts.append(community["closing"])

    if "hashtags" in community:
        parts.append(" ".join(community["hashtags"]))

    # Combine and truncate to max 255 chars
    desc = "\n".join(parts).strip()
    return desc[:255]


async def create_group_wizard(
    group_title,
    group_description,
    photo_path,
    user_usernames,
    public_username_base,
    welcome_message
):
    try:
        await client.start()
        logger.info("Starting group creation wizard")

        human_user_entities = []
        if user_usernames:
            human_user_entities = await resolve_users(user_usernames)
            if not human_user_entities:
                logger.warning(f"Could not resolve any of the provided human users for invitation: {user_usernames}")
        else:
            logger.info("No human user usernames provided for invitation.")


        chat_id = await create_basic_group(group_title, group_description)
        logger.info(f"Created supergroup with ID: {chat_id}, Title: '{group_title}'")

        if photo_path:
            await upload_and_set_photo(chat_id, photo_path)

       
        logger.info("Group description was set during creation.")

        public_link = await set_public_link(chat_id, public_username_base)
        if public_link:
            logger.info(f"Set public link: {public_link}")
        else:
            logger.warning(f"Failed to set public link for base: {public_username_base}. The group will remain private or without a custom link.")

        if human_user_entities:
            await invite_users(chat_id, human_user_entities)
            logger.info(f"Attempted to invite {len(human_user_entities)} resolved human users to the group.")
        else:
            logger.info("No human users were invited (either none provided, or none could be resolved).")

        await promote_bots(chat_id, BOT_USERNAMES)
        
        await post_and_pin_welcome(chat_id, welcome_message)

        setup_keyword_moderation(chat_id)
        logger.info("Setup keyword moderation")

        print(f"🎉 Group Created: {group_title}")
        print(f"🔗 Public Link: {public_link or 'Private Group / Link not set'}")

        print("[Listening for banned keywords... Press Ctrl+C to stop.]")
        await client.run_until_disconnected()
       

    except ValueError as ve:
        logger.error(f"ValueError in group creation wizard: {ve}")
       
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred in group creation wizard: {e}")
        raise


