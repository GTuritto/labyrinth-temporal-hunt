from __future__ import annotations

import random
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from gsm.models import (
    LabyrinthState, UserInput, GameStateResponse, Direction
)
from gsm.physics import Position, PhysicsConfig, simulate_movement, AudioProximity
from gsm.temporal import (
    TemporalState, MinotaurStatus, tick_timers, apply_lantern_use, 
    trigger_minotaur_jump, get_minotaur_reentry_position, tick
)


@dataclass
class GameStateManager:
    """Manages the complete game state with deterministic physics and temporal logic."""
    
    # Immutable configuration
    config: PhysicsConfig = field(default_factory=PhysicsConfig)
    
    # Mutable game state
    user_position: Position = field(default_factory=lambda: Position(25, 25, 0))
    minotaur_position: Position = field(default_factory=lambda: Position(10, 10, 0))
    user_stamina: float = 1.0
    user_inventory: list[str] = field(default_factory=list)
    
    # Temporal state
    temporal_state: TemporalState = field(default_factory=TemporalState)
    
    # Timers and cooldowns
    game_tick: int = 0
    user_cooldown: float = 0.0
    
    # Game state
    message: str = "Welcome to the Labyrinth."
    status: str = "active"
    
    # Last action results
    last_steps_moved: int = 0
    last_time_taken: float = 0.0
    last_stop_reason: str = "SUCCESS"
    
    def apply_user_input(self, user_input: UserInput) -> GameStateResponse:
        """Apply user input and return complete validated game state response."""
        # Check for encounter at start of turn
        if self._check_encounter():
            self.status = "DEATH"
            self.message = "The Minotaur catches you! Game Over."
            return self._build_validated_response()
        
        # Handle USE command for lantern
        if user_input.command == "USE" and user_input.target == "LANTERN":
            return self._handle_lantern_use()
        
        # Simulate movement/action
        new_pos, new_stamina, env_delta = simulate_movement(
            LabyrinthState(), user_input, self.user_position,
            self.minotaur_position, self.user_stamina, self.config
        )
        
        # Store action results
        self.last_steps_moved = env_delta.steps_moved
        self.last_time_taken = env_delta.time_taken
        self.last_stop_reason = env_delta.stop_reason.value
        
        # Update state
        self.user_position = new_pos
        self.user_stamina = new_stamina
        self._advance_time(env_delta.time_taken)
        
        # Check for encounter after movement
        if self._check_encounter():
            self.status = "DEATH"
            self.message = "The Minotaur catches you! Game Over."
            return self._build_validated_response()
        
        # Check for escape condition (3 stones)
        stones = [item for item in self.user_inventory if "STONE" in item and item in ["RED STONE", "BLUE STONE", "YELLOW STONE"]]
        if len(stones) >= 3:
            self.status = "ESCAPED"
            self.message = "You have collected all three mystical stones and escaped the labyrinth!"
            return self._build_validated_response()
        
        # Build message based on command
        self._update_message(user_input, env_delta)
        
        return self._build_validated_response()
    
    def _handle_lantern_use(self) -> GameStateResponse:
        """Handle lantern usage for minotaur paralysis."""
        if "LANTERN" not in self.user_inventory:
            self.message = "You don't have a lantern to use."
        else:
            self.temporal_state, success = apply_lantern_use(self.temporal_state)
            if success:
                self.user_inventory.remove("LANTERN")
                self.message = "You activate the lantern! A brilliant light paralyzes the Minotaur."
            else:
                self.message = "The lantern flickers but has no effect."
        
        self.last_steps_moved = 0
        self.last_time_taken = 0.0
        self.last_stop_reason = "SUCCESS"
        return self._build_validated_response()
    
    def _advance_time(self, time_delta: float) -> None:
        """Advance game time and update all timers."""
        self.game_tick += int(time_delta * 10)
        self.user_cooldown = max(0.0, self.user_cooldown - time_delta)
        
        # Store previous status to detect transitions
        prev_status = self.temporal_state.minotaur_status
        prev_jump_duration = self.temporal_state.jump_duration
        
        self.temporal_state = tick_timers(self.temporal_state, time_delta)
        
        # Only restore position if minotaur just transitioned from VANISHED to CHASING_3D
        if (prev_status == MinotaurStatus.VANISHED and 
            self.temporal_state.minotaur_status == MinotaurStatus.CHASING_3D and
            prev_jump_duration > 0.0 and self.temporal_state.jump_duration == 0.0):
            reentry_x, reentry_y, reentry_z = get_minotaur_reentry_position(self.temporal_state)
            self.minotaur_position = Position(reentry_x, reentry_y, reentry_z)
    
    def _check_encounter(self) -> bool:
        """Check encounter rule: death on co-location while minotaur is CHASING_3D."""
        if self.temporal_state.minotaur_status != MinotaurStatus.CHASING_3D:
            return False
        return (self.user_position.x == self.minotaur_position.x and
                self.user_position.y == self.minotaur_position.y and
                self.user_position.z == self.minotaur_position.z)
    
    def _update_message(self, user_input: UserInput, env_delta) -> None:
        """Update message based on command type."""
        if user_input.command == "MOVE" and env_delta.steps_moved > 0:
            direction_name = user_input.direction.value if user_input.direction else "unknown"
            speed_desc = "run" if user_input.speed == 2 and self.user_stamina > 0 else "walk"
            self.message = f"You {speed_desc} {direction_name} for {env_delta.steps_moved} steps."
            if env_delta.stop_reason.value == "COLLISION":
                self.message += " You stop at an obstacle."
        elif user_input.command == "LOOK":
            items = self._get_visible_items()
            items_desc = ", ".join(items) if items else "nothing of interest"
            self.message = f"You examine your surroundings. You see: {items_desc}."
        elif user_input.command == "GRAB":
            if user_input.target and user_input.target in self._get_visible_items():
                self.user_inventory.append(user_input.target)
                self.message = f"You grab the {user_input.target}."
            else:
                self.message = f"You don't see a {user_input.target or 'item'} here."
        elif user_input.command == "HALT":
            self.message = "You stop and listen carefully."
        else:
            self.message = "You remain in place."
    
    def _get_visible_paths(self) -> List[str]:
        """Get visible directions from current position."""
        visible = []
        for direction in [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]:
            test_pos = self.user_position.move_in_direction(direction, 1)
            if (0 <= test_pos.x < self.config.grid_width and 
                0 <= test_pos.y < self.config.grid_height):
                visible.append(direction.value)
        return visible
    
    def _get_visible_items(self) -> List[str]:
        """Get items visible from current position."""
        items = []
        item_hash = (self.user_position.x * 13 + self.user_position.y * 23) % 100
        if item_hash < 3:
            items.append("RED STONE")
        elif item_hash < 6:
            items.append("BLUE STONE")
        elif item_hash < 8:
            items.append("YELLOW STONE")
        elif item_hash < 10 and self.temporal_state.lantern_available:
            items.append("LANTERN")
        return items
    
    def _get_audio_proximity(self) -> AudioProximity:
        """Get current audio proximity to minotaur."""
        if self.temporal_state.minotaur_status != MinotaurStatus.CHASING_3D:
            return AudioProximity.NONE
        
        distance = self.user_position.distance_to(self.minotaur_position)
        if distance <= 3.0:
            return AudioProximity.VERY_CLOSE
        elif distance <= 8.0:
            return AudioProximity.CLOSE
        elif distance <= 15.0:
            return AudioProximity.FAINT
        else:
            return AudioProximity.NONE
    
    def _build_validated_response(self) -> GameStateResponse:
        """Build complete GameStateResponse with Pydantic validation."""
        user_state = {
            "position": {"x": self.user_position.x, "y": self.user_position.y, "z": self.user_position.z},
            "stamina_pct": round(self.user_stamina * 100, 1),
            "inventory": self.user_inventory.copy(),
            "lantern_cooldown": self.temporal_state.lantern_respawn_cooldown
        }
        
        environment = {
            "visible_paths": self._get_visible_paths(),
            "visible_items": self._get_visible_items(),
            "message": self.message,
            "steps_moved": self.last_steps_moved,
            "time_taken": self.last_time_taken,
            "stop_reason": self.last_stop_reason
        }
        
        # Build minotaur cue with proximity and status
        audio_prox = self._get_audio_proximity()
        if self.temporal_state.minotaur_status == MinotaurStatus.VANISHED:
            minotaur_cue = f"The Minotaur has vanished... ({self.temporal_state.jump_duration:.1f}s remaining)"
        elif self.temporal_state.minotaur_status == MinotaurStatus.PARALYZED:
            minotaur_cue = f"The Minotaur is paralyzed by light! ({self.temporal_state.paralysis_duration:.1f}s remaining)"
        elif audio_prox == AudioProximity.VERY_CLOSE:
            minotaur_cue = "The Minotaur's breathing is right behind you!"
        elif audio_prox == AudioProximity.CLOSE:
            minotaur_cue = "Heavy footsteps echo nearby."
        elif audio_prox == AudioProximity.FAINT:
            minotaur_cue = "You hear distant sounds in the labyrinth."
        else:
            minotaur_cue = "The labyrinth is eerily quiet."
        
        return GameStateResponse(
            status=self.status,
            user_state=user_state,
            environment=environment,
            minotaur_cue=minotaur_cue,
            raw_text_output=self.message
        )

    def trigger_minotaur_jump(self) -> None:
        """Manually trigger minotaur jump."""
        self.temporal_state = trigger_minotaur_jump(
            LabyrinthState(seed=42), self.temporal_state,
            self.minotaur_position.x, self.minotaur_position.y, self.minotaur_position.z
        )


# Legacy function for backward compatibility
def simulate_step(state: LabyrinthState, hunter_room_id: str, rng: Optional[random.Random] = None) -> LabyrinthState:
    """Simulate a single step for the hunter within the labyrinth."""
    from gsm.physics import move_between_rooms, trap_trigger_probability
    rng = rng or random.Random(state.seed)
    new_room_id, stamina_delta = move_between_rooms(state, hunter_room_id)
    if state.hunter:
        state.hunter.stamina = max(0.0, state.hunter.stamina + stamina_delta)

    room_map = {r.id: r for r in state.rooms}
    room = room_map.get(new_room_id)
    if room and state.hunter and rng.random() < trap_trigger_probability(room):
        state.hunter.stamina = max(0.0, state.hunter.stamina - rng.uniform(5.0, 15.0))

    return tick(state, rng)
