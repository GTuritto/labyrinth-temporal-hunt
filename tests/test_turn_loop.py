import pytest
import json
from unittest.mock import patch

from gsm.models import UserInput, GameStateResponse, MinotaurDecision
from gsm.engine import GameStateManager
from gsm.physics import Position
from gsm.temporal import MinotaurStatus
from graph.turn_loop import (
    TurnState, user_turn_node, gsm_apply_user_node, minotaur_turn_node, 
    gsm_apply_minotaur_node, build_turn_loop_graph, create_initial_state,
    run_single_turn, run_game_loop, should_continue
)


class TestTurnLoopNodes:
    def test_user_turn_node_with_human_input(self):
        """Test user_turn_node with human input string."""
        state = create_initial_state(human_input="move north 5")
        
        result = user_turn_node(state)
        
        assert result["last_user_input"] is not None
        assert result["last_user_input"].command == "MOVE"
        assert result["current_phase"] == "user_apply"

    def test_user_turn_node_without_input(self):
        """Test user_turn_node defaults to LOOK when no input."""
        state = create_initial_state()
        
        result = user_turn_node(state)
        
        assert result["last_user_input"].command == "LOOK"
        assert result["current_phase"] == "user_apply"

    def test_user_turn_node_error_fallback(self):
        """Test user_turn_node falls back to LOOK on error."""
        state = create_initial_state()
        state["human_input"] = "invalid malformed input that should fail parsing"
        
        result = user_turn_node(state)
        
        # Should fallback to LOOK on parsing error
        assert result["last_user_input"].command == "LOOK"
        assert result["current_phase"] == "user_apply"

    def test_gsm_apply_user_node_success(self):
        """Test gsm_apply_user_node applies input successfully."""
        state = create_initial_state()
        state["last_user_input"] = UserInput(command="LOOK")
        
        result = gsm_apply_user_node(state)
        
        assert result["last_user_response"] is not None
        assert isinstance(result["last_user_response"], GameStateResponse)
        assert result["current_phase"] == "minotaur_turn"
        assert len(result["turn_logs"]) == 1
        assert result["turn_logs"][0]["phase"] == "user_apply"

    def test_gsm_apply_user_node_no_input_fallback(self):
        """Test gsm_apply_user_node handles missing input."""
        state = create_initial_state()
        state["last_user_input"] = None
        
        result = gsm_apply_user_node(state)
        
        assert result["last_user_response"] is not None
        assert result["current_phase"] == "minotaur_turn"

    def test_minotaur_turn_node_chase_logic(self):
        """Test minotaur_turn_node generates appropriate decisions."""
        state = create_initial_state()
        
        # Create a mock response with user position
        mock_response = GameStateResponse(
            status="active",
            user_state={"position": {"x": 30, "y": 30, "z": 0}, "stamina_pct": 100.0, "inventory": [], "lantern_cooldown": 0.0},
            environment={"visible_paths": [], "visible_items": [], "message": "", "steps_moved": 0, "time_taken": 0.0, "stop_reason": "SUCCESS"},
            minotaur_cue="Test",
            raw_text_output="Test"
        )
        state["last_user_response"] = mock_response
        
        result = minotaur_turn_node(state)
        
        assert result["last_minotaur_decision"] is not None
        assert isinstance(result["last_minotaur_decision"], MinotaurDecision)
        assert result["current_phase"] == "minotaur_apply"

    def test_minotaur_turn_node_game_over(self):
        """Test minotaur_turn_node waits when game is over."""
        state = create_initial_state()
        
        # Create a death response
        mock_response = GameStateResponse(
            status="DEATH",
            user_state={"position": {"x": 25, "y": 25, "z": 0}, "stamina_pct": 0.0, "inventory": [], "lantern_cooldown": 0.0},
            environment={"visible_paths": [], "visible_items": [], "message": "Game Over", "steps_moved": 0, "time_taken": 0.0, "stop_reason": "SUCCESS"},
            minotaur_cue="Game Over",
            raw_text_output="Game Over"
        )
        state["last_user_response"] = mock_response
        
        result = minotaur_turn_node(state)
        
        assert result["last_minotaur_decision"].action == "WAIT"

    def test_gsm_apply_minotaur_node_jump(self):
        """Test gsm_apply_minotaur_node handles JUMP action."""
        state = create_initial_state()
        state["last_minotaur_decision"] = MinotaurDecision(action="JUMP")
        
        result = gsm_apply_minotaur_node(state)
        
        assert result["last_minotaur_response"] is not None
        assert result["current_phase"] == "user_turn"
        assert result["turn_number"] == 2
        assert len(result["turn_logs"]) == 1
        assert result["turn_logs"][0]["phase"] == "minotaur_apply"

    def test_gsm_apply_minotaur_node_pathfind(self):
        """Test gsm_apply_minotaur_node handles PATHFIND action."""
        state = create_initial_state()
        state["last_minotaur_decision"] = MinotaurDecision(
            action="PATHFIND",
            target_coords={"x": 20, "y": 20, "z": 0}
        )
        
        result = gsm_apply_minotaur_node(state)
        
        assert result["last_minotaur_response"] is not None
        assert result["gsm"].minotaur_position.x == 20
        assert result["gsm"].minotaur_position.y == 20

    def test_gsm_apply_minotaur_node_wait(self):
        """Test gsm_apply_minotaur_node handles WAIT action."""
        state = create_initial_state()
        original_pos = state["gsm"].minotaur_position
        state["last_minotaur_decision"] = MinotaurDecision(action="WAIT")
        
        result = gsm_apply_minotaur_node(state)
        
        assert result["last_minotaur_response"] is not None
        # Position should not change for WAIT
        assert result["gsm"].minotaur_position.x == original_pos.x
        assert result["gsm"].minotaur_position.y == original_pos.y


class TestTurnLoopGraph:
    def test_build_turn_loop_graph(self):
        """Test that the graph builds correctly with all nodes and edges."""
        graph = build_turn_loop_graph()
        
        # Check that all nodes are present
        assert "user_turn_node" in graph.nodes
        assert "gsm_apply_user_node" in graph.nodes
        assert "minotaur_turn_node" in graph.nodes
        assert "gsm_apply_minotaur_node" in graph.nodes

    def test_should_continue_active_game(self):
        """Test should_continue returns correct node for active game."""
        state = create_initial_state()
        state["game_status"] = "active"
        
        result = should_continue(state)
        
        assert result == "user_turn_node"

    def test_should_continue_game_over(self):
        """Test should_continue returns END for game over states."""
        from langgraph.graph import END
        state = create_initial_state()
        
        for status in ["DEATH", "ESCAPED", "ERROR"]:
            state["game_status"] = status
            result = should_continue(state)
            assert result == END

    def test_create_initial_state(self):
        """Test initial state creation."""
        state = create_initial_state("test input")
        
        assert state["turn_number"] == 1
        assert state["current_phase"] == "user_turn"
        assert state["human_input"] == "test input"
        assert state["game_status"] == "active"
        assert isinstance(state["gsm"], GameStateManager)
        assert state["turn_logs"] == []


class TestFullTurnExecution:
    def test_run_single_turn_deterministic(self):
        """Test that one full cycle executes all four nodes deterministically."""
        result = run_single_turn("look")
        
        # Should have completed one full turn
        assert result["turn_number"] == 2  # Started at 1, incremented after minotaur turn
        assert result["current_phase"] == "user_turn"
        
        # Should have both user and minotaur responses
        assert result["last_user_response"] is not None
        assert result["last_minotaur_response"] is not None
        
        # Should have logged both phases
        assert len(result["turn_logs"]) == 2
        phases = [log["phase"] for log in result["turn_logs"]]
        assert "user_apply" in phases
        assert "minotaur_apply" in phases

    def test_run_single_turn_no_input(self):
        """Test single turn with no human input defaults to LOOK."""
        result = run_single_turn()
        
        assert result["last_user_input"].command == "LOOK"
        assert result["last_user_response"] is not None

    def test_graph_state_updated_consistently(self):
        """Test that graph state is updated consistently across turns."""
        result = run_single_turn("move east 3")
        
        # User should have moved
        user_pos = result["last_user_response"].user_state["position"]
        assert user_pos["x"] > 25  # Started at 25, moved east
        
        # Game state manager should reflect the same position
        gsm_pos = result["gsm"].user_position
        assert gsm_pos.x == user_pos["x"]
        assert gsm_pos.y == user_pos["y"]
        assert gsm_pos.z == user_pos["z"]

    def test_turn_logs_json_serializable(self):
        """Test that turn logs are JSON serializable."""
        result = run_single_turn("look")
        
        # Should be able to serialize all logs to JSON
        for log in result["turn_logs"]:
            json_str = json.dumps(log)
            assert json_str is not None
            # Should be able to deserialize back
            parsed = json.loads(json_str)
            assert parsed["turn"] == log["turn"]
            assert parsed["phase"] == log["phase"]

    def test_run_game_loop_multiple_turns(self):
        """Test running multiple turns in sequence."""
        inputs = ["look", "move north 2", "grab red stone", "halt"]
        result = run_game_loop(max_turns=4, human_inputs=inputs)
        
        # Should have processed multiple turns (at least 4)
        assert result["turn_number"] >= 4
        assert len(result["turn_logs"]) >= 4  # At least 4 logs (some turns may have 2)

    def test_run_game_loop_death_condition(self):
        """Test game loop stops on death condition."""
        state = create_initial_state()
        
        # Set up death condition - minotaur at same position as user
        state["gsm"].minotaur_position = Position(
            state["gsm"].user_position.x,
            state["gsm"].user_position.y, 
            state["gsm"].user_position.z
        )
        state["gsm"].temporal_state.minotaur_status = MinotaurStatus.CHASING_3D
        
        graph = build_turn_loop_graph()
        compiled_graph = graph.compile()
        
        result = compiled_graph.invoke(state)
        
        # Game should end with death
        assert result["game_status"] == "DEATH"

    def test_error_handling_and_fallbacks(self):
        """Test that errors are handled gracefully with fallbacks."""
        # Test with invalid state
        state = create_initial_state()
        state["gsm"] = None  # This should cause errors
        
        # Should not crash, should use fallbacks
        try:
            result = gsm_apply_user_node(state)
            assert result["game_status"] == "ERROR"
            assert result["last_user_response"] is not None
        except Exception:
            pytest.fail("Error handling should prevent exceptions")

    def test_minotaur_decision_validation(self):
        """Test that minotaur decisions are validated and fallback to WAIT."""
        state = create_initial_state()
        
        # Create a game over response to trigger WAIT decision
        mock_response = GameStateResponse(
            status="DEATH",
            user_state={"position": {"x": 25, "y": 25, "z": 0}, "stamina_pct": 0.0, "inventory": [], "lantern_cooldown": 0.0},
            environment={"visible_paths": [], "visible_items": [], "message": "Game Over", "steps_moved": 0, "time_taken": 0.0, "stop_reason": "SUCCESS"},
            minotaur_cue="Game Over",
            raw_text_output="Game Over"
        )
        state["last_user_response"] = mock_response
        
        result = minotaur_turn_node(state)
        
        # Should use WAIT for game over
        assert result["last_minotaur_decision"].action == "WAIT"
