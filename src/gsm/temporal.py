from __future__ import annotations

import random
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from gsm.models import LabyrinthState, Room


class MinotaurStatus(str, Enum):
    CHASING_3D = "CHASING_3D"
    VANISHED = "VANISHED"
    PARALYZED = "PARALYZED"


@dataclass
class TemporalState:
    """Extended temporal state for minotaur behaviors and timers."""
    minotaur_status: MinotaurStatus = MinotaurStatus.CHASING_3D
    jump_duration: float = 0.0  # Time remaining in VANISHED state
    jump_cooldown: float = 0.0  # Cooldown before next jump allowed
    paralysis_duration: float = 0.0  # Time remaining in PARALYZED state
    lantern_respawn_cooldown: float = 0.0  # Time until lantern respawns
    lantern_available: bool = True  # Whether lantern exists in world
    
    # Position storage for re-entry
    vanish_position_x: int = 0
    vanish_position_y: int = 0
    vanish_position_z: int = 0


def trigger_minotaur_jump(state: LabyrinthState, temporal_state: TemporalState, 
                         current_minotaur_x: int, current_minotaur_y: int, current_minotaur_z: int,
                         rng: Optional[random.Random] = None) -> TemporalState:
    """
    Trigger minotaur jump: set status=VANISHED, choose random duration [5,10]s, 
    start cooldown=600s, freeze position for re-entry.
    """
    r = rng or random.Random(state.seed)
    
    # Only allow jump if not in cooldown and not already vanished/paralyzed
    if (temporal_state.jump_cooldown <= 0 and 
        temporal_state.minotaur_status == MinotaurStatus.CHASING_3D):
        
        temporal_state.minotaur_status = MinotaurStatus.VANISHED
        temporal_state.jump_duration = r.uniform(5.0, 10.0)  # Random duration [5,10]s
        temporal_state.jump_cooldown = 600.0  # 10 minutes cooldown
        
        # Store current position for exact re-entry
        temporal_state.vanish_position_x = current_minotaur_x
        temporal_state.vanish_position_y = current_minotaur_y
        temporal_state.vanish_position_z = current_minotaur_z
    
    return temporal_state


def tick_timers(temporal_state: TemporalState, dt: float) -> TemporalState:
    """
    Decrement all timers by dt, clamp to ≥0. 
    If VANISHED and jump_duration expired -> status=CHASING_3D and reappear at same coordinates.
    """
    # Decrement all timers
    temporal_state.jump_duration = max(0.0, temporal_state.jump_duration - dt)
    temporal_state.jump_cooldown = max(0.0, temporal_state.jump_cooldown - dt)
    temporal_state.paralysis_duration = max(0.0, temporal_state.paralysis_duration - dt)
    temporal_state.lantern_respawn_cooldown = max(0.0, temporal_state.lantern_respawn_cooldown - dt)
    
    # Check for state transitions
    if (temporal_state.minotaur_status == MinotaurStatus.VANISHED and 
        temporal_state.jump_duration <= 0):
        # Reappear at exact same coordinates
        temporal_state.minotaur_status = MinotaurStatus.CHASING_3D
    
    if (temporal_state.minotaur_status == MinotaurStatus.PARALYZED and 
        temporal_state.paralysis_duration <= 0):
        # End paralysis
        temporal_state.minotaur_status = MinotaurStatus.CHASING_3D
    
    # Check lantern respawn
    if (not temporal_state.lantern_available and 
        temporal_state.lantern_respawn_cooldown <= 0):
        temporal_state.lantern_available = True
    
    return temporal_state


def apply_lantern_use(temporal_state: TemporalState) -> tuple[TemporalState, bool]:
    """
    Apply lantern use: if lantern available, set minotaur status=PARALYZED for 120s;
    enforce single lantern in world; start lantern respawn cooldown=720s.
    Returns (updated_state, success).
    """
    if not temporal_state.lantern_available:
        return temporal_state, False
    
    # Only paralyze if minotaur is not already paralyzed or vanished
    if temporal_state.minotaur_status == MinotaurStatus.CHASING_3D:
        temporal_state.minotaur_status = MinotaurStatus.PARALYZED
        temporal_state.paralysis_duration = 120.0  # 2 minutes paralysis
    
    # Consume lantern and start respawn timer
    temporal_state.lantern_available = False
    temporal_state.lantern_respawn_cooldown = 720.0  # 12 minutes respawn
    
    return temporal_state, True


def get_minotaur_reentry_position(temporal_state: TemporalState) -> tuple[int, int, int]:
    """Get the exact coordinates where minotaur should reappear after vanishing."""
    return (temporal_state.vanish_position_x, 
            temporal_state.vanish_position_y, 
            temporal_state.vanish_position_z)


# Legacy functions for backward compatibility
def tick(state: LabyrinthState, rng: Optional[random.Random] = None) -> LabyrinthState:
    """
    Advance the global state by one tick.
    """
    r = rng or random.Random(state.seed)
    state.tick += 1

    # Simple stochastic event: artifacts may vanish
    for room in state.rooms:
        if room.has_artifact and r.random() < 0.02:
            room.has_artifact = False
    return state


def random_room(state: LabyrinthState, rng: Optional[random.Random] = None) -> Optional[Room]:
    r = rng or random.Random(state.seed)
    return r.choice(state.rooms) if state.rooms else None
