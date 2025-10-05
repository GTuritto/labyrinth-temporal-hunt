from __future__ import annotations

import json
from enum import Enum
from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel, Field, ValidationError
from loguru import logger


class Direction(str, Enum):
    NORTH = "NORTH"
    SOUTH = "SOUTH"
    EAST = "EAST"
    WEST = "WEST"
    UP_RAMP = "UP RAMP"
    DOWN_RAMP = "DOWN RAMP"


class UserInput(BaseModel):
    command: Literal["MOVE", "HALT", "LOOK", "GRAB", "USE"]
    direction: Optional[Direction] = None
    steps: int = Field(default=100, ge=1)
    speed: Literal[1, 2] = 1
    target: Optional[Literal["RED STONE", "BLUE STONE", "YELLOW STONE", "LANTERN"]] = None


class MinotaurDecision(BaseModel):
    action: Literal["PATHFIND", "JUMP", "WAIT", "CHASE"]
    target_coords: Optional[Dict[Literal["x", "y", "z"], int]] = None


class GameStateResponse(BaseModel):
    model_config = {"extra": "forbid"}  # Pydantic v2 way to reject unexpected keys
    
    status: str
    user_state: Dict[str, Any]
    environment: Dict[str, Any]
    minotaur_cue: str
    raw_text_output: str


# Legacy models for backward compatibility
class Hunter(BaseModel):
    id: str
    stamina: float = Field(ge=0.0, default=100.0)
    wisdom: float = Field(ge=0.0, default=50.0)
    inventory: List[str] = Field(default_factory=list)


class Minotaur(BaseModel):
    id: str
    ferocity: float = Field(ge=0.0, default=75.0)
    cunning: float = Field(ge=0.0, default=60.0)


class Room(BaseModel):
    id: str
    connections: List[str] = Field(default_factory=list)
    has_trap: bool = False
    has_artifact: bool = False


class LabyrinthState(BaseModel):
    tick: int = 0
    rooms: List[Room] = Field(default_factory=list)
    hunter: Optional[Hunter] = None
    minotaur: Optional[Minotaur] = None
    seed: Optional[int] = None


def parse_user_input_json(raw: str) -> UserInput:
    """
    Parse JSON string to UserInput with robust validation.
    On error, return safe default LOOK command.
    """
    try:
        data = json.loads(raw)
        return UserInput.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError) as e:
        logger.warning(f"Failed to parse user input JSON: {e}. Using default LOOK command.")
        return UserInput(command="LOOK")


def parse_minotaur_decision_json(raw: str) -> MinotaurDecision:
    """
    Parse JSON string to MinotaurDecision with robust validation.
    On error, return safe default WAIT action.
    """
    try:
        data = json.loads(raw)
        return MinotaurDecision.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError) as e:
        logger.warning(f"Failed to parse minotaur decision JSON: {e}. Using default WAIT action.")
        return MinotaurDecision(action="WAIT")
