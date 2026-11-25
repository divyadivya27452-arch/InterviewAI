/**
 * Dashboard stats, Chart.js performance trend, and recent interviews table.
 */

document.addEventListener("DOMContentLoaded", async () => {
  const { apiFetch, showToast, showLoader, hideLoader, formatDate, scoreBadgeClass, escapeHtml } = window.InterviewAI;

  let perfChart = null;

  async function loadDashboard() {
    showLoader("Loading dashboard...");
    try {
      const [stats, perf, recent] = await Promise.all([
        apiFetch("/api/dashboard/stats"),
        apiFetch("/api/dashboard/performance"),
        apiFetch("/api/dashboard/recent"),
      ]);

      renderStats(stats);
      renderPerfChart(perf.items || []);
      renderRecentTable(recent.interviews || []);
    } catch (err) {
      showToast(err.message || "Failed to load dashboard.", "error");
    } finally {
      hideLoader();
    }
  }

  function renderStats(stats) {
    document.getElementById("stat-total-interviews").textContent = stats.total_interviews ?? 0;
    document.getElementById("stat-average-score").textContent = `${stats.average_score ?? 0}%`;
    document.getElementById("stat-skills-improved").textContent = stats.skills_improved ?? 0;
    document.getElementById("stat-practice-time").textContent = stats.practice_time_formatted || "0m";

    const hintEl = document.getElementById("stat-skills-hint");
    if (hintEl && Array.isArray(stats.improved_skill_names) && stats.improved_skill_names.length > 0) {
      hintEl.textContent = stats.improved_skill_names.join(", ");
    }
  }

  function renderPerfChart(items) {
    const chartContainer = document.getElementById("perf-chart-container");
    const emptyState = document.getElementById("perf-empty-state");

    if (!items.length) {
      chartContainer.classList.add("hidden");
      emptyState.classList.remove("hidden");
      return;
    }

    chartContainer.classList.remove("hidden");
    emptyState.classList.add("hidden");

    const ctx = document.getElementById("dashboardPerfChart").getContext("2d");
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, "rgba(37, 99, 235, 0.28)");
    gradient.addColorStop(1, "rgba(37, 99, 235, 0.02)");

    if (perfChart) perfChart.destroy();

    perfChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: items.map((i) => i.label || formatDate(i.date)),
        datasets: [
          {
            label: "Overall Score (%)",
            data: items.map((i) => i.score),
            borderColor: "#2563eb",
            backgroundColor: gradient,
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: "#1d4ed8",
            pointBorderColor: "#ffffff",
            pointBorderWidth: 2,
            pointRadius: 5,
            pointHoverRadius: 7,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel: (ctxItem) => {
                const item = items[ctxItem.dataIndex];
                return `${item.role} (${item.type} · ${item.level})`;
              },
            },
          },
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: { callback: (val) => `${val}%` },
            grid: { color: "#f1f5f9" },
          },
          x: {
            grid: { display: false },
          },
        },
      },
    });
  }

  function renderRecentTable(interviews) {
    const tableWrapper = document.getElementById("recent-table-wrapper");
    const emptyState = document.getElementById("recent-empty-state");
    const tbody = document.getElementById("recent-interviews-body");

    if (!interviews.length) {
      tableWrapper.classList.add("hidden");
      emptyState.classList.remove("hidden");
      return;
    }

    tableWrapper.classList.remove("hidden");
    emptyState.classList.add("hidden");

    tbody.innerHTML = interviews
      .map((item) => {
        const isCompleted = item.status === "Completed";
        const statusBadge = isCompleted
          ? '<span class="badge badge-emerald">Completed</span>'
          : '<span class="badge badge-amber">In Progress</span>';
        const scoreHtml = isCompleted
          ? `<span class="badge ${scoreBadgeClass(item.score)}">${item.score}%</span>`
          : '<span class="badge badge-slate">—</span>';
        const actionBtn = isCompleted
          ? `<a href="/feedback/${encodeURIComponent(item.id)}" class="btn btn-outline btn-sm">View Feedback</a>`
          : `<a href="/interview?resume=${encodeURIComponent(item.id)}" class="btn btn-primary btn-sm">Resume</a>`;

        return `
          <tr>
            <td>${escapeHtml(formatDate(item.date))}</td>
            <td><strong>${escapeHtml(item.role)}</strong></td>
            <td>${escapeHtml(item.type)}</td>
            <td>${scoreHtml}</td>
            <td>${statusBadge}</td>
            <td class="text-right">${actionBtn}</td>
          </tr>
        `;
      })
      .join("");
  }

  loadDashboard();
});
