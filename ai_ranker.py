"""
ai_ranker.py
============
AI-assisted corrective-action prioritization for the
Green ICT Decision Support System.

Pipeline:
    priority_rules + action_rules + gap_analysis
        -> AHP criteria weights
        -> TOPSIS reference ranking
        -> RandomForest learned scorer
        -> ranked corrective actions + explanation
"""

from pathlib import Path
import csv
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, cross_val_score


BASE_DIR = Path(__file__).resolve().parent
PRIORITY_RULES_FILE = BASE_DIR / "priority_rules.csv"
ACTION_RULES_FILE   = BASE_DIR / "action_rules.csv"
GAP_RULES_FILE      = BASE_DIR / "gap_analysis.csv"


# ==================================================================
# CSV HELPERS
# ==================================================================
def _read_csv(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _num(value, default=3):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


# ==================================================================
# 1. AHP  — derive criteria weights + consistency check
# ==================================================================
CRITERIA = ["gap_severity", "barrier_severity",
            "environmental_impact", "implementation_feasibility"]

# Pairwise judgement matrix (Saaty scale).
# Justification: gap & barrier severity dominate priority; env. impact
# equal; feasibility is a moderating, not dominant, factor.
AHP_PAIRWISE = np.array([
    [1.0,  2.0,  2.0,  3.0],
    [0.5,  1.0,  1.0,  2.0],
    [0.5,  1.0,  1.0,  2.0],
    [1/3,  0.5,  0.5,  1.0],
])

RI_TABLE = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90,
            5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}


def ahp_weights(matrix=AHP_PAIRWISE):
    """Return (weights, lambda_max, CI, CR). CR < 0.10 => consistent."""
    n = matrix.shape[0]
    vals, vecs = np.linalg.eig(matrix)
    k = int(np.argmax(vals.real))
    lambda_max = float(vals.real[k])
    w = vecs[:, k].real
    w = w / w.sum()
    ci = (lambda_max - n) / (n - 1)
    cr = ci / RI_TABLE[n] if RI_TABLE[n] else 0.0
    return w, lambda_max, ci, cr


# ==================================================================
# 2. TOPSIS — reference ranking (all criteria are "benefit" criteria)
# ==================================================================
def topsis_scores(score_matrix, weights):
    """
    score_matrix : (n_actions, 4)  raw GS/BS/EI/IF in [1,5]
    weights      : (4,)  AHP weights
    returns      : closeness coefficient in [0,1]  (higher = higher priority)
    """
    denom = np.sqrt((score_matrix ** 2).sum(axis=0))
    denom[denom == 0] = 1.0
    norm = score_matrix / denom
    weighted = norm * weights
    ideal_best  = weighted.max(axis=0)
    ideal_worst = weighted.min(axis=0)
    d_best  = np.sqrt(((weighted - ideal_best)  ** 2).sum(axis=1))
    d_worst = np.sqrt(((weighted - ideal_worst) ** 2).sum(axis=1))
    s = d_best + d_worst
    s[s == 0] = 1.0
    return d_worst / s


# ==================================================================
# 3. FEATURE ENGINEERING
# ==================================================================
GAP_TYPE_VOCAB = [
    "measurement gap", "comparability gap", "disclosure gap",
    "evidence gap", "implementation gap", "performance gap",
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
    + [f"gaptype_{g.replace(' ', '_')}" for g in GAP_TYPE_VOCAB]
    + [f"barrier_{b.replace(' ', '_')}" for b in BARRIER_VOCAB]
    + ["regulatory_dependency",
       "actor_btrc", "actor_government",
       "actor_operator", "actor_energy"]
)


def _multi_hot(text, vocab):
    text = str(text or "").lower()
    return [1.0 if term in text else 0.0 for term in vocab]


def _actor_flags(actor_text):
    t = str(actor_text or "").lower()
    return [
        1.0 if "btrc" in t else 0.0,
        1.0 if "government" in t else 0.0,
        1.0 if "operator" in t else 0.0,
        1.0 if "energy" in t else 0.0,
    ]


def build_feature_table():
    """
    Join priority_rules + action_rules + gap_analysis into one
    feature matrix. Returns (records, X, y_reference, weights, ahp_info).
    """
    priority = _read_csv(PRIORITY_RULES_FILE)
    actions  = {r["action_id"].strip(): r for r in _read_csv(ACTION_RULES_FILE)}
    gaps     = {r["gap_id"].strip():    r for r in _read_csv(GAP_RULES_FILE)}

    records, rows = [], []

    for pr in priority:
        gid = pr["gap_id"].strip().upper()
        aid = pr["action_id"].strip().upper()
        action = actions.get(aid, {})
        gap    = gaps.get(gid, {})

        # --- four MCDM scores ---
        scores = [
            _num(pr["gap_severity"]),
            _num(pr["barrier_severity"]),
            _num(pr["environmental_impact"]),
            _num(pr["implementation_feasibility"]),
        ]

        # --- categorical / textual features ---
        gap_type   = gap.get("gap_type", "")
        barrier    = action.get("barrier_category", "")
        reg_dep    = 1.0 if str(action.get("regulatory_dependency", "")).strip().lower() == "yes" else 0.0
        actor_flags = _actor_flags(action.get("responsible_actor", ""))

        feature = (
            scores
            + _multi_hot(gap_type, GAP_TYPE_VOCAB)
            + _multi_hot(barrier, BARRIER_VOCAB)
            + [reg_dep]
            + actor_flags
        )

        records.append({
            "gap_id": gid, "action_id": aid,
            "gap": gap.get("gap", ""),
            "gap_type": gap_type,
            "barrier_category": barrier,
            "corrective_action": action.get("corrective_action", ""),
            "responsible_actor": action.get("responsible_actor", ""),
            "regulatory_dependency": action.get("regulatory_dependency", ""),
            "GS": scores[0], "BS": scores[1], "EI": scores[2], "IF": scores[3],
        })
        rows.append(feature)

    X = np.asarray(rows, dtype=float)

    w, lmax, ci, cr = ahp_weights()
    y_ref = topsis_scores(X[:, :4], w)

    return records, X, y_ref, w, {"lambda_max": lmax, "CI": ci, "CR": cr}


# ==================================================================
# 4. AUGMENTATION + MODEL TRAINING
# ==================================================================
def _augment(X, weights, n_copies=300, noise=0.30, seed=42):
    """
    Perturb the 4 MCDM scores, recompute TOPSIS reference.
    Gives the RF enough samples to learn smooth non-linear behaviour.
    """
    rng = np.random.default_rng(seed)
    X_all, y_all = [X], [topsis_scores(X[:, :4], weights)]

    for _ in range(n_copies):
        Xn = X.copy()
        jitter = rng.normal(0, noise, size=(X.shape[0], 4))
        Xn[:, :4] = np.clip(Xn[:, :4] + jitter, 1.0, 5.0)
        X_all.append(Xn)
        y_all.append(topsis_scores(Xn[:, :4], weights))

    return np.vstack(X_all), np.concatenate(y_all)


def train_ranker(X, y, seed=42):
    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=2,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X, y)
    return model


def cross_validate_ranker(X, y, cv=5, seed=42):
    model = RandomForestRegressor(
        n_estimators=200, max_depth=8, random_state=seed, n_jobs=-1,
    )
    scores = cross_val_score(model, X, y, cv=cv,
                             scoring="neg_mean_absolute_error")
    return {"cv_mae": float(-scores.mean()),
            "cv_mae_std": float(scores.std())}


# ==================================================================
# 5. PRIORITY BAND
# ==================================================================
def priority_band(score):
    if score >= 0.75: return "Very High"
    if score >= 0.55: return "High"
    if score >= 0.35: return "Medium"
    return "Low"


# ==================================================================
# 6. FULL RANKING PIPELINE
# ==================================================================
_RANKER_CACHE = None


def _get_ranker():
    global _RANKER_CACHE
    if _RANKER_CACHE is not None:
        return _RANKER_CACHE

    records, X, y_ref, w, ahp_info = build_feature_table()
    Xa, ya = _augment(X, w)
    model = train_ranker(Xa, ya)

    _RANKER_CACHE = {
        "records": records,
        "X": X,
        "y_ref": y_ref,
        "weights": w,
        "ahp": ahp_info,
        "model": model,
        "cv": cross_validate_ranker(Xa, ya),
    }
    return _RANKER_CACHE


def rank_actions():
    """
    Returns a list of dicts (one per corrective action) sorted by
    AI-predicted priority, highest first, with explanations.
    """
    ctx = _get_ranker()
    records, X, model, w, y_ref = (
        ctx["records"], ctx["X"], ctx["model"], ctx["weights"], ctx["y_ref"]
    )

    y_pred = model.predict(X)
    order = np.argsort(-y_pred)

    importances = sorted(
        zip(FEATURE_NAMES, model.feature_importances_),
        key=lambda t: -t[1],
    )[:5]

    ranked = []
    for rank, idx in enumerate(order, start=1):
        r = dict(records[idx])
        r["ai_priority_score"] = round(float(y_pred[idx]), 4)
        r["reference_topsis_score"] = round(float(y_ref[idx]), 4)
        r["priority_level"] = priority_band(float(y_pred[idx]))
        r["rank"] = rank
        r["ahp_weights"] = {
            "GS": round(w[0], 3), "BS": round(w[1], 3),
            "EI": round(w[2], 3), "IF": round(w[3], 3),
        }
        r["explanation"] = (
            f"Ranked #{rank} because GS={r['GS']}, BS={r['BS']}, "
            f"EI={r['EI']}, IF={r['IF']} combined with gap type "
            f"'{r['gap_type']}' and barrier '{r['barrier_category']}'."
        )
        ranked.append(r)

    return {
        "ranked_actions": ranked,
        "ahp": ctx["ahp"],
        "cv_mae": ctx["cv"]["cv_mae"],
        "top_features": [{"feature": f, "importance": round(float(i), 4)}
                         for f, i in importances],
    }


# ==================================================================
# 7. SCORE A BRAND-NEW GAP (no priority_rules entry needed)
# ==================================================================
def predict_new_action(gap_severity, barrier_severity,
                       environmental_impact, implementation_feasibility,
                       gap_type="", barrier_category="",
                       regulatory_dependency="No",
                       responsible_actor=""):
    """
    Use the trained AI model to prioritise a corrective action that
    was not part of the original hand-coded rule set.
    """
    ctx = _get_ranker()
    feature = (
        [gap_severity, barrier_severity,
         environmental_impact, implementation_feasibility]
        + _multi_hot(gap_type, GAP_TYPE_VOCAB)
        + _multi_hot(barrier_category, BARRIER_VOCAB)
        + [1.0 if str(regulatory_dependency).lower() == "yes" else 0.0]
        + _actor_flags(responsible_actor)
    )
    score = float(ctx["model"].predict(np.asarray([feature], dtype=float))[0])
    return {"ai_priority_score": round(score, 4),
            "priority_level": priority_band(score)}


# ==================================================================
# 8. CLI TEST
# ==================================================================
if __name__ == "__main__":
    result = rank_actions()
    w = result["ahp"]
    print("=" * 68)
    print("AHP CRITERIA WEIGHTS")
    print("=" * 68)
    for name, weight in zip(CRITERIA, ahp_weights()[0]):
        print(f"  {name:30s} {weight:.3f}")
    print(f"  lambda_max = {w['lambda_max']:.4f} | "
          f"CI = {w['CI']:.4f} | CR = {w['CR']:.4f}")
    print(f"  cross-validated MAE = {result['cv_mae']:.4f}")

    print("\n" + "=" * 68)
    print("AI-RANKED CORRECTIVE ACTIONS")
    print("=" * 68)
    for a in result["ranked_actions"]:
        print(f"#{a['rank']:2d}  {a['action_id']}  "
              f"{a['ai_priority_score']:.3f}  "
              f"[{a['priority_level']:9s}]  {a['gap_id']}  "
              f"{a['corrective_action'][:55]}")

    print("\nTop predictive features:")
    for f in result["top_features"]:
        print(f"  {f['feature']:35s} {f['importance']:.4f}")