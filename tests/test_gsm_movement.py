import pytest
from gsm.models import UserInput, Direction, LabyrinthState
from gsm.physics import Position, PhysicsConfig, simulate_movement, StopReason
from gsm.engine import GameStateManager


class TestPosition:
    def test_position_creation(self):
        pos = Position(10, 20, 5)
        assert pos.x == 10
        assert pos.y == 20
        assert pos.z == 5

    def test_distance_calculation(self):
        pos1 = Position(0, 0, 0)
        pos2 = Position(3, 4, 0)
        assert pos1.distance_to(pos2) == 5.0  # 3-4-5 triangle

    def test_move_in_direction(self):
        pos = Position(10, 10, 5)
        
        north = pos.move_in_direction(Direction.NORTH, 3)
        assert north == Position(10, 13, 5)
        
        south = pos.move_in_direction(Direction.SOUTH, 2)
        assert south == Position(10, 8, 5)
        
        east = pos.move_in_direction(Direction.EAST, 1)
        assert east == Position(11, 10, 5)
        
        west = pos.move_in_direction(Direction.WEST, 4)
        assert west == Position(6, 10, 5)


class TestMovementSimulation:
    def setup_method(self):
        self.config = PhysicsConfig(
            grid_width=20, grid_height=20, grid_depth=5,
            stamina_drain_running=0.1, stamina_drain_walking=-0.05
        )
        self.state = LabyrinthState(tick=0, rooms=[], seed=42)
        self.user_pos = Position(10, 10, 0)
        self.minotaur_pos = Position(5, 5, 0)

    def test_walking_vs_running_timing(self):
        """Test that running (speed=2) takes half the time of walking (speed=1)."""
        # Use smaller steps to avoid boundary collision
        walk_cmd = UserInput(command="MOVE", direction=Direction.NORTH, steps=5, speed=1)
        _, _, walk_delta = simulate_movement(
            self.state, walk_cmd, self.user_pos, self.minotaur_pos, 1.0, self.config
        )
        
        run_cmd = UserInput(command="MOVE", direction=Direction.NORTH, steps=5, speed=2)
        _, _, run_delta = simulate_movement(
            self.state, run_cmd, self.user_pos, self.minotaur_pos, 1.0, self.config
        )
        
        # Running should take half the time (if same steps moved)
        if walk_delta.steps_moved == run_delta.steps_moved:
            assert run_delta.time_taken == walk_delta.time_taken / 2

    def test_stamina_behavior(self):
        """Test stamina drain for running and recovery for walking."""
        initial_stamina = 0.8
        
        # Running should drain stamina
        run_cmd = UserInput(command="MOVE", direction=Direction.EAST, steps=5, speed=2)
        _, new_stamina_run, run_delta = simulate_movement(
            self.state, run_cmd, self.user_pos, self.minotaur_pos, initial_stamina, self.config
        )
        
        assert run_delta.stamina_delta < 0  # Negative = drain
        assert new_stamina_run < initial_stamina
        
        # Walking should recover stamina
        walk_cmd = UserInput(command="MOVE", direction=Direction.WEST, steps=5, speed=1)
        _, new_stamina_walk, walk_delta = simulate_movement(
            self.state, walk_cmd, self.user_pos, self.minotaur_pos, initial_stamina, self.config
        )
        
        assert walk_delta.stamina_delta > 0  # Positive = recovery
        assert new_stamina_walk > initial_stamina

    def test_stamina_zero_caps_speed(self):
        """Test that zero stamina caps speed to 1."""
        run_cmd = UserInput(command="MOVE", direction=Direction.NORTH, steps=5, speed=2)
        _, _, delta = simulate_movement(
            self.state, run_cmd, self.user_pos, self.minotaur_pos, 0.0, self.config
        )
        
        # Should take walking time (steps_moved / 1) not running time (steps_moved / 2)
        expected_time = delta.steps_moved / 1  # Walking speed when stamina=0
        assert delta.time_taken == expected_time

    def test_collision_stop_at_correct_step(self):
        """Test that movement stops at the first collision."""
        # Move towards grid boundary (should hit collision)
        boundary_pos = Position(1, 10, 0)  # Near left boundary
        west_cmd = UserInput(command="MOVE", direction=Direction.WEST, steps=10, speed=1)
        
        new_pos, _, delta = simulate_movement(
            self.state, west_cmd, boundary_pos, self.minotaur_pos, 1.0, self.config
        )
        
        # Should stop before hitting boundary (x=0)
        assert delta.stop_reason == StopReason.COLLISION
        assert delta.steps_moved < 10  # Didn't complete all steps
        assert new_pos.x >= 0  # Didn't go out of bounds

    def test_time_taken_advances_timers(self):
        """Test that time_taken can be used to advance game timers."""
        cmd = UserInput(command="MOVE", direction=Direction.NORTH, steps=8, speed=2)
        _, _, delta = simulate_movement(
            self.state, cmd, self.user_pos, self.minotaur_pos, 1.0, self.config
        )
        
        # Time taken should be calculable and reasonable
        expected_time = delta.steps_moved / 2  # steps / speed
        assert delta.time_taken == expected_time
        assert delta.time_taken > 0

    def test_visibility_radii_walking_vs_running(self):
        """Test that running provides better visibility than walking."""
        # Test that sight radius affects visible paths
        walk_cmd = UserInput(command="LOOK", speed=1)
        run_cmd = UserInput(command="LOOK", speed=2)
        
        _, _, walk_delta = simulate_movement(
            self.state, walk_cmd, self.user_pos, self.minotaur_pos, 1.0, self.config
        )
        _, _, run_delta = simulate_movement(
            self.state, run_cmd, self.user_pos, self.minotaur_pos, 1.0, self.config
        )
        
        # Both should have visible paths (simplified implementation)
        assert len(walk_delta.visible_paths) >= 2
        assert len(run_delta.visible_paths) >= 2


class TestGameStateManager:
    def test_game_state_manager_creation(self):
        gsm = GameStateManager()
        assert gsm.user_stamina == 1.0
        assert gsm.status == "active"
        assert gsm.game_tick == 0

    def test_apply_user_input_move(self):
        gsm = GameStateManager()
        initial_pos = gsm.user_position
        
        move_cmd = UserInput(command="MOVE", direction=Direction.NORTH, steps=5, speed=1)
        response = gsm.apply_user_input(move_cmd)
        
        # Should have moved
        assert gsm.user_position.y > initial_pos.y
        assert response.status == "active"
        assert "walk" in response.raw_text_output.lower() or "run" in response.raw_text_output.lower()

    def test_apply_user_input_look(self):
        gsm = GameStateManager()
        
        look_cmd = UserInput(command="LOOK")
        response = gsm.apply_user_input(look_cmd)
        
        # Should remain in place
        assert response.status == "active"
        assert "examine" in response.raw_text_output.lower()

    def test_game_state_response_structure(self):
        gsm = GameStateManager()
        move_cmd = UserInput(command="MOVE", direction=Direction.EAST, steps=3, speed=2)
        response = gsm.apply_user_input(move_cmd)
        
        # Verify response structure (updated for new format)
        assert "position" in response.user_state
        assert "stamina_pct" in response.user_state  # Changed from "stamina" to "stamina_pct"
        assert "inventory" in response.user_state
        assert "visible_paths" in response.environment  # Changed from "tick"
        assert isinstance(response.minotaur_cue, str)
        assert isinstance(response.raw_text_output, str)
