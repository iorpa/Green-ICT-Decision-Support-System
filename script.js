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
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {

                loginMessage.textContent =
                    data.message || "Invalid username or password.";

                return;
            }

            showApplication(data);

        } catch (error) {

            console.error(error);

            loginMessage.textContent =
                "Could not connect to the server.";
        }
    });


    logoutBtn.addEventListener("click", async () => {

        try {

            await fetch("/api/logout", {
                method: "POST"
            });

        } catch (error) {

            console.error(error);
        }

        location.reload();
    });


    function showApplication(data) {

        loginView.style.display = "none";
        appView.style.display = "block";

        currentUser.textContent = data.operator || "Operator";

        loadOperatorData();
    }


    
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

            loginView.style.display = "block";
            appView.style.display = "none";
        }
    }


 
    async function loadOperatorData() {

        try {

            const response = await fetch("/api/data");
            const result = await response.json();

            if (!result.success) {
                return;
            }

            dataTableBody.innerHTML = "";

            if (result.data.length === 0) {

                emptyMessage.style.display = "block";

                return;
            }

            emptyMessage.style.display = "none";

            result.data.forEach(row => {

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

            console.error("Error loading data:", error);
        }
    }


    dataForm.addEventListener("submit", async (e) => {

        e.preventDefault();

        const data = {
            year: document.getElementById("year").value,
            area: document.getElementById("area").value,
            indicator: document.getElementById("indicator").value,
            value: document.getElementById("value").value,
            unit: document.getElementById("unit").value,
            source: document.getElementById("source").value,
            notes: document.getElementById("notes").value
        };

        try {

            const response = await fetch("/add-data", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!result.success) {

                alert(result.message);

                return;
            }

            alert("Evidence saved successfully.");

            dataForm.reset();

            loadOperatorData();

        } catch (error) {

            console.error("Error adding evidence:", error);

            alert("Could not save evidence.");
        }
    });



    runModelBtn.addEventListener("click", async () => {

        analysisStatus.textContent =
            "Running decision-support model...";

        resultsCard.style.display = "none";

        try {

            const response = await fetch("/api/run-model", {
                method: "POST"
            });

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



            if (result.findings && result.findings.length > 0) {

                result.findings.forEach((finding, index) => {

                    const div = document.createElement("div");

                    div.className = "result-card";

                    div.innerHTML = `
                        <h3>Finding ${index + 1}</h3>

                        <p>
                            <b>Area:</b>
                            ${finding.area}
                        </p>

                        <p>
                            <b>Indicator:</b>
                            ${finding.indicator}
                        </p>

                        <p>
                            <b>Value:</b>
                            ${finding.value}
                        </p>

                        <p>
                            <b>Gap:</b>
                            ${finding.gap}
                        </p>

                        <p>
                            <b>Barrier:</b>
                            ${finding.barrier}
                        </p>

                        <p>
                            <b>Corrective Action:</b>
                            ${finding.action}
                        </p>
                    `;

                    modelResults.appendChild(div);
                });

            } else {

                modelResults.innerHTML = `
                    <div class="result-card">
                        <h3>No Findings</h3>
                        <p>No evidence is available for analysis.</p>
                    </div>
                `;
            }



            if (result.results && result.results.length > 0) {

                const rankingTitle = document.createElement("h3");

                rankingTitle.textContent =
                    "Corrective Action Ranking";

                rankingTitle.style.marginBottom = "15px";

                modelResults.appendChild(rankingTitle);


                result.results.forEach((item, index) => {

                    const div = document.createElement("div");

                    div.className = "result-card";

                    div.innerHTML = `
                        <h3>
                            Priority ${item.Rank || index + 1}
                        </h3>

                        <p>
                            <b>Corrective Action:</b>
                            ${item.action}
                        </p>

                        <p>
                            <b>Evidence Count:</b>
                            ${item.evidence_count}
                        </p>
                    `;

                    modelResults.appendChild(div);
                });
            }

        } catch (error) {

            console.error("Model error:", error);

            analysisStatus.textContent =
                "Could not run the decision-support model.";
        }
    });


   

    clearAllBtn.addEventListener("click", async () => {

        if (!confirm("Clear all your evidence?")) {
            return;
        }

        try {

            const response = await fetch("/api/clear-data", {
                method: "POST"
            });

            const result = await response.json();

            alert(result.message);

            resultsCard.style.display = "none";

            modelResults.innerHTML = "";

            analysisStatus.textContent = "";

            loadOperatorData();

        } catch (error) {

            console.error("Error clearing data:", error);

            alert("Could not clear evidence.");
        }
    });


 

    function addCell(row, value) {

        const cell = document.createElement("td");

        cell.textContent =
            value === undefined || value === null
                ? ""
                : value;

        row.appendChild(cell);
    }
    

    checkSession();

});