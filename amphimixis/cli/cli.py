"""CLI"""

from amphimixis import general


# pylint: disable=too-few-public-methods
class CLI(general.IUI):
    """CLI class implementing IUI interface"""

    def print(self) -> None:
        """Print message to the console

        :param str message: Message to print to the console"""

    def update_message(self, message: str, build_id: str) -> None:
        """Update message for specific build

        :param str message: Message to store
        :param str build_id: Build identifier
        """

    def step(self, build_id: str) -> None:
        """Advance the progress counter by one step

        :param str build_id: Build identifier
        """
