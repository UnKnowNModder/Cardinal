"""all the dataclass schema for tournament."""
from __future__ import annotations

from pydantic import BaseModel, Field

from server.enums import SeriesType, TournamentStage, TournamentType, Status


class SeasonSchema(BaseModel):
    """schema for a unique season."""

    series: SeriesType = SeriesType.BO3
    type: TournamentType = TournamentType.SOLO
    stage: TournamentStage = TournamentStage.REGISTRATION
    created_at: str = ""
    participant_role_id: int = 0


class TournamentSchema(BaseModel):
    """Schema for all the seasons."""

    active_season: str = "0"
    registrations_status: bool = False
    seasons: dict[str, SeasonSchema] = Field(default_factory=dict)

class TeamSchema(BaseModel):
    """schema for a team."""
    id: int
    name: str
    score: int = 0
    series: int = 0

class MatchSchema(BaseModel):
    """schema for a match."""
    teams: list[TeamSchema] = Field(default_factory=list)
    status: Status = Status.PENDING
    winner: TeamSchema | None = None
    loser: TeamSchema | None = None
    group_key: str | None = None
    round_key: str | None = None