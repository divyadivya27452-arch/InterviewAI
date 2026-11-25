/**
 * My Profile Settings Page: Edit profile + photo upload, change password, delete account.
 */

document.addEventListener("DOMContentLoaded", () => {
  const { apiFetch, showToast, showLoader, hideLoader } = window.InterviewAI;

  const profileForm = document.getElementById("profile-form");
  const photoInput = document.getElementById("profile-photo-input");
  const photoPreview = document.getElementById("profile-photo-preview");
  const topbarAvatar = document.getElementById("topbar-user-avatar");
  const topbarName = document.getElementById("topbar-user-name");

  const passwordForm = document.getElementById("password-form");

  const openDeleteModalBtn = document.getElementById("open-delete-account-btn");
  const deleteModal = document.getElementById("delete-account-modal");
  const cancelDeleteBtn = document.getElementById("cancel-delete-account-btn");
  const confirmDeleteBtn = document.getElementById("confirm-delete-account-btn");
  const deletePasswordInput = document.getElementById("delete-account-password");

  // Live preview when choosing a new avatar photo
  if (photoInput) {
    photoInput.addEventListener("change", () => {
      const file = photoInput.files[0];
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) {
        showToast("Image file must be 5 MB or smaller.", "error");
        photoInput.value = "";
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        photoPreview.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  // Save profile info & optional photo
  if (profileForm) {
    profileForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("profile-name").value.trim();
      const email = document.getElementById("profile-email").value.trim();

      if (name.length < 2) {
        showToast("Name must be at least 2 characters.", "error");
        return;
      }
      if (!email.includes("@")) {
        showToast("Please provide a valid email address.", "error");
        return;
      }

      const formData = new FormData(profileForm);
      showLoader("Saving profile...");

      try {
        const res = await apiFetch("/api/profile", {
          method: "PUT",
          body: formData,
        });
        if (res.user) {
          if (topbarName) topbarName.textContent = res.user.name;
          if (topbarAvatar) topbarAvatar.src = res.user.photo;
          photoPreview.src = res.user.photo;
        }
        showToast("Profile updated successfully!", "success");
      } catch (err) {
        showToast(err.message, "error");
      } finally {
        hideLoader();
      }
    });
  }

  // Change password
  if (passwordForm) {
    passwordForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const old_password = document.getElementById("old-password").value;
      const new_password = document.getElementById("new-password").value;
      const confirm_password = document.getElementById("confirm-new-password").value;

      if (!old_password || !new_password || !confirm_password) {
        showToast("Please complete all password fields.", "error");
        return;
      }
      if (new_password.length < 6) {
        showToast("New password must be at least 6 characters.", "error");
        return;
      }
      if (new_password !== confirm_password) {
        showToast("New passwords do not match.", "error");
        return;
      }

      showLoader("Updating password...");
      try {
        await apiFetch("/api/profile/password", {
          method: "PUT",
          body: JSON.stringify({ old_password, new_password, confirm_password }),
        });
        passwordForm.reset();
        showToast("Password changed successfully.", "success");
      } catch (err) {
        showToast(err.message, "error");
      } finally {
        hideLoader();
      }
    });
  }

  // Delete account modal
  if (openDeleteModalBtn) {
    openDeleteModalBtn.addEventListener("click", () => {
      deletePasswordInput.value = "";
      deleteModal.classList.remove("hidden");
    });
  }

  if (cancelDeleteBtn) {
    cancelDeleteBtn.addEventListener("click", () => {
      deleteModal.classList.add("hidden");
    });
  }

  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener("click", async () => {
      const password = deletePasswordInput.value;
      if (!password) {
        showToast("Please enter your password to confirm account deletion.", "error");
        return;
      }
      confirmDeleteBtn.disabled = true;
      showLoader("Deleting account...");
      try {
        await apiFetch("/api/profile", {
          method: "DELETE",
          body: JSON.stringify({ password }),
        });
        showToast("Account deleted. Goodbye!", "info");
        setTimeout(() => {
          window.location.href = "/login";
        }, 500);
      } catch (err) {
        showToast(err.message, "error");
        confirmDeleteBtn.disabled = false;
      } finally {
        hideLoader();
      }
    });
  }
});
