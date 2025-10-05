from __future__ import annotations

import random
from typing import Tuple, Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from gsm.models import LabyrinthState, Room, UserInput, Direction


class StopReason(str, Enum):
    COLLISION = "COLLISION"
    ENCOUNTER = "ENCOUNTER"
    SUCCESS = "SUCCESS"


class AudioProximity(str, Enum):
    NONE = "NONE"
    FAINT = "FAINT"
    CLOSE = "CLOSE"
    VERY_CLOSE = "VERY_CLOSE"


@dataclass
class Position:
    x: int
    y: int
    z: int = 0

    def distance_to(self, other: 'Position') -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2) ** 0.5

    def move_in_direction(self, direction: Direction, steps: int = 1) -> 'Position':
        """Move position in given direction by specified steps."""
        new_pos = Position(self.x, self.y, self.z)
        
        if direction == Direction.NORTH:
            new_pos.y += steps
        elif direction == Direction.SOUTH:
            new_pos.y -= steps
        elif direction == Direction.EAST:
            new_pos.x += steps
        elif direction == Direction.WEST:
            new_pos.x -= steps
        elif direction == Direction.UP_RAMP:
            new_pos.z += steps
        elif direction == Direction.DOWN_RAMP:
            new_pos.z -= steps
            
        return new_pos


@dataclass
class PhysicsConfig:
    """Immutable physics configuration."""
    grid_width: int = 50
    grid_height: int = 50
    grid_depth: int = 10
    stamina_drain_running: float = 0.02  # per step when speed=2
    stamina_drain_walking: float = -0.01  # negative = recovery when speed=1
    sight_radius_walking: int = 2
    sight_radius_running: int = 6
    audio_distance_faint: float = 15.0
    audio_distance_close: float = 8.0
    audio_distance_very_close: float = 3.0


@dataclass
class EnvironmentDelta:
    """Results of movement simulation."""
    steps_moved: int
    stop_reason: StopReason
    time_taken: float
    stamina_delta: float
    visible_paths: List[Direction]
    visible_items: List[str]
    audio_proximity: AudioProximity


def simulate_movement(
    state: LabyrinthState, 
    command: UserInput, 
    user_pos: Position, 
    minotaur_pos: Position,
    current_stamina: float,
    config: PhysicsConfig = None
) -> Tuple[Position, float, EnvironmentDelta]:
    """Simulate movement based on user command."""
    if config is None:
        config = PhysicsConfig()
    
    # Handle non-movement commands
    if command.command != "MOVE":
        sight_radius = config.sight_radius_running if command.speed == 2 else config.sight_radius_walking
        return user_pos, current_stamina, EnvironmentDelta(
            steps_moved=0,
            stop_reason=StopReason.SUCCESS,
            time_taken=0.0,
            stamina_delta=0.0,
            visible_paths=[Direction.NORTH, Direction.SOUTH],  # Simplified
            visible_items=[],
            audio_proximity=AudioProximity.NONE
        )
    
    if not command.direction:
        return user_pos, current_stamina, EnvironmentDelta(
            steps_moved=0, stop_reason=StopReason.SUCCESS, time_taken=0.0,
            stamina_delta=0.0, visible_paths=[], visible_items=[], audio_proximity=AudioProximity.NONE
        )
    
    # Determine effective speed (cap to 1 if stamina is 0)
    effective_speed = command.speed if current_stamina > 0 else 1
    
    # Simulate step-by-step movement
    current_pos = user_pos
    steps_moved = 0
    stop_reason = StopReason.SUCCESS
    
    for step in range(command.steps):
        next_pos = current_pos.move_in_direction(command.direction, 1)
        
        # Check for collision (simplified: boundaries)
        if (next_pos.x < 0 or next_pos.x >= config.grid_width or 
            next_pos.y < 0 or next_pos.y >= config.grid_height):
            stop_reason = StopReason.COLLISION
            break
        
        current_pos = next_pos
        steps_moved += 1
    
    # Calculate time and stamina
    time_taken = steps_moved / effective_speed
    if effective_speed == 2:
        stamina_delta = -steps_moved * config.stamina_drain_running
    else:
        stamina_delta = -steps_moved * config.stamina_drain_walking
    
    new_stamina = max(0.0, min(1.0, current_stamina + stamina_delta))
    
    env_delta = EnvironmentDelta(
        steps_moved=steps_moved,
        stop_reason=stop_reason,
        time_taken=time_taken,
        stamina_delta=stamina_delta,
        visible_paths=[Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST],
        visible_items=[],
        audio_proximity=AudioProximity.NONE
    )
    
    return current_pos, new_stamina, env_delta


# Legacy functions for backward compatibility
def move_between_rooms(state: LabyrinthState, current_room_id: str) -> Tuple[str, float]:
    """Randomly move to a connected room. Returns (new_room_id, stamina_delta)."""
    room_map = {r.id: r for r in state.rooms}
    current = room_map.get(current_room_id)
    if not current or not current.connections:
        return current_room_id, 0.0

    new_room_id = random.choice(current.connections)
    stamina_delta = -random.uniform(0.5, 3.0)
    return new_room_id, stamina_delta


def trap_trigger_probability(room: Room) -> float:
    return 0.35 if room.has_trap else 0.0
