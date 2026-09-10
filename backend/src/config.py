from dataclasses import dataclass

@dataclass
class Config:
    MIN_EV: float = 5.0
    MIN_EDGE: float = 2.0
    KELLY_MULT: float = 0.25
    MAX_STAKE: float = 2.0
    DQ_GATE: int = 50
    SMART_MONEY_SHIFT: float = 0.08
    SMART_MONEY_MIN_PCT: int = 65
    RHO_RANGE: tuple = (-0.20, 0.20)
    TIMEZONE: str = "Europe/Rome"

config = Config()
