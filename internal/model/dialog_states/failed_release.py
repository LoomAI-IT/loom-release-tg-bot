from aiogram.fsm.state import StatesGroup, State


class FailedReleasesStates(StatesGroup):
    view_releases = State()