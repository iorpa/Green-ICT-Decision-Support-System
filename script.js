document.addEventListener("DOMContentLoaded", () => {
  const loginView = document.getElementById("loginView");
  const appView = document.getElementById("appView");

  const loginForm = document.getElementById("loginForm");
  const loginUsername = document.getElementById("loginUsername");
  const loginPassword = document.getElementById("loginPassword");
  const loginMessage = document.getElementById("loginMessage");

  const currentUser = document.getElementById("currentUser");
  const logoutBtn = document.getElementById("logoutBtn");

  const dataForm = document.getElementById("dataForm");
  const dataTableBody = document.getElementById("dataTableBody");
  const emptyMessage = document.getElementById("emptyMessage");
  const clearAllBtn = document.getElementById("clearAll");

  const runModelBtn = document.getElementById("runModel");
  const analysisStatus = document.getElementById("analysisStatus");

  const resultsCard = document.getElementById("resultsCard");
  const modelResults = document.getElementById("modelResults");

  // ============================================================
  // LOGIN
  // ============================================================

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = loginUsername.value.trim();
    const password = loginPassword.value;

    if (!username || !password) {
      loginMessage.textContent =
        "Please enter username and password.";
      return;
    }

    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username,
          password: password,
        }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        loginMessage.textContent =
          data.message || "Invalid username or password.";
        return;
      }

      loginMessage.textContent = "";

      showApplication(data);
    } catch (error) {
      console.error("Login error:", error);

      loginMessage.textContent =
        "Could not connect to the server.";
    }
  });

  // ============================================================
  // LOGOUT
  // ============================================================

  logoutBtn.addEventListener("click", async () => {
    try {
      await fetch("/api/logout", {
        method: "POST",
      });
    } catch (error) {
      console.error("Logout error:", error);
    }

    location.reload();
  });

  // ============================================================
  // SHOW APPLICATION
  // ============================================================

  function showApplication(data) {
    loginView.style.display = "none";
    appView.style.display = "block";

    currentUser.textContent =
      data.operator || "Operator";

    loadOperatorData();
  }

  // ============================================================
  // CHECK SESSION
  // ============================================================

  async function checkSession() {
    try {
      const response = await fetch("/api/session");

      const data = await response.json();

      if (data.logged_in) {
        showApplication(data);
      } else {
        loginView.style.display = "block";
        appView.style.display = "none";
      }
    } catch (error) {
      console.error("Session error:", error);

      loginView.style.display = "block";
      appView.style.display = "none";
    }
  }

  // ============================================================
  // LOAD OPERATOR DATA
  // ============================================================

  async function loadOperatorData() {
    try {
      const response = await fetch("/api/data");

      const result = await response.json();

      if (!result.success) {
        return;
      }

      dataTableBody.innerHTML = "";

      if (!result.data || result.data.length === 0) {
        emptyMessage.style.display = "block";
        return;
      }

      emptyMessage.style.display = "none";

      result.data.forEach((row) => {
        const tr = document.createElement("tr");

        addCell(tr, row.year);
        addCell(tr, row.area);
        addCell(tr, row.indicator);
        addCell(tr, row.value);
        addCell(tr, row.unit);
        addCell(tr, row.source);
        addCell(tr, row.notes);

        dataTableBody.appendChild(tr);
      });
    } catch (error) {
      console.error(
        "Error loading operator data:",
        error
      );
    }
  }

  // ============================================================
  // ADD EVIDENCE
  // ============================================================

  dataForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const data = {
      year: document.getElementById("year").value,
      area: document.getElementById("area").value,
      indicator: document.getElementById("indicator").value,
      value: document.getElementById("value").value,
      unit: document.getElementById("unit").value,
      source: document.getElementById("source").value,
      notes: document.getElementById("notes").value,
    };

    try {
      const response = await fetch("/add-data", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (!result.success) {
        alert(
          result.message || "Could not save evidence."
        );

        return;
      }

      alert("Evidence saved successfully.");

      dataForm.reset();

      loadOperatorData();
    } catch (error) {
      console.error(
        "Error adding evidence:",
        error
      );

      alert("Could not save evidence.");
    }
  });

  // ============================================================
  // RUN DECISION-SUPPORT MODEL
  // ============================================================

  runModelBtn.addEventListener("click", async () => {
    analysisStatus.textContent =
      "Running decision-support model...";

    resultsCard.style.display = "none";

    modelResults.innerHTML = "";

    try {
      const response = await fetch(
        "/api/run-model",
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (!response.ok || !result.success) {
        analysisStatus.textContent =
          result.message || "Model failed.";

        return;
      }

      analysisStatus.textContent =
        "Analysis completed.";

      resultsCard.style.display = "block";

      modelResults.innerHTML = "";

      // ========================================================
      // FINAL DECISION-SUPPORT RESULTS
      // ========================================================

      if (
        result.results &&
        result.results.length > 0
      ) {
        const heading =
          document.createElement("h3");

        heading.textContent =
          "Decision-Support Results";

        heading.style.marginBottom = "15px";

        modelResults.appendChild(heading);

        result.results.forEach(
          (item, index) => {
            const div =
              document.createElement("div");

            div.className = "result-card";

            const priority =
              item.priority_level !== undefined &&
              item.priority_level !== ""
                ? item.priority_level
                : "Not scored";

            const score =
              item.priority_score !== undefined &&
              item.priority_score !== ""
                ? item.priority_score
                : "Not scored";

            const aiScore =
              item.ai_priority_score !== undefined &&
              item.ai_priority_score !== ""
                ? item.ai_priority_score
                : "Not scored";

            const aiLevel =
              item.ai_priority_level !== undefined &&
              item.ai_priority_level !== ""
                ? item.ai_priority_level
                : "Not scored";

            div.innerHTML = `
              <h3>
                Action ${index + 1}
              </h3>

              <p>
                <b>Gap ID:</b>
                ${item.gap_id || ""}
              </p>

              <p>
                <b>Gap:</b>
                ${item.gap || ""}
              </p>

              <p>
                <b>Gap Type:</b>
                ${item.gap_type || ""}
              </p>

              <p>
                <b>Barrier Category:</b>
                ${item.barrier_category || ""}
              </p>

              <p>
                <b>Corrective Action:</b>
                ${item.corrective_action || ""}
              </p>

              <p>
                <b>Responsible Actor:</b>
                ${item.responsible_actor || ""}
              </p>

              <p>
                <b>Regulatory Dependency:</b>
                ${item.regulatory_dependency || ""}
              </p>

              <hr>

              <p>
                <b>Gap Severity (GS):</b>
                ${item.gap_severity ?? ""}
              </p>

              <p>
                <b>Barrier Severity (BS):</b>
                ${item.barrier_severity ?? ""}
              </p>

              <p>
                <b>Environmental Impact (EI):</b>
                ${item.environmental_impact ?? ""}
              </p>

              <p>
                <b>Implementation Feasibility (IF):</b>
                ${item.implementation_feasibility ?? ""}
              </p>

              <p>
                <b>Priority Score:</b>
                ${score}
              </p>

              <p>
                <b>Priority Level:</b>
                ${priority}
              </p>

              <p>
                <b>AI Priority Score:</b>
                ${aiScore}
              </p>

              <p>
                <b>AI Priority Level:</b>
                ${aiLevel}
              </p>

              <p>
                <b>Explanation:</b>
                ${item.explanation || ""}
              </p>
            `;

            modelResults.appendChild(div);
          }
        );

        // ======================================================
        // AHP / AI METADATA
        // ======================================================

        if (
          result.ai_meta &&
          result.ai_meta.ahp
        ) {
          const meta =
            document.createElement("div");

          meta.className = "result-card";

          const w = result.ai_meta.ahp;

          // ----------------------------------------------------
          // AHP WEIGHTS
          // ----------------------------------------------------

          let gapSeverity = "";
          let barrierSeverity = "";
          let environmentalImpact = "";
          let implementationFeasibility = "";

          /*
           * POSSIBLE FORMAT 1
           *
           * {
           *   GS: 0.424,
           *   BS: 0.227,
           *   EI: 0.227,
           *   IF: 0.122
           * }
           */

          if (
            w.GS !== undefined ||
            w.BS !== undefined ||
            w.EI !== undefined ||
            w.IF !== undefined
          ) {
            gapSeverity = w.GS;
            barrierSeverity = w.BS;
            environmentalImpact = w.EI;
            implementationFeasibility = w.IF;
          }

          /*
           * POSSIBLE FORMAT 2
           *
           * {
           *   gap_severity: 0.424,
           *   barrier_severity: 0.227,
           *   environmental_impact: 0.227,
           *   implementation_feasibility: 0.122
           * }
           */

          else if (
            w.gap_severity !== undefined ||
            w.barrier_severity !== undefined ||
            w.environmental_impact !== undefined ||
            w.implementation_feasibility !== undefined
          ) {
            gapSeverity = w.gap_severity;
            barrierSeverity = w.barrier_severity;
            environmentalImpact =
              w.environmental_impact;
            implementationFeasibility =
              w.implementation_feasibility;
          }

          /*
           * POSSIBLE FORMAT 3
           *
           * {
           *   weights: {
           *     gap_severity: 0.424,
           *     barrier_severity: 0.227,
           *     environmental_impact: 0.227,
           *     implementation_feasibility: 0.122
           *   }
           * }
           */

          else if (
            w.weights &&
            !Array.isArray(w.weights)
          ) {
            gapSeverity =
              w.weights.GS ??
              w.weights.gap_severity ??
              w.weights.gapSeverity;

            barrierSeverity =
              w.weights.BS ??
              w.weights.barrier_severity ??
              w.weights.barrierSeverity;

            environmentalImpact =
              w.weights.EI ??
              w.weights.environmental_impact ??
              w.weights.environmentalImpact;

            implementationFeasibility =
              w.weights.IF ??
              w.weights.implementation_feasibility ??
              w.weights.implementationFeasibility;
          }

          /*
           * POSSIBLE FORMAT 4
           *
           * weights is an array:
           *
           * [
           *   0.424,
           *   0.227,
           *   0.227,
           *   0.122
           * ]
           *
           * Order:
           *
           * 0 = Gap Severity
           * 1 = Barrier Severity
           * 2 = Environmental Impact
           * 3 = Implementation Feasibility
           */

          else if (
            Array.isArray(w.weights)
          ) {
            gapSeverity = w.weights[0];
            barrierSeverity = w.weights[1];
            environmentalImpact = w.weights[2];
            implementationFeasibility =
              w.weights[3];
          }

          /*
           * POSSIBLE FORMAT 5
           *
           * criteria_weights is an array
           */

          else if (
            Array.isArray(w.criteria_weights)
          ) {
            gapSeverity =
              w.criteria_weights[0];

            barrierSeverity =
              w.criteria_weights[1];

            environmentalImpact =
              w.criteria_weights[2];

            implementationFeasibility =
              w.criteria_weights[3];
          }

          /*
           * POSSIBLE FORMAT 6
           *
           * criteria_weights is an object
           */

          else if (
            w.criteria_weights &&
            typeof w.criteria_weights === "object"
          ) {
            gapSeverity =
              w.criteria_weights.GS ??
              w.criteria_weights.gap_severity;

            barrierSeverity =
              w.criteria_weights.BS ??
              w.criteria_weights.barrier_severity;

            environmentalImpact =
              w.criteria_weights.EI ??
              w.criteria_weights.environmental_impact;

            implementationFeasibility =
              w.criteria_weights.IF ??
              w.criteria_weights.implementation_feasibility;
          }

          // ----------------------------------------------------
          // CONSISTENCY RATIO
          // ----------------------------------------------------

          const consistencyRatio =
            w.CR ??
            w.cr ??
            w.consistency_ratio ??
            w.consistencyRatio ??
            result.ai_meta.consistency_ratio ??
            "";

          // ----------------------------------------------------
          // CROSS-VALIDATED MAE
          // ----------------------------------------------------

          const cvMae =
            result.ai_meta.cv_mae ??
            result.ai_meta.CV_MAE ??
            result.ai_meta.cvMAE ??
            "";

          // ----------------------------------------------------
          // TOP PREDICTIVE FEATURES
          // ----------------------------------------------------

          const topFeatures =
            Array.isArray(
              result.ai_meta.top_features
            )
              ? result.ai_meta.top_features
              : [];

          // ----------------------------------------------------
          // DISPLAY AHP INFORMATION
          // ----------------------------------------------------

          meta.innerHTML = `
            <h3>
              AHP Criteria Weights
            </h3>

            <p>
              <b>Gap Severity:</b>
              ${formatNumber(gapSeverity)}
              |
              <b>Barrier Severity:</b>
              ${formatNumber(barrierSeverity)}
              |
              <b>Environmental Impact:</b>
              ${formatNumber(environmentalImpact)}
              |
              <b>Feasibility:</b>
              ${formatNumber(
                implementationFeasibility
              )}
            </p>

            <p>
              <b>Consistency Ratio (CR):</b>
              ${formatNumber(consistencyRatio)}
              (must be &lt; 0.10)
            </p>

            <p>
              <b>Cross-validated MAE:</b>
              ${formatNumber(cvMae)}
            </p>

            <h3 style="margin-top:12px;">
              Top Predictive Features
            </h3>

            <ul>
              ${
                topFeatures.length > 0
                  ? topFeatures
                      .map(
                        (f) => `
                          <li>
                            ${f.feature || ""}
                            :
                            ${formatNumber(
                              f.importance
                            )}
                          </li>
                        `
                      )
                      .join("")
                  : `
                      <li>
                        No feature information available.
                      </li>
                    `
              }
            </ul>
          `;

          modelResults.appendChild(meta);
        }
      }

      // ========================================================
      // FALLBACK: GAP FINDINGS
      // ========================================================

      else if (
        result.findings &&
        result.findings.length > 0
      ) {
        const heading =
          document.createElement("h3");

        heading.textContent =
          "Identified Gaps";

        heading.style.marginBottom =
          "15px";

        modelResults.appendChild(heading);

        result.findings.forEach(
          (finding, index) => {
            const div =
              document.createElement("div");

            div.className =
              "result-card";

            div.innerHTML = `
              <h3>
                Finding ${index + 1}
              </h3>

              <p>
                <b>Area:</b>
                ${finding.area || ""}
              </p>

              <p>
                <b>Indicator:</b>
                ${finding.indicator || ""}
              </p>

              <p>
                <b>Value:</b>
                ${finding.value || ""}
              </p>

              <p>
                <b>Gap:</b>
                ${finding.gap || ""}
              </p>

              <p>
                <b>Gap Type:</b>
                ${finding.gap_type || ""}
              </p>
            `;

            modelResults.appendChild(div);
          }
        );
      }

      // ========================================================
      // NO FINDINGS
      // ========================================================

      else {
        modelResults.innerHTML = `
          <div class="result-card">

            <h3>
              No Findings
            </h3>

            <p>
              No gaps were identified
              for the selected operator
              based on the current
              evidence and model rules.
            </p>

          </div>
        `;
      }
    } catch (error) {
      console.error(
        "Model error:",
        error
      );

      analysisStatus.textContent =
        "Could not run the decision-support model.";
    }
  });

  // ============================================================
  // CLEAR OPERATOR EVIDENCE
  // ============================================================

  clearAllBtn.addEventListener(
    "click",
    async () => {
      if (
        !confirm(
          "Clear all your evidence?"
        )
      ) {
        return;
      }

      try {
        const response =
          await fetch(
            "/api/clear-data",
            {
              method: "POST",
            }
          );

        const result =
          await response.json();

        alert(result.message);

        resultsCard.style.display =
          "none";

        modelResults.innerHTML = "";

        analysisStatus.textContent = "";

        loadOperatorData();
      } catch (error) {
        console.error(
          "Error clearing data:",
          error
        );

        alert(
          "Could not clear evidence."
        );
      }
    }
  );

  // ============================================================
  // TABLE CELL HELPER
  // ============================================================

  function addCell(row, value) {
    const cell =
      document.createElement("td");

    cell.textContent =
      value === undefined ||
      value === null
        ? ""
        : value;

    row.appendChild(cell);
  }

  // ============================================================
  // NUMBER FORMATTER
  // ============================================================

  function formatNumber(value) {
    if (
      value === undefined ||
      value === null ||
      value === ""
    ) {
      return "Not available";
    }

    const number = Number(value);

    if (!Number.isNaN(number)) {
      return number.toFixed(4);
    }

    return value;
  }

  // ============================================================
  // START APPLICATION
  // ============================================================

  checkSession();
});