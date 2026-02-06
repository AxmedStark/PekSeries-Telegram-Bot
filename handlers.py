import logging
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction
from api import TVMazeClient
from config import ADMIN_ID
from states import AddShow

router = Router()


def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add series", callback_data="btn_add")],
        [InlineKeyboardButton(text="📋 My list", callback_data="btn_list"),
         InlineKeyboardButton(text="📅 Calendar", callback_data="btn_calendar")],
        [InlineKeyboardButton(text="ℹ️ Help", callback_data="btn_help")]
    ])


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Hi! I'm checking releases of new episodes for you.\nChoose action:",
        reply_markup=get_main_keyboard()
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, db):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        users_count, subs_count = await db.get_stats()
        await message.answer(
            f"👑 <b>Admin Panel</b>\n\n"
            f"👥 Users: {users_count}\n"
            f"📺 Subscriptions: {subs_count}",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Admin Error: {e}")
        await message.answer("⚠️ Error fetching stats.")



@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    await message.answer("✍️ Send me name of series or link from TVMaze:")
    await state.set_state(AddShow.waiting_for_title)


@router.callback_query(F.data == "btn_add")
async def cb_add_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Send me name of series or link from TVMaze:")
    await state.set_state(AddShow.waiting_for_title)
    await callback.answer()


@router.message(AddShow.waiting_for_title)
async def process_add_show(message: Message, state: FSMContext, db):
    # Показываем статус "печатает", пока ищем
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    query = message.text
    msg = await message.answer(f"🔍 Searching «{query}»...")

    sid, name, url = await TVMazeClient.search_show(query)

    if sid:
        is_added = await db.add_subscription(
            user_id=message.from_user.id,
            show_id=sid,
            show_name=name,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        if is_added:
            details = await TVMazeClient.get_show_details(sid)

            if not details:
                details = {'year': '????', 'rating': 'N/A', 'status': 'Unknown', 'genres': ''}

            status_emoji = "🟢" if details['status'] == "Running" else "🔴" if details['status'] == "Ended" else "🟡"

            text = (
                f"✅ <b>Subscription added!</b>\n\n"
                f"🎬 <b><a href='{url}'>{name}</a></b> ({details['year']})\n"
                f"⭐ Rating: <b>{details['rating']}</b>\n"
                f"{status_emoji} Status: {details['status']}\n"
                f"🎭 Genres: {details['genres']}\n\n"
                f"<i>I'll notify you when a new episode is released.</i>"
            )

            await msg.edit_text(text, parse_mode="HTML", reply_markup=get_main_keyboard())
        else:
            await msg.edit_text(f"ℹ️ You are already subscribed to <b>{name}</b>.", parse_mode="HTML",
                                reply_markup=get_main_keyboard())
    else:
        await msg.edit_text("❌ Couldn't find it. Try a different name.", reply_markup=get_main_keyboard())

    await state.clear()



@router.message(Command("list"))
async def cmd_list(message: Message, db):
    await show_user_list(message, db)


@router.callback_query(F.data == "btn_list")
async def cb_list(callback: CallbackQuery, db):
    await show_user_list(callback.message, db)
    await callback.answer()


async def show_user_list(message_obj: Message, db):
    subs = await db.get_user_subscriptions(message_obj.chat.id)  # Используем chat.id, это универсально

    if not subs:
        try:
            await message_obj.edit_text("Your list is empty.", reply_markup=get_main_keyboard())
        except:
            await message_obj.answer("Your list is empty.", reply_markup=get_main_keyboard())
        return

    buttons = []
    for show_name, show_id in subs:
        buttons.append([InlineKeyboardButton(text=f"❌ Delete: {show_name}", callback_data=f"del_{show_name}")])
    buttons.append([InlineKeyboardButton(text="🔙 Menu", callback_data="btn_menu")])

    try:
        await message_obj.edit_text("Your series:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except:
        await message_obj.answer("Your series:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("del_"))
async def cb_delete(callback: CallbackQuery, db):
    show_name = callback.data.split("del_")[1]
    await db.delete_subscription(callback.from_user.id, show_name)
    await callback.answer(f"{show_name} deleted!")
    await cb_list(callback, db)



@router.message(Command("calendar"))
async def cmd_calendar(message: Message, db):
    await show_calendar(message, db)


@router.callback_query(F.data == "btn_calendar")
async def cb_calendar(callback: CallbackQuery, db):
    await callback.answer("Updating calendar...")
    await show_calendar(callback.message, db)


async def show_calendar(message_obj: Message, db):

    msg = None
    try:
        msg = await message_obj.edit_text("⏳ Checking release dates...")
    except:
        msg = await message_obj.answer("⏳ Checking release dates...")

    subs = await db.get_user_subscriptions(message_obj.chat.id)
    if not subs:
        await msg.edit_text("List is empty.", reply_markup=get_main_keyboard())
        return

    report = []
    for show_name, show_id in subs:
        next_ep = await TVMazeClient.get_next_episode(show_id)
        if next_ep:
            date = next_ep.get('airdate', '???')
            s_num = f"S{next_ep.get('season')}E{next_ep.get('number')}"
            report.append(f"📅 <b>{date}</b>: {show_name} ({s_num})")

    report.sort()
    result_text = "<b>🗓 Upcoming releases:</b>\n\n" + ("\n".join(report) if report else "No upcoming releases found.")

    # Добавляем кнопку "Назад"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Menu", callback_data="btn_menu")]])

    await msg.edit_text(result_text, parse_mode="HTML", reply_markup=kb)



@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "🤖 <b>How to use me:</b>\n\n"
        "1. Press <b>Add series</b> (or /add)\n"
        "2. Type name of series\n"
        "3. I'll inform you about new episodes!\n\n"
        "Use /list to manage subscriptions."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())


@router.callback_query(F.data == "btn_help")
async def cb_help(callback: CallbackQuery):
    text = (
        "🤖 <b>How to use me:</b>\n\n"
        "1. Press <b>Add series</b>\n"
        "2. Type name of series\n"
        "3. I'll inform you about new episodes!\n\n"
        "In <b>Calendar</b> you can see upcoming releases."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_keyboard())


@router.callback_query(F.data == "btn_menu")
async def cb_menu(callback: CallbackQuery):
    await callback.message.edit_text("Main menu:", reply_markup=get_main_keyboard())


@router.message()
async def unknown_message(message: Message):
    await message.answer(
        "I don't understand this message 🤷‍♂️\n"
        "Please use menu buttons or commands (e.g. /start).",
        reply_markup=get_main_keyboard()
    )