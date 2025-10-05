from __future__ import annotations

import json
import os
from typing import Optional, Dict, Any

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
from gsm.models import UserInput, GameStateResponse
from gsm.engine import GameStateManager
from graph.turn_loop import run_single_turn, create_initial_state, user_turn_node, gsm_apply_user_node
from agents.memory_manager import MemoryManager
from agents.mistral_user import MistralUserAgent
from agents.gemini_minotaur import GeminiMinotaurAgent


def init_game_state() -> Dict[str, Any]:
    """Initialize the game state with GameStateManager."""
    return {
        "gsm": GameStateManager(),
        "turn_number": 1,
        "game_status": "active",
        "turn_history": [],
        "memory": MemoryManager(max_items=200)
    }


def format_position(pos: Dict[str, Any]) -> str:
    """Format position for display."""
    return f"({pos['x']}, {pos['y']}, {pos['z']})"


def format_minotaur_status(cue: str) -> str:
    """Extract and format minotaur status from cue."""
    if "vanished" in cue.lower():
        return "🌫️ VANISHED"
    elif "paralyzed" in cue.lower():
        return "⚡ PARALYZED"
    elif "breathing" in cue.lower():
        return "😤 VERY CLOSE"
    elif "footsteps" in cue.lower():
        return "👣 CLOSE"
    elif "distant" in cue.lower():
        return "🔊 DISTANT"
    else:
        return "🔇 QUIET"


def main() -> None:
    st.set_page_config(
        page_title="Labyrinth Temporal Hunt", 
        page_icon="🏛️", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    settings = Settings()
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Game Settings")
    st.sidebar.write(f"**Mode:** {settings.APP_MODE}")
    st.sidebar.write(f"**Log Level:** {settings.LOG_LEVEL}")
    st.sidebar.write(f"**Seed:** {settings.RANDOM_SEED}")
    
    # Initialize game state
    if "game_state" not in st.session_state:
        st.session_state["game_state"] = init_game_state()
    
    game_state = st.session_state["game_state"]
    gsm: GameStateManager = game_state["gsm"]
    memory: MemoryManager = game_state["memory"]
    
    # Main title
    st.title("🏛️ Labyrinth Temporal Hunt")
    st.caption("🎮 Interactive turn-based game with LangGraph AI agents and temporal mechanics")
    
    # Game status bar
    col_status1, col_status2, col_status3, col_status4 = st.columns(4)
    
    with col_status1:
        st.metric("🎯 Turn", game_state["turn_number"])
    
    with col_status2:
        status_color = "🟢" if game_state["game_status"] == "active" else "🔴"
        st.metric("📊 Status", f"{status_color} {game_state['game_status'].upper()}")
    
    with col_status3:
        user_pos = gsm.user_position
        st.metric("📍 Position", format_position({"x": user_pos.x, "y": user_pos.y, "z": user_pos.z}))
    
    with col_status4:
        st.metric("⚡ Stamina", f"{gsm.user_stamina * 100:.0f}%")
    
    st.divider()
    
    # Main game interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎮 Game Controls")
        
        # Command input section
        st.write("**Enter your command:**")
        
        # Quick action buttons
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        
        with col_btn1:
            if st.button("👁️ LOOK", use_container_width=True):
                st.session_state["command_input"] = "look"
        
        with col_btn2:
            if st.button("⬆️ NORTH", use_container_width=True):
                st.session_state["command_input"] = "move north 3"
        
        with col_btn3:
            if st.button("⬇️ SOUTH", use_container_width=True):
                st.session_state["command_input"] = "move south 3"
        
        with col_btn4:
            if st.button("🛑 HALT", use_container_width=True):
                st.session_state["command_input"] = "halt"
        
        col_btn5, col_btn6, col_btn7, col_btn8 = st.columns(4)
        
        with col_btn5:
            if st.button("⬅️ WEST", use_container_width=True):
                st.session_state["command_input"] = "move west 3"
        
        with col_btn6:
            if st.button("➡️ EAST", use_container_width=True):
                st.session_state["command_input"] = "move east 3"
        
        with col_btn7:
            if st.button("🔴 GRAB RED", use_container_width=True):
                st.session_state["command_input"] = "grab red stone"
        
        with col_btn8:
            if st.button("🏮 USE LANTERN", use_container_width=True):
                st.session_state["command_input"] = "use lantern"
        
        # Text input for custom commands
        command_input = st.text_input(
            "Or type a custom command:",
            value=st.session_state.get("command_input", ""),
            placeholder="e.g., 'move north 5', 'grab blue stone', 'use lantern'",
            key="text_command"
        )
        
        # Execute turn button
        if st.button("🚀 **Execute Turn**", type="primary", use_container_width=True):
            if command_input.strip():
                try:
                    # Execute the turn using our LangGraph system
                    with st.spinner("🎲 Processing turn..."):
                        result = run_single_turn(command_input.strip())
                    
                    # Update game state
                    game_state["gsm"] = result["gsm"]
                    game_state["turn_number"] = result["turn_number"]
                    game_state["game_status"] = result["game_status"]
                    game_state["turn_history"].extend(result["turn_logs"])
                    
                    # Add to memory
                    memory.add("user", command_input.strip())
                    if result["last_user_response"]:
                        memory.add("system", result["last_user_response"].raw_text_output)
                    
                    st.success("✅ Turn executed successfully!")
                    st.session_state["command_input"] = ""
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error executing turn: {str(e)}")
            else:
                st.warning("⚠️ Please enter a command first!")
    
    with col2:
        st.subheader("🎯 Game State")
        
        # Current game information
        if hasattr(gsm, 'last_response') and gsm.last_response:
            response = gsm.last_response
        else:
            # Get current state by executing a LOOK command
            temp_state = create_initial_state()
            temp_state["gsm"] = gsm
            temp_state = user_turn_node(temp_state)
            temp_state = gsm_apply_user_node(temp_state)
            response = temp_state["last_user_response"]
        
        if response:
            # Environment info
            st.write("**🌍 Environment:**")
            st.write(f"• **Paths:** {', '.join(response.environment['visible_paths'])}")
            st.write(f"• **Items:** {', '.join(response.environment['visible_items']) if response.environment['visible_items'] else 'None'}")
            
            # Inventory
            st.write("**🎒 Inventory:**")
            inventory = response.user_state['inventory']
            if inventory:
                for item in inventory:
                    st.write(f"• {item}")
            else:
                st.write("• *Empty*")
            
            # Minotaur status
            st.write("**👹 Minotaur:**")
            minotaur_status = format_minotaur_status(response.minotaur_cue)
            st.write(f"• **Status:** {minotaur_status}")
            
            # Lantern cooldown
            lantern_cd = response.user_state.get('lantern_cooldown', 0)
            if lantern_cd > 0:
                st.write(f"• **Lantern:** {lantern_cd:.1f}s cooldown")
            else:
                st.write("• **Lantern:** Ready")
            
            # Last message
            st.write("**📝 Last Message:**")
            st.info(response.environment['message'])
            
            # Minotaur cue
            st.write("**🔊 Audio Cue:**")
            st.write(response.minotaur_cue)
    
    st.divider()
    
    # AI Agents section
    st.subheader("🤖 AI Agents")
    
    col_ai1, col_ai2 = st.columns(2)
    
    with col_ai1:
        st.write("**🎯 Hunter Agent (Mistral)**")
        hunter_prompt = st.text_area(
            "Hunter strategy:",
            value="Analyze the current situation and suggest the best next move to find stones and avoid the Minotaur.",
            height=100,
            key="hunter_prompt"
        )
        
        if st.button("🧠 Ask Hunter AI", use_container_width=True):
            try:
                mistral_agent = MistralUserAgent(settings=settings)
                current_state = json.dumps({
                    "position": format_position({"x": gsm.user_position.x, "y": gsm.user_position.y, "z": gsm.user_position.z}),
                    "stamina": f"{gsm.user_stamina * 100:.0f}%",
                    "inventory": response.user_state['inventory'] if response else [],
                    "environment": response.environment if response else {},
                    "minotaur_cue": response.minotaur_cue if response else ""
                }, indent=2)
                
                messages = [
                    {"role": "system", "content": "You are a tactical hunter in a labyrinth. Analyze the game state and provide strategic advice."},
                    {"role": "user", "content": f"Current state:\n{current_state}\n\nStrategy request: {hunter_prompt}"},
                ]
                
                with st.spinner("🤔 Hunter AI thinking..."):
                    ai_response = mistral_agent.complete(messages) or "No response from AI agent."
                
                memory.add("hunter_ai", ai_response)
                st.success("🎯 Hunter AI Response:")
                st.write(ai_response)
                
            except Exception as e:
                st.error(f"❌ Hunter AI error: {str(e)}")
    
    with col_ai2:
        st.write("**👹 Minotaur Agent (Gemini)**")
        minotaur_prompt = st.text_area(
            "Minotaur behavior:",
            value="Describe the Minotaur's current hunting strategy and psychological state.",
            height=100,
            key="minotaur_prompt"
        )
        
        if st.button("🧠 Ask Minotaur AI", use_container_width=True):
            try:
                gemini_agent = GeminiMinotaurAgent(settings=settings)
                minotaur_pos = gsm.minotaur_position
                current_state = json.dumps({
                    "minotaur_position": format_position({"x": minotaur_pos.x, "y": minotaur_pos.y, "z": minotaur_pos.z}),
                    "user_position": format_position({"x": gsm.user_position.x, "y": gsm.user_position.y, "z": gsm.user_position.z}),
                    "minotaur_status": gsm.temporal_state.minotaur_status.value,
                    "turn": game_state["turn_number"]
                }, indent=2)
                
                messages = [
                    {"role": "system", "content": "You are the cunning Minotaur hunting in your labyrinth. Describe your thoughts and strategy."},
                    {"role": "user", "content": f"Current state:\n{current_state}\n\nBehavior analysis: {minotaur_prompt}"},
                ]
                
                with st.spinner("😈 Minotaur AI thinking..."):
                    ai_response = gemini_agent.complete(messages) or "No response from AI agent."
                
                memory.add("minotaur_ai", ai_response)
                st.success("👹 Minotaur AI Response:")
                st.write(ai_response)
                
            except Exception as e:
                st.error(f"❌ Minotaur AI error: {str(e)}")
    
    # Game history and memory
    st.divider()
    
    col_hist1, col_hist2 = st.columns(2)
    
    with col_hist1:
        st.subheader("📜 Turn History")
        if game_state["turn_history"]:
            # Show last 5 turns
            recent_history = game_state["turn_history"][-10:]
            for log in reversed(recent_history):
                with st.expander(f"Turn {log['turn']} - {log['phase'].replace('_', ' ').title()}"):
                    st.json(log)
        else:
            st.write("*No turns executed yet*")
    
    with col_hist2:
        st.subheader("🧠 AI Memory")
        history = memory.get_history()
        if history:
            for role, content in reversed(history[-8:]):
                role_icon = {"user": "🎮", "system": "🎯", "hunter_ai": "🏹", "minotaur_ai": "👹"}.get(role, "💬")
                st.write(f"**{role_icon} {role.replace('_', ' ').title()}:** {content[:200]}{'...' if len(content) > 200 else ''}")
        else:
            st.write("*No AI interactions yet*")
    
    # Reset game button
    st.divider()
    if st.button("🔄 **Reset Game**", type="secondary"):
        st.session_state["game_state"] = init_game_state()
        st.success("🎮 Game reset successfully!")
        st.rerun()


if __name__ == "__main__":
    # Streamlit will invoke main(), but keep this for direct Python execution.
    main()
