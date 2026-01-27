import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from api import TVMazeClient
from config import ADMIN_ID
from states import AddShow  # Импортируем состояния

router = Router()


# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить сериал", callback_data="btn_add")],
        [InlineKeyboardButton(text="📋 Мои подписки", callback_data="btn_list"),
         InlineKeyboardButton(text="📅 Календарь", callback_data="btn_calendar")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="btn_help")]
    ])


# --- БАЗОВЫЕ КОМАНДЫ ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я слежу за выходом новых серий.\nВыбери действие:",
        reply_markup=get_main_keyboard()
    )


# --- АДМИН ПАНЕЛЬ ---
@router.message(Command("admin"))
async def cmd_admin(message: Message, db):
    if message.from_user.id != ADMIN_ID:
        return  # Игнорируем чужих

    users_count, subs_count = db.get_stats()
    await message.answer(
        f"👑 <b>Панель Администратора</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"📺 Активных подписок: {subs_count}",
        parse_mode="HTML"
    )


# --- FSM: ДОБАВЛЕНИЕ СЕРИАЛА ЧЕРЕЗ КНОПКУ ---
@router.callback_query(F.data == "btn_add")
async def cb_add_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Напиши название сериала или отправь ссылку на TVMaze:")
    await state.set_state(AddShow.waiting_for_title)
    await callback.answer()


@router.message(AddShow.waiting_for_title)
async def process_add_show(message: Message, state: FSMContext, db):
    query = message.text
    msg = await message.answer(f"🔍 Ищу «{query}»...")

    sid, name, url = await TVMazeClient.search_show(query)

    if sid:
        if db.add_subscription(message.from_user.id, sid, name):
            await msg.edit_text(
                f"✅ Подписался на <b><a href='{url}'>{name}</a></b>!",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
        else:
            await msg.edit_text(f"ℹ️ Ты уже подписан на {name}.", reply_markup=get_main_keyboard())
    else:
        await msg.edit_text("❌ Ничего не найдено. Попробуй другое название.", reply_markup=get_main_keyboard())

    await state.clear()


# --- СПИСОК (С удалением) ---
@router.callback_query(F.data == "btn_list")
async def cb_list(callback: CallbackQuery, db):
    subs = db.get_user_subscriptions(callback.from_user.id)
    if not subs:
        await callback.message.edit_text("У тебя пока нет подписок.", reply_markup=get_main_keyboard())
        return

    buttons = []
    for show_name, show_id in subs:
        buttons.append([InlineKeyboardButton(text=f"❌ Удалить: {show_name}", callback_data=f"del_{show_name}")])
    buttons.append([InlineKeyboardButton(text="🔙 В меню", callback_data="btn_menu")])

    await callback.message.edit_text("Твои сериалы (нажми, чтобы удалить):",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("del_"))
async def cb_delete(callback: CallbackQuery, db):
    show_name = callback.data.split("del_")[1]
    db.delete_subscription(callback.from_user.id, show_name)
    await callback.answer(f"{show_name} удален!")
    # Обновляем список
    await cb_list(callback, db)


# --- КАЛЕНДАРЬ РЕЛИЗОВ ---
@router.callback_query(F.data == "btn_calendar")
async def cb_calendar(callback: CallbackQuery, db):
    await callback.answer("Загружаю календарь...")
    msg = await callback.message.answer("⏳ Проверяю даты выхода...")

    subs = db.get_user_subscriptions(callback.from_user.id)
    if not subs:
        await msg.edit_text("Список пуст.")
        return

    report = []
    # Асинхронно собираем даты (это может занять время, если подписок много)
    for show_name, show_id in subs:
        next_ep = await TVMazeClient.get_next_episode(show_id)
        if next_ep:
            date = next_ep.get('airdate', '???')
            ep_name = next_ep.get('name', 'Episode')
            s_num = f"S{next_ep.get('season')}E{next_ep.get('number')}"
            report.append(f"📅 <b>{date}</b>: {show_name} ({s_num})")

    report.sort()  # Сортируем по дате

    result_text = "<b>🗓 Ближайшие премьеры:</b>\n\n" + (
        "\n".join(report) if report else "Пока нет информации о новых сериях.")

    await msg.edit_text(result_text, parse_mode="HTML")



# --- КНОПКИ НАВИГАЦИИ ---
@router.callback_query(F.data == "btn_menu")
async def cb_menu(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=get_main_keyboard())


@router.callback_query(F.data == "btn_help")
async def cb_help(callback: CallbackQuery):
    text = (
        "🤖 <b>Как пользоваться ботом:</b>\n\n"
        "1. Жми <b>Добавить сериал</b>\n"
        "2. Пиши название (например 'Ведьмак')\n"
        "3. Бот сам будет присылать уведомления, когда выйдет новая серия!\n\n"
        "В разделе <b>Календарь</b> можно посмотреть ближайшие даты."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_keyboard())