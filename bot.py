from pyrogram import Client, filters, idle
from pyrogram.types import *
from pyrogram.errors import *
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio, datetime, time
from os import environ as env

# --- Constants ---

ACCEPTED_TEXT = "Hey {user}\n\nYour Request For {chat} Is Accepted ✅"
R_TEXT = "Hey {user}\n\nYour Request For {chat} Is Ejected"
START_TEXT = "Hai {}\n\nI am Auto Request Accept Bot With Working For All Channel. Add Me In Your Channel To Use"
REQUIRED_KEYWORDS = ["@LarvaLinks", "@PiratesHunts_Bot", "@MovieWalaChat"]

CHANNEL_ID = -1002557174306
ADMIN_ID = 8094066652

# --- Environment Setup ---
API_ID = int(env.get('API_ID', 26292638))
API_HASH = env.get('API_HASH', "2201865f0e468725d3b9e0f54b090f0f")
BOT_TOKEN = env.get('BOT_TOKEN', "7828770858:AAH78_btTyPNvRb6rESFKQT6Br0QT4Esh6w")
DB_URL = env.get('DB_URL', "mongodb+srv://Bhardwaj:7vVHr6zrvpsMsU3@cluster0.p2smf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# --- DB and Bot ---
Dbclient = AsyncIOMotorClient(DB_URL)
Cluster = Dbclient['Cluster0']
Data = Cluster['users']
Bot = Client(name='AutoAcceptBot', api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Periodic Bio Validator ---
async def validate_users():
    async for user_doc in Data.find({}):
        user_id = user_doc['id']
        if int(user_id) == ADMIN_ID:
            continue
        try:
            member = await Bot.get_chat_member(CHANNEL_ID, user_id)
            user = await Bot.get_chat(user_id)
            bio = user.bio or ""
            if not any(k.lower() in bio.lower() for k in REQUIRED_KEYWORDS):
                print(f"Kicking user {user_id} for missing keywords")
                await Bot.send_message(
                    user_id,
                    "You have been removed from the channel due to missing required keywords in your bio.\n\nPlease update your bio with any of the following and try again:\n" +
                    "\n".join(REQUIRED_KEYWORDS)
                )
                await Bot.ban_chat_member(CHANNEL_ID, user_id)
                await Bot.unban_chat_member(CHANNEL_ID, user_id)
                await Data.delete_one({'id': user_id})
        except UserNotParticipant:
            print(f"User {user_id} not in channel")
            await Data.delete_one({'id': user_id})
        except Exception as e:
            print(f"Error checking user {user_id}: {e}")

# --- Periodic Task ---
async def periodic_check():
    while True:
        print("Running bio validation...")
        await validate_users()
        await asyncio.sleep(60)

# --- Command Handlers ---
@Bot.on_message(filters.command("start") & filters.private)
async def start_handler(c, m):
    user_id = m.from_user.id
    if not await Data.find_one({'id': user_id}):
        await Data.insert_one({'id': user_id})
    button = [[
        InlineKeyboardButton('Movie Provider🤞', url='https://t.me/PiratesHunts_Bot'),
        InlineKeyboardButton('Support🔆', url='https://t.me/MovieWalaChat')
    ]]
    await m.reply_text(text=START_TEXT.format(m.from_user.mention), disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(button))

@Bot.on_message(filters.command(["broadcast", "users"]) & filters.user(ADMIN_ID))
async def broadcast(c, m):
    if m.text == "/users":
        total_users = await Data.count_documents({})
        return await m.reply(f"Total Users: {total_users}")
    b_msg = m.reply_to_message
    sts = await m.reply_text("Broadcasting your messages...")
    users = Data.find({})
    total_users = await Data.count_documents({})
    done = success = failed = 0
    start_time = time.time()
    async for user in users:
        user_id = int(user['id'])
        try:
            await b_msg.copy(chat_id=user_id)
            success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await b_msg.copy(chat_id=user_id)
            success += 1
        except (InputUserDeactivated, UserIsBlocked, PeerIdInvalid):
            await Data.delete_many({'id': user_id})
            failed += 1
        except Exception:
            failed += 1
        done += 1
        if done % 20 == 0:
            await sts.edit(f"Broadcasting...\nTotal: {total_users}\nDone: {done}\nSuccess: {success}\nFailed: {failed}")
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.delete()
    await m.reply_text(f"Broadcast Done in {time_taken}.\nTotal: {total_users}\nSuccess: {success}\nFailed: {failed}")

# --- Join Request Handler ---
@Bot.on_chat_join_request()
async def join_request(c, m):
    user_id = m.from_user.id
    chat_id = m.chat.id
    try:
        user = await Bot.get_chat(user_id)
        bio = user.bio or ""
        print(f"[Join Request] {user_id} bio: {bio}")
        if not any(k.lower() in bio.lower() for k in REQUIRED_KEYWORDS):
            await c.decline_chat_join_request(chat_id, user_id)
            await c.send_message(user_id, R_TEXT.format(user=m.from_user.mention, chat=m.chat.title))
            return
        if not await Data.find_one({'id': user_id}):
            await Data.insert_one({'id': user_id})
        await c.approve_chat_join_request(chat_id, user_id)
        await c.send_message(user_id, ACCEPTED_TEXT.format(user=m.from_user.mention, chat=m.chat.title))
    except Exception as e:
        print(f"Join request error for {user_id}: {e}")

# --- Manual Check Handler ---
@Bot.on_message(filters.command("runcheck") & filters.user(ADMIN_ID))
async def manual_check(_, __):
    await validate_users()
    print("Manual check completed.")

# --- Fix for Koyeb: msg_id too low ---
from pyrogram.session.session import Session
Session._start_time = int(time.time())

# --- Start Bot ---
Bot.start()
asyncio.get_event_loop().create_task(periodic_check())
print("Bot running... Made By PiratesHunts")
idle()
Bot.stop()
