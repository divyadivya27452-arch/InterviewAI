/**
 * Interview History Page: Search, filters, pagination, and delete record.
 */

document.addEventListener("DOMContentLoaded", () => {
  const { apiFetch, showToast, showLoader, hideLoader, formatDate, scoreBadgeClass, escapeHtml } = window.InterviewAI;

  const searchInput = document.getElementById("filter-search");
  const roleSelect = document.getElementById("filter-role");
  const typeSelect = document.getElementById("filter-type");
  const levelSelect = document.getElementById("filter-level");
  const dateFromInput = document.getElementById("filter-date-from");
  const dateToInput = document.getElementById("filter-date-to");
  const resetBtn = document.getElementById("reset-filters-btn");

  const tableWrapper = document.getElementById("history-table-wrapper");
  const tbody = document.getElementById("history-table-body");
  const emptyState = document.getElementById("history-empty-state");
  const countLabel = document.getElementById("history-count-label");
  const paginationBar = document.getElementById("history-pagination");
  const prevPageBtn = document.getElementById("prev-page-btn");
  const nextPageBtn = document.getElementById("next-page-btn");
  const paginationInfo = document.getElementById("pagination-info");

  const deleteModal = document.getElementById("delete-interview-modal");
  const cancelDeleteBtn = document.getElementById("cancel-delete-interview-btn");
  const confirmDeleteBtn = document.getElementById("confirm-delete-interview-btn");

  let currentPage = 1;
  let totalPages = 1;
  let pendingDeleteId = null;
  let debounceTimer = null;

  async function fetchHistory() {
    const params = new URLSearchParams({
      page: currentPage,
      limit: 8,
    });
    if (searchInput.value.trim()) params.set("search", searchInput.value.trim());
    if (roleSelect.value) params.set("role", roleSelect.value);
    if (typeSelect.value) params.set("type", typeSelect.value);
    if (levelSelect.value) params.set("level", levelSelect.value);
    if (dateFromInput.value) params.set("date_from", dateFromInput.value);
    if (dateToInput.value) params.set("date_to", dateToInput.value);

    showLoader("Loading interview history...");
    try {
      const data = await apiFetch(`/api/interviews?${params.toString()}`);
      currentPage = data.page;
      totalPages = data.total_pages;
      renderTable(data.interviews || [], data.total || 0);
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      hideLoader();
    }
  }

  function renderTable(items, total) {
    countLabel.textContent = `${total} interview record${total === 1 ? "" : "s"} found`;

    if (!items.length) {
      tableWrapper.classList.add("hidden");
      paginationBar.classList.add("hidden");
      emptyState.classList.remove("hidden");
      return;
    }

    tableWrapper.classList.remove("hidden");
    emptyState.classList.add("hidden");
    paginationBar.classList.remove("hidden");

    tbody.innerHTML = items
      .map((item) => {
        const isCompleted = item.status === "Completed";
        const statusBadge = isCompleted
          ? '<span class="badge badge-emerald">Completed</span>'
          : '<span class="badge badge-amber">In Progress</span>';
        const scoreHtml = isCompleted
          ? `<span class="badge ${scoreBadgeClass(item.score)}">${item.score}%</span>`
          : '<span class="badge badge-slate">—</span>';
        const viewBtn = isCompleted
          ? `<a href="/feedback/${encodeURIComponent(item.id)}" class="btn btn-outline btn-sm">View Feedback</a>`
          : `<a href="/interview?resume=${encodeURIComponent(item.id)}" class="btn btn-primary btn-sm">Resume</a>`;

        return `
          <tr>
            <td>${escapeHtml(formatDate(item.date))}</td>
            <td><strong>${escapeHtml(item.role)}</strong></td>
            <td>${escapeHtml(item.type)}</td>
            <td>${escapeHtml(item.level)}</td>
            <td>${item.total_questions}</td>
            <td>${scoreHtml}</td>
            <td>${statusBadge}</td>
            <td class="text-right">
              <div style="display:inline-flex; gap:8px; align-items:center;">
                ${viewBtn}
                <button type="button" class="btn btn-ghost btn-sm text-danger delete-record-btn" data-id="${escapeHtml(item.id)}">Delete</button>
              </div>
            </td>
          </tr>
        `;
      })
      .join("");

    paginationInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    prevPageBtn.disabled = currentPage <= 1;
    nextPageBtn.disabled = currentPage >= totalPages;

    tbody.querySelectorAll(".delete-record-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        pendingDeleteId = btn.dataset.id;
        deleteModal.classList.remove("hidden");
      });
    });
  }

  function triggerFilteredReload() {
    currentPage = 1;
    fetchHistory();
  }

  searchInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(triggerFilteredReload, 300);
  });

  [roleSelect, typeSelect, levelSelect, dateFromInput, dateToInput].forEach((el) => {
    el.addEventListener("change", triggerFilteredReload);
  });

  resetBtn.addEventListener("click", () => {
    searchInput.value = "";
    roleSelect.value = "";
    typeSelect.value = "";
    levelSelect.value = "";
    dateFromInput.value = "";
    dateToInput.value = "";
    triggerFilteredReload();
  });

  prevPageBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage -= 1;
      fetchHistory();
    }
  });

  nextPageBtn.addEventListener("click", () => {
    if (currentPage < totalPages) {
      currentPage += 1;
      fetchHistory();
    }
  });

  cancelDeleteBtn.addEventListener("click", () => {
    pendingDeleteId = null;
    deleteModal.classList.add("hidden");
  });

  confirmDeleteBtn.addEventListener("click", async () => {
    if (!pendingDeleteId) return;
    confirmDeleteBtn.disabled = true;
    try {
      await apiFetch(`/api/interviews/${encodeURIComponent(pendingDeleteId)}`, {
        method: "DELETE",
      });
      showToast("Interview record deleted.", "success");
      deleteModal.classList.add("hidden");
      pendingDeleteId = null;
      fetchHistory();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      confirmDeleteBtn.disabled = false;
    }
  });

  fetchHistory();
});
