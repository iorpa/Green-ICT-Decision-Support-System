from flask import Flask, request, jsonify, send_from_directory, session
from functools import wraps
from pathlib import Path
import csv
import secrets

from model import run_model


# ============================================================
# BASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)

# Development/demo secret key.
# For production, use an environment variable instead.
app.secret_key = "green-ict-demo-secret-key-2026"


# ============================================================
# FILE CONFIGURATION
# ============================================================

OPERATOR_DATA_FILE = BASE_DIR / "operator_data.csv"


OPERATOR_DATA_HEADERS = [
    "year",
    "operator",
    "area",
    "indicator",
    "value",
    "unit",
    "source",
    "notes",
]


# ============================================================
# OPERATOR LOGIN ACCOUNTS
# ============================================================

OPERATOR_ACCOUNTS = {
    "Grameenphone": "GP2026",
    "Banglalink": "BL2026",
    "Robi": "RO2026",
}


# ============================================================
# CSV FUNCTIONS
# ============================================================

def create_operator_csv():
    """
    Create operator_data.csv if it does not already exist.
    """

    if not OPERATOR_DATA_FILE.exists():

        with OPERATOR_DATA_FILE.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(file)
            writer.writerow(OPERATOR_DATA_HEADERS)


def read_operator_rows():
    """
    Read all operator evidence rows from CSV.
    """

    create_operator_csv()

    with OPERATOR_DATA_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        return list(csv.DictReader(file))


# ============================================================
# OPERATOR NORMALIZATION
# ============================================================

def normalize_operator(value):
    """
    Normalize operator names for safe comparison.
    """

    return str(value or "").strip().casefold()


def operator_matches(row_operator, session_operator):
    """
    Check whether a CSV row belongs to the logged-in operator.
    """

    return (
        normalize_operator(row_operator)
        == normalize_operator(session_operator)
    )


# ============================================================
# LOGIN DECORATOR
# ============================================================

def operator_required(function):
    """
    Require an authenticated operator for protected routes.
    """

    @wraps(function)
    def wrapper(*args, **kwargs):

        if session.get("role") != "operator":

            return jsonify({
                "success": False,
                "message": "Operator login required.",
            }), 401

        if not session.get("operator"):

            return jsonify({
                "success": False,
                "message": "Operator session is missing.",
            }), 401

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/login")
def login():

    data = request.get_json(silent=True) or {}

    username = str(
        data.get("username", "")
    ).strip()

    password = str(
        data.get("password", "")
    )

    for operator, expected_password in OPERATOR_ACCOUNTS.items():

        if username.casefold() == operator.casefold():

            if secrets.compare_digest(
                password,
                expected_password,
            ):

                session.clear()

                session["role"] = "operator"
                session["operator"] = operator
                session["username"] = operator

                return jsonify({
                    "success": True,
                    "role": "operator",
                    "operator": operator,
                    "message": f"{operator} login successful.",
                })

            break

    return jsonify({
        "success": False,
        "message": "Invalid username or password.",
    }), 401


# ============================================================
# LOGOUT
# ============================================================

@app.post("/api/logout")
def logout():

    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully.",
    })


# ============================================================
# SESSION
# ============================================================

@app.get("/api/session")
def get_session():

    return jsonify({
        "success": True,
        "logged_in": "role" in session,
        "role": session.get("role"),
        "operator": session.get("operator"),
        "username": session.get("username"),
    })


# ============================================================
# FRONTEND FILES
# ============================================================

@app.get("/")
def home():

    return send_from_directory(
        BASE_DIR,
        "index.html",
    )


@app.get("/style.css")
def css():

    return send_from_directory(
        BASE_DIR,
        "style.css",
    )


@app.get("/script.js")
def javascript():

    return send_from_directory(
        BASE_DIR,
        "script.js",
    )


# ============================================================
# GET OPERATOR DATA
# ============================================================

@app.get("/api/data")
@operator_required
def get_my_data():

    operator = session["operator"]

    rows = read_operator_rows()

    own_rows = [
        row
        for row in rows
        if operator_matches(
            row.get("operator", ""),
            operator,
        )
    ]

    return jsonify({
        "success": True,
        "operator": operator,
        "count": len(own_rows),
        "data": own_rows,
    })


# ============================================================
# ADD OPERATOR DATA
# ============================================================

@app.post("/add-data")
@operator_required
def add_data():

    data = request.get_json(silent=True) or {}

    operator = session["operator"]

    required_fields = [
        "year",
        "area",
        "indicator",
        "value",
        "unit",
        "source",
    ]

    missing = [
        field
        for field in required_fields
        if str(data.get(field, "")).strip() == ""
    ]

    if missing:

        return jsonify({
            "success": False,
            "message":
                "Missing required fields: "
                + ", ".join(missing),
        }), 400

    create_operator_csv()

    row = [

        str(
            data.get("year", "")
        ).strip(),

        operator,

        str(
            data.get("area", "")
        ).strip(),

        str(
            data.get("indicator", "")
        ).strip(),

        str(
            data.get("value", "")
        ).strip(),

        str(
            data.get("unit", "")
        ).strip(),

        str(
            data.get("source", "")
        ).strip(),

        str(
            data.get("notes", "")
        ).strip(),
    ]

    with OPERATOR_DATA_FILE.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)
        writer.writerow(row)

    return jsonify({
        "success": True,
        "message": "Evidence saved successfully.",
        "operator": operator,
    })


# ============================================================
# RUN GREEN ICT DECISION-SUPPORT MODEL
# ============================================================

@app.post("/api/run-model")
@operator_required
def run_operator_model():

    operator = session["operator"]

    try:

        output = run_model(
            operator=operator,
            export=False,
        )

        return jsonify({
            "success": True,
            "operator": operator,

            # Detailed/consolidated gap findings
            "findings": output.get(
                "findings",
                [],
            ),

            # Corrective-action results
            # Expected to contain A01-A08
            "results": output.get(
                "results",
                [],
            ),

            # AHP, TOPSIS, regression-model
            # comparison and ranking metadata
            "ai_meta": output.get(
                "ai_meta",
                {},
            ),
        })

    except Exception as error:

        app.logger.exception(
            "Model execution failed"
        )

        return jsonify({
            "success": False,
            "message":
                "The decision-support model could not run.",
            "error": str(error),
        }), 500


# ============================================================
# CLEAR CURRENT OPERATOR DATA
# ============================================================

@app.post("/api/clear-data")
@operator_required
def clear_my_data():

    operator = session["operator"]

    rows = read_operator_rows()

    remaining_rows = [

        row

        for row in rows

        if not operator_matches(
            row.get("operator", ""),
            operator,
        )
    ]

    with OPERATOR_DATA_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=OPERATOR_DATA_HEADERS,
        )

        writer.writeheader()
        writer.writerows(remaining_rows)

    return jsonify({
        "success": True,
        "message":
            f"All evidence for {operator} was cleared.",
    })


# ============================================================
# APPLICATION STATUS
# ============================================================

@app.get("/api/status")
def status():

    return jsonify({

        "success": True,

        "application":
            "Green ICT Decision Support System",

        "model_file":
            (BASE_DIR / "model.py").exists(),

        "operator_data":
            OPERATOR_DATA_FILE.exists(),

        "logged_in":
            "role" in session,

        "role":
            session.get("role"),

        "operator":
            session.get("operator"),
    })


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    create_operator_csv()

    print("=" * 60)
    print("GREEN ICT DECISION SUPPORT SYSTEM")
    print("=" * 60)

    print(
        "Open: http://127.0.0.1:5000"
    )

    print()

    print("Demo operator accounts:")

    print(
        "  Grameenphone -> GP2026"
    )

    print(
        "  Banglalink   -> BL2026"
    )

    print(
        "  Robi         -> RO2026"
    )

    print()

    print("Corrective-action model:")
    print("  Consolidated gaps: G01-G08")
    print("  Corrective actions: A01-A08")

    print("=" * 60)

    app.run(
        debug=True
    )