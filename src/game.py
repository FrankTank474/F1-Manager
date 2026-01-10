"""Core Game State Management"""

import json
import os
import random
from typing import List, Optional, Dict, Any
from pathlib import Path

from .models import Driver, DriverStats, Car, Team, Track, TrackType
from .data import F1_DRIVERS, F2_DRIVERS, AI_TEAMS, TRACKS
from .systems import RaceEngine, DriverMarket, UpgradeSystem, StandingsManager, SponsorManager
from .systems import RivalryManager, NewsGenerator
from .systems.race_engine import TireCompound, Weather
from .ui import MenuSystem, clear_screen, press_enter_to_continue, get_int_input


class GameState:
    def __init__(self):
        self.player_team: Optional[Team] = None
        self.teams: List[Team] = []
        self.all_drivers: List[Driver] = []
        self.tracks: List[Track] = []
        self.current_season: int = 1
        self.current_race: int = 0
        self.standings_manager: Optional[StandingsManager] = None
        self.driver_market: Optional[DriverMarket] = None
        self.upgrade_system: Optional[UpgradeSystem] = None
        self.sponsor_manager: SponsorManager = SponsorManager()
        self.rivalry_manager: RivalryManager = RivalryManager()
        self.news_generator: NewsGenerator = NewsGenerator()

    def initialize_new_game(self, team_name: str) -> None:
        """Initialize a new game with player team."""
        # Create all drivers
        self._create_drivers()

        # Create AI teams
        self._create_ai_teams()

        # Create player team
        self._create_player_team(team_name)

        # Create tracks
        self._create_tracks()

        # Initialize systems
        self._initialize_systems()

    def _create_drivers(self) -> None:
        """Create all driver instances from data."""
        self.all_drivers = []

        # F1 Drivers
        for data in F1_DRIVERS:
            driver = Driver(
                name=data["name"],
                age=data["age"],
                nationality=data["nationality"],
                stats=DriverStats(**data["stats"]),
                salary=data["salary"],
                market_value=data["market_value"],
                team_name=data["team_name"]
            )
            self.all_drivers.append(driver)

        # F2 Drivers
        for data in F2_DRIVERS:
            driver = Driver(
                name=data["name"],
                age=data["age"],
                nationality=data["nationality"],
                stats=DriverStats(**data["stats"]),
                salary=data["salary"],
                market_value=data["market_value"],
                team_name=data.get("team_name")
            )
            self.all_drivers.append(driver)

    def _create_ai_teams(self) -> None:
        """Create AI team instances from data."""
        self.teams = []

        for data in AI_TEAMS:
            car = Car(**data["car"])
            team = Team(
                name=data["name"],
                budget=data["budget"],
                car=car,
                is_player_team=False
            )

            # Assign drivers to team
            for driver in self.all_drivers:
                if driver.team_name == team.name:
                    team.drivers.append(driver)

            self.teams.append(team)

    def _create_player_team(self, team_name: str) -> None:
        """Create the player's team."""
        car = Car(
            downforce=64,
            aero_efficiency=64,
            chassis=64,
            power_unit=64,
            reliability=64,
            tire_cooling=65
        )

        self.player_team = Team(
            name=team_name,
            budget=50,
            car=car,
            is_player_team=True
        )

        self.teams.append(self.player_team)

    def _create_tracks(self) -> None:
        """Create track instances from data."""
        self.tracks = []

        for data in TRACKS:
            track = Track(
                name=data["name"],
                country=data["country"],
                city=data["city"],
                track_type=TrackType(data["track_type"]),
                laps=data["laps"],
                base_lap_time=data["base_lap_time"],
                pit_loss_time=data["pit_loss_time"],
                overtaking_difficulty=data["overtaking_difficulty"],
                tire_degradation=data["tire_degradation"],
                drs_zones=data["drs_zones"]
            )
            self.tracks.append(track)

    def _initialize_systems(self) -> None:
        """Initialize game systems."""
        self.standings_manager = StandingsManager(self.teams, self.all_drivers, self.player_team)
        self.driver_market = DriverMarket(self.all_drivers, self.teams)
        self.upgrade_system = UpgradeSystem(self.player_team)

    def get_next_track(self) -> Optional[Track]:
        """Get the next track in the calendar."""
        if self.current_race < len(self.tracks):
            return self.tracks[self.current_race]
        return None

    def advance_race(self, race_results: List[tuple] = None) -> List[str]:
        """Move to the next race. Returns list of events (e.g., AI upgrades)."""
        self.current_race += 1
        messages = []

        # Give AI teams income from race results and sponsors
        if race_results:
            self.process_ai_race_income(race_results)
        self.process_ai_sponsor_income()

        # AI teams try to upgrade their cars every 5 races
        if self.current_race % 5 == 0:
            upgrade_messages = self.process_ai_car_upgrades()
            messages.extend(upgrade_messages)

        return messages

    def is_season_complete(self) -> bool:
        """Check if the season is complete."""
        return self.current_race >= len(self.tracks)

    def start_new_season(self) -> None:
        """Start a new season."""
        self.current_season += 1
        self.current_race = 0

        # Reset all team season stats
        for team in self.teams:
            team.reset_season_stats()

        # Reset ALL driver stats (including free agents not on teams)
        for driver in self.all_drivers:
            driver.reset_season_stats()

        # Clear season headlines
        self.news_generator.clear_season()

        # Ensure all AI teams have 2 drivers
        if self.driver_market:
            self.driver_market.ensure_all_teams_have_drivers(self.player_team)

    def process_ai_race_income(self, race_results: List[tuple]) -> None:
        """
        Give AI teams income from race results.
        race_results: List of (driver, team, position)
        """
        from .systems.standings import RACE_PRIZE_MONEY

        for driver, team, position in race_results:
            if team != self.player_team and position > 0:
                prize = RACE_PRIZE_MONEY.get(position, 0.25)
                team.add_income(prize)

    def process_ai_sponsor_income(self) -> None:
        """
        Give AI teams sponsor income based on their tier.
        Top teams get more sponsor money, backmarkers get less.
        Called once per race.
        """
        for team in self.teams:
            if team == self.player_team:
                continue

            # Sponsor income based on car performance (proxy for team prestige)
            car_rating = team.car.overall
            if car_rating >= 85:
                # Top teams - major sponsors
                sponsor_income = random.uniform(2.0, 4.0)
            elif car_rating >= 75:
                # Upper midfield
                sponsor_income = random.uniform(1.2, 2.5)
            elif car_rating >= 65:
                # Midfield
                sponsor_income = random.uniform(0.8, 1.5)
            else:
                # Backmarkers
                sponsor_income = random.uniform(0.4, 1.0)

            team.add_income(sponsor_income)

    def process_ai_car_upgrades(self) -> List[str]:
        """
        AI teams upgrade their cars if they have enough budget.
        They prioritize their weakest stats and spend aggressively.
        In last 7 races, they save money for driver transfers.
        Returns list of upgrade messages.
        """
        messages = []
        races_remaining = len(self.tracks) - self.current_race

        for team in self.teams:
            if team == self.player_team:
                continue

            car = team.car

            # In last 7 races, save money for transfers - only upgrade if very rich
            if races_remaining <= 7:
                min_budget_to_upgrade = 50  # Need $50M+ to upgrade in transfer window
            else:
                min_budget_to_upgrade = 10  # More aggressive spending during season

            if team.budget < min_budget_to_upgrade:
                continue

            upgraded_any = False

            # Find weakest stat
            stats = ['downforce', 'aero_efficiency', 'chassis', 'power_unit', 'reliability', 'tire_cooling']
            stat_values = [(s, getattr(car, s)) for s in stats]
            stat_values.sort(key=lambda x: x[1])  # Sort by value ascending

            # Try to upgrade weakest stats (up to 3 upgrades per cycle if they can afford it)
            upgrades_done = 0
            max_upgrades = 3 if races_remaining > 7 else 1

            for stat_name, current_value in stat_values:
                if upgrades_done >= max_upgrades:
                    break
                if current_value >= 99:
                    continue

                # Calculate upgrade cost
                upgrade_cost = car.get_upgrade_cost(stat_name, 1)

                # AI teams spend if they have enough (keep small reserve)
                reserve_needed = 15 if races_remaining > 7 else 40
                if team.budget >= upgrade_cost + reserve_needed:
                    team.spend(upgrade_cost)
                    car.upgrade_stat(stat_name, 1)
                    upgraded_any = True
                    upgrades_done += 1

            if upgraded_any:
                messages.append(f"{team.name} developed their car (Budget: ${team.budget:.1f}M)")

        return messages

    def process_end_of_season_transfers(self) -> List[str]:
        """Process AI transfers at end of season."""
        if self.driver_market:
            return self.driver_market.process_ai_transfers(self.player_team)
        return []

    def process_rising_stars(self, race_results: List[tuple]) -> List[str]:
        """
        Check for rising star status after a race.
        Young drivers who outperform their car get rising star boost.
        Returns list of messages about rising stars.
        """
        messages = []

        for driver, team, position in race_results:
            if position <= 0:  # DNF
                continue

            car_rating = team.car.overall

            # Check if this triggers rising star
            if driver.check_rising_star(position, car_rating):
                messages.append(f"RISING STAR: {driver.name} ({driver.age}) is on fire! (+5 races growth boost)")

            # Apply growth if already a rising star
            if driver.rising_star_races > 0:
                growth = driver.apply_rising_star_growth()
                if growth:
                    for stat, old, new in growth:
                        messages.append(f"  {driver.name}: {stat.replace('_', ' ').title()} {old} -> {new}")

                # Tick down the rising star counter
                driver.tick_rising_star()

        return messages

    def get_player_constructor_position(self) -> int:
        """Get player's position in constructor standings."""
        standings = self.standings_manager.get_constructor_standings()
        for pos, team in standings:
            if team == self.player_team:
                return pos
        return len(self.teams) + 1

    def apply_season_prize_money(self) -> int:
        """Apply prize money at end of season. Returns amount for player."""
        standings = self.standings_manager.get_constructor_standings()

        player_prize = 0
        for pos, team in standings:
            prize = team.get_season_prize_money(pos)
            team.add_income(prize)
            if team == self.player_team:
                player_prize = prize

        return player_prize

    def save_game(self, filename: str = "savegame.json") -> bool:
        """Save game state to file."""
        save_path = Path(__file__).parent.parent / filename

        save_data = {
            "player_team_name": self.player_team.name,
            "player_budget": self.player_team.budget,
            "player_car": {
                "downforce": self.player_team.car.downforce,
                "aero_efficiency": self.player_team.car.aero_efficiency,
                "chassis": self.player_team.car.chassis,
                "power_unit": self.player_team.car.power_unit,
                "reliability": self.player_team.car.reliability,
                "tire_cooling": self.player_team.car.tire_cooling
            },
            "player_drivers": [d.name for d in self.player_team.drivers],
            "player_season_points": self.player_team.season_points,
            "current_season": self.current_season,
            "current_race": self.current_race,
            "driver_points": {d.name: d.season_points for d in self.all_drivers},
            "team_points": {t.name: t.season_points for t in self.teams}
        }

        try:
            with open(save_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving game: {e}")
            return False

    def load_game(self, filename: str = "savegame.json") -> bool:
        """Load game state from file."""
        save_path = Path(__file__).parent.parent / filename

        if not save_path.exists():
            return False

        try:
            with open(save_path, 'r') as f:
                save_data = json.load(f)

            # Initialize with saved team name
            self.initialize_new_game(save_data["player_team_name"])

            # Restore player state
            self.player_team.budget = save_data["player_budget"]
            self.player_team.car.downforce = save_data["player_car"]["downforce"]
            self.player_team.car.aero_efficiency = save_data["player_car"]["aero_efficiency"]
            self.player_team.car.chassis = save_data["player_car"]["chassis"]
            self.player_team.car.power_unit = save_data["player_car"]["power_unit"]
            self.player_team.car.reliability = save_data["player_car"]["reliability"]
            self.player_team.car.tire_cooling = save_data["player_car"].get("tire_cooling", 65)
            self.player_team.season_points = save_data.get("player_season_points", 0)

            # Restore drivers
            self.player_team.drivers = []
            for driver_name in save_data["player_drivers"]:
                for driver in self.all_drivers:
                    if driver.name == driver_name:
                        # Remove from current team if any
                        for team in self.teams:
                            if driver in team.drivers:
                                team.drivers.remove(driver)
                        driver.team_name = self.player_team.name
                        self.player_team.drivers.append(driver)
                        break

            # Restore season state
            self.current_season = save_data["current_season"]
            self.current_race = save_data["current_race"]

            # Restore points
            for driver in self.all_drivers:
                if driver.name in save_data.get("driver_points", {}):
                    driver.season_points = save_data["driver_points"][driver.name]

            for team in self.teams:
                if team.name in save_data.get("team_points", {}):
                    team.season_points = save_data["team_points"][team.name]

            # Re-initialize upgrade system with loaded car
            self.upgrade_system = UpgradeSystem(self.player_team)

            return True
        except Exception as e:
            print(f"Error loading game: {e}")
            return False


class Game:
    def __init__(self):
        self.state = GameState()
        self.menu = MenuSystem()
        self.running = True

    def run(self) -> None:
        """Main game loop."""
        while self.running:
            choice = self.menu.display_start_menu()

            if choice == '1':
                self._start_new_game()
            elif choice == '2':
                self._load_game()
            elif choice == '3':
                self.running = False
                print("\n  Thanks for playing F1 Manager 2026!")
                return

    def _start_new_game(self) -> None:
        """Start a new game."""
        team_name = self.menu.display_new_game_menu()

        if not team_name:
            team_name = "New Team"

        self.state.initialize_new_game(team_name)

        # Force player to sign drivers
        self._initial_driver_signing()

        # Offer sponsor selection
        clear_screen()
        print("\n  SPONSOR SELECTION")
        print("  Sponsors pay you money when you meet race objectives!")
        if MenuSystem.confirm_action("Would you like to review sponsor offers?"):
            self._select_sponsor()

        # Enter main game loop
        self._main_game_loop()

    def _load_game(self) -> None:
        """Load an existing game."""
        if self.state.load_game():
            self.menu.display_success("Game loaded successfully!")
            self._main_game_loop()
        else:
            self.menu.display_error("No save file found or failed to load.")

    def _initial_driver_signing(self) -> None:
        """Handle initial driver signing at game start."""
        while len(self.state.player_team.drivers) < 2:
            clear_screen()
            remaining = 2 - len(self.state.player_team.drivers)
            print(f"\n  You need to sign {remaining} more driver(s) to complete your lineup.")
            print(self.state.driver_market.display_market(self.state.player_team.budget))

            driver_num = get_int_input(
                f"\n  Enter driver number to sign (1-{len(self.state.driver_market.get_available_drivers())}): ",
                1, len(self.state.driver_market.get_available_drivers())
            )

            if driver_num == -1:
                if len(self.state.player_team.drivers) < 2:
                    print("\n  You must sign 2 drivers before continuing!")
                    press_enter_to_continue()
                    continue
                break

            drivers = self.state.driver_market.get_available_drivers()
            if 0 < driver_num <= len(drivers):
                selected_driver = drivers[driver_num - 1]
                print(self.state.driver_market.display_driver_details(selected_driver))

                if MenuSystem.confirm_action(f"Sign {selected_driver.name} for ${selected_driver.market_value}M?"):
                    success, message = self.state.driver_market.sign_driver(
                        self.state.player_team, selected_driver
                    )
                    if success:
                        self.menu.display_success(message)
                    else:
                        self.menu.display_error(message)

    def _main_game_loop(self) -> None:
        """Main game menu loop."""
        while self.running:
            choice = self.menu.display_main_menu(
                self.state.player_team.name,
                self.state.player_team.budget,
                self.state.current_season,
                self.state.current_race + 1,
                len(self.state.tracks)
            )

            if choice == '1':
                self._race_weekend()
            elif choice == '2':
                self._fast_forward_races()
            elif choice == '3':
                self._view_driver_standings()
            elif choice == '4':
                self._view_constructor_standings()
            elif choice == '5':
                self._team_management()
            elif choice == '6':
                self._view_calendar()
            elif choice == '7':
                self._save_game()
            elif choice == '8':
                if MenuSystem.confirm_action("Are you sure you want to quit?"):
                    self.running = False
                    return

    def _fast_forward_races(self) -> None:
        """Handle fast-forward simulation of multiple races."""
        if len(self.state.player_team.drivers) < 2:
            self.menu.display_error("You need 2 drivers to race! Go to Team Management to sign drivers.")
            return

        total_races = len(self.state.tracks)
        remaining = total_races - self.state.current_race

        if remaining == 0:
            self._end_season()
            return

        choice = self.menu.display_fast_forward_menu(self.state.current_race, total_races)

        if choice.lower() == 'b':
            return

        # Determine how many races to simulate
        races_map = {'1': 3, '2': 5, '3': 10, '4': remaining}
        races_to_simulate = min(races_map.get(choice, 0), remaining)

        if races_to_simulate == 0:
            return

        # Confirm action
        if not MenuSystem.confirm_action(f"Simulate {races_to_simulate} race(s)? Your team will use AI pit strategy."):
            return

        clear_screen()
        print(f"\n  FAST FORWARD MODE - Simulating {races_to_simulate} races...")
        print("=" * 60)

        # Store results for summary
        race_summaries = []
        total_prize_earned = 0.0

        for i in range(races_to_simulate):
            track = self.state.get_next_track()
            if not track:
                break

            print(f"\n  Race {i+1}/{races_to_simulate}: {track.name}...")

            # Create race engine and run qualifying
            race_engine = RaceEngine(track, self.state.teams, self.state.player_team, self.state.rivalry_manager)
            race_engine.run_qualifying()

            # Run quick race (fully automated)
            results = race_engine.run_quick_race()

            # Update standings
            self.state.standings_manager.update_race_results(results)

            # Calculate prize money
            total_prize, driver_prizes = self.state.standings_manager.calculate_race_prize_money(results)
            if total_prize > 0:
                self.state.player_team.budget += total_prize
                total_prize_earned += total_prize

            # Check sponsor objective
            sponsor_payment = 0.0
            sponsor_met = False
            if self.state.sponsor_manager.current_sponsor:
                best_finish = 99
                for driver, team, position in results:
                    if team == self.state.player_team and position > 0:
                        best_finish = min(best_finish, position)
                if best_finish == 99:
                    best_finish = 0
                sponsor_met, sponsor_payment = self.state.sponsor_manager.check_race_objective(best_finish)
                if sponsor_payment > 0:
                    self.state.player_team.budget += sponsor_payment
                    total_prize_earned += sponsor_payment

            # Process rising stars (silent in fast-forward)
            self.state.process_rising_stars(results)

            # Advance rivalry manager
            self.state.rivalry_manager.advance_race()

            # Track incidents for summary
            incident_count = len(race_engine.race_incidents) if hasattr(race_engine, 'race_incidents') else 0

            # Get player results for summary
            player_results = []
            for driver, team, position in results:
                if team == self.state.player_team:
                    if position > 0:
                        player_results.append((driver.name, position))
                    else:
                        player_results.append((driver.name, "DNF"))

            race_summaries.append({
                'track': track.name,
                'results': player_results,
                'prize': total_prize,
                'sponsor_met': sponsor_met,
                'sponsor_pay': sponsor_payment,
                'incidents': incident_count
            })

            print(f"    Done! ", end="")
            for name, pos in player_results:
                pos_str = f"P{pos}" if isinstance(pos, int) else pos
                print(f"{name}: {pos_str}  ", end="")
            print()

            # Advance to next race (pass results for AI income)
            ai_upgrade_messages = self.state.advance_race(results)

            # Show AI upgrades during fast-forward
            if ai_upgrade_messages:
                print("\n    AI TEAM DEVELOPMENTS:")
                for msg in ai_upgrade_messages:
                    print(f"      {msg}")

            # Check if season complete
            if self.state.is_season_complete():
                break

        # Display summary
        clear_screen()
        print("\n" + "=" * 70)
        print("  FAST FORWARD SUMMARY")
        print("=" * 70)
        print(f"  {'Race':<35} {'Driver 1':<15} {'Driver 2':<15}")
        print("-" * 70)

        for summary in race_summaries:
            results_strs = []
            for name, pos in summary['results']:
                pos_str = f"P{pos}" if isinstance(pos, int) else pos
                results_strs.append(f"{name[:12]}: {pos_str}")

            while len(results_strs) < 2:
                results_strs.append("-")

            print(f"  {summary['track']:<35} {results_strs[0]:<15} {results_strs[1]:<15}")

        print("-" * 70)
        print(f"  Total Prize Money Earned: ${total_prize_earned:.2f}M")
        print(f"  New Budget: ${self.state.player_team.budget:.1f}M")
        print("=" * 70)

        press_enter_to_continue()

        # Show updated standings
        print(self.state.standings_manager.display_driver_standings())
        print(self.state.standings_manager.display_constructor_standings())
        press_enter_to_continue()

        # Check if season ended
        if self.state.is_season_complete():
            self._end_season()

    def _race_weekend(self) -> None:
        """Handle a race weekend."""
        if len(self.state.player_team.drivers) < 2:
            self.menu.display_error("You need 2 drivers to race! Go to Team Management to sign drivers.")
            return

        track = self.state.get_next_track()
        if not track:
            self._end_season()
            return

        # Show track info
        self.menu.display_race_weekend_intro(
            track.get_info_display(),
            self.state.current_race + 1,
            len(self.state.tracks)
        )

        # Create race engine with rivalry manager
        race_engine = RaceEngine(track, self.state.teams, self.state.player_team, self.state.rivalry_manager)

        # Qualifying
        clear_screen()
        print("\n  QUALIFYING SESSION IN PROGRESS...")
        race_engine.run_qualifying()
        print(race_engine.display_qualifying_results())
        press_enter_to_continue()

        # Tire selection
        tire_choice = self.menu.display_tire_selection("Dry")
        tire_map = {'1': TireCompound.SOFT, '2': TireCompound.MEDIUM, '3': TireCompound.HARD}
        starting_tire = tire_map.get(tire_choice, TireCompound.MEDIUM)

        # Initialize race
        race_engine.initialize_race(starting_tire)

        # Race start
        clear_screen()
        print("\n  LIGHTS OUT AND AWAY WE GO!")
        race_engine._simulate_race_start()
        press_enter_to_continue()

        # Race simulation with pit stop prompts
        while race_engine.race_state.current_lap < race_engine.race_state.total_laps:
            events = race_engine._simulate_lap()
            ai_events = race_engine.simulate_ai_pits()

            # Show status every 5 laps or on events
            if race_engine.race_state.current_lap % 5 == 0 or events or ai_events:
                clear_screen()
                print(race_engine.get_race_status())

                for event in events + ai_events:
                    print(f"  {event}")

                # Check for pit stop prompt
                pit_info_list = race_engine.get_player_pit_prompt()
                if pit_info_list:
                    # Show full race standings first
                    clear_screen()
                    print(race_engine.get_race_status())

                    compound_map = {
                        '1': TireCompound.SOFT,
                        '2': TireCompound.MEDIUM,
                        '3': TireCompound.HARD,
                        '4': TireCompound.INTERMEDIATE,
                        '5': TireCompound.WET
                    }

                    # Handle each driver individually
                    for pit_info in pit_info_list:
                        choice = self.menu.display_pit_stop_prompt(
                            pit_info["driver"],
                            pit_info["tire_wear"],
                            pit_info["current_compound"],
                            pit_info["weather"],
                            pit_info["position"],
                            pit_info["laps_remaining"],
                            pit_info.get("grip_level", "GOOD")
                        )

                        if choice.lower() == 'e':
                            # Stay out until end - no more prompts for this driver
                            race_engine.set_driver_no_pit_prompts(pit_info["driver"])
                            print(f"  {pit_info['driver']} will stay out until the end of the race.")
                            press_enter_to_continue()
                        elif choice != 's' and choice != 'S':
                            if choice in compound_map:
                                result = race_engine.pit_driver(pit_info["driver"], compound_map[choice])
                                print(f"  {result}")
                                press_enter_to_continue()

        # Race complete - show results
        clear_screen()
        results = race_engine.get_final_results()
        self.state.standings_manager.update_race_results(results)
        print(race_engine.display_race_results())

        # Calculate and award race prize money
        total_prize, driver_prizes = self.state.standings_manager.calculate_race_prize_money(results)
        if total_prize > 0:
            self.state.player_team.budget += total_prize
            print("\n" + "-" * 50)
            print("  RACE PRIZE MONEY EARNED")
            print("-" * 50)
            for driver_name, position, prize in driver_prizes:
                print(f"  P{position} {driver_name}: ${prize:.2f}M")
            print("-" * 50)
            print(f"  Total Earned: ${total_prize:.2f}M")
            print(f"  New Budget: ${self.state.player_team.budget:.1f}M")
            print("-" * 50)

        # Check sponsor objective
        if self.state.sponsor_manager.current_sponsor:
            # Get best finish from player team
            best_finish = 99
            for driver, team, position in results:
                if team == self.state.player_team and position > 0:
                    best_finish = min(best_finish, position)
            if best_finish == 99:
                best_finish = 0  # Both DNF'd

            met, payment = self.state.sponsor_manager.check_race_objective(best_finish)
            print("\n" + "-" * 50)
            print("  SPONSOR OBJECTIVE")
            print("-" * 50)
            sponsor = self.state.sponsor_manager.current_sponsor
            print(f"  {sponsor.name}: {sponsor.objective.description}")
            if met:
                self.state.player_team.budget += payment
                print(f"  OBJECTIVE MET! Earned ${payment:.2f}M")
                print(f"  New Budget: ${self.state.player_team.budget:.1f}M")
            else:
                print(f"  Objective NOT met. No sponsor payment.")
            print("-" * 50)

        # Check for rising stars
        rising_star_messages = self.state.process_rising_stars(results)
        if rising_star_messages:
            print("\n" + "-" * 50)
            print("  YOUNG DRIVER DEVELOPMENT")
            print("-" * 50)
            for msg in rising_star_messages:
                print(f"  {msg}")
            print("-" * 50)

        # Show incident summary if there were incidents
        if race_engine.race_incidents:
            print("\n" + "-" * 50)
            print("  RACE INCIDENTS")
            print("-" * 50)
            for incident in race_engine.race_incidents[:5]:  # Show max 5
                flag_info = ""
                if incident.causes_red_flag:
                    flag_info = " [RED FLAG]"
                elif incident.causes_safety_car:
                    flag_info = " [SC]"
                print(f"  Lap {incident.lap}: {incident.description}{flag_info}")
            print("-" * 50)

        # Generate and display headlines
        # Get championship info for headlines
        driver_standings = self.state.standings_manager.get_driver_standings()
        champ_leader = driver_standings[0][1].name if driver_standings else ""
        champ_gap = 0
        if len(driver_standings) >= 2:
            champ_gap = driver_standings[0][1].season_points - driver_standings[1][1].season_points

        # Get active rivalries
        active_rivalries = self.state.rivalry_manager.get_race_drama_potential(
            [d.name for d, t, p in results if p > 0]
        )

        headlines = self.state.news_generator.generate_race_headlines(
            race_results=results,
            track_name=track.name,
            qualifying_positions=race_engine.qualifying_positions,
            incidents=[str(i.description) for i in race_engine.race_incidents],
            rivalries=active_rivalries,
            championship_leader=champ_leader,
            championship_gap=champ_gap,
            player_team_name=self.state.player_team.name
        )

        if headlines:
            print(self.state.news_generator.display_headlines(headlines, "POST-RACE NEWS"))
            press_enter_to_continue()

        # Show rivalries if any are notable
        active = self.state.rivalry_manager.get_active_rivalries(40)
        if active:
            print(self.state.rivalry_manager.display_rivalries())

        # Advance rivalry manager
        self.state.rivalry_manager.advance_race()

        # Show updated standings
        print(self.state.standings_manager.display_driver_standings())
        press_enter_to_continue()

        # Advance to next race (pass results for AI income)
        ai_upgrade_messages = self.state.advance_race(results)

        # Show AI upgrades if any
        if ai_upgrade_messages:
            print("\n" + "-" * 50)
            print("  AI TEAM DEVELOPMENTS")
            print("-" * 50)
            for msg in ai_upgrade_messages:
                print(f"  {msg}")
            print("-" * 50)
            press_enter_to_continue()

        # Check if season complete
        if self.state.is_season_complete():
            self._end_season()

    def _end_season(self) -> None:
        """Handle end of season."""
        position = self.state.get_player_constructor_position()
        prize = self.state.apply_season_prize_money()

        self.menu.display_season_end(self.state.current_season, prize, position)

        # Sponsor season bonus
        if self.state.sponsor_manager.current_sponsor:
            bonus = self.state.sponsor_manager.get_season_bonus()
            clear_screen()
            print("\n" + "=" * 60)
            print("  SPONSOR SEASON SUMMARY")
            print("=" * 60)
            sponsor = self.state.sponsor_manager.current_sponsor
            sm = self.state.sponsor_manager
            success_rate = (sm.objectives_met / sm.races_completed * 100) if sm.races_completed > 0 else 0
            print(f"  Sponsor: {sponsor.name}")
            print(f"  Objectives Met: {sm.objectives_met}/{sm.races_completed} ({success_rate:.0f}%)")
            print(f"  Race Earnings: ${sm.total_earnings:.2f}M")
            if bonus > 0:
                self.state.player_team.budget += bonus
                print(f"  SEASON BONUS EARNED: ${bonus:.1f}M (80%+ objectives met!)")
                print(f"  New Budget: ${self.state.player_team.budget:.1f}M")
            else:
                print(f"  Season Bonus: NOT EARNED (needed 80% objectives)")
            print("=" * 60)
            press_enter_to_continue()

        # Check for championship win
        if position == 1:
            self.menu.display_championship_won(self.state.current_season)

        # Show final standings
        print(self.state.standings_manager.display_constructor_standings())
        press_enter_to_continue()

        # Driver development - age up and develop all drivers
        self._process_driver_development()

        # Process AI transfers at end of season
        transfer_messages = self.state.process_end_of_season_transfers()
        if transfer_messages:
            clear_screen()
            print("\n" + "=" * 70)
            print("  OFF-SEASON TRANSFER ACTIVITY")
            print("=" * 70)
            for msg in transfer_messages:
                print(f"  {msg}")
            print("=" * 70)
            press_enter_to_continue()

        # Start new season
        if MenuSystem.confirm_action("Start next season?"):
            # Reset sponsor for new season
            self.state.sponsor_manager.reset_for_new_season()
            self.state.start_new_season()

            # Prompt player to select new sponsor
            clear_screen()
            print("\n  NEW SEASON - SPONSOR SELECTION")
            if MenuSystem.confirm_action("Would you like to review sponsor offers for the new season?"):
                self._select_sponsor()
        else:
            self.running = False

    def _process_driver_development(self) -> None:
        """Process driver aging and stat development at end of season."""
        clear_screen()
        print("\n" + "=" * 70)
        print("  DRIVER DEVELOPMENT - OFF-SEASON")
        print("=" * 70)

        # Track significant changes for player team
        player_driver_changes = []

        for driver in self.state.all_drivers:
            old_overall = driver.stats.overall
            old_age = driver.age

            # Age up the driver
            driver.age_up()

            # Check if young driver had a good season (for bonus growth)
            had_good_season = False
            if driver.age <= 27 and driver.team_name:
                # Find their team to check car rating
                for team in self.state.teams:
                    if team.name == driver.team_name:
                        car_rating = team.car.overall
                        avg_pos = driver.get_average_position()

                        # Determine expected position based on car
                        if car_rating >= 85:
                            expected_avg = 6
                        elif car_rating >= 75:
                            expected_avg = 10
                        elif car_rating >= 65:
                            expected_avg = 14
                        else:
                            expected_avg = 17

                        # Good season = beating expectations by 2+ positions on average
                        if avg_pos < 99 and avg_pos <= expected_avg - 2:
                            had_good_season = True
                        # Or any podiums/wins
                        if driver.podiums > 0 or driver.race_wins > 0:
                            had_good_season = True
                        break

            # Develop stats based on age and performance
            changes = driver.develop_stats(had_good_season=had_good_season)

            new_overall = driver.stats.overall

            # Track player driver changes
            if driver in self.state.player_team.drivers:
                player_driver_changes.append({
                    'driver': driver,
                    'old_age': old_age,
                    'changes': changes,
                    'old_overall': old_overall,
                    'new_overall': new_overall
                })

        # Display player team driver development
        print("\n  YOUR TEAM'S DRIVER DEVELOPMENT:")
        print("-" * 70)

        if player_driver_changes:
            for info in player_driver_changes:
                driver = info['driver']
                print(f"\n  {driver.name} (Age {info['old_age']} -> {driver.age})")
                print(f"  Overall: {info['old_overall']} -> {info['new_overall']}")

                if info['changes']:
                    for stat_name, old_val, new_val in info['changes']:
                        direction = "+" if new_val > old_val else ""
                        diff = new_val - old_val
                        stat_display = stat_name.replace('_', ' ').title()
                        print(f"    {stat_display}: {old_val} -> {new_val} ({direction}{diff})")
                else:
                    print("    No stat changes this season")
        else:
            print("  No drivers on your team!")

        # Show some notable league-wide development
        print("\n" + "-" * 70)
        print("  NOTABLE LEAGUE DEVELOPMENTS:")
        print("-" * 70)

        # Find biggest improvers and decliners
        all_changes = []
        for driver in self.state.all_drivers:
            if driver not in self.state.player_team.drivers:
                # Recalculate overall (it was already updated)
                all_changes.append((driver, driver.stats.overall))

        # Show a few random notable changes
        notable = random.sample(self.state.all_drivers, min(5, len(self.state.all_drivers)))
        for driver in notable:
            if driver not in self.state.player_team.drivers:
                age_bracket = ""
                if driver.age < 23:
                    age_bracket = "(Rising star)"
                elif driver.age > 34:
                    age_bracket = "(Veteran)"
                print(f"  {driver.name}, {driver.age} - Overall: {driver.stats.overall} {age_bracket}")

        print("=" * 70)
        press_enter_to_continue()

    def _view_driver_standings(self) -> None:
        """View current driver standings."""
        clear_screen()
        print(self.state.standings_manager.display_driver_standings())
        press_enter_to_continue()

    def _view_constructor_standings(self) -> None:
        """View current constructor standings."""
        clear_screen()
        print(self.state.standings_manager.display_constructor_standings())
        press_enter_to_continue()

    def _team_management(self) -> None:
        """Team management menu."""
        while True:
            choice = self.menu.display_team_menu()

            if choice.lower() == 'b':
                break
            elif choice == '1':
                self._view_my_drivers()
            elif choice == '2':
                self._view_my_car()
            elif choice == '3':
                self._driver_market()
            elif choice == '4':
                self._upgrade_car()
            elif choice == '5':
                self._view_rival_teams()
            elif choice == '6':
                self._manage_sponsors()
            elif choice == '7':
                self._view_rivalries()

    def _view_my_drivers(self) -> None:
        """View player's current drivers."""
        clear_screen()
        print(f"\n  {self.state.player_team.name} - DRIVERS")
        print("=" * 50)

        if not self.state.player_team.drivers:
            print("\n  No drivers signed!")
        else:
            for i, driver in enumerate(self.state.player_team.drivers, 1):
                print(f"\n  Driver {i}: {driver}")
                print(driver.get_stats_display())
                print(f"  Season Points: {driver.season_points}")
                print(f"  Salary: ${driver.salary}M/season")

        print("=" * 50)
        press_enter_to_continue()

    def _view_my_car(self) -> None:
        """View player's car stats."""
        clear_screen()
        print(f"\n  {self.state.player_team.name} - CAR")
        print("=" * 50)
        print(self.state.player_team.car.get_stats_display())
        print("=" * 50)
        press_enter_to_continue()

    def _driver_market(self) -> None:
        """Handle driver market."""
        while True:
            clear_screen()
            print(self.state.driver_market.display_market(self.state.player_team.budget))

            print("\n  Options:")
            print("  [#] Sign a driver (enter number)")
            print("  [R] Release a driver")
            print("  [B] Back")

            choice = input("\n  Enter choice: ").strip().lower()

            if choice == 'b':
                break
            elif choice == 'r':
                self._release_driver()
            else:
                try:
                    driver_num = int(choice)
                    drivers = self.state.driver_market.get_available_drivers()
                    if 0 < driver_num <= len(drivers):
                        selected_driver = drivers[driver_num - 1]
                        print(self.state.driver_market.display_driver_details(selected_driver))

                        if MenuSystem.confirm_action(f"Sign {selected_driver.name} for ${selected_driver.market_value}M?"):
                            success, message = self.state.driver_market.sign_driver(
                                self.state.player_team, selected_driver
                            )
                            if success:
                                self.menu.display_success(message)
                            else:
                                self.menu.display_error(message)
                except ValueError:
                    pass

    def _release_driver(self) -> None:
        """Release a driver from the team."""
        if not self.state.player_team.drivers:
            self.menu.display_error("No drivers to release!")
            return

        print("\n  Your drivers:")
        for i, driver in enumerate(self.state.player_team.drivers, 1):
            print(f"  [{i}] {driver.name}")

        choice = get_int_input(
            "\n  Select driver to release (B to cancel): ",
            1, len(self.state.player_team.drivers)
        )

        if choice == -1:
            return

        driver = self.state.player_team.drivers[choice - 1]
        if MenuSystem.confirm_action(f"Release {driver.name}?"):
            success, message = self.state.driver_market.release_driver(
                self.state.player_team, driver
            )
            if success:
                self.menu.display_success(message)
            else:
                self.menu.display_error(message)

    def _upgrade_car(self) -> None:
        """Handle car upgrades."""
        while True:
            clear_screen()
            print(self.state.upgrade_system.display_upgrade_menu())

            print("\n  Enter component number to upgrade, or B to go back: ")
            choice = input("  Choice: ").strip().lower()

            if choice == 'b':
                break

            try:
                upgrade_num = int(choice)
                options = self.state.upgrade_system.get_upgrade_options()

                if 0 < upgrade_num <= len(options):
                    stat_name, display_name, current, cost, new_val = options[upgrade_num - 1]

                    if MenuSystem.confirm_action(f"Upgrade {display_name} from {current} to {new_val} for ${cost}M?"):
                        success, message = self.state.upgrade_system.purchase_upgrade(stat_name)
                        if success:
                            self.menu.display_success(message)
                        else:
                            self.menu.display_error(message)
            except ValueError:
                pass

    def _view_rival_teams(self) -> None:
        """View all rival teams and their car ratings."""
        clear_screen()
        print("\n" + "=" * 80)
        print("  RIVAL TEAMS OVERVIEW")
        print("=" * 80)
        print(f"  {'Team':<25} {'Car Rating':<12} {'Drivers':<35}")
        print("-" * 80)

        # Sort teams by car overall rating (descending)
        sorted_teams = sorted(
            [t for t in self.state.teams if t != self.state.player_team],
            key=lambda t: t.car.overall,
            reverse=True
        )

        for team in sorted_teams:
            driver_names = ", ".join([d.name for d in team.drivers]) if team.drivers else "No drivers"
            # Truncate driver names if too long
            if len(driver_names) > 33:
                driver_names = driver_names[:30] + "..."
            print(f"  {team.name:<25} {team.car.overall:<12} {driver_names:<35}")

        # Show player team for comparison
        print("-" * 80)
        player_drivers = ", ".join([d.name for d in self.state.player_team.drivers]) if self.state.player_team.drivers else "No drivers"
        print(f"  {self.state.player_team.name:<25} {self.state.player_team.car.overall:<12} {player_drivers:<35}  (YOU)")
        print("=" * 80)

        # Show detailed stats option
        print("\n  Enter team number for detailed stats, or B to go back:")
        for i, team in enumerate(sorted_teams, 1):
            print(f"  [{i}] {team.name}")

        choice = input("\n  Choice: ").strip().lower()
        if choice != 'b':
            try:
                team_num = int(choice)
                if 0 < team_num <= len(sorted_teams):
                    self._show_team_details(sorted_teams[team_num - 1])
            except ValueError:
                pass

    def _show_team_details(self, team: Team) -> None:
        """Show detailed information about a team."""
        clear_screen()
        print("\n" + "=" * 60)
        print(f"  {team.name}")
        print("=" * 60)
        print(f"\n  CAR STATS (Overall: {team.car.overall}):")
        print(team.car.get_stats_display())
        print(f"\n  DRIVERS:")
        if team.drivers:
            for driver in team.drivers:
                print(f"\n  {driver.name} (Age: {driver.age})")
                print(f"  Overall: {driver.stats.overall}")
                print(driver.get_stats_display())
        else:
            print("  No drivers signed")
        print("\n" + "=" * 60)
        press_enter_to_continue()

    def _view_rivalries(self) -> None:
        """View current driver rivalries."""
        clear_screen()
        active = self.state.rivalry_manager.get_active_rivalries(20)

        if active:
            print(self.state.rivalry_manager.display_rivalries())

            # Show detailed rivalry info if requested
            print("\n  Enter rivalry number for details, or B to go back:")
            active.sort(key=lambda r: r.intensity, reverse=True)
            for i, rivalry in enumerate(active, 1):
                print(f"  [{i}] {rivalry.driver1} vs {rivalry.driver2}")

            choice = input("\n  Choice: ").strip().lower()
            if choice != 'b':
                try:
                    num = int(choice)
                    if 0 < num <= len(active):
                        rivalry = active[num - 1]
                        clear_screen()
                        print("\n" + "=" * 60)
                        print(f"  RIVALRY: {rivalry.driver1} vs {rivalry.driver2}")
                        print("=" * 60)
                        print(f"  Intensity: {rivalry.intensity}/100 [{rivalry.level}]")
                        print(f"  Total Incidents: {len(rivalry.interactions)}")
                        print("\n  INCIDENT HISTORY:")
                        print("-" * 60)
                        for interaction in rivalry.interactions[-5:]:  # Last 5
                            print(f"  {interaction.race} Lap {interaction.lap}: {interaction.description}")
                        print("=" * 60)
                        press_enter_to_continue()
                except ValueError:
                    pass
        else:
            print("\n" + "=" * 60)
            print("  DRIVER RIVALRIES")
            print("=" * 60)
            print("\n  No notable driver rivalries have developed yet.")
            print("  Rivalries form when drivers collide, make aggressive moves,")
            print("  or battle closely for position over multiple races.")
            print("\n" + "=" * 60)
            press_enter_to_continue()

    def _manage_sponsors(self) -> None:
        """Manage team sponsors."""
        clear_screen()

        if self.state.sponsor_manager.current_sponsor:
            # Show current sponsor status
            print(self.state.sponsor_manager.get_status_display())
            press_enter_to_continue()
        else:
            # No sponsor - offer to select one
            print("\n  You don't have a sponsor for this season!")
            if MenuSystem.confirm_action("Would you like to view sponsor offers?"):
                self._select_sponsor()

    def _select_sponsor(self) -> None:
        """Select a sponsor from offers."""
        # Generate offers based on team's constructor position (as reputation)
        position = self.state.get_player_constructor_position()
        # Convert position to reputation (1st = 100, 11th = 0)
        reputation = max(0, 100 - (position - 1) * 10)

        offers = self.state.sponsor_manager.generate_sponsor_offers(reputation)

        clear_screen()
        print(self.state.sponsor_manager.display_sponsor_selection(offers))

        choice = get_int_input("\n  Select sponsor (1-5), or B to decline all: ", 1, 5)

        if choice != -1:
            selected = offers[choice - 1]
            if MenuSystem.confirm_action(f"Sign with {selected.name}?"):
                self.state.sponsor_manager.select_sponsor(selected)
                self.menu.display_success(f"Signed sponsorship deal with {selected.name}!")
            else:
                print("  Sponsor offer declined.")
                press_enter_to_continue()

    def _view_calendar(self) -> None:
        """View season calendar."""
        self.menu.display_season_calendar(TRACKS, self.state.current_race)

    def _save_game(self) -> None:
        """Save the current game."""
        if self.state.save_game():
            self.menu.display_success("Game saved successfully!")
        else:
            self.menu.display_error("Failed to save game.")
