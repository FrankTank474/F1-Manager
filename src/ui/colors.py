"""Terminal color utilities for F1 Manager"""


class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Basic colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

    # 256 color mode for more specific team colors
    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        """Create an RGB color code (requires 256 color terminal)."""
        return f'\033[38;2;{r};{g};{b}m'

    @staticmethod
    def bg_rgb(r: int, g: int, b: int) -> str:
        """Create an RGB background color code."""
        return f'\033[48;2;{r};{g};{b}m'


# Team colors matching real F1 team colors
TEAM_COLORS = {
    # Top teams
    "Red Bull Racing": Colors.rgb(30, 65, 255),      # Blue
    "Ferrari": Colors.rgb(220, 0, 0),                 # Red
    "McLaren": Colors.rgb(255, 135, 0),               # Papaya orange
    "Mercedes": Colors.rgb(0, 210, 190),              # Teal

    # Midfield
    "Aston Martin": Colors.rgb(0, 111, 98),           # British racing green
    "Alpine": Colors.rgb(0, 144, 255),                # Blue
    "Williams": Colors.rgb(0, 90, 255),               # Blue

    # Backmarkers
    "RB": Colors.rgb(70, 130, 180),                   # Steel blue
    "Haas": Colors.rgb(180, 180, 180),                # Silver/white
    "Sauber": Colors.rgb(82, 226, 82),                # Green (Kick livery)
}

# Default color for player/unknown teams
DEFAULT_TEAM_COLOR = Colors.BRIGHT_WHITE


def get_team_color(team_name: str) -> str:
    """Get the color code for a team."""
    return TEAM_COLORS.get(team_name, DEFAULT_TEAM_COLOR)


def colorize(text: str, team_name: str) -> str:
    """Colorize text based on team."""
    color = get_team_color(team_name)
    return f"{color}{text}{Colors.RESET}"


def colorize_driver_line(position: int, driver_name: str, team_name: str,
                          extra_info: str = "", is_player: bool = False) -> str:
    """
    Create a color-coded driver line for results display.

    Args:
        position: Race/quali position
        driver_name: Driver's name
        team_name: Team name for color
        extra_info: Additional info (time gap, points, etc.)
        is_player: If True, add a marker for player's team
    """
    color = get_team_color(team_name)
    marker = " *" if is_player else "  "

    # Color the driver name and team
    colored_line = (
        f"{marker}{position:<3} "
        f"{color}{driver_name:<22}{Colors.RESET} "
        f"{color}{team_name:<18}{Colors.RESET} "
        f"{extra_info}"
    )
    return colored_line


def colorize_team_line(position: int, team_name: str,
                        extra_info: str = "", is_player: bool = False) -> str:
    """Create a color-coded team line for constructor standings."""
    color = get_team_color(team_name)
    marker = " *" if is_player else "  "

    colored_line = (
        f"{marker}{position:<3} "
        f"{color}{team_name:<30}{Colors.RESET} "
        f"{extra_info}"
    )
    return colored_line
