import logging
from pathlib import Path
from typing import Callable

import numpy as np

from src.training.data_preparer import prepare_from_folders, split_train_test
from src.training.model_saver import save
from src.training.model_trainer import train, optimize_lgbm, evaluate


class TrainingManager:
    def __init__(self, progress_callback: Callable[[str, int], None] | None = None) -> None:
        self._progress = progress_callback or (lambda s, p: None)

    def run_pipeline(
        self,
        alpha_dir: str | Path,
        beta_dir: str | Path,
        gamma_dir: str | Path,
        model_name: str,
        filter_threshold: float = 1000,
        n_trials: int = 0,
    ) -> dict:
        self._progress("Preparing data...", 10)
        features, labels = prepare_from_folders(alpha_dir, beta_dir, gamma_dir, filter_threshold)
        if len(features) == 0:
            raise ValueError("No valid features extracted")

        self._progress("Splitting data...", 30)
        X_train, X_test, y_train, y_test = split_train_test(features, labels)

        logger = logging.getLogger("usplit")

        if n_trials > 0:
            self._progress(f"Optuna tuning ({n_trials} trials)...", 40)
            logger.info(f"Starting Optuna optimization with {n_trials} trials")
            best_params = optimize_lgbm(X_train, y_train, n_trials=n_trials)
            logger.info(f"Best params: {best_params}")
            self._progress("Training with best params...", 65)
            model = train(X_train, y_train, params=best_params)
        else:
            self._progress("Training model...", 50)
            model = train(X_train, y_train)

        self._progress("Evaluating...", 75)
        ev_result = evaluate(model, X_test, y_test, logger=logger)

        self._progress("Saving model...", 90)
        model_path = save(model, model_name, ev_result)

        self._progress("Done", 100)
        return {"model_path": str(model_path), **ev_result}
