"""
model_comparison.py
===================
Compares three regression models for Green ICT corrective-action
prioritization: Random Forest, Gaussian Process, Gradient Boosting.

Reuses feature engineering and TOPSIS reference from ai_ranker.py.
"""

import csv
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel
from sklearn.model_selection import KFold, cross_val_score

from ai_ranker import build_feature_table, _augment


def get_models():
    """Return the three candidate models."""
    return {
        "Random Forest": RandomForestRegressor(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=1,
        ),
        "Gaussian Process": GaussianProcessRegressor(
            kernel=ConstantKernel(1.0, (1e-2, 1e2))
                   * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2)),
            alpha=1e-3,
            normalize_y=True,
            random_state=42,
            optimizer=None,          # <-- skip hyperparameter fitting
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            random_state=42,
        ),
    }


def compare_models(cv_folds=5, seed=42):
    """Train + evaluate all three models with K-fold CV."""
    records, X, y_ref, weights, ahp_info = build_feature_table()
    Xa, ya = _augment(X, weights)

    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=seed)

    results = []
    for name, model in get_models().items():
        print(f"  Evaluating: {name} ...", end=" ", flush=True)
        try:
            mae = -cross_val_score(
                model, Xa, ya, cv=kf,
                scoring="neg_mean_absolute_error", n_jobs=1,
            )
            r2 = cross_val_score(
                model, Xa, ya, cv=kf,
                scoring="r2", n_jobs=1,
            )
            results.append({
                "model": name,
                "cv_mae": float(mae.mean()),
                "cv_mae_std": float(mae.std()),
                "cv_r2": float(r2.mean()),
                "cv_r2_std": float(r2.std()),
            })
            print(f"done (MAE={mae.mean():.4f})")
        except Exception as exc:
            print(f"FAILED: {exc}")
            results.append({
                "model": name,
                "cv_mae": None,
                "cv_mae_std": None,
                "cv_r2": None,
                "cv_r2_std": None,
            })

    # Sort only valid results by MAE (lower is better)
    valid = [r for r in results if r["cv_mae"] is not None]
    valid.sort(key=lambda r: r["cv_mae"])
    failed = [r for r in results if r["cv_mae"] is None]
    return valid + failed


def format_console(results):
    """Print a nicely formatted table."""
    print()
    print("=" * 82)
    print("MODEL COMPARISON — 5-FOLD CROSS-VALIDATION")
    print("=" * 82)
    print(f"{'Model':<22} {'CV MAE':>11} {'± Std':>9} {'CV R²':>9} {'± Std':>9}")
    print("-" * 82)
    for r in results:
        if r["cv_mae"] is None:
            print(f"{r['model']:<22} {'FAILED':>11}")
        else:
            print(
                f"{r['model']:<22} "
                f"{r['cv_mae']:>11.4f} "
                f"{r['cv_mae_std']:>9.4f} "
                f"{r['cv_r2']:>9.4f} "
                f"{r['cv_r2_std']:>9.4f}"
            )
    print("=" * 82)
    if results and results[0]["cv_mae"] is not None:
        best = results[0]
        print(f"\nBest model (lowest MAE): {best['model']} "
              f"(CV MAE = {best['cv_mae']:.4f})")
    print(f"Note: Random Forest was retained as the primary model "
          f"because it provides native feature-importance output,\n"
          f"which is required for explainability of the priority ranking.\n")


def export_csv(results, filename="model_comparison_results.csv"):
    """Save results to CSV for the paper."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["model", "cv_mae", "cv_mae_std", "cv_r2", "cv_r2_std"],
        )
        w.writeheader()
        w.writerows(results)
    print(f"Saved: {filename}")


if __name__ == "__main__":
    print("Running model comparison (this may take up to 30 seconds)...\n")
    results = compare_models()
    format_console(results)
    export_csv(results)