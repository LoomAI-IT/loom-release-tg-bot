from aiogram.fsm.state import StatesGroup, State


class SuccessfulReleasesStates(StatesGroup):
    view_releases = State()