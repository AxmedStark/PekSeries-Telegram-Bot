import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
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
    if message.from_user.id != ADMIN_ID:
        return

    users_count, subs_count = await db.get_stats()
    await message.answer(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Users: {users_count}\n"
        f"📺 Subscriptions: {subs_count}",
        parse_mode="HTML"
    )


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
    query = message.text
    msg = await message.answer(f"🔍 Searching «{query}»...")

    sid, name, url = await TVMazeClient.search_show(query)

    if sid:
        if await db.add_subscription(message.from_user.id, sid, name):
            await msg.edit_text(
                f"✅ Added <b><a href='{url}'>{name}</a></b> to your list!",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
        else:
            await msg.edit_text(f"ℹ️ I already added {name}.", reply_markup=get_main_keyboard())
    else:
        await msg.edit_text("❌ I couldn't find it. Try different name.", reply_markup=get_main_keyboard())

    await state.clear()


@router.message(Command("list"))
async def cmd_list(message: Message, db):
    subs = await db.get_user_subscriptions(message.from_user.id)
    if not subs:
        await message.answer("Your list is empty.", reply_markup=get_main_keyboard())
        return

    buttons = []
    for show_name, show_id in subs:
        buttons.append([InlineKeyboardButton(text=f"❌ Delete: {show_name}", callback_data=f"del_{show_name}")])
    buttons.append([InlineKeyboardButton(text="🔙 Menu", callback_data="btn_menu")])

    await message.answer("Your series:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "btn_list")
async def cb_list(callback: CallbackQuery, db):
    subs = await db.get_user_subscriptions(callback.from_user.id)
    if not subs:
        await callback.message.edit_text("Your list is empty.", reply_markup=get_main_keyboard())
        return

    buttons = []
    for show_name, show_id in subs:
        buttons.append([InlineKeyboardButton(text=f"❌ Delete: {show_name}", callback_data=f"del_{show_name}")])
    buttons.append([InlineKeyboardButton(text="🔙 Menu", callback_data="btn_menu")])

    await callback.message.edit_text("Your series:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("del_"))
async def cb_delete(callback: CallbackQuery, db):
    show_name = callback.data.split("del_")[1]
    await db.delete_subscription(callback.from_user.id, show_name)
    await callback.answer(f"{show_name} deleted!")
    await cb_list(callback, db)


@router.message(Command("calendar"))
async def cmd_calendar(message: Message, db):
    msg = await message.answer("⏳ Checking release dates...")
    subs = await db.get_user_subscriptions(message.from_user.id)

    if not subs:
        await msg.edit_text("List is empty.")
        return

    report = []
    for show_name, show_id in subs:
        next_ep = await TVMazeClient.get_next_episode(show_id)
        if next_ep:
            date = next_ep.get('airdate', '???')
            ep_name = next_ep.get('name', 'Episode')
            s_num = f"S{next_ep.get('season')}E{next_ep.get('number')}"
            report.append(f"📅 <b>{date}</b>: {show_name} ({s_num}) - {ep_name}\n")

    report.sort()
    result_text = "<b>🗓 Upcoming releases:</b>\n\n" + ("\n".join(report) if report else "No upcoming releases yet.")
    await msg.edit_text(result_text, parse_mode="HTML")


@router.callback_query(F.data == "btn_calendar")
async def cb_calendar(callback: CallbackQuery, db):
    await callback.answer("Updating calendar...")
    msg = await callback.message.answer("⏳ Checking release dates...")
    subs = await db.get_user_subscriptions(callback.from_user.id)
    if not subs:
        await msg.edit_text("List is empty.")
        return

    report = []
    for show_name, show_id in subs:
        next_ep = await TVMazeClient.get_next_episode(show_id)
        if next_ep:
            date = next_ep.get('airdate', '???')
            ep_name = next_ep.get('name', 'Episode')
            s_num = f"S{next_ep.get('season')}E{next_ep.get('number')}"
            report.append(f"📅 <b>{date}</b>: {show_name} ({s_num}) - {ep_name}\n")

    report.sort()
    result_text = "<b>🗓 Upcoming releases:</b>\n\n" + ("\n".join(report) if report else "No upcoming releases yet.")
    await msg.edit_text(result_text, parse_mode="HTML")


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