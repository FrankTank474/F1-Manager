"""News Feed & Headlines System - Generate dramatic post-race headlines"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Driver, Team


class HeadlineType(Enum):
    VICTORY = "Victory"
    UPSET = "Upset"
    PODIUM = "Podium"
    RIVALRY = "Rivalry"
    CRASH = "Crash"
    COMEBACK = "Comeback"
    DISAPPOINTMENT = "Disappointment"
    CHAMPIONSHIP = "Championship"
    RISING_STAR = "Rising Star"
    RETIREMENT = "Retirement"
    CONTROVERSY = "Controversy"


@dataclass
class Headline:
    headline_type: HeadlineType
    title: str
    subtitle: str = ""
    priority: int = 1  # 1-5, higher = more important


class NewsGenerator:
    def __init__(self):
        self.season_headlines: List[Headline] = []

    def generate_race_headlines(
        self,
        race_results: List[Tuple['Driver', 'Team', int]],
        track_name: str,
        qualifying_positions: Dict[str, int],
        incidents: List[str],
        rivalries: List[Tuple[str, str, int]],
        championship_leader: str,
        championship_gap: int,
        player_team_name: str
    ) -> List[Headline]:
        """Generate headlines for a completed race."""
        headlines = []

        # Get winner info
        winner = None
        winner_team = None
        for driver, team, pos in race_results:
            if pos == 1:
                winner = driver
                winner_team = team
                break

        if not winner:
            return headlines

        # === VICTORY HEADLINES ===
        quali_pos = qualifying_positions.get(winner.name, 1)

        # Check if it's an upset victory
        if winner_team and winner_team.car.overall < 75:
            headlines.append(Headline(
                headline_type=HeadlineType.UPSET,
                title=f"SHOCK! {winner.name} wins at {track_name}!",
                subtitle=f"Underdog {winner_team.name} stuns the field",
                priority=5
            ))
        elif quali_pos >= 10:
            headlines.append(Headline(
                headline_type=HeadlineType.COMEBACK,
                title=f"INCREDIBLE! {winner.name} wins from P{quali_pos}!",
                subtitle=f"Sensational drive at {track_name}",
                priority=5
            ))
        elif quali_pos >= 5:
            headlines.append(Headline(
                headline_type=HeadlineType.COMEBACK,
                title=f"{winner.name} storms to victory from P{quali_pos}",
                subtitle=f"Strategic masterclass at {track_name}",
                priority=4
            ))
        else:
            victory_templates = [
                f"{winner.name} triumphs at {track_name}",
                f"{winner.name} takes victory in {track_name}",
                f"{winner.name} wins at {track_name}",
                f"Dominant {winner.name} wins {track_name} GP",
            ]
            headlines.append(Headline(
                headline_type=HeadlineType.VICTORY,
                title=random.choice(victory_templates),
                subtitle=f"{winner_team.name if winner_team else 'Unknown'} celebrates",
                priority=3
            ))

        # === PODIUM HEADLINES ===
        podium_drivers = []
        for driver, team, pos in race_results:
            if pos in [2, 3]:
                podium_drivers.append((driver, team, pos))

        for driver, team, pos in podium_drivers:
            quali_pos = qualifying_positions.get(driver.name, pos)
            if quali_pos >= 10 and team.car.overall < 80:
                headlines.append(Headline(
                    headline_type=HeadlineType.UPSET,
                    title=f"P{pos}! {driver.name} scores shock podium!",
                    subtitle=f"{team.name} punches above their weight",
                    priority=4
                ))

        # === DISAPPOINTMENT HEADLINES ===
        for driver, team, pos in race_results:
            quali_pos = qualifying_positions.get(driver.name, pos)
            if quali_pos <= 3 and pos > 10:
                headlines.append(Headline(
                    headline_type=HeadlineType.DISAPPOINTMENT,
                    title=f"Disaster for {driver.name}",
                    subtitle=f"From P{quali_pos} to P{pos} at {track_name}",
                    priority=3
                ))
            elif quali_pos == 1 and pos > 5:
                headlines.append(Headline(
                    headline_type=HeadlineType.DISAPPOINTMENT,
                    title=f"{driver.name} loses pole advantage",
                    subtitle=f"Pole sitter finishes P{pos}",
                    priority=3
                ))

        # === DNF HEADLINES ===
        dnfs = [(d, t) for d, t, p in race_results if p == 0]
        if len(dnfs) >= 4:
            headlines.append(Headline(
                headline_type=HeadlineType.CRASH,
                title=f"Carnage at {track_name}!",
                subtitle=f"{len(dnfs)} drivers fail to finish",
                priority=4
            ))
        for driver, team in dnfs:
            if driver.season_points > 100:  # Top driver DNF
                headlines.append(Headline(
                    headline_type=HeadlineType.DISAPPOINTMENT,
                    title=f"Heartbreak for {driver.name}",
                    subtitle=f"Championship contender retires at {track_name}",
                    priority=3
                ))

        # === RIVALRY HEADLINES ===
        for d1, d2, intensity in rivalries:
            if intensity >= 60:
                headlines.append(Headline(
                    headline_type=HeadlineType.RIVALRY,
                    title=f"{d1} vs {d2}: The feud continues!",
                    subtitle="Intense battle at " + track_name,
                    priority=3
                ))

        # === PLAYER TEAM HEADLINES ===
        player_results = [(d, p) for d, t, p in race_results if t.name == player_team_name and p > 0]
        if player_results:
            best_pos = min(p for _, p in player_results)
            best_driver = next(d for d, p in player_results if p == best_pos)

            if best_pos == 1:
                headlines.append(Headline(
                    headline_type=HeadlineType.VICTORY,
                    title=f"YOUR TEAM WINS! {best_driver.name} victorious!",
                    subtitle=f"Historic win for {player_team_name}",
                    priority=5
                ))
            elif best_pos <= 3:
                headlines.append(Headline(
                    headline_type=HeadlineType.PODIUM,
                    title=f"PODIUM! {best_driver.name} finishes P{best_pos}!",
                    subtitle=f"Great result for {player_team_name}",
                    priority=4
                ))
            elif best_pos <= 6:
                headlines.append(Headline(
                    headline_type=HeadlineType.PODIUM,
                    title=f"Points finish for {player_team_name}",
                    subtitle=f"{best_driver.name} secures P{best_pos}",
                    priority=2
                ))

        # === CHAMPIONSHIP HEADLINES ===
        if championship_gap <= 10:
            headlines.append(Headline(
                headline_type=HeadlineType.CHAMPIONSHIP,
                title=f"Title race goes down to the wire!",
                subtitle=f"Just {championship_gap} points in it",
                priority=4
            ))
        elif championship_gap <= 30:
            headlines.append(Headline(
                headline_type=HeadlineType.CHAMPIONSHIP,
                title=f"{championship_leader} extends championship lead",
                subtitle=f"Now {championship_gap} points clear",
                priority=2
            ))

        # === RISING STAR HEADLINES ===
        for driver, team, pos in race_results:
            if driver.age <= 23 and pos <= 5 and team.car.overall < 80:
                headlines.append(Headline(
                    headline_type=HeadlineType.RISING_STAR,
                    title=f"Star in the making: {driver.name}",
                    subtitle=f"{driver.age}-year-old shines with P{pos}",
                    priority=3
                ))

        # Sort by priority and return top headlines
        headlines.sort(key=lambda h: h.priority, reverse=True)
        self.season_headlines.extend(headlines[:5])

        return headlines[:5]

    def generate_season_end_headlines(
        self,
        driver_champion: str,
        driver_champion_team: str,
        constructor_champion: str,
        player_team_name: str,
        player_position: int,
        notable_moments: List[str]
    ) -> List[Headline]:
        """Generate headlines for end of season."""
        headlines = []

        # Champion headline
        headlines.append(Headline(
            headline_type=HeadlineType.CHAMPIONSHIP,
            title=f"{driver_champion} IS WORLD CHAMPION!",
            subtitle=f"{driver_champion_team} driver claims the title",
            priority=5
        ))

        # Constructor champion
        headlines.append(Headline(
            headline_type=HeadlineType.CHAMPIONSHIP,
            title=f"{constructor_champion} wins Constructors' Championship",
            subtitle="Season-long effort pays off",
            priority=4
        ))

        # Player team result
        if player_position == 1:
            headlines.append(Headline(
                headline_type=HeadlineType.CHAMPIONSHIP,
                title=f"GLORY! {player_team_name} ARE CHAMPIONS!",
                subtitle="Your journey to the top is complete!",
                priority=5
            ))
        elif player_position <= 3:
            headlines.append(Headline(
                headline_type=HeadlineType.PODIUM,
                title=f"{player_team_name} secures P{player_position} in championship",
                subtitle="Strong season for the team",
                priority=3
            ))
        elif player_position <= 6:
            headlines.append(Headline(
                headline_type=HeadlineType.PODIUM,
                title=f"Solid season for {player_team_name}",
                subtitle=f"Team finishes P{player_position} in standings",
                priority=2
            ))

        return headlines

    def generate_transfer_headlines(
        self,
        transfers: List[Tuple[str, str, str, str]]  # (driver, old_team, new_team, reason)
    ) -> List[Headline]:
        """Generate headlines for transfer activity."""
        headlines = []

        for driver, old_team, new_team, reason in transfers:
            if old_team and new_team:
                headlines.append(Headline(
                    headline_type=HeadlineType.CONTROVERSY,
                    title=f"BREAKING: {driver} joins {new_team}!",
                    subtitle=f"Leaves {old_team} after {reason}",
                    priority=3
                ))
            elif new_team:
                headlines.append(Headline(
                    headline_type=HeadlineType.CONTROVERSY,
                    title=f"{driver} signs for {new_team}",
                    subtitle="Free agent finds new home",
                    priority=2
                ))
            elif old_team:
                headlines.append(Headline(
                    headline_type=HeadlineType.CONTROVERSY,
                    title=f"{driver} leaves {old_team}",
                    subtitle=f"Driver out: {reason}",
                    priority=2
                ))

        return headlines

    def display_headlines(self, headlines: List[Headline], title: str = "NEWS FEED") -> str:
        """Display headlines in a formatted way."""
        if not headlines:
            return ""

        lines = [
            "\n" + "=" * 70,
            f"  {title}",
            "=" * 70,
        ]

        for i, headline in enumerate(headlines[:5], 1):
            # Add visual priority indicator
            if headline.priority >= 5:
                marker = ">>> "
            elif headline.priority >= 4:
                marker = " >> "
            elif headline.priority >= 3:
                marker = "  > "
            else:
                marker = "    "

            lines.append(f"{marker}{headline.title}")
            if headline.subtitle:
                lines.append(f"      {headline.subtitle}")
            if i < len(headlines[:5]):
                lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def display_season_review(self) -> str:
        """Display the best headlines from the entire season."""
        if not self.season_headlines:
            return ""

        # Get top headlines by priority
        top_headlines = sorted(
            self.season_headlines,
            key=lambda h: h.priority,
            reverse=True
        )[:10]

        return self.display_headlines(top_headlines, "SEASON REVIEW - TOP STORIES")

    def clear_season(self) -> None:
        """Clear season headlines for new season."""
        self.season_headlines = []


class RaceSummaryGenerator:
    """Generate quick race summary text."""

    @staticmethod
    def generate_summary(
        winner: str,
        winner_team: str,
        track_name: str,
        incidents: int,
        safety_cars: int,
        red_flags: int,
        weather_changes: bool,
        closest_battle: Optional[Tuple[str, str]] = None
    ) -> str:
        """Generate a short race summary."""
        lines = []

        # Opening
        if red_flags > 0:
            lines.append(f"A dramatic and interrupted {track_name} Grand Prix saw")
        elif safety_cars >= 2:
            lines.append(f"A chaotic {track_name} Grand Prix featuring {safety_cars} safety cars saw")
        elif weather_changes:
            lines.append(f"A weather-affected {track_name} Grand Prix saw")
        elif incidents >= 3:
            lines.append(f"An action-packed {track_name} Grand Prix saw")
        else:
            lines.append(f"The {track_name} Grand Prix concluded with")

        # Winner
        lines.append(f"{winner} take victory for {winner_team}.")

        # Drama elements
        if closest_battle:
            lines.append(f"The battle between {closest_battle[0]} and {closest_battle[1]} was the highlight.")

        if incidents >= 4:
            lines.append(f"Multiple incidents brought out safety cars throughout the race.")
        elif safety_cars > 0:
            lines.append(f"A safety car period shook up the order mid-race.")

        return " ".join(lines)
