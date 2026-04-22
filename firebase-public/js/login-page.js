import { auth } from "./firebase-config.js";
import {
  signInWithEmailAndPassword,
  onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/11.0.0/firebase-auth.js";

const form = document.getElementById("loginForm");
const toastContainer = document.getElementById("toastContainer");

function showToast(message, type = "info") {
  if (!toastContainer) return;
  const el = document.createElement("div");
  el.className =
    "pointer-events-auto px-4 py-3 rounded-lg shadow-lg text-sm font-medium mb-2 " +
    (type === "error"
      ? "bg-rose-600 text-white"
      : type === "success"
      ? "bg-emerald-600 text-white"
      : "bg-slate-800 text-white");
  el.textContent = message;
  toastContainer.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

window.togglePw = function (id, btn) {
  const inp = document.getElementById(id);
  const icon = btn.querySelector("i");
  if (!inp || !icon) return;
  if (inp.type === "password") {
    inp.type = "text";
    icon.className = "bi bi-eye";
  } else {
    inp.type = "password";
    icon.className = "bi bi-eye-slash";
  }
};

if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = form.email.value.trim();
    const password = form.password.value;
    try {
      await signInWithEmailAndPassword(auth, email, password);
      showToast("Logged in successfully", "success");
      setTimeout(() => {
        window.location.href = "/";
      }, 800);
    } catch (err) {
      console.error(err);
      showToast(err.message || "Login failed", "error");
    }
  });
}

onAuthStateChanged(auth, (user) => {
  if (user) {
    // Already logged in; redirect to home
    window.location.href = "/";
  }
});

