import json
import pytest
from pydantic import ValidationError

from gsm.models import (
    Direction,
    UserInput,
    MinotaurDecision,
    GameStateResponse,
    parse_user_input_json,
    parse_minotaur_decision_json,
)


class TestDirection:
    def test_valid_directions(self):
        assert Direction.NORTH == "NORTH"
        assert Direction.UP_RAMP == "UP RAMP"
        assert Direction.DOWN_RAMP == "DOWN RAMP"


class TestUserInput:
    def test_valid_user_input(self):
        ui = UserInput(command="MOVE", direction=Direction.NORTH, steps=50, speed=2, target="RED STONE")
        assert ui.command == "MOVE"
        assert ui.direction == Direction.NORTH
        assert ui.steps == 50
        assert ui.speed == 2
        assert ui.target == "RED STONE"

    def test_defaults(self):
        ui = UserInput(command="LOOK")
        assert ui.command == "LOOK"
        assert ui.direction is None
        assert ui.steps == 100
        assert ui.speed == 1
        assert ui.target is None

    def test_invalid_command(self):
        with pytest.raises(ValidationError):
            UserInput(command="INVALID")

    def test_invalid_speed(self):
        with pytest.raises(ValidationError):
            UserInput(command="MOVE", speed=3)

    def test_invalid_steps(self):
        with pytest.raises(ValidationError):
            UserInput(command="MOVE", steps=0)

    def test_invalid_target(self):
        with pytest.raises(ValidationError):
            UserInput(command="GRAB", target="INVALID STONE")


class TestMinotaurDecision:
    def test_valid_minotaur_decision(self):
        md = MinotaurDecision(action="PATHFIND", target_coords={"x": 10, "y": 20, "z": 5})
        assert md.action == "PATHFIND"
        assert md.target_coords == {"x": 10, "y": 20, "z": 5}

    def test_defaults(self):
        md = MinotaurDecision(action="WAIT")
        assert md.action == "WAIT"
        assert md.target_coords is None

    def test_invalid_action(self):
        with pytest.raises(ValidationError):
            MinotaurDecision(action="INVALID")

    def test_invalid_coords_type(self):
        with pytest.raises(ValidationError):
            MinotaurDecision(action="JUMP", target_coords={"x": "not_int", "y": 20, "z": 5})


class TestGameStateResponse:
    def test_valid_game_state_response(self):
        gsr = GameStateResponse(
            status="active",
            user_state={"health": 100, "position": {"x": 5, "y": 10}},
            environment={"room_id": "R1", "lighting": "dim"},
            minotaur_cue="The beast stirs in the shadows...",
            raw_text_output="You see a narrow corridor ahead."
        )
        assert gsr.status == "active"
        assert gsr.user_state["health"] == 100
        assert gsr.environment["room_id"] == "R1"

    def test_rejects_unexpected_keys(self):
        with pytest.raises(ValidationError) as exc_info:
            GameStateResponse(
                status="active",
                user_state={},
                environment={},
                minotaur_cue="",
                raw_text_output="",
                unexpected_field="should_fail"
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestParseUserInputJson:
    def test_valid_json(self):
        json_str = '{"command": "MOVE", "direction": "NORTH", "steps": 25, "speed": 2}'
        ui = parse_user_input_json(json_str)
        assert ui.command == "MOVE"
        assert ui.direction == Direction.NORTH
        assert ui.steps == 25
        assert ui.speed == 2

    def test_minimal_valid_json(self):
        json_str = '{"command": "LOOK"}'
        ui = parse_user_input_json(json_str)
        assert ui.command == "LOOK"
        assert ui.steps == 100  # default

    def test_invalid_json_syntax(self):
        json_str = '{"command": "MOVE", invalid}'
        ui = parse_user_input_json(json_str)
        assert ui.command == "LOOK"  # fallback

    def test_invalid_command_field(self):
        json_str = '{"command": "INVALID_COMMAND"}'
        ui = parse_user_input_json(json_str)
        assert ui.command == "LOOK"  # fallback

    def test_invalid_field_types(self):
        json_str = '{"command": "MOVE", "steps": "not_a_number"}'
        ui = parse_user_input_json(json_str)
        assert ui.command == "LOOK"  # fallback

    def test_missing_required_field(self):
        json_str = '{"direction": "NORTH"}'  # missing command
        ui = parse_user_input_json(json_str)
        assert ui.command == "LOOK"  # fallback

    def test_extra_fields_ignored(self):
        json_str = '{"command": "HALT", "extra_field": "ignored"}'
        ui = parse_user_input_json(json_str)
        assert ui.command == "HALT"  # should work, extra fields ignored in UserInput

    def test_empty_string(self):
        ui = parse_user_input_json("")
        assert ui.command == "LOOK"  # fallback

    def test_null_input(self):
        ui = parse_user_input_json("null")
        assert ui.command == "LOOK"  # fallback


class TestParseMinotaurDecisionJson:
    def test_valid_json(self):
        json_str = '{"action": "PATHFIND", "target_coords": {"x": 15, "y": 25, "z": 3}}'
        md = parse_minotaur_decision_json(json_str)
        assert md.action == "PATHFIND"
        assert md.target_coords == {"x": 15, "y": 25, "z": 3}

    def test_minimal_valid_json(self):
        json_str = '{"action": "WAIT"}'
        md = parse_minotaur_decision_json(json_str)
        assert md.action == "WAIT"
        assert md.target_coords is None

    def test_invalid_json_syntax(self):
        json_str = '{"action": "CHASE", malformed}'
        md = parse_minotaur_decision_json(json_str)
        assert md.action == "WAIT"  # fallback

    def test_invalid_action_field(self):
        json_str = '{"action": "INVALID_ACTION"}'
        md = parse_minotaur_decision_json(json_str)
        assert md.action == "WAIT"  # fallback

    def test_invalid_coords_structure(self):
        json_str = '{"action": "JUMP", "target_coords": {"x": "not_int", "y": 10}}'
        md = parse_minotaur_decision_json(json_str)
        assert md.action == "WAIT"  # fallback

    def test_missing_required_field(self):
        json_str = '{"target_coords": {"x": 5, "y": 10, "z": 2}}'  # missing action
        md = parse_minotaur_decision_json(json_str)
        assert md.action == "WAIT"  # fallback

    def test_empty_string(self):
        md = parse_minotaur_decision_json("")
        assert md.action == "WAIT"  # fallback

    def test_null_input(self):
        md = parse_minotaur_decision_json("null")
        assert md.action == "WAIT"  # fallback


class TestFuzzInvalidFields:
    """Fuzz testing with various invalid field combinations."""
    
    def test_fuzz_user_input_invalid_combinations(self):
        invalid_cases = [
            '{"command": 123}',  # wrong type
            '{"command": "MOVE", "direction": "INVALID_DIR"}',  # invalid direction
            '{"command": "GRAB", "steps": -5}',  # negative steps
            '{"command": "USE", "speed": 0}',  # invalid speed
            '{"command": "LOOK", "target": "INVALID_TARGET"}',  # invalid target
            '[]',  # wrong JSON structure
            '{"nested": {"command": "MOVE"}}',  # nested structure
        ]
        
        for invalid_json in invalid_cases:
            ui = parse_user_input_json(invalid_json)
            assert ui.command == "LOOK", f"Failed for: {invalid_json}"

    def test_fuzz_minotaur_decision_invalid_combinations(self):
        invalid_cases = [
            '{"action": 456}',  # wrong type
            '{"action": "PATHFIND", "target_coords": "not_dict"}',  # wrong coords type
            '{"action": "CHASE", "target_coords": {"x": 1.5, "y": 2, "z": 3}}',  # float coords
            '{"action": "JUMP", "target_coords": {"a": 1, "b": 2}}',  # wrong coord keys
            '[]',  # wrong JSON structure
            '{"nested": {"action": "WAIT"}}',  # nested structure
        ]
        
        for invalid_json in invalid_cases:
            md = parse_minotaur_decision_json(invalid_json)
            assert md.action == "WAIT", f"Failed for: {invalid_json}"
