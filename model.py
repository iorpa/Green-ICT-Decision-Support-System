from ai_ranker import rank_actions as ai_rank_actions
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

    Used internally for cross-operator analysis.
    """

    return read_csv_file(OPERATOR_DATA_FILE)


# =============================================================
# RULE LOADERS
# =============================================================

def load_gap_rules():
    """Load consolidated gap-analysis rules."""

    return read_csv_file(GAP_RULES_FILE)


def load_action_rules():
    """Load corrective-action rules."""

    return read_csv_file(ACTION_RULES_FILE)


def load_priority_rules():
    """Load decision-support priority rules."""

    return read_csv_file(PRIORITY_RULES_FILE)


# =============================================================
# EVIDENCE SEARCH
# =============================================================

def find_evidence(
    evidence_rows,
    area=None,
    indicator=None
):
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
# CONSOLIDATED GAP ANALYSIS
# =============================================================

def analyze_gap(
    rule,
    operator,
    evidence_rows,
    all_evidence_rows
):
    """
    Apply one of the eight consolidated gap-analysis rules.

    IMPORTANT:
    Each G01-G08 produces at most ONE consolidated finding
    for each operator.

    G01 - Inconsistent Green ICT measurement
    G02 - Missing GHG and e-waste data
    G03 - Rising energy consumption and emissions
    G04 - Limited physical renewable-energy adoption
    G05 - Renewable procurement barriers
    G06 - Infrastructure-sharing evidence gap
    G07 - Organizational implementation weakness
    G08 - Weak policy measurability
    """

    gap_id = get_rule_id(rule)

    # =========================================================
    # G01 - Inconsistent Green ICT measurement
    # =========================================================

    if gap_id == "G01":

        return [{
            "area": "Green ICT Measurement",

            "indicator": (
                "Green ICT KPIs and reporting indicators"
            ),

            "value": "Not standardized",

            "unit": "",

            "source": "",

            "notes": (
                "Operators use different Green ICT "
                "indicators, units, baselines, and "
                "reporting levels. This represents a "
                "measurement and comparability gap."
            )
        }]

    # =========================================================
    # G02 - Missing GHG and e-waste data
    # =========================================================

    if gap_id == "G02":

        relevant = []

        for row in evidence_rows:

            area = normalize_text(
                row.get("area", "")
            )

            indicator = normalize_text(
                row.get("indicator", "")
            )

            combined_text = (
                area + " " + indicator
            )

            if (
                "ghg" in combined_text
                or "carbon" in combined_text
                or "e-waste" in combined_text
                or "waste" in combined_text
            ):

                if is_missing(
                    row.get("value")
                ):

                    relevant.append(row)

        # -----------------------------------------------------
        # IMPORTANT:
        # Several evidence rows may support G02.
        # They are consolidated into ONE G02 finding.
        # -----------------------------------------------------

        source = ""

        for row in relevant:

            if str(
                row.get(
                    "source",
                    ""
                )
            ).strip():

                source = row.get(
                    "source",
                    ""
                )

                break

        return [{
            "area": "GHG / E-waste Management",

            "indicator": (
                "Operator-level GHG emissions "
                "and e-waste information"
            ),

            "value": "Not sufficiently disclosed",

            "unit": "",

            "source": source,

            "notes": (
                "Operator-level GHG and e-waste "
                "information is incomplete or "
                "reported using different scopes, "
                "measures, or classifications."
            )
        }]

    # =========================================================
    # G03 - Rising energy consumption and emissions
    # =========================================================

    if gap_id == "G03":

        energy_rows = []

        for row in evidence_rows:

            area = normalize_text(
                row.get("area", "")
            )

            indicator = normalize_text(
                row.get("indicator", "")
            )

            if (
                "energy" in area
                or "energy consumption" in indicator
                or "fuel" in indicator
                or "emission" in indicator
            ):

                if not is_missing(
                    row.get("value")
                ):

                    energy_rows.append(row)

        source = ""

        if energy_rows:

            source = energy_rows[0].get(
                "source",
                ""
            )

            value = "Rising environmental pressure"

            notes = (
                "Energy demand and associated "
                "emissions remain important "
                "environmental concerns despite "
                "existing efficiency measures."
            )

        else:

            value = "Requires improved management"

            notes = (
                "Improved network energy efficiency "
                "and energy-demand management are "
                "required."
            )

        return [{
            "area": "Energy Efficiency",

            "indicator": (
                "Energy consumption and "
                "associated emissions"
            ),

            "value": value,

            "unit": "",

            "source": source,

            "notes": notes
        }]

    # =========================================================
    # G04 - Limited physical renewable-energy adoption
    # =========================================================

    if gap_id == "G04":

        renewable_rows = []

        for row in evidence_rows:

            area = normalize_text(
                row.get("area", "")
            )

            indicator = normalize_text(
                row.get("indicator", "")
            )

            if area == "renewable energy":

                if (
                    "solar" in indicator
                    or "hybrid" in indicator
                    or "renewable" in indicator
                    or "site" in indicator
                ):

                    if not is_missing(
                        row.get("value")
                    ):

                        renewable_rows.append(row)

        source = ""

        if renewable_rows:

            source = renewable_rows[0].get(
                "source",
                ""
            )

        return [{
            "area": "Renewable Energy",

            "indicator": (
                "Physical solar and hybrid "
                "renewable-energy deployment"
            ),

            "value": "Limited or uneven adoption",

            "unit": "",

            "source": source,

            "notes": (
                "Physical renewable-energy deployment "
                "remains limited or uneven across "
                "network sites."
            )
        }]

    # =========================================================
    # G05 - Renewable procurement barriers
    # =========================================================

    if gap_id == "G05":

        relevant = []

        for row in evidence_rows:

            indicator = normalize_text(
                row.get("indicator", "")
            )

            value = normalize_text(
                row.get("value", "")
            )

            if (
                "cppa" in indicator
                or "renewable procurement" in indicator
                or "power purchase" in indicator
            ):

                if (
                    "pending" in value
                    or "unresolved" in value
                    or "not available" in value
                    or "barrier" in value
                ):

                    relevant.append(row)

        # -----------------------------------------------------
        # Consolidate multiple supporting rows into ONE G05.
        # -----------------------------------------------------

        source = ""

        for row in relevant:

            if str(
                row.get(
                    "source",
                    ""
                )
            ).strip():

                source = row.get(
                    "source",
                    ""
                )

                break

        return [{
            "area": "Renewable Energy Procurement",

            "indicator": (
                "CPPA and renewable-electricity "
                "procurement"
            ),

            "value": "Procurement barriers identified",

            "unit": "",

            "source": source,

            "notes": (
                "Renewable electricity procurement "
                "can be constrained by regulatory, "
                "contractual, and implementation "
                "mechanisms."
            )
        }]

    # =========================================================
    # G06 - Infrastructure-sharing evidence gap
    # =========================================================

    if gap_id == "G06":

        relevant = [
            row
            for row in evidence_rows
            if (
                "infrastructure sharing"
                in normalize_text(
                    row.get("area", "")
                )
            )
        ]

        source = ""

        for row in relevant:

            if str(
                row.get(
                    "source",
                    ""
                )
            ).strip():

                source = row.get(
                    "source",
                    ""
                )

                break

        return [{
            "area": "Infrastructure Sharing",

            "indicator": (
                "Tower, fibre, and other "
                "infrastructure sharing"
            ),

            "value": "Insufficient quantitative evidence",

            "unit": "",

            "source": source,

            "notes": (
                "Insufficient quantitative operator-level "
                "evidence is available to assess "
                "infrastructure-sharing coverage and "
                "resource-efficiency benefits."
            )
        }]

    # =========================================================
    # G07 - Organizational implementation weakness
    # =========================================================

    if gap_id == "G07":

        return [{
            "area": "Organizational Implementation",

            "indicator": (
                "Green ICT responsibilities, monitoring, "
                "coordination, and accountability"
            ),

            "value": "Requires stronger implementation",

            "unit": "",

            "source": "",

            "notes": (
                "Differences in organizational "
                "responsibilities, monitoring, "
                "coordination, and accountability "
                "can limit consistent Green ICT "
                "implementation."
            )
        }]

    # =========================================================
    # G08 - Weak policy measurability
    # =========================================================

    if gap_id == "G08":

        return [{
            "area": "Policy and Regulation",

            "indicator": (
                "Green ICT targets, timelines, "
                "monitoring, and verification"
            ),

            "value": (
                "Requires clearer measurable requirements"
            ),

            "unit": "",

            "source": "",

            "notes": (
                "Green ICT requirements need clearer "
                "quantitative targets, timelines, "
                "monitoring arrangements, and "
                "verification mechanisms."
            )
        }]

    # =========================================================
    # UNKNOWN GAP
    # =========================================================

    return None


# =============================================================
# ACTION RULE MATCHING
# =============================================================

def find_action_rules(
    gap_id,
    action_rules
):
    """
    Map consolidated gaps to corrective actions.

    G01 -> A01
    G02 -> A02
    G03 -> A03
    G04 -> A04
    G05 -> A05
    G06 -> A06
    G07 -> A07
    G08 -> A08
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
    Find the priority-scoring rule for a
    specific gap and corrective action.
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
    Apply the rule-based Decision-Support Model.

    Criteria:

    GS = Gap Severity
    BS = Barrier Severity
    EI = Environmental Impact
    IF = Implementation Feasibility

    Formula:

    Priority Score =
        (GS + BS + EI + IF) / 4

    This score is retained as the rule-based
    reference/audit score.

    AI prioritization is performed separately
    by ai_ranker.py.
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

        # -----------------------------------------------------
        # No priority rule
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Parse four criteria
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Invalid score handling
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Calculate rule-based priority score
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Store scores
        # -----------------------------------------------------

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
    Sort results from highest rule-based priority
    score to lowest.

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
# REMOVE DUPLICATE CONSOLIDATED GAPS
# =============================================================

def ensure_one_finding_per_gap(findings):
    """
    Ensure that the consolidated model contains only one
    finding for each gap ID.

    Expected:
        G01, G02, G03, G04, G05, G06, G07, G08

    This is a final safety layer. It prevents duplicate
    evidence rows from creating duplicate consolidated gaps.
    """

    unique_findings = {}

    for finding in findings:

        gap_id = str(
            finding.get(
                "gap_id",
                ""
            )
        ).strip().upper()

        if not gap_id:
            continue

        if gap_id not in unique_findings:

            unique_findings[gap_id] = finding

    return list(
        unique_findings.values()
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
    8 Consolidated Gaps
          ↓
    Barrier Diagnosis
          ↓
    8 Corrective Actions
          ↓
    Rule-Based Priority Scoring
          ↓
    AHP → TOPSIS → Regression
          ↓
    AI Priority Ranking
    """

    if not operator:

        return {
            "findings": [],
            "results": [],
            "ai_meta": {}
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

    print(
        "Operator:",
        operator
    )

    print(
        "Operator evidence rows:",
        len(evidence_rows)
    )

    print(
        "All evidence rows:",
        len(all_evidence_rows)
    )

    print(
        "Gap rules loaded:",
        len(gap_rules)
    )

    print(
        "Action rules loaded:",
        len(action_rules)
    )

    print(
        "Priority rules loaded:",
        len(priority_rules)
    )

    print(
        "Gap rule IDs:",
        [
            rule.get("gap_id")
            for rule in gap_rules
        ]
    )

    print(
        "Action rule IDs:",
        [
            rule.get("action_id")
            for rule in action_rules
        ]
    )

    print(
        "Priority rule IDs:",
        [
            (
                rule.get("gap_id"),
                rule.get("action_id")
            )
            for rule in priority_rules
        ]
    )

    print(
        "=============================================\n"
    )

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
    # 6A. FINAL CONSOLIDATION SAFETY CHECK
    # =========================================================

    findings = ensure_one_finding_per_gap(
        findings
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
    # 8. RULE-BASED PRIORITY SCORING
    # =========================================================

    results = apply_priority_scoring(
        results,
        priority_rules
    )

    # =========================================================
    # 9. AI PRIORITIZATION
    # =========================================================

    ai_meta = {}

    try:

        ai_output = ai_rank_actions()

        if not isinstance(
            ai_output,
            dict
        ):

            raise ValueError(
                "AI ranker returned an invalid result."
            )

        ranked_actions = ai_output.get(
            "ranked_actions",
            []
        )

        ai_lookup = {}

        for action in ranked_actions:

            gap_id = str(
                action.get(
                    "gap_id",
                    ""
                )
            ).strip().upper()

            action_id = str(
                action.get(
                    "action_id",
                    ""
                )
            ).strip().upper()

            if not gap_id or not action_id:
                continue

            ai_lookup[
                (gap_id, action_id)
            ] = action

        # -----------------------------------------------------
        # Merge AI results
        # -----------------------------------------------------

        for result in results:

            key = (
                str(
                    result.get(
                        "gap_id",
                        ""
                    )
                ).strip().upper(),

                str(
                    result.get(
                        "action_id",
                        ""
                    )
                ).strip().upper()
            )

            ai = ai_lookup.get(
                key
            )

            if ai:

                result["ai_priority_score"] = (
                    ai.get(
                        "ai_priority_score",
                        ""
                    )
                )

                result["ai_priority_level"] = (
                    ai.get(
                        "priority_level",
                        ""
                    )
                )

                result["ai_rank"] = (
                    ai.get(
                        "rank",
                        9999
                    )
                )

                result["explanation"] = (
                    ai.get(
                        "explanation",
                        ""
                    )
                )

            else:

                result["ai_priority_score"] = ""
                result["ai_priority_level"] = ""
                result["ai_rank"] = 9999
                result["explanation"] = ""

        # -----------------------------------------------------
        # Sort by AI rank
        # -----------------------------------------------------

        def safe_ai_rank(result):

            rank = result.get(
                "ai_rank",
                9999
            )

            try:

                return int(rank)

            except (
                TypeError,
                ValueError
            ):

                return 9999

        results.sort(
            key=safe_ai_rank
        )

        # -----------------------------------------------------
        # AI metadata
        # -----------------------------------------------------

        ai_meta = {
            "ahp": ai_output.get(
                "ahp",
                {}
            ),

            "cv_mae": ai_output.get(
                "cv_mae",
                None
            ),

            "top_features": ai_output.get(
                "top_features",
                []
            )
        }

    except Exception as error:

        print(
            "AI ranking failed:",
            error
        )

        ai_meta = {}

        # -----------------------------------------------------
        # Rule-based fallback
        # -----------------------------------------------------

        for result in results:

            result["ai_priority_score"] = ""
            result["ai_priority_level"] = ""
            result["ai_rank"] = ""
            result["explanation"] = ""

    # =========================================================
    # 10. FALLBACK TO RULE-BASED SORT
    # =========================================================

    if not ai_meta:

        results = sort_by_priority(
            results
        )

    # =========================================================
    # FINAL DEBUG
    # =========================================================

    print(
        "\n================ FINAL RESULTS ================"
    )

    print(
        "Total findings:",
        len(findings)
    )

    print(
        "Total results:",
        len(results)
    )

    print(
        "Final actions:",
        [
            result.get("action_id")
            for result in results
        ]
    )

    print(
        "AI ranking available:",
        bool(ai_meta)
    )

    if ai_meta:

        print(
            "Selected model CV MAE:",
            ai_meta.get(
                "cv_mae"
            )
        )

    print(
        "================================================\n"
    )

    # =========================================================
    # 11. RETURN MODEL OUTPUT
    # =========================================================

    return {
        "findings": findings,
        "results": results,
        "ai_meta": ai_meta
    }


# =============================================================
# DIRECT SCRIPT EXECUTION
# =============================================================

if __name__ == "__main__":

    print(
        "\n=============================================="
    )

    print(
        "Green ICT Decision-Support Model"
    )

    print(
        "==============================================\n"
    )

    operators = [
        "Grameenphone",
        "Banglalink",
        "Robi"
    ]

    for operator in operators:

        print(
            "\n----------------------------------------------"
        )

        print(
            "Running model for:",
            operator
        )

        print(
            "----------------------------------------------"
        )

        output = run_model(
            operator=operator
        )

        print(
            "\nResults for",
            operator
        )

        print(
            "-" * 100
        )

        for result in output["results"]:

            print(
                result.get(
                    "ai_rank",
                    ""
                ),
                "|",
                result.get(
                    "action_id",
                    ""
                ),
                "|",
                result.get(
                    "identified_problem",
                    ""
                ),
                "| Rule:",
                result.get(
                    "priority_score",
                    ""
                ),
                "| AI:",
                result.get(
                    "ai_priority_score",
                    ""
                ),
                "|",
                result.get(
                    "ai_priority_level",
                    ""
                )
            )

        print(
            "-" * 100
        )