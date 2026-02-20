from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from xgboost import XGBClassifier

from .config import Module2Config
from .feature_pipeline import FeaturePipeline
from .models import TrainRecord, parse_datetime


@dataclass
class TrainSummary:
    train_rows: int
    valid_rows: int
    positive_ratio: float
    threshold: float
    model_path: str


def train_from_jsonl(cfg: Module2Config) -> TrainSummary:
    records = _load_records(cfg.train.train_jsonl_path, cfg.train.train_window_days)
    if not records:
        raise ValueError(f"No training records found in {cfg.train.train_jsonl_path}")

    features = FeaturePipeline.from_config(cfg.features)
    x_rows: list[np.ndarray] = []
    y_rows: list[int] = []

    for record in records:
        context = record.aggregated_alert
        for raw_alert in record.raw_alerts:
            x_rows.append(features.transform_one(raw_alert=raw_alert, context=context))
            y_rows.append(record.label)

    x = np.vstack(x_rows).astype(np.float32)
    y = np.array(y_rows, dtype=np.int32)

    train_idx, valid_idx = _split_indices(len(y), cfg.train.test_ratio, cfg.train.random_seed)
    x_train, y_train = x[train_idx], y[train_idx]
    x_valid, y_valid = x[valid_idx], y[valid_idx]

    pos_count = max(int(np.sum(y_train == 1)), 1)
    neg_count = max(int(np.sum(y_train == 0)), 1)
    scale_pos_weight = float(neg_count) / float(pos_count)

    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=cfg.train.n_estimators,
        max_depth=cfg.train.max_depth,
        learning_rate=cfg.train.learning_rate,
        subsample=cfg.train.subsample,
        colsample_bytree=cfg.train.colsample_bytree,
        scale_pos_weight=scale_pos_weight,
        random_state=cfg.train.random_seed,
        n_jobs=4,
    )
    model.fit(x_train, y_train)

    threshold = cfg.model.decision_threshold
    if len(valid_idx) > 0:
        valid_prob = model.predict_proba(x_valid)[:, 1]
        threshold = _best_f1_threshold(valid_prob, y_valid, default=threshold)

    artifact = {
        "model": model,
        "threshold": float(threshold),
        "feature_state": features.export_state(),
        "trained_at": datetime.now(tz=UTC).isoformat(),
        "feature_dim": int(features.feature_dim),
    }

    model_path = Path(cfg.model.model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as f:
        pickle.dump(artifact, f)

    return TrainSummary(
        train_rows=int(len(train_idx)),
        valid_rows=int(len(valid_idx)),
        positive_ratio=float(np.mean(y)),
        threshold=float(threshold),
        model_path=str(model_path),
    )


def _load_records(path: str, train_window_days: int) -> list[TrainRecord]:
    file_path = Path(path)
    if not file_path.exists():
        return []

    cutoff = datetime.now(tz=UTC) - timedelta(days=train_window_days)
    records: list[TrainRecord] = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            ts = _extract_record_time(payload)
            if ts < cutoff:
                continue
            records.append(TrainRecord.from_dict(payload))
    return records


def _extract_record_time(payload: dict[str, Any]) -> datetime:
    candidates = [
        payload.get("@timestamp"),
        payload.get("timestamp"),
        payload.get("created_at"),
        (payload.get("aggregated_alert") or {}).get("last_seen") if isinstance(payload.get("aggregated_alert"), dict) else None,
    ]
    for candidate in candidates:
        if candidate is None or candidate == "":
            continue
        dt = parse_datetime(candidate)
        return dt
    return datetime.now(tz=UTC)


def _split_indices(total: int, test_ratio: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    if total <= 2:
        all_idx = np.arange(total)
        return all_idx, np.array([], dtype=np.int32)
    rng = np.random.default_rng(seed)
    indices = np.arange(total)
    rng.shuffle(indices)
    valid_size = int(total * test_ratio)
    valid_size = max(1, min(valid_size, total - 1))
    valid_idx = indices[:valid_size]
    train_idx = indices[valid_size:]
    return train_idx, valid_idx


def _best_f1_threshold(prob: np.ndarray, y_true: np.ndarray, default: float) -> float:
    best_threshold = default
    best_f1 = -1.0
    for threshold in np.linspace(0.30, 0.95, 27):
        y_pred = (prob >= threshold).astype(np.int32)
        tp = float(np.sum((y_pred == 1) & (y_true == 1)))
        fp = float(np.sum((y_pred == 1) & (y_true == 0)))
        fn = float(np.sum((y_pred == 0) & (y_true == 1)))
        precision = tp / (tp + fp) if tp + fp > 0 else 0.0
        recall = tp / (tp + fn) if tp + fn > 0 else 0.0
        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = (2.0 * precision * recall) / (precision + recall)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = float(threshold)
    return best_threshold
