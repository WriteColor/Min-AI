"""browser_launch.py — Clean browser launcher helper."""
from actions.browser_registry import launch_url

def browser_launch(url: str) -> bool:
    """Launch the preferred or system default browser."""
    return launch_url(url)
