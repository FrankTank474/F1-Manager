"""Text-based Menu System for F1 Manager"""

import os
import sys
from typing import Optional, List, Callable


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def press_enter_to_continue():
    """Wait for user to press enter."""
    input("\n  Press Enter to continue...")


def get_input(prompt: str, valid_options: Optional[List[str]] = None) -> str:
    """Get validated input from user."""
    while True:
        try:
            response = input(prompt).strip()
            if valid_options is None:
                return response
            if response.lower() in [opt.lower() for opt in valid_options]:
                return response
            print(f"  Invalid option. Please choose from: {', '.join(valid_options)}")
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            sys.exit(0)


def get_int_input(prompt: str, min_val: int = 0, max_val: int = 100) -> int:
    """Get integer input from user within range."""
    while True:
        try:
            response = input(prompt).strip()
            if response.lower() == 'b':
                return -1  # Back option
            value = int(response)
            if min_val <= value <= max_val:
                return value
            print(f"  Please enter a number between {min_val} and {max_val}")
        except ValueError:
            print("  Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            sys.exit(0)


class MenuSystem:
    @staticmethod
    def display_title_screen() -> None:
        """Display game title screen."""
        clear_screen()
        print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║     ███████╗ ██╗    ███╗   ███╗ █████╗ ███╗   ██╗ █████╗  ██████╗ ║
    ║     ██╔════╝███║    ████╗ ████║██╔══██╗████╗  ██║██╔══██╗██╔════╝ ║
    ║     █████╗  ╚██║    ██╔████╔██║███████║██╔██╗ ██║███████║██║  ███╗║
    ║     ██╔══╝   ██║    ██║╚██╔╝██║██╔══██║██║╚██╗██║██╔══██║██║   ██║║
    ║     ██║      ██║    ██║ ╚═╝ ██║██║  ██║██║ ╚████║██║  ██║╚██████╔╝║
    ║     ╚═╝      ╚═╝    ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ║
    ║                                                                   ║
    ║                         2 0 2 6   S E A S O N                     ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)

    @staticmethod
    def display_main_menu(team_name: str, budget: float, season: int, race_num: int, total_races: int) -> str:
        """Display main game menu and get user choice."""
        clear_screen()
        budget_str = f"${budget:.1f}M"
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                     F1 MANAGER 2026                               ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║  Team: {team_name:<25}  Season: {season:<3}                      ║
    ║  Budget: {budget_str:<20}  Race: {race_num}/{total_races:<15}  ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║    [1] Continue to Next Race                                      ║
    ║    [2] Fast Forward (Simulate Multiple Races)                     ║
    ║    [3] View Driver Standings                                      ║
    ║    [4] View Constructor Standings                                 ║
    ║    [5] Team Management                                            ║
    ║    [6] View Season Calendar                                       ║
    ║    [7] Save Game                                                  ║
    ║    [8] Quit Game                                                  ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return get_input("  Enter choice: ", ['1', '2', '3', '4', '5', '6', '7', '8'])

    @staticmethod
    def display_team_menu() -> str:
        """Display team management menu."""
        clear_screen()
        print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                     TEAM MANAGEMENT                               ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║    [1] View My Drivers                                            ║
    ║    [2] View My Car                                                ║
    ║    [3] Driver Market                                              ║
    ║    [4] Upgrade Car                                                ║
    ║    [5] View Rival Teams                                           ║
    ║    [6] Sponsors                                                   ║
    ║    [7] Driver Rivalries                                           ║
    ║    [B] Back to Main Menu                                          ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return get_input("  Enter choice: ", ['1', '2', '3', '4', '5', '6', '7', 'b', 'B'])

    @staticmethod
    def display_new_game_menu() -> str:
        """Display new game setup."""
        clear_screen()
        print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                      NEW GAME SETUP                               ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║  Welcome to F1 Manager 2026!                                      ║
    ║                                                                   ║
    ║  You are about to create your own F1 team and compete against     ║
    ║  the established teams on the grid. Starting with a modest        ║
    ║  budget and a backmarker car, your goal is to build a             ║
    ║  championship-winning operation over multiple seasons.            ║
    ║                                                                   ║
    ║  Starting Resources:                                              ║
    ║  - Budget: $50M                                                   ║
    ║  - Car Performance: Backmarker level                              ║
    ║  - Drivers: You must sign 2 drivers from the market               ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return input("\n  Enter your team name: ").strip()

    @staticmethod
    def display_start_menu() -> str:
        """Display initial start menu."""
        MenuSystem.display_title_screen()
        print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║    [1] New Game                                                   ║
    ║    [2] Load Game                                                  ║
    ║    [3] Quit                                                       ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return get_input("  Enter choice: ", ['1', '2', '3'])

    @staticmethod
    def display_race_weekend_intro(track_info: str, next_race: int, total_races: int) -> None:
        """Display race weekend introduction."""
        clear_screen()
        print(f"\n  RACE {next_race} OF {total_races}")
        print(track_info)
        press_enter_to_continue()

    @staticmethod
    def display_tire_selection(weather: str) -> str:
        """Display tire selection for race start."""
        clear_screen()
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                    STARTING TIRE SELECTION                        ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║  Weather: {weather:<20}                                          ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║    [1] Soft     - Fastest, high degradation                       ║
    ║    [2] Medium   - Balanced pace and wear                          ║
    ║    [3] Hard     - Slowest, lowest degradation                     ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return get_input("  Select starting tire: ", ['1', '2', '3'])

    @staticmethod
    def display_pit_stop_prompt(driver_name: str, tire_wear: float, current_compound: str,
                                weather: str, position: int, laps_remaining: int,
                                grip_level: str = "GOOD") -> str:
        """Display pit stop decision prompt."""
        # Color code the grip level
        if grip_level == "OPTIMAL":
            grip_display = f"\033[32m{grip_level}\033[0m"  # Green
        elif grip_level == "GOOD":
            grip_display = f"\033[36m{grip_level}\033[0m"  # Cyan
        elif grip_level == "WORN":
            grip_display = f"\033[33m{grip_level}\033[0m"  # Yellow
        elif grip_level == "CRITICAL":
            grip_display = f"\033[31m{grip_level}\033[0m"  # Red
        else:  # DEAD
            grip_display = f"\033[31m{grip_level}\033[0m"  # Red

        # Tire recommendation based on laps remaining
        if weather in ["Light Rain", "Heavy Rain"]:
            if weather == "Heavy Rain":
                rec = "WET recommended"
            else:
                rec = "INTER recommended"
        elif laps_remaining > 30:
            rec = "HARD can finish"
        elif laps_remaining > 18:
            rec = "MEDIUM can finish"
        else:
            rec = "SOFT can finish"

        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                      PIT STOP DECISION                            ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║  Driver: {driver_name:<25}  Position: P{position:<3}             ║
    ║  Current Tire: {current_compound:<10}  Wear: {tire_wear:.0f}%                        ║
    ║  Grip Level: {grip_display:<18}                                   ║
    ║  Weather: {weather:<15}  Laps Remaining: {laps_remaining:<5}              ║
    ║  Strategy Tip: {rec:<20}                                   ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║    [1] Pit for Soft tires    (Fast, ~12 lap life)                 ║
    ║    [2] Pit for Medium tires  (Balanced, ~22 lap life)             ║
    ║    [3] Pit for Hard tires    (Slow, ~35 lap life)                 ║
    ║    [4] Pit for Intermediate tires (Light rain)                    ║
    ║    [5] Pit for Wet tires     (Heavy rain)                         ║
    ║    [S] Stay out (ask again later)                                 ║
    ║    [E] Stay out until END of race (no more prompts)               ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return get_input("  Your decision: ", ['1', '2', '3', '4', '5', 's', 'S', 'e', 'E'])

    @staticmethod
    def display_season_calendar(tracks: list, current_race: int) -> None:
        """Display the season calendar."""
        clear_screen()
        print("\n" + "=" * 60)
        print("  2026 SEASON CALENDAR")
        print("=" * 60)
        print(f"  {'#':<4} {'Grand Prix':<35} {'Status':<12}")
        print("-" * 60)

        for i, track in enumerate(tracks):
            status = "COMPLETED" if i < current_race else "NEXT" if i == current_race else ""
            marker = " >> " if i == current_race else "    "
            print(f"{marker}{i+1:<3} {track['name']:<35} {status:<12}")

        print("=" * 60)
        press_enter_to_continue()

    @staticmethod
    def display_season_end(season: int, prize_money: int, final_position: int) -> None:
        """Display end of season summary."""
        clear_screen()
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                    SEASON {season} COMPLETE!                          ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║  Final Constructor Position: P{final_position:<3}                              ║
    ║  Prize Money Earned: ${prize_money}M                                    ║
    ║                                                                   ║
    ║  The prize money has been added to your budget.                   ║
    ║  Prepare for next season!                                         ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        press_enter_to_continue()

    @staticmethod
    def display_championship_won(season: int) -> None:
        """Display championship victory screen."""
        clear_screen()
        print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║     ██████╗██╗  ██╗ █████╗ ███╗   ███╗██████╗ ██╗ ██████╗ ███╗   ██║
    ║    ██╔════╝██║  ██║██╔══██╗████╗ ████║██╔══██╗██║██╔═══██╗████╗  ██║
    ║    ██║     ███████║███████║██╔████╔██║██████╔╝██║██║   ██║██╔██╗ ██║
    ║    ██║     ██╔══██║██╔══██║██║╚██╔╝██║██╔═══╝ ██║██║   ██║██║╚██╗██║
    ║    ╚██████╗██║  ██║██║  ██║██║ ╚═╝ ██║██║     ██║╚██████╔╝██║ ╚████║
    ║     ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        print(f"\n  CONGRATULATIONS! You've won the Constructor Championship in Season {season}!")
        print("\n  From humble beginnings as a backmarker team, you've built")
        print("  a championship-winning operation. A true rags-to-riches story!")
        press_enter_to_continue()

    @staticmethod
    def display_error(message: str) -> None:
        """Display an error message."""
        print(f"\n  ERROR: {message}")
        press_enter_to_continue()

    @staticmethod
    def display_success(message: str) -> None:
        """Display a success message."""
        print(f"\n  SUCCESS: {message}")
        press_enter_to_continue()

    @staticmethod
    def confirm_action(message: str) -> bool:
        """Ask for confirmation."""
        response = get_input(f"\n  {message} (y/n): ", ['y', 'n', 'Y', 'N'])
        return response.lower() == 'y'

    @staticmethod
    def display_fast_forward_menu(current_race: int, total_races: int) -> str:
        """Display fast-forward options menu."""
        remaining = total_races - current_race
        clear_screen()
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                      FAST FORWARD MODE                            ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║  Current Race: {current_race + 1}/{total_races}                                            ║
    ║  Races Remaining: {remaining:<5}                                           ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║    [1] Simulate next 3 races                                      ║
    ║    [2] Simulate next 5 races                                      ║
    ║    [3] Simulate next 10 races                                     ║
    ║    [4] Simulate rest of season ({remaining} races)                        ║
    ║    [B] Back to Main Menu                                          ║
    ║                                                                   ║
    ║  Note: Fast-forward uses AI pit strategy for your team.           ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return get_input("  Enter choice: ", ['1', '2', '3', '4', 'b', 'B'])
