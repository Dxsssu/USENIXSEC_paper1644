from __future__ import annotations

import argparse

from .config import Module2Config
from .pipeline import run_pipeline
from .trainer import train_from_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Module2: Business Logic Self-Learning")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="Train XGBoost model and save .pkl artifact")
    train_parser.add_argument(
        "--train-jsonl",
        default=None,
        help="Override training jsonl path (default from env/config).",
    )

    subparsers.add_parser("serve", help="Run online matching pipeline")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    cfg = Module2Config.from_env()

    if args.command == "train":
        if args.train_jsonl:
            cfg = Module2Config(
                queue=cfg.queue,
                elastic=cfg.elastic,
                model=cfg.model,
                features=cfg.features,
                train=cfg.train.__class__(
                    train_jsonl_path=args.train_jsonl,
                    train_window_days=cfg.train.train_window_days,
                    test_ratio=cfg.train.test_ratio,
                    random_seed=cfg.train.random_seed,
                    n_estimators=cfg.train.n_estimators,
                    max_depth=cfg.train.max_depth,
                    learning_rate=cfg.train.learning_rate,
                    subsample=cfg.train.subsample,
                    colsample_bytree=cfg.train.colsample_bytree,
                ),
            )
        summary = train_from_jsonl(cfg)
        print(
            "trained",
            f"model={summary.model_path}",
            f"train_rows={summary.train_rows}",
            f"valid_rows={summary.valid_rows}",
            f"positive_ratio={summary.positive_ratio:.4f}",
            f"threshold={summary.threshold:.4f}",
        )
        return

    if args.command == "serve":
        run_pipeline(cfg)
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
