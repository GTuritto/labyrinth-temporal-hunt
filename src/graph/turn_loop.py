from __future__ import annotations

import json
import logging
from typing import Dict, Any, Optional, TypedDict
from dataclasses import asdict

from langgraph.graph import StateGraph, END
from pydantic import ValidationError

from gsm.models import UserInput, GameStateResponse, MinotaurDecision, parse_user_input_json, parse_minotaur_decision_json
from gsm.engine import GameStateManager
from gsm.physics import Position
from gsm.temporal import TemporalState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TurnState(TypedDict):
    """Shared state for the turn-based game loop."""
    # Game state manager instance
    gsm: GameStateManager
    
    # Current turn information
    turn_number: int
    current_phase: str  # "user_turn", "user_apply", "minotaur_turn", "minotaur_apply"
    
    # Last inputs and responses
    last_user_input: Optional[UserInput]
    last_user_response: Optional[GameStateResponse]
    last_minotaur_decision: Optional[MinotaurDecision]
    last_minotaur_response: Optional[GameStateResponse]
    
    # Human input (if provided directly as string)
    human_input: Optional[str]
    
    # Game status tracking
    game_status: str  # "active", "DEATH", "ESCAPED"
    
    # Turn logs for debugging/analysis
    turn_logs: list[Dict[str, Any]]
    
    # Control flags
    single_turn_mode: bool


def user_turn_node(state: TurnState) -> TurnState:
    """
    Generate or parse user input for the current turn.
    Returns UserInput (parsed from human string if provided, or default LOOK).
    """
    logger.info(f"Turn {state['turn_number']}: Processing user turn")
    
    try:
        if state.get("human_input"):
            # Try to parse human input string as JSON first
            user_input = None
            try:
                # Check if input looks like JSON
                if state["human_input"].strip().startswith('{'):
                    user_input = parse_user_input_json(state["human_input"])
            except:
                pass
            
            # If JSON parsing failed or input doesn't look like JSON, use simple text parsing
            if user_input is None:
                text = state["human_input"].lower().strip()
                if "move" in text:
                    if "north" in text:
                        user_input = UserInput(command="MOVE", direction="NORTH", steps=5)
                    elif "east" in text:
                        user_input = UserInput(command="MOVE", direction="EAST", steps=3)
                    elif "south" in text:
                        user_input = UserInput(command="MOVE", direction="SOUTH", steps=3)
                    elif "west" in text:
                        user_input = UserInput(command="MOVE", direction="WEST", steps=3)
                    else:
                        user_input = UserInput(command="MOVE", direction="NORTH", steps=1)
                elif "look" in text:
                    user_input = UserInput(command="LOOK")
                elif "grab" in text:
                    if "stone" in text:
                        user_input = UserInput(command="GRAB", target="RED STONE")
                    else:
                        user_input = UserInput(command="GRAB")
                elif "halt" in text:
                    user_input = UserInput(command="HALT")
                else:
                    user_input = UserInput(command="LOOK")
            
            logger.info(f"Parsed human input: {user_input}")
        else:
            # Default to LOOK command if no human input
            user_input = UserInput(command="LOOK")
            logger.info("No human input provided, defaulting to LOOK")
        
        # Validate the user input
        if not isinstance(user_input, UserInput):
            logger.warning("Invalid user input, falling back to LOOK")
            user_input = UserInput(command="LOOK")
        
        state["last_user_input"] = user_input
        state["current_phase"] = "user_apply"
        
        return state
        
    except Exception as e:
        logger.error(f"Error in user_turn_node: {e}")
        # Fallback to safe default
        state["last_user_input"] = UserInput(command="LOOK")
        state["current_phase"] = "user_apply"
        return state


def gsm_apply_user_node(state: TurnState) -> TurnState:
    """
    Apply user input to the game state manager.
    Returns GameStateResponse with updated game state.
    """
    logger.info(f"Turn {state['turn_number']}: Applying user input to GSM")
    
    try:
        user_input = state["last_user_input"]
        if not user_input:
            logger.warning("No user input to apply, using default LOOK")
            user_input = UserInput(command="LOOK")
        
        # Apply user input to game state manager
        gsm = state["gsm"]
        response = gsm.apply_user_input(user_input)
        
        # Validate response
        if not isinstance(response, GameStateResponse):
            logger.error("Invalid GameStateResponse from GSM")
            raise ValueError("Invalid response from GameStateManager")
        
        state["last_user_response"] = response
        state["game_status"] = response.status
        state["current_phase"] = "minotaur_turn"
        
        # Log the turn
        turn_log = {
            "turn": state["turn_number"],
            "phase": "user_apply",
            "input": user_input.model_dump(),
            "response": {
                "status": response.status,
                "user_state": response.user_state,
                "environment": response.environment,
                "minotaur_cue": response.minotaur_cue,
                "raw_text_output": response.raw_text_output
            }
        }
        state["turn_logs"].append(turn_log)
        logger.info(f"User turn applied: {json.dumps(turn_log, indent=2)}")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in gsm_apply_user_node: {e}")
        # Create fallback response
        fallback_response = GameStateResponse(
            status="ERROR",
            user_state={"position": {"x": 0, "y": 0, "z": 0}, "stamina_pct": 0.0, "inventory": [], "lantern_cooldown": 0.0},
            environment={"visible_paths": [], "visible_items": [], "message": f"Error: {str(e)}", "steps_moved": 0, "time_taken": 0.0, "stop_reason": "ERROR"},
            minotaur_cue="System error occurred.",
            raw_text_output=f"Game error: {str(e)}"
        )
        state["last_user_response"] = fallback_response
        state["game_status"] = "ERROR"
        state["current_phase"] = "minotaur_turn"
        return state


def minotaur_turn_node(state: TurnState) -> TurnState:
    """
    Generate minotaur decision based on current context and last response.
    Returns MinotaurDecision (or default WAIT if generation fails).
    """
    logger.info(f"Turn {state['turn_number']}: Processing minotaur turn")
    
    try:
        last_response = state["last_user_response"]
        gsm = state["gsm"]
        
        # Simple minotaur AI logic based on game state
        if not last_response or last_response.status in ["DEATH", "ESCAPED", "ERROR"]:
            # Game over, minotaur waits
            decision = MinotaurDecision(action="WAIT")
        else:
            # Basic minotaur behavior: chase user or jump occasionally
            user_pos = last_response.user_state["position"]
            minotaur_pos = {
                "x": gsm.minotaur_position.x,
                "y": gsm.minotaur_position.y, 
                "z": gsm.minotaur_position.z
            }
            
            # Calculate distance to user
            dx = user_pos["x"] - minotaur_pos["x"]
            dy = user_pos["y"] - minotaur_pos["y"]
            distance = (dx*dx + dy*dy) ** 0.5
            
            if distance > 10.0 and gsm.temporal_state.jump_cooldown <= 0:
                # Far from user and can jump - trigger jump
                decision = MinotaurDecision(action="JUMP")
            elif distance > 5.0:
                # Move towards user
                target_x = minotaur_pos["x"] + (1 if dx > 0 else -1 if dx < 0 else 0)
                target_y = minotaur_pos["y"] + (1 if dy > 0 else -1 if dy < 0 else 0)
                decision = MinotaurDecision(
                    action="PATHFIND",
                    target_coords={"x": target_x, "y": target_y, "z": minotaur_pos["z"]}
                )
            else:
                # Close to user - chase directly
                decision = MinotaurDecision(
                    action="CHASE",
                    target_coords=user_pos
                )
        
        # Validate decision
        if not isinstance(decision, MinotaurDecision):
            logger.warning("Invalid minotaur decision, falling back to WAIT")
            decision = MinotaurDecision(action="WAIT")
        
        state["last_minotaur_decision"] = decision
        state["current_phase"] = "minotaur_apply"
        
        return state
        
    except Exception as e:
        logger.error(f"Error in minotaur_turn_node: {e}")
        # Fallback to safe default
        state["last_minotaur_decision"] = MinotaurDecision(action="WAIT")
        state["current_phase"] = "minotaur_apply"
        return state


def gsm_apply_minotaur_node(state: TurnState) -> TurnState:
    """
    Apply minotaur decision to the game state manager.
    Returns GameStateResponse with updated game state.
    """
    logger.info(f"Turn {state['turn_number']}: Applying minotaur decision to GSM")
    
    try:
        decision = state["last_minotaur_decision"]
        if not decision:
            logger.warning("No minotaur decision to apply, using default WAIT")
            decision = MinotaurDecision(action="WAIT")
        
        gsm = state["gsm"]
        
        # Apply minotaur decision based on action type
        if decision.action == "JUMP":
            # Trigger minotaur jump
            gsm.trigger_minotaur_jump()
            logger.info("Minotaur jump triggered")
        elif decision.action == "PATHFIND" and decision.target_coords:
            # Move minotaur towards target
            target = decision.target_coords
            gsm.minotaur_position = Position(target["x"], target["y"], target["z"])
            logger.info(f"Minotaur moved to {target}")
        elif decision.action == "CHASE" and decision.target_coords:
            # Move minotaur to exact target position
            target = decision.target_coords
            gsm.minotaur_position = Position(target["x"], target["y"], target["z"])
            logger.info(f"Minotaur chased to {target}")
        else:
            # WAIT or invalid action - do nothing
            logger.info("Minotaur waits")
        
        # Generate a LOOK response to get updated game state
        look_input = UserInput(command="LOOK")
        response = gsm.apply_user_input(look_input)
        
        # Validate response
        if not isinstance(response, GameStateResponse):
            logger.error("Invalid GameStateResponse from minotaur GSM apply")
            raise ValueError("Invalid response from GameStateManager")
        
        state["last_minotaur_response"] = response
        state["game_status"] = response.status
        state["current_phase"] = "user_turn"
        state["turn_number"] += 1
        
        # Log the minotaur turn
        turn_log = {
            "turn": state["turn_number"] - 1,
            "phase": "minotaur_apply", 
            "decision": decision.model_dump(),
            "response": {
                "status": response.status,
                "user_state": response.user_state,
                "environment": response.environment,
                "minotaur_cue": response.minotaur_cue,
                "raw_text_output": response.raw_text_output
            }
        }
        state["turn_logs"].append(turn_log)
        logger.info(f"Minotaur turn applied: {json.dumps(turn_log, indent=2)}")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in gsm_apply_minotaur_node: {e}")
        # Create fallback response
        fallback_response = GameStateResponse(
            status="ERROR",
            user_state={"position": {"x": 0, "y": 0, "z": 0}, "stamina_pct": 0.0, "inventory": [], "lantern_cooldown": 0.0},
            environment={"visible_paths": [], "visible_items": [], "message": f"Minotaur error: {str(e)}", "steps_moved": 0, "time_taken": 0.0, "stop_reason": "ERROR"},
            minotaur_cue="Minotaur system error occurred.",
            raw_text_output=f"Minotaur error: {str(e)}"
        )
        state["last_minotaur_response"] = fallback_response
        state["game_status"] = "ERROR"
        state["current_phase"] = "user_turn"
        state["turn_number"] += 1
        return state


def should_continue(state: TurnState) -> str:
    """Determine if the game should continue or end."""
    if state["game_status"] in ["DEATH", "ESCAPED", "ERROR"]:
        return END
    # Check if this is a single turn run (marked by special flag)
    if state.get("single_turn_mode", False) and state["turn_number"] > 1:
        return END
    return "user_turn_node"


def build_turn_loop_graph() -> StateGraph:
    """Build and return the complete turn loop graph."""
    
    # Create the graph
    graph = StateGraph(TurnState)
    
    # Add nodes
    graph.add_node("user_turn_node", user_turn_node)
    graph.add_node("gsm_apply_user_node", gsm_apply_user_node)
    graph.add_node("minotaur_turn_node", minotaur_turn_node)
    graph.add_node("gsm_apply_minotaur_node", gsm_apply_minotaur_node)
    
    # Add edges
    graph.add_edge("user_turn_node", "gsm_apply_user_node")
    graph.add_edge("gsm_apply_user_node", "minotaur_turn_node")
    graph.add_edge("minotaur_turn_node", "gsm_apply_minotaur_node")
    
    # Add conditional edge for game continuation
    graph.add_conditional_edges(
        "gsm_apply_minotaur_node",
        should_continue,
        {
            "user_turn_node": "user_turn_node",
            END: END
        }
    )
    
    # Set entry point
    graph.set_entry_point("user_turn_node")
    
    return graph


def create_initial_state(human_input: Optional[str] = None, single_turn_mode: bool = False) -> TurnState:
    """Create initial state for the turn loop."""
    return TurnState(
        gsm=GameStateManager(),
        turn_number=1,
        current_phase="user_turn",
        last_user_input=None,
        last_user_response=None,
        last_minotaur_decision=None,
        last_minotaur_response=None,
        human_input=human_input,
        game_status="active",
        turn_logs=[],
        single_turn_mode=single_turn_mode
    )


def run_single_turn(human_input: Optional[str] = None) -> TurnState:
    """Run a single complete turn (user + minotaur) and return final state."""
    graph = build_turn_loop_graph()
    compiled_graph = graph.compile()
    
    initial_state = create_initial_state(human_input, single_turn_mode=True)
    
    # Run one complete cycle with recursion limit
    config = {"recursion_limit": 10}
    final_state = compiled_graph.invoke(initial_state, config=config)
    
    return final_state


def run_game_loop(max_turns: int = 100, human_inputs: Optional[list[str]] = None) -> TurnState:
    """Run the complete game loop for multiple turns."""
    # Create initial state
    state = create_initial_state()
    
    # Run individual turns manually
    for turn in range(max_turns):
        if state["game_status"] in ["DEATH", "ESCAPED", "ERROR"]:
            logger.info(f"Game ended with status: {state['game_status']}")
            break
        
        # Set human input for this turn if provided
        if human_inputs and turn < len(human_inputs):
            state["human_input"] = human_inputs[turn]
        else:
            state["human_input"] = None
        
        # Run one complete turn cycle manually
        try:
            # User turn
            state = user_turn_node(state)
            state = gsm_apply_user_node(state)
            
            # Check for game over after user turn
            if state["game_status"] in ["DEATH", "ESCAPED", "ERROR"]:
                break
            
            # Minotaur turn
            state = minotaur_turn_node(state)
            state = gsm_apply_minotaur_node(state)
            
        except Exception as e:
            logger.error(f"Error in game loop turn {turn}: {e}")
            state["game_status"] = "ERROR"
            break
    
    logger.info(f"Game completed after {state['turn_number']} turns with status: {state['game_status']}")
    return state


# Legacy function for backward compatibility
def build_turn_loop():
    """Legacy function - use build_turn_loop_graph() instead."""
    return build_turn_loop_graph().compile()
