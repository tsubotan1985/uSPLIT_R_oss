import logging

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix


_DEFAULT_PARAMS = {
    "objective": "multiclass",
    "num_class": 3,
    "metric": "multi_logloss",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "class_weight": "balanced",
    "verbosity": -1,
}


def train(X_train: np.ndarray, y_train: np.ndarray, params: dict | None = None) -> object:
    import lightgbm as lgb
    if params is None:
        params = _DEFAULT_PARAMS
    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train)
    return model


def optimize_lgbm(X_train: np.ndarray, y_train: np.ndarray, n_trials: int = 50) -> dict:
    import optuna
    import lightgbm as lgb
    from sklearn.model_selection import cross_val_score

    def objective(trial: optuna.Trial) -> float:
        max_depth = trial.suggest_int("max_depth", 3, 15)
        params = {
            "objective": "multiclass",
            "num_class": 3,
            "metric": "multi_logloss",
            "boosting_type": "gbdt",
            "class_weight": "balanced",
            "verbosity": -1,
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000, step=50),
            "max_depth": max_depth,
            "num_leaves": trial.suggest_int("num_leaves", 10, max(10, min(2**max_depth, 256))),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.6, 1.0),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 10.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 10.0),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        }
        model = lgb.LGBMClassifier(**params)
        scores = cross_val_score(model, X_train, y_train, cv=3, scoring="f1_macro", n_jobs=1)
        return scores.mean()

    study = optuna.create_study(
        direction="maximize",
        pruner=optuna.pruners.MedianPruner(),
        study_name="lgbm_optimization",
    )
    study.optimize(objective, n_trials=n_trials)

    best = study.best_params
    best.update({
        "objective": "multiclass",
        "num_class": 3,
        "metric": "multi_logloss",
        "boosting_type": "gbdt",
        "class_weight": "balanced",
        "verbosity": -1,
    })
    return best


def evaluate(model: object, X_test: np.ndarray, y_test: np.ndarray, logger: logging.Logger | None = None) -> dict:
    from sklearn.metrics import accuracy_score
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, target_names=["alpha", "beta", "gamma"], output_dict=True)
    cm = confusion_matrix(y_test, y_pred)
    return {"accuracy": accuracy_score(y_test, y_pred), "report": report, "confusion_matrix": cm}
