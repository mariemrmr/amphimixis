class ProgressTracker:
    """Spinner for show progress to user."""

    braille = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self):
        self.counter = 0
        self.message = "Building..."

    def update_message(self, message: str) -> None:
        pass

    def redraw_spinner(self) -> None:
        pass

    def clear_spinner(self) -> None:
        pass

    def next_spinner(self) -> None:
        pass
