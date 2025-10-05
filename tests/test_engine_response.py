import pytest
from gsm.models import UserInput, Direction, GameStateResponse
from gsm.engine import GameStateManager
from gsm.physics import Position
from gsm.temporal import MinotaurStatus
from pydantic import ValidationError


class TestGameStateResponseValidation:
    def test_response_schema_validation(self):
        """Test that all responses return valid GameStateResponse objects."""
        gsm = GameStateManager()
        commands = [
            UserInput(command="LOOK"),
            UserInput(command="MOVE", direction=Direction.NORTH, steps=3),
            UserInput(command="HALT")
        ]
        
        for cmd in commands:
            response = gsm.apply_user_input(cmd)
            assert isinstance(response, GameStateResponse)
            assert hasattr(response, 'status')
            assert hasattr(response, 'user_state')
            assert hasattr(response, 'environment')

    def test_response_rejects_extra_keys(self):
        """Test GameStateResponse rejects unexpected keys."""
        with pytest.raises(ValidationError):
            GameStateResponse(
                status="active",
                user_state={"position": {"x": 0, "y": 0, "z": 0}, "stamina_pct": 100.0, "inventory": [], "lantern_cooldown": 0.0},
                environment={"visible_paths": [], "visible_items": [], "message": "", "steps_moved": 0, "time_taken": 0.0, "stop_reason": "SUCCESS"},
                minotaur_cue="Test",
                raw_text_output="Test",
                unexpected_field="should_fail"
            )


class TestEscapeCondition:
    def test_escaped_on_three_stones(self):
        """Test ESCAPED status when collecting 3 stones."""
        gsm = GameStateManager()
        gsm.user_inventory = ["RED STONE", "BLUE STONE", "YELLOW STONE"]
        
        response = gsm.apply_user_input(UserInput(command="LOOK"))
        
        assert gsm.status == "ESCAPED"
        assert response.status == "ESCAPED"
        assert "escaped" in response.raw_text_output.lower()

    def test_not_escaped_on_two_stones(self):
        """Test no escape with only 2 stones."""
        gsm = GameStateManager()
        gsm.user_inventory = ["RED STONE", "BLUE STONE"]
        
        response = gsm.apply_user_input(UserInput(command="LOOK"))
        
        assert gsm.status == "active"


class TestDeathCondition:
    def test_death_on_co_location_chasing(self):
        """Test DEATH when minotaur catches user while CHASING_3D."""
        gsm = GameStateManager()
        gsm.minotaur_position = Position(gsm.user_position.x, gsm.user_position.y, gsm.user_position.z)
        gsm.temporal_state.minotaur_status = MinotaurStatus.CHASING_3D
        
        response = gsm.apply_user_input(UserInput(command="LOOK"))
        
        assert gsm.status == "DEATH"
        assert response.status == "DEATH"

    def test_no_death_when_vanished(self):
        """Test no death when minotaur is VANISHED."""
        gsm = GameStateManager()
        gsm.minotaur_position = Position(gsm.user_position.x, gsm.user_position.y, gsm.user_position.z)
        gsm.temporal_state.minotaur_status = MinotaurStatus.VANISHED
        gsm.temporal_state.jump_duration = 5.0  # Still vanished for 5 seconds
        
        response = gsm.apply_user_input(UserInput(command="LOOK"))
        
        assert gsm.status == "active"


class TestMinotaurCueProximity:
    def test_very_close_proximity_cue(self):
        """Test minotaur cue for VERY_CLOSE proximity."""
        gsm = GameStateManager()
        gsm.minotaur_position = Position(gsm.user_position.x + 2, gsm.user_position.y, gsm.user_position.z)
        gsm.temporal_state.minotaur_status = MinotaurStatus.CHASING_3D
        
        response = gsm.apply_user_input(UserInput(command="LOOK"))
        
        assert "breathing" in response.minotaur_cue.lower()

    def test_close_proximity_cue(self):
        """Test minotaur cue for CLOSE proximity."""
        gsm = GameStateManager()
        gsm.minotaur_position = Position(gsm.user_position.x + 5, gsm.user_position.y, gsm.user_position.z)
        gsm.temporal_state.minotaur_status = MinotaurStatus.CHASING_3D
        
        response = gsm.apply_user_input(UserInput(command="LOOK"))
        
        assert "footsteps" in response.minotaur_cue.lower()

    def test_faint_proximity_cue(self):
        """Test minotaur cue for FAINT proximity."""
        gsm = GameStateManager()
        gsm.minotaur_position = Position(gsm.user_position.x + 12, gsm.user_position.y, gsm.user_position.z)
        gsm.temporal_state.minotaur_status = MinotaurStatus.CHASING_3D
        
        response = gsm.apply_user_input(UserInput(command="LOOK"))
        
        assert "distant" in response.minotaur_cue.lower()

    def test_vanished_status_cue(self):
        """Test minotaur cue when VANISHED."""
        gsm = GameStateManager()
        gsm.temporal_state.minotaur_status = MinotaurStatus.VANISHED
        gsm.temporal_state.jump_duration = 7.5
        
        response = gsm.apply_user_input(UserInput(command="LOOK"))
        
        assert "vanished" in response.minotaur_cue.lower()
        assert "7.5" in response.minotaur_cue

    def test_paralyzed_status_cue(self):
        """Test minotaur cue when PARALYZED."""
        gsm = GameStateManager()
        gsm.temporal_state.minotaur_status = MinotaurStatus.PARALYZED
        gsm.temporal_state.paralysis_duration = 45.2
        
        response = gsm.apply_user_input(UserInput(command="LOOK"))
        
        assert "paralyzed" in response.minotaur_cue.lower()
        assert "45.2" in response.minotaur_cue
