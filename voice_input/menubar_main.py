"""Menubar App 進入點。"""

import logging

from .config import load_config
from .menubar_app import VoiceInputMenuBarApp


def main():
    config = load_config()

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    app = VoiceInputMenuBarApp(config)
    app.run()


if __name__ == "__main__":
    main()
