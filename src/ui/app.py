from __future__ import annotations

import asyncio
import os
import random
from typing import Optional

import streamlit as st
from loguru import logger

# Optional performance on Unix
try:  # pragma: no cover
    import uvloop  # type: ignore

    if "PYCHARM_HOSTED" not in os.environ:
        uvloop.install()
except Exception:
    pass

from infra.settings import Settings
from gsm.models import LabyrinthState, Room, Hunter, Minotaur
from gsm.engine import simulate_step
from agents.memory_manager import MemoryManager
from agents.mistral_user import MistralUserAgent
from agents.gemini_minotaur import GeminiMinotaurAgent


def init_state(seed: int) -> LabyrinthState:
    rng = random.Random(seed)
    rooms = []
    # Create a small ring of rooms
    for i in range(6):
        rid = f"R{i}"
        connections = [f"R{(i-1)%6}", f"R{(i+1)%6}"]
        rooms.append(
            Room(
                id=rid,
                connections=connections,
                has_trap=(rng.random() < 0.25),
                has_artifact=(rng.random() < 0.2),
            )
        )
    state = LabyrinthState(
        tick=0,
        rooms=rooms,
        hunter=Hunter(id="hunter-1"),
        minotaur=Minotaur(id="minotaur-1"),
        seed=seed,
    )
    return state


def main() -> None:
    st.set_page_config(page_title="Labyrinth Temporal Hunt", page_icon="🧭", layout="wide")
    settings = Settings()
    st.sidebar.header("Settings")
    st.sidebar.write(f"APP_MODE: {settings.APP_MODE}")
    st.sidebar.write(f"LOG_LEVEL: {settings.LOG_LEVEL}")
    st.sidebar.write(f"RANDOM_SEED: {settings.RANDOM_SEED}")

    if "state" not in st.session_state:
        st.session_state["state"] = init_state(settings.RANDOM_SEED)
        st.session_state["hunter_room"] = "R0"
        st.session_state["memory"] = MemoryManager(max_items=200)

    memory: MemoryManager = st.session_state["memory"]
    state: LabyrinthState = st.session_state["state"]
    hunter_room: str = st.session_state["hunter_room"]

    st.title("Labyrinth Temporal Hunt")
    st.caption("A scaffolded app with agents, temporal engine, and LangGraph stubs.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("World")
        st.write(f"Tick: {state.tick}")
        st.write(f"Hunter stamina: {state.hunter.stamina if state.hunter else 'n/a'}")
        st.write(f"Current room: {hunter_room}")

        if st.button("Simulate Step"):
            state = simulate_step(state, hunter_room)
            # Update hunter position provisionally to next connected room
            room_map = {r.id: r for r in state.rooms}
            next_rooms = room_map[hunter_room].connections if hunter_room in room_map else []
            if next_rooms:
                st.session_state["hunter_room"] = next_rooms[0]
            st.session_state["state"] = state
            st.success("Step simulated.")

    with col2:
        st.subheader("Agents")
        user_prompt = st.text_area("Hunter prompt", value="Observe surroundings and plan next move.", height=100)
        mino_prompt = st.text_area("Minotaur prompt", value="Stalk the hunter silently.", height=100)

        mistral_agent = MistralUserAgent(settings=settings)
        gemini_agent = GeminiMinotaurAgent(settings=settings)

        colA, colB = st.columns(2)
        with colA:
            if st.button("Ask Mistral (Hunter)"):
                messages = [
                    {"role": "system", "content": "You are a tactical hunter."},
                    {"role": "user", "content": user_prompt},
                ]
                out = mistral_agent.complete(messages) or "(No response; missing API key or error.)"
                memory.add("hunter", out)
                st.write(out)

        with colB:
            if st.button("Ask Gemini (Minotaur)"):
                messages = [
                    {"role": "system", "content": "You are the cunning Minotaur."},
                    {"role": "user", "content": mino_prompt},
                ]
                out = gemini_agent.complete(messages) or "(No response; missing API key or error.)"
                memory.add("minotaur", out)
                st.write(out)

    st.divider()
    st.subheader("Conversation Memory (recent)")
    for role, content in memory.get_history()[-10:]:
        st.markdown(f"**{role}:** {content}")


if __name__ == "__main__":
    # Streamlit will invoke main(), but keep this for direct Python execution.
    main()
