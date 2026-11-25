/**
 * Login & Registration handlers.
 */

document.addEventListener("DOMContentLoaded", () => {
  const { apiFetch, showToast } = window.InterviewAI;

  // Toggle password visibility buttons
  document.querySelectorAll(".toggle-password").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.target);
      if (!target) return;
      const isPassword = target.type === "password";
      target.type = isPassword ? "text" : "password";
      btn.textContent = isPassword ? "Hide" : "Show";
    });
  });

  // Login Form
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("login-email").value.trim();
      const password = document.getElementById("login-password").value;
      const submitBtn = document.getElementById("login-submit-btn");

      if (!email || !password) {
        showToast("Please enter both email and password.", "error");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = "Signing in...";

      try {
        await apiFetch("/api/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        showToast("Welcome back! Redirecting...", "success");
        setTimeout(() => {
          window.location.href = "/dashboard";
        }, 350);
      } catch (err) {
        showToast(err.message, "error");
        submitBtn.disabled = false;
        submitBtn.textContent = "Sign In";
      }
    });
  }

  // Register Form
  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("reg-name").value.trim();
      const email = document.getElementById("reg-email").value.trim();
      const password = document.getElementById("reg-password").value;
      const confirmPassword = document.getElementById("reg-confirm-password").value;
      const submitBtn = document.getElementById("register-submit-btn");

      if (name.length < 2) {
        showToast("Full name must be at least 2 characters.", "error");
        return;
      }
      if (!email.includes("@")) {
        showToast("Please enter a valid email address.", "error");
        return;
      }
      if (password.length < 6) {
        showToast("Password must be at least 6 characters.", "error");
        return;
      }
      if (password !== confirmPassword) {
        showToast("Passwords do not match.", "error");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = "Creating account...";

      try {
        await apiFetch("/api/register", {
          method: "POST",
          body: JSON.stringify({
            name,
            email,
            password,
            confirm_password: confirmPassword,
          }),
        });
        showToast("Account created! Redirecting to dashboard...", "success");
        setTimeout(() => {
          window.location.href = "/dashboard";
        }, 400);
      } catch (err) {
        showToast(err.message, "error");
        submitBtn.disabled = false;
        submitBtn.textContent = "Create Account";
      }
    });
  }
});
