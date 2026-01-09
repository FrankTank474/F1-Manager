from dataclasses import dataclass
from enum import Enum


class TrackType(Enum):
    STREET = "street"
    HIGH_DOWNFORCE = "high_downforce"
    POWER = "power"
    BALANCED = "balanced"


@dataclass
class Track:
    name: str
    country: str
    city: str
    track_type: TrackType
    laps: int
    base_lap_time: float  # Base lap time in seconds
    pit_loss_time: float  # Time lost for pit stop in seconds
    overtaking_difficulty: int  # 1-10 (1 = easy, 10 = very hard)
    tire_degradation: float  # Multiplier for tire wear (0.5-2.0)
    drs_zones: int  # Number of DRS zones

    def __str__(self) -> str:
        return f"{self.name} - {self.city}, {self.country}"

    def get_info_display(self) -> str:
        type_str = self.track_type.value.replace("_", " ").title()

        # Show which car attributes matter most at this track
        if self.track_type == TrackType.HIGH_DOWNFORCE:
            key_attrs = "DOWNFORCE crucial, Chassis important"
        elif self.track_type == TrackType.POWER:
            key_attrs = "POWER UNIT crucial, Aero Efficiency helps"
        elif self.track_type == TrackType.STREET:
            key_attrs = "CHASSIS crucial, Downforce important"
        else:  # BALANCED
            key_attrs = "All-round car needed, Aero Efficiency key"

        return (
            f"{'=' * 55}\n"
            f"  {self.name}\n"
            f"  {self.city}, {self.country}\n"
            f"{'=' * 55}\n"
            f"  Type: {type_str}\n"
            f"  Laps: {self.laps}\n"
            f"  DRS Zones: {self.drs_zones}\n"
            f"  Overtaking: {'Easy' if self.overtaking_difficulty <= 3 else 'Medium' if self.overtaking_difficulty <= 6 else 'Hard'}\n"
            f"  Tire Wear: {'Low' if self.tire_degradation < 1.0 else 'Medium' if self.tire_degradation < 1.3 else 'High'}\n"
            f"  Key Attributes: {key_attrs}"
        )

    def get_downforce_bonus(self) -> float:
        """Returns how much downforce matters at this track."""
        if self.track_type == TrackType.HIGH_DOWNFORCE:
            return 1.3
        elif self.track_type == TrackType.STREET:
            return 1.2
        elif self.track_type == TrackType.POWER:
            return 0.8
        return 1.0

    def get_power_bonus(self) -> float:
        """Returns how much power matters at this track."""
        if self.track_type == TrackType.POWER:
            return 1.3
        elif self.track_type == TrackType.STREET:
            return 0.8
        elif self.track_type == TrackType.HIGH_DOWNFORCE:
            return 0.9
        return 1.0
