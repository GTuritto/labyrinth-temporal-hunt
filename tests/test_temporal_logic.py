import pytest
import random
from gsm.models import LabyrinthState, UserInput, Direction
from gsm.physics import Position
from gsm.engine import GameStateManager
from gsm.temporal import (
    TemporalState, MinotaurStatus, trigger_minotaur_jump, tick_timers, 
    apply_lantern_use, get_minotaur_reentry_position
)


class TestMinotaurJump:
    def test_trigger_minotaur_jump(self):
        """Test minotaur jump mechanics."""
        state = LabyrinthState(seed=42)
        temporal_state = TemporalState()
        rng = random.Random(42)
        
        # Initial state should be CHASING_3D
        assert temporal_state.minotaur_status == MinotaurStatus.CHASING_3D
        
        # Trigger jump
        updated_state = trigger_minotaur_jump(state, temporal_state, 10, 15, 2, rng)
        
        # Should be VANISHED with duration [5,10]s and cooldown 600s
        assert updated_state.minotaur_status == MinotaurStatus.VANISHED
        assert 5.0 <= updated_state.jump_duration <= 10.0
        assert updated_state.jump_cooldown == 600.0
        
        # Position should be stored for re-entry
        assert updated_state.vanish_position_x == 10
        assert updated_state.vanish_position_y == 15
        assert updated_state.vanish_position_z == 2

    def test_jump_cooldown_prevents_multiple_jumps(self):
        """Test that jump cooldown prevents immediate re-jumping."""
        state = LabyrinthState(seed=42)
        temporal_state = TemporalState(jump_cooldown=300.0)  # Still in cooldown
        
        # Try to trigger jump while in cooldown
        updated_state = trigger_minotaur_jump(state, temporal_state, 5, 5, 0)
        
        # Should remain CHASING_3D (no jump allowed)
        assert updated_state.minotaur_status == MinotaurStatus.CHASING_3D
        assert updated_state.jump_cooldown == 300.0

    def test_reentry_is_positional(self):
        """Test that minotaur reappears at exact same coordinates."""
        temporal_state = TemporalState(
            vanish_position_x=25,
            vanish_position_y=30,
            vanish_position_z=5
        )
        
        x, y, z = get_minotaur_reentry_position(temporal_state)
        assert x == 25
        assert y == 30
        assert z == 5


class TestTimerTicking:
    def test_tick_timers_decrements_all_timers(self):
        """Test that tick_timers decrements all timers correctly."""
        temporal_state = TemporalState(
            jump_duration=8.0,
            jump_cooldown=500.0,
            paralysis_duration=100.0,
            lantern_respawn_cooldown=600.0
        )
        
        # Tick 2.5 seconds
        updated_state = tick_timers(temporal_state, 2.5)
        
        assert updated_state.jump_duration == 5.5
        assert updated_state.jump_cooldown == 497.5
        assert updated_state.paralysis_duration == 97.5
        assert updated_state.lantern_respawn_cooldown == 597.5

    def test_timers_clamp_to_zero(self):
        """Test that timers don't go below zero."""
        temporal_state = TemporalState(
            jump_duration=1.0,
            paralysis_duration=0.5
        )
        
        # Tick more than remaining time
        updated_state = tick_timers(temporal_state, 3.0)
        
        assert updated_state.jump_duration == 0.0
        assert updated_state.paralysis_duration == 0.0

    def test_vanished_to_chasing_transition(self):
        """Test transition from VANISHED to CHASING_3D when jump_duration expires."""
        temporal_state = TemporalState(
            minotaur_status=MinotaurStatus.VANISHED,
            jump_duration=1.0
        )
        
        # Tick past jump duration
        updated_state = tick_timers(temporal_state, 2.0)
        
        assert updated_state.minotaur_status == MinotaurStatus.CHASING_3D
        assert updated_state.jump_duration == 0.0

    def test_paralyzed_to_chasing_transition(self):
        """Test transition from PARALYZED to CHASING_3D when paralysis expires."""
        temporal_state = TemporalState(
            minotaur_status=MinotaurStatus.PARALYZED,
            paralysis_duration=2.0
        )
        
        # Tick past paralysis duration
        updated_state = tick_timers(temporal_state, 3.0)
        
        assert updated_state.minotaur_status == MinotaurStatus.CHASING_3D
        assert updated_state.paralysis_duration == 0.0


class TestLanternMechanics:
    def test_lantern_use_success(self):
        """Test successful lantern use paralyzes minotaur."""
        temporal_state = TemporalState(
            minotaur_status=MinotaurStatus.CHASING_3D,
            lantern_available=True
        )
        
        updated_state, success = apply_lantern_use(temporal_state)
        
        assert success is True
        assert updated_state.minotaur_status == MinotaurStatus.PARALYZED
        assert updated_state.paralysis_duration == 120.0  # 2 minutes
        assert updated_state.lantern_available is False
        assert updated_state.lantern_respawn_cooldown == 720.0  # 12 minutes

    def test_lantern_use_when_unavailable(self):
        """Test lantern use fails when no lantern available."""
        temporal_state = TemporalState(lantern_available=False)
        
        updated_state, success = apply_lantern_use(temporal_state)
        
        assert success is False
        assert updated_state.lantern_available is False

    def test_only_one_lantern_exists(self):
        """Test that only one lantern exists in the world."""
        temporal_state = TemporalState(lantern_available=True)
        
        # Use lantern
        updated_state, _ = apply_lantern_use(temporal_state)
        assert updated_state.lantern_available is False
        
        # Try to use again (should fail)
        updated_state2, success = apply_lantern_use(updated_state)
        assert success is False

    def test_lantern_respawn_after_720s(self):
        """Test lantern respawns after 720s from end of paralysis."""
        temporal_state = TemporalState(
            lantern_available=False,
            lantern_respawn_cooldown=1.0  # Almost ready to respawn
        )
        
        # Tick past respawn time
        updated_state = tick_timers(temporal_state, 2.0)
        
        assert updated_state.lantern_available is True
        assert updated_state.lantern_respawn_cooldown == 0.0


class TestEncounterMechanics:
    def test_death_on_co_location_while_chasing(self):
        """Test death occurs when user and minotaur occupy same position while CHASING_3D."""
        gsm = GameStateManager()
        
        # Set minotaur to same position as user
        gsm.minotaur_position = Position(gsm.user_position.x, gsm.user_position.y, gsm.user_position.z)
        gsm.temporal_state.minotaur_status = MinotaurStatus.CHASING_3D
        
        # Any action should trigger encounter check
        move_cmd = UserInput(command="LOOK")
        response = gsm.apply_user_input(move_cmd)
        
        assert gsm.status == "DEATH"
        assert "Game Over" in response.raw_text_output

    def test_no_death_when_minotaur_vanished(self):
        """Test no death when minotaur is VANISHED even at same position."""
        gsm = GameStateManager()
        
        # Set minotaur to same position but VANISHED
        gsm.minotaur_position = Position(gsm.user_position.x, gsm.user_position.y, gsm.user_position.z)
        gsm.temporal_state.minotaur_status = MinotaurStatus.VANISHED
        gsm.temporal_state.jump_duration = 5.0  # Still vanished for 5 seconds
        
        move_cmd = UserInput(command="LOOK")
        response = gsm.apply_user_input(move_cmd)
        
        assert gsm.status == "active"  # Still alive

    def test_no_death_when_minotaur_paralyzed(self):
        """Test no death when minotaur is PARALYZED even at same position."""
        gsm = GameStateManager()
        
        # Set minotaur to same position but PARALYZED
        gsm.minotaur_position = Position(gsm.user_position.x, gsm.user_position.y, gsm.user_position.z)
        gsm.temporal_state.minotaur_status = MinotaurStatus.PARALYZED
        gsm.temporal_state.paralysis_duration = 60.0  # Still paralyzed for 60 seconds
        
        move_cmd = UserInput(command="LOOK")
        response = gsm.apply_user_input(move_cmd)
        
        assert gsm.status == "active"  # Still alive


class TestGameStateManagerIntegration:
    def test_time_advancement_flows_into_tick_timers(self):
        """Test that movement time_taken flows into tick_timers."""
        gsm = GameStateManager()
        gsm.temporal_state.paralysis_duration = 10.0
        
        # Move command that takes time
        move_cmd = UserInput(command="MOVE", direction=Direction.NORTH, steps=5, speed=1)
        gsm.apply_user_input(move_cmd)
        
        # Paralysis duration should have decreased by movement time
        assert gsm.temporal_state.paralysis_duration < 10.0

    def test_minotaur_reappears_at_exact_coordinates(self):
        """Test minotaur reappears at exact vanish coordinates."""
        gsm = GameStateManager()
        
        # Set initial minotaur position
        original_pos = Position(20, 25, 3)
        gsm.minotaur_position = original_pos
        
        # Trigger jump (vanish)
        gsm.trigger_minotaur_jump()
        assert gsm.temporal_state.minotaur_status == MinotaurStatus.VANISHED
        
        # Move minotaur elsewhere (shouldn't matter)
        gsm.minotaur_position = Position(50, 50, 9)
        
        # Advance time past jump duration
        gsm._advance_time(15.0)  # More than max jump duration (10s)
        
        # Should reappear at original position
        assert gsm.temporal_state.minotaur_status == MinotaurStatus.CHASING_3D
        assert gsm.minotaur_position.x == original_pos.x
        assert gsm.minotaur_position.y == original_pos.y
        assert gsm.minotaur_position.z == original_pos.z

    def test_lantern_use_integration(self):
        """Test complete lantern use workflow."""
        gsm = GameStateManager()
        
        # Add lantern to inventory
        gsm.user_inventory.append("LANTERN")
        gsm.temporal_state.lantern_available = True
        
        # Use lantern
        use_cmd = UserInput(command="USE", target="LANTERN")
        response = gsm.apply_user_input(use_cmd)
        
        # Lantern should be consumed, minotaur paralyzed
        assert "LANTERN" not in gsm.user_inventory
        assert gsm.temporal_state.minotaur_status == MinotaurStatus.PARALYZED
        assert gsm.temporal_state.paralysis_duration == 120.0
        assert gsm.temporal_state.lantern_available is False
        assert "paralyzes" in response.raw_text_output.lower()
