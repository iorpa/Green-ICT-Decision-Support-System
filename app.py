from flask import Flask, request, jsonify, send_from_directory, session
from functools import wraps
from pathlib import Path
import csv
import secrets

from model import run_model

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)

app.secret_key = secrets.token_hex(32)

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

OPERATOR_ACCOUNTS = {
    "Grameenphone": "GP2026",
    "Banglalink": "BL2026",
    "Robi": "RO2026",
}

def create_operator_csv():

    if not OPERATOR_DATA_FILE.exists():

        with OPERATOR_DATA_FILE.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(file)
            writer.writerow(OPERATOR_DATA_HEADERS)


def read_operator_rows():

    create_operator_csv()

    with OPERATOR_DATA_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        return list(csv.DictReader(file))


def normalize_operator(value):

    return str(value or "").strip().casefold()


def operator_matches(row_operator, session_operator):

    return (
        normalize_operator(row_operator)
        == normalize_operator(session_operator)
    )


def operator_required(function):

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



@app.post("/api/logout")
def logout():

    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully.",
    })



@app.get("/api/session")
def get_session():

    return jsonify({
        "success": True,
        "logged_in": "role" in session,
        "role": session.get("role"),
        "operator": session.get("operator"),
        "username": session.get("username"),
    })


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
            "findings": output["findings"],
            "results": output["results"],
            "ai_meta": output.get("ai_meta", {}),   # NEW
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

    print("=" * 60)


    app.run(debug=True)