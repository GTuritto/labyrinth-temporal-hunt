from gsm.models import LabyrinthState, Room, Hunter, Minotaur
from gsm.engine import simulate_step


def test_engine_runs():
    state = LabyrinthState(
        rooms=[
            Room(id="A", connections=["B"]),
            Room(id="B", connections=["A"]),
        ],
        hunter=Hunter(id="h1"),
        minotaur=Minotaur(id="m1"),
        seed=123,
    )
    new_state = simulate_step(state, "A")
    assert isinstance(new_state, LabyrinthState)
    assert new_state.tick == 1
