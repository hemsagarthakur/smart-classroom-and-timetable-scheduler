document.addEventListener("DOMContentLoaded", () => {
    const analyticsPayload = window.analyticsPayload;
    const analyticsCharts = [];

    const renderAnalyticsCharts = () => {
        if (!analyticsPayload || typeof Chart === "undefined") {
            return;
        }

        analyticsCharts.splice(0).forEach((chart) => chart.destroy());

        const css = getComputedStyle(document.body);
        const textColor = css.getPropertyValue("--text-main").trim() || "#17212b";
        const mutedColor = css.getPropertyValue("--text-soft").trim() || "#5c6672";
        const gridColor = document.body.classList.contains("dark-mode") ? "rgba(148,163,184,0.18)" : "rgba(23,33,43,0.10)";

        const makeBarChart = (id, label, labels, values, color, extraDatasets = []) => {
            const element = document.getElementById(id);
            if (!element) return;
            const chart = new Chart(element, {
                type: "bar",
                data: {
                    labels,
                    datasets: [
                        {
                            label,
                            data: values,
                            backgroundColor: color,
                            borderRadius: 12,
                            borderSkipped: false
                        },
                        ...extraDatasets
                    ]
                },
                options: {
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: textColor }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: mutedColor },
                            grid: { display: false }
                        },
                        y: {
                            ticks: { color: mutedColor },
                            grid: { color: gridColor }
                        }
                    }
                }
            });
            analyticsCharts.push(chart);
        };

        const makePieChart = (id, labels, values, colors) => {
            const element = document.getElementById(id);
            if (!element) return;
            const chart = new Chart(element, {
                type: "pie",
                data: {
                    labels,
                    datasets: [{ data: values, backgroundColor: colors, borderColor: "rgba(255,255,255,0.65)", borderWidth: 2 }]
                },
                options: {
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {
                                color: textColor,
                                usePointStyle: true,
                                padding: 18
                            }
                        }
                    }
                }
            });
            analyticsCharts.push(chart);
        };

        makeBarChart(
            "facultyWorkloadChart",
            "Hours",
            analyticsPayload.faculty.labels,
            analyticsPayload.faculty.values,
            "rgba(95, 63, 255, 0.9)",
            [{
                type: "line",
                label: "Max Hours",
                data: analyticsPayload.faculty.limits,
                borderColor: "rgba(255, 96, 159, 0.9)",
                backgroundColor: "rgba(255, 96, 159, 0.15)",
                tension: 0.25,
                fill: false,
                pointRadius: 3
            }]
        );
        makeBarChart(
            "roomUtilizationChart",
            "Utilization %",
            analyticsPayload.rooms.labels,
            analyticsPayload.rooms.values,
            "rgba(44, 182, 227, 0.92)"
        );
        makePieChart(
            "subjectDistributionChart",
            analyticsPayload.subjects.labels,
            analyticsPayload.subjects.values,
            ["#ff4d6d", "#6c63ff", "#2ec4b6", "#ff9f1c", "#3a86ff", "#d946ef", "#22c55e", "#f97316", "#8b5cf6", "#06b6d4"]
        );
        makePieChart(
            "conflictStatsChart",
            analyticsPayload.conflicts.labels,
            analyticsPayload.conflicts.values,
            ["#22c55e", "#ef4444"]
        );
    };

    const darkModeToggle = document.getElementById("dark-mode-toggle");
    const savedTheme = localStorage.getItem("smartSchedulerTheme");
    if (savedTheme === "dark") {
        document.body.classList.add("dark-mode");
        if (darkModeToggle) darkModeToggle.textContent = "Light Mode";
    }
    if (darkModeToggle) {
        darkModeToggle.addEventListener("click", () => {
            document.body.classList.toggle("dark-mode");
            const isDark = document.body.classList.contains("dark-mode");
            localStorage.setItem("smartSchedulerTheme", isDark ? "dark" : "light");
            darkModeToggle.textContent = isDark ? "Light Mode" : "Dark Mode";
            renderAnalyticsCharts();
        });
    }

    const generateForm = document.getElementById("generate-form");
    const deptSelect = document.getElementById("generate-dept");
    const semesterSelect = document.getElementById("generate-semester");
    const validationBox = document.getElementById("validation-box");
    const validationList = document.getElementById("validation-list");
    const generateButton = document.getElementById("generate-btn");

    const runPrevalidation = () => {
        if (!deptSelect || !semesterSelect || !validationBox || !validationList || !generateButton) {
            return;
        }
        if (!deptSelect.value || !semesterSelect.value) {
            generateButton.disabled = true;
            validationBox.classList.add("d-none");
            return;
        }

        fetch(`/admin/validate-data?dept_id=${encodeURIComponent(deptSelect.value)}&semester=${encodeURIComponent(semesterSelect.value)}`)
            .then((response) => response.json())
            .then((data) => {
                validationList.innerHTML = "";
                if (data.valid) {
                    generateButton.disabled = false;
                    validationBox.classList.add("d-none");
                    return;
                }
                generateButton.disabled = true;
                validationBox.classList.remove("d-none");
                (data.warnings || []).forEach((warning) => {
                    const item = document.createElement("li");
                    item.textContent = warning;
                    validationList.appendChild(item);
                });
            })
            .catch(() => {
                generateButton.disabled = true;
                validationBox.classList.remove("d-none");
                validationList.innerHTML = "<li>Unable to validate generation data right now.</li>";
            });
    };

    if (deptSelect && semesterSelect) {
        deptSelect.addEventListener("change", runPrevalidation);
        semesterSelect.addEventListener("change", runPrevalidation);
        runPrevalidation();
    }

    if (generateForm) {
        generateForm.addEventListener("submit", () => {
            const button = document.getElementById("generate-btn");
            const spinner = document.getElementById("generate-spinner");
            const label = button ? button.querySelector(".button-label") : null;
            if (button && spinner) {
                button.disabled = true;
                spinner.classList.remove("d-none");
            }
            if (label) {
                label.textContent = "Generating...";
            }
        });
    }

    document.querySelectorAll(".fixed-slot-toggle").forEach((toggle) => {
        const wrapper = document.querySelector(".fixed-subject-wrapper");
        const sync = () => {
            if (!wrapper) return;
            wrapper.classList.toggle("d-none", !toggle.checked);
        };
        toggle.addEventListener("change", sync);
        sync();
    });

    document.querySelectorAll("[data-validate]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!form.checkValidity()) {
                event.preventDefault();
                form.classList.add("was-validated");
                alert("Please fill all required fields before submitting.");
            }
        });
    });

    document.querySelectorAll(".delete-form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm("Are you sure you want to delete this record?")) {
                event.preventDefault();
            }
        });
    });

    renderAnalyticsCharts();
});
