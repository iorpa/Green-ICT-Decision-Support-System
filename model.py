from pathlib import Path
import csv


BASE_DIR = Path(__file__).resolve().parent

OPERATOR_DATA_FILE = BASE_DIR / "operator_data.csv"
GAP_RULES_FILE = BASE_DIR / "gap_analysis.csv"
ACTION_RULES_FILE = BASE_DIR / "action_rules.csv"
PRIORITY_RULES_FILE = BASE_DIR / "priority_rules.csv"


# =============================================================
# CSV HELPERS
# =============================================================

def read_csv_file(file_path):
    """Read a CSV file and return a list of dictionaries."""

    if not file_path.exists():
        return []

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        return list(csv.DictReader(file))


def normalize_operator(value):
    """Normalize operator names for comparison."""

    return str(value or "").strip().lower()


def normalize_text(value):
    """Normalize text for comparison."""

    return str(value or "").strip().lower()


def is_missing(value):
    """
    Check whether an evidence value is missing
    or not sufficiently disclosed.
    """

    if value is None:
        return True

    value = str(value).strip().lower()

    return value in {
        "",
        "na",
        "n/a",
        "not available",
        "not disclosed",
        "not sufficiently disclosed",
        "missing",
        "unknown"
    }


# =============================================================
# OPERATOR EVIDENCE
# =============================================================

def operator_matches(row_operator, selected_operator):
    """Check whether a CSV row belongs to the selected operator."""

    return (
        normalize_operator(row_operator)
        == normalize_operator(selected_operator)
    )


def load_operator_evidence(operator):
    """Load evidence belonging only to the selected operator."""

    rows = read_csv_file(OPERATOR_DATA_FILE)

    return [
        row
        for row in rows
        if operator_matches(
            row.get("operator"),
            operator
        )
    ]


def load_all_operator_evidence():
    """
    Load evidence for all operators.

    Used internally for cross-operator gap analysis.
    """

    return read_csv_file(OPERATOR_DATA_FILE)


# =============================================================
# RULE LOADERS
# =============================================================

def load_gap_rules():
    """Load gap-analysis rules."""

    return read_csv_file(GAP_RULES_FILE)


def load_action_rules():
    """
    Load barrier and corrective-action rules
    from action_rules.csv.
    """

    return read_csv_file(ACTION_RULES_FILE)


def load_priority_rules():
    """
    Load Decision-Support Model scoring rules
    from priority_rules.csv.
    """

    return read_csv_file(PRIORITY_RULES_FILE)


# =============================================================
# EVIDENCE SEARCH
# =============================================================

def find_evidence(evidence_rows, area=None, indicator=None):
    """
    Find evidence matching an area and/or indicator.
    Matching is case-insensitive.
    """

    area = normalize_text(area)
    indicator = normalize_text(indicator)

    matches = []

    for row in evidence_rows:

        row_area = normalize_text(
            row.get("area", "")
        )

        row_indicator = normalize_text(
            row.get("indicator", "")
        )

        area_match = (
            not area
            or row_area == area
        )

        indicator_match = (
            not indicator
            or row_indicator == indicator
        )

        if area_match and indicator_match:
            matches.append(row)

    return matches


# =============================================================
# GAP RULE HELPERS
# =============================================================

def get_rule_id(rule):
    """Return the gap rule ID."""

    return str(
        rule.get("gap_id", "")
    ).strip().upper()


def get_gap_type(rule):
    """Return the gap type."""

    return str(
        rule.get("gap_type", "")
    ).strip()


# =============================================================
# BUILD GAP FINDING
# =============================================================

def build_finding(
    operator,
    rule,
    evidence=None,
    custom_value=None
):
    """
    Build one standardized gap finding.
    """

    if evidence is None:
        evidence = {}

    value = (
        custom_value
        if custom_value is not None
        else evidence.get("value", "")
    )

    return {
        "operator": operator,

        "gap_id": rule.get(
            "gap_id",
            ""
        ),

        "area": evidence.get(
            "area",
            rule.get(
                "green_ict_area",
                ""
            )
        ),

        "indicator": evidence.get(
            "indicator",
            rule.get(
                "indicator",
                ""
            )
        ),

        "value": value,

        "unit": evidence.get(
            "unit",
            ""
        ),

        "source": evidence.get(
            "source",
            ""
        ),

        "notes": evidence.get(
            "notes",
            ""
        ),

        "gap": rule.get(
            "gap",
            ""
        ),

        "gap_type": rule.get(
            "gap_type",
            ""
        ),

        "policy_basis": rule.get(
            "policy_basis",
            ""
        ),

        "evidence_basis": rule.get(
            "evidence_basis",
            ""
        ),

        "rule": rule.get(
            "rule",
            ""
        )
    }


# =============================================================
# GAP ANALYSIS
# =============================================================

def analyze_gap(
    rule,
    operator,
    evidence_rows,
    all_evidence_rows
):
    """
    Apply one gap-analysis rule.

    This function performs Gap Analysis only.

    It does NOT perform:

    - barrier diagnosis
    - corrective-action mapping
    - priority scoring
    """

    gap_id = get_rule_id(rule)

    # =========================================================
    # G01 - Energy-efficiency measurement gap
    # =========================================================

    if gap_id == "G01":

        return [{
            "area": "Energy Efficiency",
            "indicator": (
                "Energy-efficiency performance indicators"
            ),
            "value": "Not standardized",
            "unit": "",
            "source": "",
            "notes": (
                "Policy-level measurement gap."
            )
        }]


    # =========================================================
    # G02 - Energy-efficiency comparability gap
    # =========================================================

    if gap_id == "G02":

        operator_rows = [
            row
            for row in all_evidence_rows
            if operator_matches(
                row.get("operator"),
                operator
            )
        ]

        energy_rows = [
            row
            for row in operator_rows
            if normalize_text(
                row.get("area", "")
            ) == "energy efficiency"
        ]

        comparable_indicators = []

        for row in energy_rows:

            indicator = normalize_text(
                row.get("indicator", "")
            )

            if (
                "energy savings" in indicator
                or "energy reduction" in indicator
            ):

                if not is_missing(
                    row.get("value")
                ):

                    comparable_indicators.append(
                        row
                    )

        if not comparable_indicators:

            other_operator_has_quantitative = False

            for row in all_evidence_rows:

                row_operator = normalize_operator(
                    row.get("operator")
                )

                if (
                    row_operator
                    == normalize_operator(operator)
                ):
                    continue

                area = normalize_text(
                    row.get("area", "")
                )

                indicator = normalize_text(
                    row.get("indicator", "")
                )

                if area != "energy efficiency":
                    continue

                if (
                    "energy savings" in indicator
                    or "energy reduction" in indicator
                ):

                    if not is_missing(
                        row.get("value")
                    ):

                        other_operator_has_quantitative = True
                        break

            if other_operator_has_quantitative:

                return [{
                    "area": "Energy Efficiency",
                    "indicator": (
                        "Energy savings and energy "
                        "reduction indicators"
                    ),
                    "value": (
                        "Not sufficiently comparable"
                    ),
                    "unit": "",
                    "source": "",
                    "notes": (
                        "Comparable quantitative "
                        "energy-efficiency evidence "
                        "is not sufficiently disclosed "
                        "for the selected operator."
                    )
                }]

        return None


    # =========================================================
    # G03 - Renewable-energy reporting comparability gap
    # =========================================================

    if gap_id == "G03":

        renewable_rows = [
            row
            for row in all_evidence_rows
            if normalize_text(
                row.get("area", "")
            ) == "renewable energy"
        ]

        reporting_units = set()

        for row in renewable_rows:

            value = row.get("value")

            unit = normalize_text(
                row.get("unit", "")
            )

            if not is_missing(value):

                if unit:
                    reporting_units.add(unit)

        if len(reporting_units) > 1:

            return [{
                "area": "Renewable Energy",
                "indicator": (
                    "Renewable-energy adoption, "
                    "generation and capacity"
                ),
                "value": (
                    "Different reporting measures "
                    "and units"
                ),
                "unit": "",
                "source": "",
                "notes": (
                    "Operators report renewable-energy "
                    "adoption using different measures "
                    "and units."
                )
            }]

        return None


    # =========================================================
    # G04 - Renewable-energy procurement
    # implementation gap
    # =========================================================

    if gap_id == "G04":

        relevant = []

        for row in evidence_rows:

            indicator = normalize_text(
                row.get("indicator", "")
            )

            value = normalize_text(
                row.get("value", "")
            )

            if "cppa" in indicator:

                if (
                    "pending" in value
                    or "unresolved" in value
                    or "not available" in value
                ):

                    relevant.append(row)

        if relevant:
            return relevant

        return None


    # =========================================================
    # G05 - GHG disclosure gap
    # =========================================================

    if gap_id == "G05":

        relevant = []

        for row in evidence_rows:

            area = normalize_text(
                row.get("area", "")
            )

            indicator = normalize_text(
                row.get("indicator", "")
            )

            if area != "ghg / carbon reduction":
                continue

            if (
                "ghg" in indicator
                or "scope 1+2" in indicator
                or "scope 1" in indicator
                or "carbon emission" in indicator
            ):

                if is_missing(
                    row.get("value")
                ):

                    relevant.append(row)

        if relevant:
            return relevant

        return None


    # =========================================================
    # G06 - GHG comparability gap
    # =========================================================

    if gap_id == "G06":

        ghg_rows = [
            row
            for row in all_evidence_rows
            if normalize_text(
                row.get("area", "")
            ) == "ghg / carbon reduction"
        ]

        operators_with_ghg_data = set()

        for row in ghg_rows:

            if not is_missing(
                row.get("value")
            ):

                operator_name = normalize_operator(
                    row.get("operator")
                )

                operators_with_ghg_data.add(
                    operator_name
                )

        if len(operators_with_ghg_data) >= 2:

            return [{
                "area": "GHG / Carbon Reduction",
                "indicator": (
                    "GHG emissions measures, "
                    "baselines and targets"
                ),
                "value": (
                    "Not sufficiently comparable"
                ),
                "unit": "",
                "source": "",
                "notes": (
                    "Operators use different GHG "
                    "measures, baselines and "
                    "reporting levels."
                )
            }]

        return None


    # =========================================================
    # G07 - GHG performance gap
    # =========================================================

    if gap_id == "G07":

        if normalize_operator(
            operator
        ) != "grameenphone":

            return None

        emissions_rows = [
            row
            for row in evidence_rows
            if normalize_text(
                row.get("indicator", "")
            ) == "scope 1+2 emissions"
        ]

        target_rows = [
            row
            for row in evidence_rows
            if "scope 1+2 reduction target"
            in normalize_text(
                row.get("indicator", "")
            )
        ]

        if emissions_rows and target_rows:

            emissions_value = str(
                emissions_rows[0].get(
                    "value",
                    ""
                )
            ).strip()

            target_value = str(
                target_rows[0].get(
                    "value",
                    ""
                )
            ).strip()

            return [{
                "area": "GHG / Carbon Reduction",
                "indicator": (
                    "Operator-specific GHG reduction "
                    "target and reported performance"
                ),
                "value": (
                    f"2025 Scope 1+2 emissions: "
                    f"{emissions_value}; "
                    f"2030 reduction target: "
                    f"{target_value}"
                ),
                "unit": "",
                "source": emissions_rows[0].get(
                    "source",
                    ""
                ),
                "notes": (
                    "Performance gap assessed against "
                    "the operator's own stated reduction "
                    "target/pathway. This does not by "
                    "itself establish BTRC policy "
                    "non-compliance."
                )
            }]

        return None


    # =========================================================
    # G08 - E-waste disclosure gap
    # =========================================================

    if gap_id == "G08":

        relevant = []

        for row in evidence_rows:

            area = normalize_text(
                row.get("area", "")
            )

            indicator = normalize_text(
                row.get("indicator", "")
            )

            if area != "e-waste management":
                continue

            if (
                "e-waste" in indicator
                or "waste" in indicator
            ):

                if is_missing(
                    row.get("value")
                ):

                    relevant.append(row)

        if relevant:
            return relevant

        return None


    # =========================================================
    # G09 - E-waste comparability gap
    # =========================================================

    if gap_id == "G09":

        ewaste_rows = [
            row
            for row in all_evidence_rows
            if normalize_text(
                row.get("area", "")
            ) == "e-waste management"
        ]

        if ewaste_rows:

            operators_with_data = set()

            for row in ewaste_rows:

                if not is_missing(
                    row.get("value")
                ):

                    operators_with_data.add(
                        normalize_operator(
                            row.get("operator")
                        )
                    )

            if len(operators_with_data) >= 1:

                return [{
                    "area": "E-waste Management",
                    "indicator": (
                        "E-waste collection, recycling "
                        "and disposal reporting"
                    ),
                    "value": (
                        "Not sufficiently comparable"
                    ),
                    "unit": "",
                    "source": "",
                    "notes": (
                        "Operators provide different "
                        "levels of detail and do not "
                        "consistently report comparable "
                        "telecom-specific e-waste "
                        "quantities."
                    )
                }]

        return None


    # =========================================================
    # G10 - Infrastructure-sharing
    # evidence/disclosure gap
    # =========================================================

    if gap_id == "G10":

        relevant = [
            row
            for row in evidence_rows
            if normalize_text(
                row.get("area", "")
            ) == "infrastructure sharing"
        ]

        if not relevant:

            return [{
                "area": "Infrastructure Sharing",
                "indicator": (
                    "Tower, fibre, radio-network and "
                    "other infrastructure sharing"
                ),
                "value": (
                    "Not sufficiently disclosed"
                ),
                "unit": "",
                "source": "",
                "notes": (
                    "Policy supports infrastructure "
                    "sharing, but sufficient quantitative "
                    "operator-level evidence is not "
                    "available."
                )
            }]

        return None


    # =========================================================
    # G11 - Tower-fiberization evidence gap
    # =========================================================

    if gap_id == "G11":

        relevant = [
            row
            for row in evidence_rows
            if (
                "fiber"
                in normalize_text(
                    row.get("indicator", "")
                )
                or
                "fibre"
                in normalize_text(
                    row.get("indicator", "")
                )
            )
        ]

        if not relevant:

            return [{
                "area": "Tower Fiberization",
                "indicator": (
                    "Percentage of mobile towers "
                    "fiberized"
                ),
                "value": (
                    "Not sufficiently disclosed"
                ),
                "unit": "",
                "source": "",
                "notes": (
                    "Policy sets measurable "
                    "fiberization targets, but "
                    "sufficient operator-level data "
                    "are unavailable to verify progress. "
                    "This is an Evidence Gap, not a "
                    "finding of non-compliance."
                )
            }]

        return None


    # =========================================================
    # G12 - Government support / renewable
    # procurement gap
    # =========================================================

    if gap_id == "G12":

        relevant = []

        for row in evidence_rows:

            indicator = normalize_text(
                row.get("indicator", "")
            )

            value = normalize_text(
                row.get("value", "")
            )

            if "cppa" in indicator:

                if (
                    "pending" in value
                    or "unresolved" in value
                ):

                    relevant.append(row)

        if relevant:
            return relevant

        return None


    # =========================================================
    # G13 - Diesel-use policy tension
    # =========================================================

    if gap_id == "G13":

        return [{
            "area": (
                "Network Resilience / "
                "Carbon Reduction"
            ),
            "indicator": (
                "Diesel backup generation at "
                "disaster-prone tower sites"
            ),
            "value": (
                "25% policy requirement"
            ),
            "unit": "",
            "source": "",
            "notes": (
                "Policy tension between network "
                "resilience and carbon reduction. "
                "Diesel backup supports resilience "
                "but can increase fuel consumption "
                "and emissions."
            )
        }]

    return None


# =============================================================
# ACTION RULE MATCHING
# =============================================================

def find_action_rules(
    gap_id,
    action_rules
):
    """
    Find corrective-action rules associated
    with a gap ID.
    """

    gap_id = str(
        gap_id or ""
    ).strip().upper()

    matches = []

    for action_rule in action_rules:

        action_id = str(
            action_rule.get(
                "action_id",
                ""
            )
        ).strip().upper()

        expected_gap_id = ""

        if action_id.startswith("A"):

            number = action_id[1:]

            if number.isdigit():

                expected_gap_id = (
                    "G"
                    + number.zfill(2)
                )

        if expected_gap_id == gap_id:

            matches.append(
                action_rule
            )

    return matches


# =============================================================
# BARRIER + CORRECTIVE ACTION MAPPING
# =============================================================

def apply_action_mapping(
    findings,
    action_rules
):
    """
    Add barrier diagnosis and corrective-action
    information to identified gap findings.
    """

    mapped_findings = []

    for finding in findings:

        gap_id = str(
            finding.get(
                "gap_id",
                ""
            )
        ).strip().upper()

        matching_actions = find_action_rules(
            gap_id,
            action_rules
        )

        if matching_actions:

            for action_rule in matching_actions:

                enriched_finding = dict(
                    finding
                )

                enriched_finding.update({

                    "action_id":
                        action_rule.get(
                            "action_id",
                            ""
                        ),

                    "identified_problem":
                        action_rule.get(
                            "identified_problem",
                            ""
                        ),

                    "barrier_category":
                        action_rule.get(
                            "barrier_category",
                            ""
                        ),

                    "corrective_action":
                        action_rule.get(
                            "corrective_action",
                            ""
                        ),

                    "action_policy_basis":
                        action_rule.get(
                            "policy_basis",
                            ""
                        ),

                    "action_evidence_basis":
                        action_rule.get(
                            "evidence_basis",
                            ""
                        ),

                    "responsible_actor":
                        action_rule.get(
                            "responsible_actor",
                            ""
                        ),

                    "regulatory_dependency":
                        action_rule.get(
                            "regulatory_dependency",
                            ""
                        )
                })

                mapped_findings.append(
                    enriched_finding
                )

        else:

            enriched_finding = dict(
                finding
            )

            enriched_finding.update({

                "action_id": "",

                "identified_problem":
                    finding.get(
                        "gap",
                        ""
                    ),

                "barrier_category": "",

                "corrective_action": "",

                "action_policy_basis": "",

                "action_evidence_basis": "",

                "responsible_actor": "",

                "regulatory_dependency": ""
            })

            mapped_findings.append(
                enriched_finding
            )

    return mapped_findings


# =============================================================
# PRIORITY RULE MATCHING
# =============================================================

def find_priority_rule(
    gap_id,
    action_id,
    priority_rules
):
    """
    Find the priority-scoring rule for
    a specific gap and corrective action.
    """

    gap_id = str(
        gap_id or ""
    ).strip().upper()

    action_id = str(
        action_id or ""
    ).strip().upper()

    for rule in priority_rules:

        rule_gap_id = str(
            rule.get(
                "gap_id",
                ""
            )
        ).strip().upper()

        rule_action_id = str(
            rule.get(
                "action_id",
                ""
            )
        ).strip().upper()

        if (
            rule_gap_id == gap_id
            and
            rule_action_id == action_id
        ):

            return rule

    return None


# =============================================================
# SCORE CONVERSION
# =============================================================

def parse_score(value):
    """
    Convert a CSV score into an integer.

    Valid range:
    1 to 5
    """

    try:

        score = int(
            float(
                str(value).strip()
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    if score < 1 or score > 5:
        return None

    return score


# =============================================================
# PRIORITY LEVEL
# =============================================================

def get_priority_level(score):
    """
    Convert priority score into the classification
    defined in the Decision-Support Model.
    """

    if score >= 4.00:
        return "Very High"

    if score >= 3.00:
        return "High"

    if score >= 2.00:
        return "Medium"

    return "Low"


# =============================================================
# PRIORITY SCORING
# =============================================================

def apply_priority_scoring(
    results,
    priority_rules
):
    """
    Apply the Decision-Support Model.

    Criteria:

    GS = Gap Severity
    BS = Barrier Severity
    EI = Environmental Impact
    IF = Implementation Feasibility

    Formula:

    Priority Score =
        (GS + BS + EI + IF) / 4
    """

    prioritized_results = []

    for result in results:

        gap_id = str(
            result.get(
                "gap_id",
                ""
            )
        ).strip().upper()

        action_id = str(
            result.get(
                "action_id",
                ""
            )
        ).strip().upper()

        priority_rule = find_priority_rule(
            gap_id,
            action_id,
            priority_rules
        )

        enriched_result = dict(
            result
        )

        if not priority_rule:

            enriched_result.update({

                "gap_severity": "",

                "barrier_severity": "",

                "environmental_impact": "",

                "implementation_feasibility": "",

                "priority_score": "",

                "priority_level": "",

                "gap_severity_basis": "",

                "barrier_severity_basis": "",

                "environmental_impact_basis": "",

                "implementation_feasibility_basis": ""
            })

            prioritized_results.append(
                enriched_result
            )

            continue

        gs = parse_score(
            priority_rule.get(
                "gap_severity"
            )
        )

        bs = parse_score(
            priority_rule.get(
                "barrier_severity"
            )
        )

        ei = parse_score(
            priority_rule.get(
                "environmental_impact"
            )
        )

        implementation_feasibility = parse_score(
            priority_rule.get(
                "implementation_feasibility"
            )
        )

        if (
            gs is None
            or bs is None
            or ei is None
            or implementation_feasibility is None
        ):

            enriched_result.update({

                "gap_severity":
                    priority_rule.get(
                        "gap_severity",
                        ""
                    ),

                "barrier_severity":
                    priority_rule.get(
                        "barrier_severity",
                        ""
                    ),

                "environmental_impact":
                    priority_rule.get(
                        "environmental_impact",
                        ""
                    ),

                "implementation_feasibility":
                    priority_rule.get(
                        "implementation_feasibility",
                        ""
                    ),

                "priority_score": "",

                "priority_level": "",

                "gap_severity_basis":
                    priority_rule.get(
                        "gap_severity_basis",
                        ""
                    ),

                "barrier_severity_basis":
                    priority_rule.get(
                        "barrier_severity_basis",
                        ""
                    ),

                "environmental_impact_basis":
                    priority_rule.get(
                        "environmental_impact_basis",
                        ""
                    ),

                "implementation_feasibility_basis":
                    priority_rule.get(
                        "implementation_feasibility_basis",
                        ""
                    )
            })

            prioritized_results.append(
                enriched_result
            )

            continue

        priority_score = (
            gs
            + bs
            + ei
            + implementation_feasibility
        ) / 4

        priority_score = round(
            priority_score,
            2
        )

        priority_level = get_priority_level(
            priority_score
        )

        enriched_result.update({

            "gap_severity": gs,

            "barrier_severity": bs,

            "environmental_impact": ei,

            "implementation_feasibility":
                implementation_feasibility,

            "priority_score":
                priority_score,

            "priority_level":
                priority_level,

            "gap_severity_basis":
                priority_rule.get(
                    "gap_severity_basis",
                    ""
                ),

            "barrier_severity_basis":
                priority_rule.get(
                    "barrier_severity_basis",
                    ""
                ),

            "environmental_impact_basis":
                priority_rule.get(
                    "environmental_impact_basis",
                    ""
                ),

            "implementation_feasibility_basis":
                priority_rule.get(
                    "implementation_feasibility_basis",
                    ""
                )
        })

        prioritized_results.append(
            enriched_result
        )

    return prioritized_results


# =============================================================
# SORT PRIORITIZED RESULTS
# =============================================================

def sort_by_priority(results):
    """
    Sort results from highest priority score
    to lowest priority score.

    Results without a valid score are placed last.
    """

    def priority_value(result):

        score = result.get(
            "priority_score",
            ""
        )

        try:
            return float(score)

        except (
            TypeError,
            ValueError
        ):

            return -1

    return sorted(
        results,
        key=priority_value,
        reverse=True
    )


# =============================================================
# MAIN MODEL
# =============================================================

def run_model(
    operator=None,
    export=False
):
    """
    Run the complete Green ICT Decision-Support Model.

    Pipeline:

    Operator Evidence
          ↓
    Gap Analysis
          ↓
    Identified Gap
          ↓
    Barrier Diagnosis
          ↓
    Corrective Action
          ↓
    Priority Scoring
          ↓
    Priority Level
    """

    if not operator:

        return {
            "findings": [],
            "results": []
        }

    # =========================================================
    # 1. Load selected operator evidence
    # =========================================================

    evidence_rows = load_operator_evidence(
        operator
    )

    # =========================================================
    # 2. Load all operator evidence
    # =========================================================

    all_evidence_rows = load_all_operator_evidence()

    # =========================================================
    # 3. Load gap-analysis rules
    # =========================================================

    gap_rules = load_gap_rules()

    # =========================================================
    # 4. Load action rules
    # =========================================================

    action_rules = load_action_rules()

    # =========================================================
    # 5. Load priority rules
    # =========================================================

    priority_rules = load_priority_rules()


    # =========================================================
    # DEBUG INFORMATION
    # =========================================================

    print("\n================ MODEL DEBUG ================")
    print("Operator:", operator)
    print("Operator evidence rows:", len(evidence_rows))
    print("All evidence rows:", len(all_evidence_rows))
    print("Gap rules loaded:", len(gap_rules))
    print("Action rules loaded:", len(action_rules))
    print("Priority rules loaded:", len(priority_rules))
    print(
        "Gap rule IDs:",
        [
            rule.get("gap_id")
            for rule in gap_rules
        ]
    )
    print("=============================================\n")


    # =========================================================
    # 6. GAP ANALYSIS
    # =========================================================

    findings = []

    for rule in gap_rules:

        matched_evidence = analyze_gap(
            rule,
            operator,
            evidence_rows,
            all_evidence_rows
        )

        if not matched_evidence:
            continue

        if isinstance(
            matched_evidence,
            list
        ):

            for evidence in matched_evidence:

                findings.append(
                    build_finding(
                        operator,
                        rule,
                        evidence
                    )
                )

        elif isinstance(
            matched_evidence,
            dict
        ):

            findings.append(
                build_finding(
                    operator,
                    rule,
                    matched_evidence
                )
            )

    # =========================================================
    # DEBUG GAP FINDINGS
    # =========================================================

    print(
        "Gap findings generated:",
        len(findings)
    )

    print(
        "Finding IDs:",
        [
            finding.get("gap_id")
            for finding in findings
        ]
    )

    # =========================================================
    # 7. BARRIER DIAGNOSIS + CORRECTIVE ACTION
    # =========================================================

    results = apply_action_mapping(
        findings,
        action_rules
    )

    # =========================================================
    # DEBUG ACTION MAPPING
    # =========================================================

    print(
        "Results after action mapping:",
        len(results)
    )

    print(
        "Action IDs:",
        [
            result.get("action_id")
            for result in results
        ]
    )

    # =========================================================
    # 8. DECISION-SUPPORT MODEL
    # =========================================================

    results = apply_priority_scoring(
        results,
        priority_rules
    )

    # =========================================================
    # DEBUG PRIORITY SCORING
    # =========================================================

    print(
        "Results after priority scoring:",
        len(results)
    )

    print(
        "Priority scores:",
        [
            result.get("priority_score")
            for result in results
        ]
    )

    # =========================================================
    # 9. SORT BY PRIORITY
    # =========================================================

    results = sort_by_priority(
        results
    )

    # =========================================================
    # 10. RETURN MODEL OUTPUT
    # =========================================================

    return {
        "findings": findings,
        "results": results
    }