"""
ai_ranker.py
============
AI-assisted corrective-action prioritization for the
Green ICT Decision Support System.

Pipeline:
    priority_rules + action_rules + gap_analysis
        -> AHP criteria weights
        -> TOPSIS reference ranking
        -> candidate regression models
        -> 5-fold CV model selection
        -> ranked corrective actions + explanation
"""

from pathlib import Path
import csv
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, cross_val_score


BASE_DIR = Path(__file__).resolve().parent
PRIORITY_RULES_FILE = BASE_DIR / "priority_rules.csv"
ACTION_RULES_FILE = BASE_DIR / "action_rules.csv"
GAP_RULES_FILE = BASE_DIR / "gap_analysis.csv"


# ==================================================================
# CSV HELPERS
# ==================================================================

def _read_csv(path):
    if not path.exists():
        return []

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(csv.DictReader(f))


def _num(value, default=3):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


# ==================================================================
# 1. AHP — DERIVE CRITERIA WEIGHTS + CONSISTENCY CHECK
# ==================================================================

CRITERIA = [
    "gap_severity",
    "barrier_severity",
    "environmental_impact",
    "implementation_feasibility"
]


# Pairwise judgement matrix (Saaty scale).
#
# Justification:
# Gap severity and barrier severity are given higher importance.
# Environmental impact has equal importance to barrier severity.
# Implementation feasibility is treated as a moderating factor.
#
AHP_PAIRWISE = np.array([
    [1.0,  2.0,  2.0,  3.0],
    [0.5,  1.0,  1.0,  2.0],
    [0.5,  1.0,  1.0,  2.0],
    [1/3,  0.5,  0.5,  1.0],
])


RI_TABLE = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45
}


def ahp_weights(matrix=AHP_PAIRWISE):
    """
    Return:

        weights
        lambda_max
        CI
        CR

    CR < 0.10 indicates acceptable consistency.
    """

    n = matrix.shape[0]

    vals, vecs = np.linalg.eig(matrix)

    k = int(np.argmax(vals.real))

    lambda_max = float(
        vals.real[k]
    )

    w = vecs[:, k].real

    w = w / w.sum()

    ci = (
        lambda_max - n
    ) / (n - 1)

    cr = (
        ci / RI_TABLE[n]
        if RI_TABLE[n]
        else 0.0
    )

    return (
        w,
        lambda_max,
        ci,
        cr
    )


# ==================================================================
# 2. TOPSIS — REFERENCE RANKING
# ==================================================================

def topsis_scores(
    score_matrix,
    weights
):
    """
    score_matrix:
        (n_actions, 4)

        Raw GS / BS / EI / IF scores in [1, 5].

    weights:
        AHP weights for the four criteria.

    Returns:
        TOPSIS closeness coefficient in [0, 1].

    Higher value = higher priority.
    """

    denom = np.sqrt(
        (score_matrix ** 2).sum(axis=0)
    )

    denom[
        denom == 0
    ] = 1.0

    norm = (
        score_matrix / denom
    )

    weighted = (
        norm * weights
    )

    ideal_best = weighted.max(
        axis=0
    )

    ideal_worst = weighted.min(
        axis=0
    )

    d_best = np.sqrt(
        (
            (weighted - ideal_best) ** 2
        ).sum(axis=1)
    )

    d_worst = np.sqrt(
        (
            (weighted - ideal_worst) ** 2
        ).sum(axis=1)
    )

    s = (
        d_best + d_worst
    )

    s[
        s == 0
    ] = 1.0

    return (
        d_worst / s
    )


# ==================================================================
# 3. FEATURE ENGINEERING
# ==================================================================

GAP_TYPE_VOCAB = [
    "measurement gap",
    "comparability gap",
    "disclosure gap",
    "evidence gap",
    "implementation gap",
    "performance gap",
    "policy tension",
]


BARRIER_VOCAB = [
    "measurement and disclosure",
    "renewable energy implementation",
    "infrastructure and operations",
    "policy and regulation",
    "organizational implementation",
]


FEATURE_NAMES = (
    CRITERIA
    + [
        f"gaptype_{g.replace(' ', '_')}"
        for g in GAP_TYPE_VOCAB
    ]
    + [
        f"barrier_{b.replace(' ', '_')}"
        for b in BARRIER_VOCAB
    ]
    + [
        "regulatory_dependency",
        "actor_btrc",
        "actor_government",
        "actor_operator",
        "actor_energy"
    ]
)


def _multi_hot(
    text,
    vocab
):
    text = str(
        text or ""
    ).lower()

    return [
        1.0 if term in text else 0.0
        for term in vocab
    ]


def _actor_flags(
    actor_text
):
    t = str(
        actor_text or ""
    ).lower()

    return [
        1.0 if "btrc" in t else 0.0,
        1.0 if "government" in t else 0.0,
        1.0 if "operator" in t else 0.0,
        1.0 if "energy" in t else 0.0,
    ]


def build_feature_table():
    """
    Join priority_rules + action_rules + gap_analysis
    into one feature matrix.

    Returns:

        records
        X
        y_reference
        weights
        ahp_info
    """

    priority = _read_csv(
        PRIORITY_RULES_FILE
    )

    actions = {
        r["action_id"].strip(): r
        for r in _read_csv(
            ACTION_RULES_FILE
        )
    }

    gaps = {
        r["gap_id"].strip(): r
        for r in _read_csv(
            GAP_RULES_FILE
        )
    }

    records = []
    rows = []

    for pr in priority:

        gid = pr[
            "gap_id"
        ].strip().upper()

        aid = pr[
            "action_id"
        ].strip().upper()

        action = actions.get(
            aid,
            {}
        )

        gap = gaps.get(
            gid,
            {}
        )

        # ------------------------------------------------------
        # Four MCDM scores
        # ------------------------------------------------------

        scores = [
            _num(
                pr["gap_severity"]
            ),

            _num(
                pr["barrier_severity"]
            ),

            _num(
                pr["environmental_impact"]
            ),

            _num(
                pr["implementation_feasibility"]
            ),
        ]

        # ------------------------------------------------------
        # Categorical / textual features
        # ------------------------------------------------------

        gap_type = gap.get(
            "gap_type",
            ""
        )

        barrier = action.get(
            "barrier_category",
            ""
        )

        reg_dep = (
            1.0
            if str(
                action.get(
                    "regulatory_dependency",
                    ""
                )
            ).strip().lower() == "yes"
            else 0.0
        )

        actor_flags = _actor_flags(
            action.get(
                "responsible_actor",
                ""
            )
        )

        feature = (
            scores
            + _multi_hot(
                gap_type,
                GAP_TYPE_VOCAB
            )
            + _multi_hot(
                barrier,
                BARRIER_VOCAB
            )
            + [reg_dep]
            + actor_flags
        )

        records.append({
            "gap_id": gid,
            "action_id": aid,

            "gap": gap.get(
                "gap",
                ""
            ),

            "gap_type": gap_type,

            "barrier_category": barrier,

            "corrective_action": action.get(
                "corrective_action",
                ""
            ),

            "responsible_actor": action.get(
                "responsible_actor",
                ""
            ),

            "regulatory_dependency": action.get(
                "regulatory_dependency",
                ""
            ),

            "GS": scores[0],
            "BS": scores[1],
            "EI": scores[2],
            "IF": scores[3],
        })

        rows.append(
            feature
        )

    X = np.asarray(
        rows,
        dtype=float
    )

    # ----------------------------------------------------------
    # AHP
    # ----------------------------------------------------------

    w, lmax, ci, cr = ahp_weights()

    # ----------------------------------------------------------
    # TOPSIS reference scores
    # ----------------------------------------------------------

    y_ref = topsis_scores(
        X[:, :4],
        w
    )

    # ----------------------------------------------------------
    # FIX:
    # Include AHP weights inside ahp_info.
    #
    # This allows the Flask frontend to access:
    #
    # result.ai_meta.ahp.weights.GS
    # result.ai_meta.ahp.weights.BS
    # result.ai_meta.ahp.weights.EI
    # result.ai_meta.ahp.weights.IF
    # ----------------------------------------------------------

    ahp_info = {
        "weights": {
            "GS": round(
                float(w[0]),
                4
            ),

            "BS": round(
                float(w[1]),
                4
            ),

            "EI": round(
                float(w[2]),
                4
            ),

            "IF": round(
                float(w[3]),
                4
            ),
        },

        "lambda_max": round(
            float(lmax),
            4
        ),

        "CI": round(
            float(ci),
            4
        ),

        "CR": round(
            float(cr),
            4
        ),
    }

    return (
        records,
        X,
        y_ref,
        w,
        ahp_info
    )


# ==================================================================
# 4. AUGMENTATION + MODEL TRAINING
# ==================================================================

def _augment(
    X,
    weights,
    n_copies=300,
    noise=0.30,
    seed=42
):
    """
    Perturb the four MCDM scores and recompute TOPSIS.

    Original observations:
        8

    Synthetic observations:
        8 × 300 = 2400

    Total:
        2408
    """

    rng = np.random.default_rng(
        seed
    )

    X_all = [
        X
    ]

    y_all = [
        topsis_scores(
            X[:, :4],
            weights
        )
    ]

    for _ in range(
        n_copies
    ):

        Xn = X.copy()

        jitter = rng.normal(
            0,
            noise,
            size=(
                X.shape[0],
                4
            )
        )

        Xn[:, :4] = np.clip(
            Xn[:, :4] + jitter,
            1.0,
            5.0
        )

        X_all.append(
            Xn
        )

        y_all.append(
            topsis_scores(
                Xn[:, :4],
                weights
            )
        )

    return (
        np.vstack(X_all),
        np.concatenate(y_all)
    )


def train_ranker(
    X,
    y,
    seed=42
):
    """
    Train a Random Forest ranker.

    This helper is retained for compatibility.
    """

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=2,
        random_state=seed,
        n_jobs=1,
    )

    model.fit(
        X,
        y
    )

    return model


def cross_validate_ranker(
    X,
    y,
    cv=5,
    seed=42
):
    """
    Cross-validate a Random Forest model.

    This helper is retained for compatibility.
    """

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        random_state=seed,
        n_jobs=1,
    )

    scores = cross_val_score(
        model,
        X,
        y,
        cv=cv,
        scoring="neg_mean_absolute_error",
        n_jobs=1
    )

    return {
        "cv_mae": float(
            -scores.mean()
        ),

        "cv_mae_std": float(
            scores.std()
        )
    }


# ==================================================================
# 5. PRIORITY BAND
# ==================================================================

def priority_band(
    score
):

    if score >= 0.75:
        return "Very High"

    if score >= 0.55:
        return "High"

    if score >= 0.35:
        return "Medium"

    return "Low"


# ==================================================================
# 6. MODEL CANDIDATES
# ==================================================================

_RANKER_CACHE = None


def get_model_candidates():
    """
    Return the three candidate regression models.

    The best model is selected using 5-fold CV MAE.
    """

    from sklearn.ensemble import (
        GradientBoostingRegressor
    )

    from sklearn.gaussian_process import (
        GaussianProcessRegressor
    )

    from sklearn.gaussian_process.kernels import (
        RBF,
        ConstantKernel
    )

    return {

        "Random Forest":
            RandomForestRegressor(
                n_estimators=300,
                max_depth=8,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=1,
            ),

        "Gaussian Process":
            GaussianProcessRegressor(
                kernel=(
                    ConstantKernel(
                        1.0,
                        (1e-2, 1e2)
                    )
                    *
                    RBF(
                        length_scale=1.0,
                        length_scale_bounds=(
                            1e-2,
                            1e2
                        )
                    )
                ),

                alpha=1e-3,

                normalize_y=True,

                random_state=42,

                optimizer=None,
            ),

        "Gradient Boosting":
            GradientBoostingRegressor(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                random_state=42,
            ),
    }


# ==================================================================
# 7. MODEL SELECTION
# ==================================================================

def select_best_model(
    Xa,
    ya,
    cv=5
):
    """
    Compare candidate models using 5-fold CV MAE.

    The model with the lowest CV MAE is selected and
    then trained on the complete augmented dataset.
    """

    kf = KFold(
        n_splits=cv,
        shuffle=True,
        random_state=42
    )

    best_name = None

    best_model = None

    best_mae = float(
        "inf"
    )

    for name, model in get_model_candidates().items():

        try:

            mae = -cross_val_score(
                model,
                Xa,
                ya,
                cv=kf,
                scoring="neg_mean_absolute_error",
                n_jobs=1,
            ).mean()

        except Exception as exc:

            print(
                f"  [model selection] "
                f"{name}: FAILED ({exc})"
            )

            continue

        print(
            f"  [model selection] "
            f"{name}: CV MAE = {mae:.4f}"
        )

        if mae < best_mae:

            best_mae = mae

            best_name = name

            best_model = model

    if best_model is None:

        raise RuntimeError(
            "No regression model could be selected."
        )

    # ----------------------------------------------------------
    # Train selected model on full augmented dataset
    # ----------------------------------------------------------

    best_model.fit(
        Xa,
        ya
    )

    print(
        f"  [model selection] "
        f"Selected: {best_name} "
        f"(CV MAE = {best_mae:.4f})\n"
    )

    return (
        best_name,
        best_model,
        best_mae
    )


# ==================================================================
# 8. RANKER CACHE
# ==================================================================

def _get_ranker():

    global _RANKER_CACHE

    if _RANKER_CACHE is not None:
        return _RANKER_CACHE

    # ----------------------------------------------------------
    # Build feature table
    # ----------------------------------------------------------

    (
        records,
        X,
        y_ref,
        w,
        ahp_info
    ) = build_feature_table()

    # ----------------------------------------------------------
    # Augment data
    # ----------------------------------------------------------

    Xa, ya = _augment(
        X,
        w
    )

    # ----------------------------------------------------------
    # Model selection
    # ----------------------------------------------------------

    (
        best_name,
        model,
        best_mae
    ) = select_best_model(
        Xa,
        ya
    )

    # ----------------------------------------------------------
    # Cache everything
    # ----------------------------------------------------------

    _RANKER_CACHE = {

        "records":
            records,

        "X":
            X,

        "y_ref":
            y_ref,

        "weights":
            w,

        "ahp":
            ahp_info,

        "model":
            model,

        "selected_model_name":
            best_name,

        "cv": {
            "cv_mae":
                best_mae,

            "cv_mae_std":
                0.0,
        },
    }

    return _RANKER_CACHE


# ==================================================================
# 9. FULL AI RANKING PIPELINE
# ==================================================================

def rank_actions():
    """
    Return one result per corrective action, sorted by
    AI-predicted priority.

    Also returns:

        AHP weights
        lambda_max
        CI
        CR
        CV MAE
        top predictive features
    """

    ctx = _get_ranker()

    records = ctx[
        "records"
    ]

    X = ctx[
        "X"
    ]

    model = ctx[
        "model"
    ]

    w = ctx[
        "weights"
    ]

    y_ref = ctx[
        "y_ref"
    ]

    # ----------------------------------------------------------
    # Predict priority scores
    # ----------------------------------------------------------

    y_pred = model.predict(
        X
    )

    order = np.argsort(
        -y_pred
    )

    # ----------------------------------------------------------
    # Feature importance
    # ----------------------------------------------------------

    importances = sorted(
        zip(
            FEATURE_NAMES,
            model.feature_importances_
        ),
        key=lambda t: -t[1]
    )[:5]

    # ----------------------------------------------------------
    # Build ranked results
    # ----------------------------------------------------------

    ranked = []

    for rank, idx in enumerate(
        order,
        start=1
    ):

        r = dict(
            records[idx]
        )

        r[
            "ai_priority_score"
        ] = round(
            float(
                y_pred[idx]
            ),
            4
        )

        r[
            "reference_topsis_score"
        ] = round(
            float(
                y_ref[idx]
            ),
            4
        )

        r[
            "priority_level"
        ] = priority_band(
            float(
                y_pred[idx]
            )
        )

        r[
            "rank"
        ] = rank

        # ------------------------------------------------------
        # AHP weights attached to every action
        # ------------------------------------------------------

        r[
            "ahp_weights"
        ] = {

            "GS":
                round(
                    float(w[0]),
                    4
                ),

            "BS":
                round(
                    float(w[1]),
                    4
                ),

            "EI":
                round(
                    float(w[2]),
                    4
                ),

            "IF":
                round(
                    float(w[3]),
                    4
                ),
        }

        # ------------------------------------------------------
        # Explanation
        # ------------------------------------------------------

        r[
            "explanation"
        ] = (
            f"Ranked #{rank} because "
            f"GS={r['GS']}, "
            f"BS={r['BS']}, "
            f"EI={r['EI']}, "
            f"IF={r['IF']} combined with "
            f"gap type '{r['gap_type']}' "
            f"and barrier "
            f"'{r['barrier_category']}'."
        )

        ranked.append(
            r
        )

    # ----------------------------------------------------------
    # Top predictive features
    # ----------------------------------------------------------

    top_features = [
        {
            "feature": feature,
            "importance": round(
                float(importance),
                4
            )
        }

        for feature, importance
        in importances
    ]

    # ----------------------------------------------------------
    # FINAL RETURN
    # ----------------------------------------------------------

    return {

        "ranked_actions":
            ranked,

        # IMPORTANT:
        # This now contains BOTH:
        #   weights
        #   lambda_max
        #   CI
        #   CR
        #
        "ahp":
            ctx[
                "ahp"
            ],

        "cv_mae":
            ctx[
                "cv"
            ][
                "cv_mae"
            ],

        "top_features":
            top_features,
    }


# ==================================================================
# 10. SCORE A BRAND-NEW GAP
# ==================================================================

def predict_new_action(
    gap_severity,
    barrier_severity,
    environmental_impact,
    implementation_feasibility,
    gap_type="",
    barrier_category="",
    regulatory_dependency="No",
    responsible_actor=""
):
    """
    Use the trained AI model to prioritise a corrective action
    that was not part of the original hand-coded rule set.
    """

    ctx = _get_ranker()

    feature = (

        [
            gap_severity,
            barrier_severity,
            environmental_impact,
            implementation_feasibility
        ]

        + _multi_hot(
            gap_type,
            GAP_TYPE_VOCAB
        )

        + _multi_hot(
            barrier_category,
            BARRIER_VOCAB
        )

        + [
            1.0
            if str(
                regulatory_dependency
            ).lower() == "yes"
            else 0.0
        ]

        + _actor_flags(
            responsible_actor
        )
    )

    score = float(
        ctx[
            "model"
        ].predict(
            np.asarray(
                [feature],
                dtype=float
            )
        )[0]
    )

    return {

        "ai_priority_score":
            round(
                score,
                4
            ),

        "priority_level":
            priority_band(
                score
            )
    }


# ==================================================================
# 11. CLI TEST
# ==================================================================

if __name__ == "__main__":

    result = rank_actions()

    w = result[
        "ahp"
    ]

    print(
        "=" * 68
    )

    print(
        "AHP CRITERIA WEIGHTS"
    )

    print(
        "=" * 68
    )

    # ----------------------------------------------------------
    # Display AHP weights
    # ----------------------------------------------------------

    weights = w[
        "weights"
    ]

    print(
        f"  {'gap_severity':30s} "
        f"{weights['GS']:.4f}"
    )

    print(
        f"  {'barrier_severity':30s} "
        f"{weights['BS']:.4f}"
    )

    print(
        f"  {'environmental_impact':30s} "
        f"{weights['EI']:.4f}"
    )

    print(
        f"  {'implementation_feasibility':30s} "
        f"{weights['IF']:.4f}"
    )

    print(
        f"  lambda_max = "
        f"{w['lambda_max']:.4f} | "
        f"CI = "
        f"{w['CI']:.4f} | "
        f"CR = "
        f"{w['CR']:.4f}"
    )

    print(
        f"  cross-validated MAE = "
        f"{result['cv_mae']:.4f}"
    )

    print(
        "\n"
        + "=" * 68
    )

    print(
        "AI-RANKED CORRECTIVE ACTIONS"
    )

    print(
        "=" * 68
    )

    for a in result[
        "ranked_actions"
    ]:

        print(
            f"#{a['rank']:2d}  "
            f"{a['action_id']}  "
            f"{a['ai_priority_score']:.3f}  "
            f"[{a['priority_level']:9s}]  "
            f"{a['gap_id']}  "
            f"{a['corrective_action'][:55]}"
        )

    print(
        "\nTop predictive features:"
    )

    for f in result[
        "top_features"
    ]:

        print(
            f"  "
            f"{f['feature']:35s} "
            f"{f['importance']:.4f}"
        )