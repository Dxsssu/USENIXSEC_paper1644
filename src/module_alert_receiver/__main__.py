from __future__ import annotations

from .config import ReceiverConfig
from .receiver import run_receiver


def main() -> None:
    config = ReceiverConfig.from_env()
    run_receiver(config)


if __name__ == "__main__":
    main()
