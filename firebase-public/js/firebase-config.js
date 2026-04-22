import { initializeApp } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-firestore.js";
import { getStorage } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-storage.js";

const firebaseConfig = {
  apiKey: "AIzaSyBxh_aW6ZsFARHjFXol3thsJa2fMomaN2Y",
  authDomain: "g11ecommerce.firebaseapp.com",
  projectId: "g11ecommerce",
  storageBucket: "g11ecommerce.firebasestorage.app",
  messagingSenderId: "357950843863",
  appId: "1:357950843863:web:23fcf23237fa3a8023f992",
  measurementId: "G-4KTD2EPGTT"
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);