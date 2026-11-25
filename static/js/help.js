/**
 * Help Page: FAQ accordion + Support message submission.
 */

document.addEventListener("DOMContentLoaded", () => {
  const { apiFetch, showToast, showLoader, hideLoader } = window.InterviewAI;

  // FAQ Accordion
  const accordion = document.getElementById("faq-accordion");
  if (accordion) {
    accordion.querySelectorAll(".accordion-trigger").forEach((trigger) => {
      trigger.addEventListener("click", () => {
        trigger.closest(".accordion-item").classList.toggle("open");
      });
    });
  }

  // Contact Support Form
  const supportForm = document.getElementById("support-form");
  if (supportForm) {
    supportForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const subject = document.getElementById("support-subject").value.trim();
      const message = document.getElementById("support-message").value.trim();

      if (subject.length < 3) {
        showToast("Subject must be at least 3 characters.", "error");
        return;
      }
      if (message.length < 10) {
        showToast("Please enter at least 10 characters in your message.", "error");
        return;
      }

      showLoader("Sending support message...");
      try {
        await apiFetch("/api/support", {
          method: "POST",
          body: JSON.stringify({ subject, message }),
        });
        supportForm.reset();
        showToast("Support message sent successfully!", "success");
      } catch (err) {
        showToast(err.message, "error");
      } finally {
        hideLoader();
      }
    });
  }
});
