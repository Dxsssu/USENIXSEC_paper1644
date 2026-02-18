from __future__ import annotations

from .config import Module1Config
from .pipeline import run_pipeline


def main() -> None:
    run_pipeline(Module1Config.from_env())


if __name__ == "__main__":
    main()
