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
    ║    [1] View My Drivers (Stats, Morale, Contracts)                 ║
    ║    [2] View My Car                                                ║
    ║    [3] Driver Market                                              ║
    ║    [4] Car Development                                            ║
    ║    [5] View Rival Teams                                           ║
    ║    [6] Sponsors                                                   ║
    ║    [7] Driver Rivalries                                           ║
    ║    [8] Inbox                                                      ║
    ║    [B] Back to Main Menu                                          ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return get_input("  Enter choice: ", ['1', '2', '3', '4', '5', '6', '7', '8', 'b', 'B'])

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

    # ==========================================================================
    # MULTIPLAYER MENU METHODS
    # ==========================================================================

    @staticmethod
    def display_player_count_menu() -> int:
        """Select number of players (1 or 2)."""
        clear_screen()
        print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                      GAME MODE SELECTION                          ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║    [1] Single Player                                              ║
    ║        - Manage your team against AI opponents                    ║
    ║                                                                   ║
    ║    [2] Two Players (Hot-Seat)                                     ║
    ║        - Compete with a friend on the same computer               ║
    ║        - Take turns managing your teams                           ║
    ║        - Compete for drivers and championships!                   ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        choice = get_input("  Select game mode: ", ['1', '2'])
        return int(choice)

    @staticmethod
    def display_new_game_menu_multiplayer(player_number: int) -> str:
        """Display new game setup for a specific player."""
        clear_screen()
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                   PLAYER {player_number} - TEAM SETUP                         ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║  Welcome, Player {player_number}!                                             ║
    ║                                                                   ║
    ║  Create your own F1 team and compete against your rival           ║
    ║  and the established teams on the grid.                           ║
    ║                                                                   ║
    ║  Starting Resources:                                              ║
    ║  - Budget: $50M                                                   ║
    ║  - Car Performance: Backmarker level                              ║
    ║  - Drivers: You must sign 2 drivers from the market               ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return input(f"\n  Player {player_number}, enter your team name: ").strip()

    @staticmethod
    def display_player_switch_prompt(player_number: int, context: str = "YOUR TURN") -> None:
        """Display prompt to switch to another player."""
        clear_screen()
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║                                                                   ║
    ║                     ╔═══════════════════════╗                     ║
    ║                     ║    PLAYER {player_number}'s TURN    ║                     ║
    ║                     ╚═══════════════════════╝                     ║
    ║                                                                   ║
    ║                        {context:^30}                       ║
    ║                                                                   ║
    ║             Please hand the device to Player {player_number}                  ║
    ║                                                                   ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        input(f"\n  Player {player_number}, press Enter when ready...")
        clear_screen()

    @staticmethod
    def display_multiplayer_main_menu(
        player_number: int,
        team_name: str,
        budget: float,
        season: int,
        race_num: int,
        total_races: int,
        is_turn_based: bool = True
    ) -> str:
        """Display main game menu for multiplayer with player indicator."""
        clear_screen()
        budget_str = f"${budget:.1f}M"
        turn_indicator = f"PLAYER {player_number}" if is_turn_based else ""
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║          F1 MANAGER 2026 - {turn_indicator:^15}                    ║
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
    def display_multiplayer_team_menu(player_number: int, team_name: str) -> str:
        """Display team management menu for multiplayer with end turn option."""
        clear_screen()
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║           TEAM MANAGEMENT - PLAYER {player_number} ({team_name[:15]:<15})       ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║    [1] View My Drivers (Stats, Morale, Contracts)                 ║
    ║    [2] View My Car                                                ║
    ║    [3] Driver Market                                              ║
    ║    [4] Car Development                                            ║
    ║    [5] View Rival Teams                                           ║
    ║    [6] Sponsors                                                   ║
    ║    [7] Driver Rivalries                                           ║
    ║    [8] Inbox                                                      ║
    ║    [E] End Turn (Switch to other player)                          ║
    ║    [B] Back to Main Menu                                          ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return get_input("  Enter choice: ", ['1', '2', '3', '4', '5', '6', '7', '8', 'e', 'E', 'b', 'B'])

    @staticmethod
    def display_tire_selection_multiplayer(player_number: int, team_name: str, weather: str) -> str:
        """Display tire selection for race start with player indicator."""
        clear_screen()
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║         STARTING TIRE SELECTION - PLAYER {player_number}                      ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║  Team: {team_name:<25}                                    ║
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
    def display_bidding_war_start(driver_name: str, base_price: float, teams: list) -> None:
        """Display start of a bidding war."""
        clear_screen()
        team_names = ", ".join(teams)
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                      BIDDING WAR!                                 ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║  Multiple teams want to sign {driver_name:<20}!             ║
    ║                                                                   ║
    ║  Interested Teams: {team_names:<35}     ║
    ║  Starting Price: ${base_price:<10.1f}M                                  ║
    ║                                                                   ║
    ║  The highest bidder will sign the driver!                         ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        press_enter_to_continue()

    @staticmethod
    def display_bidding_war_turn(
        player_number: int,
        team_name: str,
        driver_name: str,
        current_bid: float,
        current_leader: str,
        your_budget: float
    ) -> str:
        """Display bidding war turn for a player."""
        clear_screen()
        can_bid_1 = your_budget >= current_bid + 1
        can_bid_5 = your_budget >= current_bid + 5
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║              BIDDING WAR - PLAYER {player_number} ({team_name[:15]:<15})        ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║  Driver: {driver_name:<30}                          ║
    ║  Current Bid: ${current_bid:<10.1f}M  (by {current_leader[:15]:<15})        ║
    ║  Your Budget: ${your_budget:<10.1f}M                                    ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║""")
        if can_bid_1:
            print(f"""    ║    [1] Raise by $1M  (New bid: ${current_bid + 1:.1f}M)                      ║""")
        if can_bid_5:
            print(f"""    ║    [5] Raise by $5M  (New bid: ${current_bid + 5:.1f}M)                      ║""")
        print(f"""    ║    [P] Pass (Drop out of bidding)                                 ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        valid = ['p', 'P']
        if can_bid_1:
            valid.extend(['1'])
        if can_bid_5:
            valid.extend(['5'])
        return get_input("  Your choice: ", valid)

    @staticmethod
    def display_bidding_war_result(winner_team: str, driver_name: str, final_price: float) -> None:
        """Display the result of a bidding war."""
        clear_screen()
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                    BIDDING WAR RESULT                             ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║  {winner_team:<30} wins the bidding!                ║
    ║                                                                   ║
    ║  {driver_name:<25} signs for ${final_price:<10.1f}M           ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        press_enter_to_continue()

    @staticmethod
    def display_ask_counter_bid(player_number: int, team_name: str, driver_name: str, price: float) -> bool:
        """Ask a player if they want to counter-bid for a driver."""
        clear_screen()
        print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║              DRIVER MARKET ALERT - PLAYER {player_number}                     ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║  Another team is trying to sign {driver_name:<20}!          ║
    ║  Current Price: ${price:<10.1f}M                                    ║
    ║                                                                   ║
    ║  Do you want to compete for this driver?                          ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """)
        return MenuSystem.confirm_action("Enter bidding war?")
