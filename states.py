from aiogram.fsm.state import State, StatesGroup

class AddShow(StatesGroup):
    waiting_for_title = State()