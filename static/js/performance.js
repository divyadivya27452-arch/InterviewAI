/**
 * Performance Analytics Page: Summary cards + 5 Chart.js charts.
 */

document.addEventListener("DOMContentLoaded", async () => {
  const { apiFetch, showToast, showLoader, hideLoader, formatDate } = window.InterviewAI;

  const charts = {};

  async function loadPerformance() {
    showLoader("Loading performance analytics...");
    try {
      const data = await apiFetch("/api/performance");
      const summary = data.summary || {};

      if (!summary.total_completed) {
        document.getElementById("performance-empty-state").classList.remove("hidden");
        document.getElementById("performance-content").classList.add("hidden");
        return;
      }

      document.getElementById("performance-empty-state").classList.add("hidden");
      document.getElementById("performance-content").classList.remove("hidden");

      document.getElementById("perf-best-score").textContent = `${summary.best_score}%`;
      document.getElementById("perf-lowest-score").textContent = `${summary.lowest_score}%`;
      document.getElementById("perf-top-role").textContent = summary.most_practiced_role || "—";
      document.getElementById("perf-total-completed").textContent = `${summary.total_completed} completed interviews`;

      renderTrendChart(data.score_trend || []);
      renderRadarChart(data.skill_averages || {});
      renderRoleChart(data.by_role || []);
      renderTypeChart(data.by_type || []);
      renderLevelChart(data.by_level || []);
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      hideLoader();
    }
  }

  function renderTrendChart(items) {
    const ctx = document.getElementById("perfTrendChart").getContext("2d");
    if (charts.trend) charts.trend.destroy();
    charts.trend = new Chart(ctx, {
      type: "line",
      data: {
        labels: items.map((i) => i.label || formatDate(i.date)),
        datasets: [
          {
            label: "Score (%)",
            data: items.map((i) => i.score),
            borderColor: "#2563eb",
            backgroundColor: "rgba(37, 99, 235, 0.14)",
            borderWidth: 3,
            fill: true,
            tension: 0.3,
            pointRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { min: 0, max: 100, ticks: { callback: (v) => `${v}%` } },
        },
      },
    });
  }

  function renderRadarChart(skillAverages) {
    const labels = ["Communication", "Technical Knowledge", "Confidence", "Problem Solving"];
    const ctx = document.getElementById("perfRadarChart").getContext("2d");
    if (charts.radar) charts.radar.destroy();
    charts.radar = new Chart(ctx, {
      type: "radar",
      data: {
        labels,
        datasets: [
          {
            label: "Average Skill Score",
            data: labels.map((k) => Number(skillAverages[k] || 0)),
            backgroundColor: "rgba(79, 70, 229, 0.22)",
            borderColor: "#4f46e5",
            pointBackgroundColor: "#4f46e5",
            borderWidth: 2.5,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { r: { min: 0, max: 100, ticks: { stepSize: 25, backdropColor: "transparent" } } },
      },
    });
  }

  function renderRoleChart(byRole) {
    const ctx = document.getElementById("perfRoleChart").getContext("2d");
    if (charts.role) charts.role.destroy();
    charts.role = new Chart(ctx, {
      type: "bar",
      data: {
        labels: byRole.map((r) => r.role),
        datasets: [
          {
            label: "Avg Score (%)",
            data: byRole.map((r) => r.average_score),
            backgroundColor: "#2563eb",
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { min: 0, max: 100 } },
      },
    });
  }

  function renderTypeChart(byType) {
    const ctx = document.getElementById("perfTypeChart").getContext("2d");
    if (charts.type) charts.type.destroy();
    charts.type = new Chart(ctx, {
      type: "bar",
      data: {
        labels: byType.map((t) => t.type),
        datasets: [
          {
            label: "Avg Score (%)",
            data: byType.map((t) => t.average_score),
            backgroundColor: ["#1d4ed8", "#059669", "#4f46e5"],
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { min: 0, max: 100 } },
      },
    });
  }

  function renderLevelChart(byLevel) {
    const ctx = document.getElementById("perfLevelChart").getContext("2d");
    if (charts.level) charts.level.destroy();
    charts.level = new Chart(ctx, {
      type: "bar",
      data: {
        labels: byLevel.map((l) => l.level),
        datasets: [
          {
            label: "Avg Score (%)",
            data: byLevel.map((l) => l.average_score),
            backgroundColor: ["#38bdf8", "#2563eb", "#1e3a8a"],
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { min: 0, max: 100 } },
      },
    });
  }

  loadPerformance();
});
