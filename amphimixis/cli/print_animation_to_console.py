"""Single-line spinner for build progress display"""

import sys

from amphimixis.general import IUI


class PrintAnimationToConsole(IUI):
    """Single-line console spinner implementation of IUI."""

    braille: list[str] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    build_id: str
    index: int
    message: str
    status: str

    def __init__(self):
        self.build_id = ""
        self.index = 0
        self.message = ""
        self.status = "running"

    def update_message(self, build_id: str, message: str) -> None:
        """Update build_id and message.

        :param str build_id: Build identifier
        :param str message: Message describing current build phase
        """

        self.build_id = build_id
        self.message = message
        self.draw()

    def step(self) -> None:
        """Move to next spinner."""

        self.index = (self.index + 1) % len(self.braille)
        self.draw()

    def mark_success(self) -> None:
        """Mark as successful and optionally update message."""

        self.status = "success"
        self.message = "Success!"
        self.draw()
        self.finalize()

    def mark_failed(self, error_message: str = "Failed!") -> None:
        """Mark as failed and optionally update message.

        :param str error_message: Message to display for failed build
        """

        self.status = "failed"
        if error_message == "":
            self.message = "Failed!"
        else:
            self.message = error_message

        self.draw()
        self.finalize()

    def draw(self) -> None:
        """Draw current state to stdout."""

        if self.status == "success":
            symbol = "✓"
        elif self.status == "failed":
            symbol = "✗"
        else:
            symbol = self.braille[self.index]

        sys.stdout.write(f"\r[{self.build_id}][{symbol}] {self.message}")

    def finalize(self) -> None:
        """Move to next line."""

        sys.stdout.write("\n")
