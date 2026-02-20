from __future__ import annotations

import argparse

from .config import Module3Config
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Module3: Context Enhanced LLM Investigation")
    parser.add_argument("command", choices=["serve"], help="Run mode.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "serve":
        run_pipeline(Module3Config.from_env())
        return
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
