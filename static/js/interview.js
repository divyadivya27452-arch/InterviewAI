/**
 * AI Interview Runner: Setup, step-by-step Q&A, live timer,
 * Web Speech API dictation, auto-save to MongoDB, and AI evaluation submission.
 */

document.addEventListener("DOMContentLoaded", () => {
  const { apiFetch, showToast, showLoader, hideLoader } = window.InterviewAI;

  const setupSection = document.getElementById("interview-setup-section");
  const activeSection = document.getElementById("interview-active-section");
  const setupForm = document.getElementById("interview-setup-form");

  const roleBadge = document.getElementById("hud-role-badge");
  const typeBadge = document.getElementById("hud-type-badge");
  const levelBadge = document.getElementById("hud-level-badge");
  const timerEl = document.getElementById("interview-timer");
  const progressText = document.getElementById("question-progress-text");
  const answeredCountEl = document.getElementById("question-answered-count");
  const progressBar = document.getElementById("question-progress-bar");

  const categoryBadge = document.getElementById("question-category-badge");
  const saveStatusPill = document.getElementById("save-status-pill");
  const questionPrompt = document.getElementById("question-text");
  const answerTextarea = document.getElementById("answer-textarea");
  const wordCountLabel = document.getElementById("word-count-label");

  const voiceToggleBtn = document.getElementById("voice-toggle-btn");
  const voiceBtnLabel = document.getElementById("voice-btn-label");
  const voiceStatusNote = document.getElementById("voice-status-note");

  const prevBtn = document.getElementById("prev-question-btn");
  const skipBtn = document.getElementById("skip-question-btn");
  const nextBtn = document.getElementById("next-question-btn");
  const submitBtn = document.getElementById("submit-interview-btn");
  const dotsContainer = document.getElementById("question-dots");

  const state = {
    interviewId: null,
    role: "",
    level: "",
    type: "",
    questions: [],
    currentIndex: 0,
    totalElapsedSeconds: 0,
    questionStartedAt: Date.now(),
    timerInterval: null,
    recognition: null,
    isRecording: false,
  };

  function formatTimer(secs) {
    const m = String(Math.floor(secs / 60)).padStart(2, "0");
    const s = String(secs % 60).padStart(2, "0");
    return `${m}:${s}`;
  }

  function startTimer() {
    if (state.timerInterval) clearInterval(state.timerInterval);
    timerEl.textContent = formatTimer(state.totalElapsedSeconds);
    state.timerInterval = setInterval(() => {
      state.totalElapsedSeconds += 1;
      timerEl.textContent = formatTimer(state.totalElapsedSeconds);
    }, 1000);
  }

  function updateWordCount() {
    const text = answerTextarea.value.trim();
    const words = text ? text.split(/\s+/).length : 0;
    wordCountLabel.textContent = `${words} ${words === 1 ? "word" : "words"}`;
  }

  function initSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      voiceToggleBtn.addEventListener("click", () => {
        showToast("Voice input requires Chrome or Edge (Web Speech API not supported in this browser).", "warning");
      });
      return;
    }

    const recognition = new SpeechRec();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    let finalTranscript = "";

    recognition.onstart = () => {
      state.isRecording = true;
      finalTranscript = answerTextarea.value ? answerTextarea.value.trim() + " " : "";
      voiceToggleBtn.classList.add("btn-recording");
      voiceBtnLabel.textContent = "Stop Listening";
      voiceStatusNote.textContent = "Listening... speak clearly into your microphone.";
      voiceStatusNote.classList.remove("hidden");
    };

    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + " ";
        } else {
          interim += transcript;
        }
      }
      answerTextarea.value = (finalTranscript + interim).trim();
      updateWordCount();
    };

    recognition.onerror = (event) => {
      stopVoiceInput();
      if (event.error !== "aborted") {
        showToast(`Voice recognition error: ${event.error}`, "warning");
      }
    };

    recognition.onend = () => {
      if (state.isRecording) {
        stopVoiceInput();
      }
    };

    state.recognition = recognition;

    voiceToggleBtn.addEventListener("click", () => {
      if (state.isRecording) {
        stopVoiceInput();
      } else {
        try {
          state.recognition.start();
        } catch (_err) {
          stopVoiceInput();
        }
      }
    });
  }

  function stopVoiceInput() {
    state.isRecording = false;
    if (state.recognition) {
      try {
        state.recognition.stop();
      } catch (_err) {
        // Ignore already stopped
      }
    }
    voiceToggleBtn.classList.remove("btn-recording");
    voiceBtnLabel.textContent = "Voice Input";
    voiceStatusNote.classList.add("hidden");
  }

  function renderDots() {
    dotsContainer.innerHTML = "";
    state.questions.forEach((q, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = idx + 1;
      btn.className = "q-dot";
      if (idx === state.currentIndex) btn.classList.add("current");
      else if (q.skipped) btn.classList.add("skipped");
      else if (q.answer && q.answer.trim().length > 0) btn.classList.add("answered");

      btn.addEventListener("click", async () => {
        if (idx === state.currentIndex) return;
        await persistCurrentAnswer(false);
        state.currentIndex = idx;
        renderCurrentQuestion();
      });
      dotsContainer.appendChild(btn);
    });
  }

  function renderCurrentQuestion() {
    stopVoiceInput();
    const total = state.questions.length;
    const q = state.questions[state.currentIndex];
    state.questionStartedAt = Date.now();

    roleBadge.textContent = state.role;
    typeBadge.textContent = state.type;
    levelBadge.textContent = state.level;

    progressText.textContent = `Question ${state.currentIndex + 1} of ${total}`;
    const answeredCount = state.questions.filter((item) => item.answer && item.answer.trim().length > 0).length;
    answeredCountEl.textContent = `${answeredCount} answered`;
    progressBar.style.width = `${Math.round(((state.currentIndex + 1) / total) * 100)}%`;

    categoryBadge.textContent = q.category || "Technical";
    categoryBadge.className = `badge ${q.category === "HR" ? "badge-indigo" : "badge-emerald"}`;

    questionPrompt.textContent = q.question;
    answerTextarea.value = q.skipped ? "" : (q.answer || "");
    updateWordCount();

    saveStatusPill.textContent = q.skipped ? "Skipped" : (q.answer ? "Saved" : "Not saved yet");

    prevBtn.disabled = state.currentIndex === 0;
    const isLast = state.currentIndex === total - 1;
    nextBtn.classList.toggle("hidden", isLast);

    renderDots();
  }

  async function persistCurrentAnswer(markSkipped = false) {
    const q = state.questions[state.currentIndex];
    if (!q || !state.interviewId) return;

    const deltaSecs = Math.max(0, Math.round((Date.now() - state.questionStartedAt) / 1000));
    state.questionStartedAt = Date.now();
    q.time_spent_seconds = (q.time_spent_seconds || 0) + deltaSecs;

    if (markSkipped) {
      q.answer = "";
      q.skipped = true;
    } else {
      const text = answerTextarea.value.trim();
      q.answer = text;
      if (text.length > 0) q.skipped = false;
    }

    saveStatusPill.textContent = "Saving...";
    try {
      await apiFetch("/api/interview/answer", {
        method: "POST",
        body: JSON.stringify({
          interview_id: state.interviewId,
          question_index: q.index ?? state.currentIndex,
          answer: q.answer,
          skipped: q.skipped,
          time_spent_seconds: q.time_spent_seconds,
          duration_seconds: state.totalElapsedSeconds,
        }),
      });
      saveStatusPill.textContent = q.skipped ? "Skipped & Saved" : "Saved to DB";
    } catch (err) {
      saveStatusPill.textContent = "Save retry needed";
      showToast(err.message, "error");
    }
  }

  function enterActiveInterview(payload) {
    state.interviewId = payload.interview_id || payload.id;
    state.role = payload.role;
    state.level = payload.level;
    state.type = payload.type;
    state.questions = payload.questions || [];
    state.totalElapsedSeconds = payload.duration_seconds || 0;

    // Jump to first unanswered question when resuming
    const firstPendingIdx = state.questions.findIndex((q) => !q.answer && !q.skipped);
    state.currentIndex = firstPendingIdx >= 0 ? firstPendingIdx : 0;

    setupSection.classList.add("hidden");
    activeSection.classList.remove("hidden");
    startTimer();
    renderCurrentQuestion();
  }

  // Start Interview form
  if (setupForm) {
    setupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const role = document.getElementById("setup-role").value;
      const level = document.getElementById("setup-level").value;
      const type = document.getElementById("setup-type").value;
      const total_questions = Number(document.getElementById("setup-count").value);

      showLoader("Generating your tailored interview...");
      try {
        const data = await apiFetch("/api/interview/start", {
          method: "POST",
          body: JSON.stringify({ role, level, type, total_questions }),
        });
        enterActiveInterview(data);
        showToast("Interview started. Good luck!", "success");
      } catch (err) {
        showToast(err.message, "error");
      } finally {
        hideLoader();
      }
    });
  }

  answerTextarea.addEventListener("input", updateWordCount);

  prevBtn.addEventListener("click", async () => {
    if (state.currentIndex <= 0) return;
    await persistCurrentAnswer(false);
    state.currentIndex -= 1;
    renderCurrentQuestion();
  });

  nextBtn.addEventListener("click", async () => {
    await persistCurrentAnswer(false);
    if (state.currentIndex < state.questions.length - 1) {
      state.currentIndex += 1;
      renderCurrentQuestion();
    }
  });

  skipBtn.addEventListener("click", async () => {
    await persistCurrentAnswer(true);
    if (state.currentIndex < state.questions.length - 1) {
      state.currentIndex += 1;
      renderCurrentQuestion();
    } else {
      renderDots();
      showToast("Last question skipped. Click Submit Interview when ready.", "info");
    }
  });

  submitBtn.addEventListener("click", async () => {
    stopVoiceInput();
    await persistCurrentAnswer(false);

    const unanswered = state.questions.filter((q) => !q.skipped && (!q.answer || !q.answer.trim())).length;
    if (unanswered > 0) {
      const proceed = window.confirm(
        `You still have ${unanswered} unanswered question(s). Submit and evaluate now?`
      );
      if (!proceed) return;
    }

    if (state.timerInterval) clearInterval(state.timerInterval);
    showLoader("Evaluating your answers with AI...");

    try {
      const answersPayload = state.questions.map((q, idx) => ({
        question_index: q.index ?? idx,
        answer: q.answer || "",
        skipped: Boolean(q.skipped),
        time_spent_seconds: q.time_spent_seconds || 0,
      }));

      const result = await apiFetch("/api/interview/finish", {
        method: "POST",
        body: JSON.stringify({
          interview_id: state.interviewId,
          duration_seconds: state.totalElapsedSeconds,
          answers: answersPayload,
        }),
      });

      showToast("Evaluation complete!", "success");
      window.location.href = `/feedback/${encodeURIComponent(result.id || state.interviewId)}`;
    } catch (err) {
      showToast(err.message, "error");
      startTimer();
    } finally {
      hideLoader();
    }
  });

  // Check if resuming an In Progress interview via ?resume=<id>
  async function checkResumeQuery() {
    const params = new URLSearchParams(window.location.search);
    const resumeId = params.get("resume");
    if (!resumeId) return;

    showLoader("Resuming interview session...");
    try {
      const data = await apiFetch(`/api/interviews/${encodeURIComponent(resumeId)}?mode=resume`);
      if (data.status === "Completed") {
        window.location.href = `/feedback/${encodeURIComponent(data.id)}`;
        return;
      }
      enterActiveInterview(data);
      showToast("Resumed your interview session.", "info");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      hideLoader();
    }
  }

  initSpeechRecognition();
  checkResumeQuery();
});
