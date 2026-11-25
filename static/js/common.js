/**
 * Shared frontend utilities: Fetch wrapper, toast notifications,
 * global loading spinner, date/duration formatters, and responsive sidebar.
 */

(function () {
  "use strict";

  function showToast(message, type = "info", duration = 3800) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const textSpan = document.createElement("span");
    textSpan.textContent = message;
    toast.appendChild(textSpan);

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(8px)";
      toast.style.transition = "all 0.2s ease";
      setTimeout(() => toast.remove(), 220);
    }, duration);
  }

  function showLoader(text = "Loading...") {
    const loader = document.getElementById("global-loader");
    const label = document.getElementById("loader-text");
    if (label) label.textContent = text;
    if (loader) loader.classList.remove("hidden");
  }

  function hideLoader() {
    const loader = document.getElementById("global-loader");
    if (loader) loader.classList.add("hidden");
  }

  async function apiFetch(url, options = {}) {
    const config = {
      credentials: "same-origin",
      ...options,
    };

    if (!(config.body instanceof FormData)) {
      config.headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      };
    } else {
      config.headers = { ...(options.headers || {}) };
    }

    const response = await fetch(url, config);
    let data = {};
    try {
      data = await response.json();
    } catch (_err) {
      data = {};
    }

    if (response.status === 401 && !url.includes("/api/login") && !url.includes("/api/register")) {
      window.location.href = "/login";
      throw new Error("Session expired. Redirecting to login...");
    }

    if (!response.ok) {
      throw new Error(data.error || `Request failed (${response.status})`);
    }

    return data;
  }

  function formatDate(isoString) {
    if (!isoString) return "—";
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return "—";
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function formatDuration(seconds) {
    const s = Math.max(0, Number(seconds) || 0);
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    const hrs = Math.floor(mins / 60);
    if (hrs > 0) {
      return `${hrs}h ${mins % 60}m`;
    }
    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  }

  function scoreBadgeClass(score) {
    if (score === null || score === undefined) return "badge-slate";
    if (score >= 75) return "badge-emerald";
    if (score >= 50) return "badge-amber";
    return "badge-rose";
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  // Mobile sidebar drawer controls
  document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");
    const toggleBtn = document.getElementById("sidebar-toggle-btn");
    const closeBtn = document.getElementById("sidebar-close-btn");

    function closeSidebar() {
      if (sidebar) sidebar.classList.remove("open");
      if (backdrop) backdrop.classList.remove("open");
    }

    if (toggleBtn && sidebar && backdrop) {
      toggleBtn.addEventListener("click", () => {
        sidebar.classList.add("open");
        backdrop.classList.add("open");
      });
    }
    if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
    if (backdrop) backdrop.addEventListener("click", closeSidebar);
  });

  window.InterviewAI = {
    showToast,
    showLoader,
    hideLoader,
    apiFetch,
    formatDate,
    formatDuration,
    scoreBadgeClass,
    escapeHtml,
  };
})();
