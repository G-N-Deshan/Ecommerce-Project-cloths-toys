import { auth, db } from "./firebase-config.js";
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  updateProfile
} from "https://www.gstatic.com/firebasejs/11.0.0/firebase-auth.js";
import {
  doc,
  setDoc
} from "https://www.gstatic.com/firebasejs/11.0.0/firebase-firestore.js";

const form = document.getElementById("signupForm");
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
    const fullName = form.full_name.value.trim();
    const email = form.email.value.trim();
    const password = form.password.value;
    const password2 = form.password2.value;
    const phone = form.phone.value.trim();
    const address = form.address.value.trim();

    if (!email || !password) {
      showToast("Email and password are required", "error");
      return;
    }
    if (password !== password2) {
      showToast("Passwords do not match", "error");
      return;
    }

    try {
      const cred = await createUserWithEmailAndPassword(auth, email, password);
      const user = cred.user;
      if (fullName) {
        await updateProfile(user, { displayName: fullName });
      }
      await setDoc(doc(db, "users", user.uid), {
        fullName,
        email,
        phone,
        address,
        createdAt: new Date().toISOString()
      });
      showToast("Account created successfully", "success");
      setTimeout(() => {
        window.location.href = "/";
      }, 800);
    } catch (err) {
      console.error(err);
      showToast(err.message || "Signup failed", "error");
    }
  });
}

onAuthStateChanged(auth, (user) => {
  if (user) {
    window.location.href = "/";
  }
});

