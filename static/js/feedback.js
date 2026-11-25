/**
 * AI Feedback Page: Score circle gauge, skill breakdown radar + deltas,
 * improved skills banner, and expandable per-question feedback cards.
 */

document.addEventListener("DOMContentLoaded", async () => {
  const { apiFetch, showToast, showLoader, hideLoader, formatDate, formatDuration, scoreBadgeClass, escapeHtml } = window.InterviewAI;

  const root = document.getElementById("feedback-root");
  const interviewId = (root && root.dataset.interviewId) ? root.dataset.interviewId.trim() : "latest";
  const targetId = interviewId || "latest";

  let radarChart = null;
  let allExpanded = false;

  async function loadFeedback() {
    showLoader("Loading AI feedback...");
    try {
      const data = await apiFetch(`/api/interviews/${encodeURIComponent(targetId)}`);
      if (data.status !== "Completed") {
        window.location.href = `/interview?resume=${encodeURIComponent(data.id)}`;
        return;
      }

      document.getElementById("feedback-empty-state").classList.add("hidden");
      document.getElementById("feedback-content").classList.remove("hidden");
      renderOverview(data);
      renderSkills(data.skill_scores || {}, data.previous_skill_scores || {});
      renderQuestionCards(data.questions || []);
    } catch (err) {
      if (targetId === "latest") {
        document.getElementById("feedback-empty-state").classList.remove("hidden");
        document.getElementById("feedback-content").classList.add("hidden");
      } else {
        showToast(err.message, "error");
      }
    } finally {
      hideLoader();
    }
  }

  function renderOverview(data) {
    const score = Math.round(Number(data.overall_score) || 0);
    document.getElementById("feedback-overall-score").textContent = score;

    const circle = document.getElementById("score-circle-progress");
    const circumference = 2 * Math.PI * 52; // ~326.72
    circle.style.strokeDasharray = circumference;
    const offset = circumference - (Math.max(0, Math.min(100, score)) / 100) * circumference;
    requestAnimationFrame(() => {
      circle.style.strokeDashoffset = offset;
    });

    const verdictEl = document.getElementById("feedback-score-verdict");
    if (score >= 80) {
      circle.style.stroke = "#059669";
      verdictEl.textContent = "Strong Performance";
      verdictEl.className = "verdict-pill badge-emerald";
    } else if (score >= 60) {
      circle.style.stroke = "#2563eb";
      verdictEl.textContent = "Solid Foundation";
      verdictEl.className = "verdict-pill badge-blue";
    } else if (score >= 40) {
      circle.style.stroke = "#d97706";
      verdictEl.textContent = "Needs Polish";
      verdictEl.className = "verdict-pill badge-amber";
    } else {
      circle.style.stroke = "#e11d48";
      verdictEl.textContent = "Keep Practicing";
      verdictEl.className = "verdict-pill badge-rose";
    }

    document.getElementById("feedback-role-title").textContent = `${data.role} Interview Feedback`;
    document.getElementById("feedback-date-subtitle").textContent = `Completed on ${formatDate(data.completed_at || data.created_at)}`;
    document.getElementById("feedback-eval-mode").textContent =
      data.evaluation_mode === "gemini" ? "Evaluated by Gemini AI" : "Rule-Based AI Evaluator";

    document.getElementById("fb-badge-type").textContent = data.type;
    document.getElementById("fb-badge-level").textContent = data.level;
    document.getElementById("fb-badge-questions").textContent = `${data.total_questions} Questions`;
    document.getElementById("fb-badge-duration").textContent = formatDuration(data.duration_seconds);

    const improved = data.skills_improved || [];
    const improvedBox = document.getElementById("skills-improved-box");
    const chipsRow = document.getElementById("skills-improved-chips");
    if (improved.length > 0) {
      improvedBox.classList.remove("hidden");
      chipsRow.innerHTML = improved
        .map((skill) => `<span class="badge badge-emerald">↑ ${escapeHtml(skill)}</span>`)
        .join("");
    } else {
      improvedBox.classList.add("hidden");
    }
  }

  function renderSkills(skills, prevSkills) {
    const labels = ["Communication", "Technical Knowledge", "Confidence", "Problem Solving"];
    const currentVals = labels.map((k) => Number(skills[k] || 0));
    const prevVals = labels.map((k) => Number(prevSkills[k] || 0));
    const hasPrev = Object.keys(prevSkills).length > 0;

    const ctx = document.getElementById("feedbackSkillRadar").getContext("2d");
    if (radarChart) radarChart.destroy();

    const datasets = [
      {
        label: "Current Interview",
        data: currentVals,
        backgroundColor: "rgba(37, 99, 235, 0.2)",
        borderColor: "#2563eb",
        pointBackgroundColor: "#1d4ed8",
        borderWidth: 2.5,
      },
    ];
    if (hasPrev) {
      datasets.push({
        label: "Previous Attempt",
        data: prevVals,
        backgroundColor: "rgba(100, 116, 139, 0.12)",
        borderColor: "#94a3b8",
        pointBackgroundColor: "#64748b",
        borderDash: [5, 4],
        borderWidth: 2,
      });
    }

    radarChart = new Chart(ctx, {
      type: "radar",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 0,
            max: 100,
            ticks: { stepSize: 25, backdropColor: "transparent" },
          },
        },
      },
    });

    const barsList = document.getElementById("skill-bars-list");
    barsList.innerHTML = labels
      .map((label) => {
        const val = Math.round(Number(skills[label] || 0));
        let deltaHtml = "";
        if (hasPrev) {
          const prev = Math.round(Number(prevSkills[label] || 0));
          const diff = val - prev;
          if (diff > 0) deltaHtml = `<span class="skill-delta up">▲ +${diff} vs prev</span>`;
          else if (diff < 0) deltaHtml = `<span class="skill-delta down">▼ ${diff} vs prev</span>`;
          else deltaHtml = `<span class="skill-delta flat">• 0 vs prev</span>`;
        }
        return `
          <div class="skill-bar-item">
            <div class="skill-bar-top">
              <span>${escapeHtml(label)} ${deltaHtml}</span>
              <strong>${val}%</strong>
            </div>
            <div class="skill-bar-track">
              <div class="skill-bar-fill" style="width: ${val}%;"></div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  function renderList(items) {
    if (!Array.isArray(items) || !items.length) return "<li>—</li>";
    return items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  }

  function renderQuestionCards(questions) {
    const container = document.getElementById("question-feedback-list");
    container.innerHTML = questions
      .map((q, idx) => {
        const fb = q.feedback || {};
        const score = Number(q.score || 0);
        const answerText = q.skipped || !q.answer ? "<em>Question was skipped or left blank.</em>" : escapeHtml(q.answer);
        const openClass = idx === 0 ? "open" : "";

        return `
          <div class="accordion-item ${openClass}">
            <button type="button" class="accordion-trigger">
              <div class="fb-q-header">
                <span class="badge ${scoreBadgeClass(score)}">${score}/100</span>
                <span class="badge ${q.category === "HR" ? "badge-indigo" : "badge-slate"}">${escapeHtml(q.category || "Technical")}</span>
                <span class="fb-q-title">Q${idx + 1}: ${escapeHtml(q.question)}</span>
              </div>
              <span class="accordion-chevron">▾</span>
            </button>
            <div class="accordion-panel">
              <p><strong>Question:</strong> ${escapeHtml(q.question)}</p>
              <div class="fb-answer-box">
                <strong>Your Answer:</strong> ${answerText}
              </div>
              <div class="fb-sections-grid">
                <div class="fb-box fb-strengths">
                  <h4>Strengths</h4>
                  <ul>${renderList(fb.strengths)}</ul>
                </div>
                <div class="fb-box fb-weaknesses">
                  <h4>Weaknesses</h4>
                  <ul>${renderList(fb.weaknesses)}</ul>
                </div>
                <div class="fb-box fb-improvements">
                  <h4>Suggested Improvements</h4>
                  <ul>${renderList(fb.improvements)}</ul>
                </div>
                <div class="fb-box fb-ideal">
                  <h4>Model / Ideal Answer Hint</h4>
                  <p style="margin:0;">${escapeHtml(fb.ideal_answer || q.ideal_answer || "Focus on clear structure and concrete examples.")}</p>
                </div>
              </div>
            </div>
          </div>
        `;
      })
      .join("");

    container.querySelectorAll(".accordion-trigger").forEach((trigger) => {
      trigger.addEventListener("click", () => {
        trigger.closest(".accordion-item").classList.toggle("open");
      });
    });

    const toggleAllBtn = document.getElementById("toggle-all-cards-btn");
    toggleAllBtn.addEventListener("click", () => {
      allExpanded = !allExpanded;
      container.querySelectorAll(".accordion-item").forEach((el) => {
        el.classList.toggle("open", allExpanded);
      });
      toggleAllBtn.textContent = allExpanded ? "Collapse All" : "Expand All";
    });
  }

  loadFeedback();
});
