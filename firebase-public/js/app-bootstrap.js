// Bootstrap the frontend app:
// - Render navbar, footer, and home page shells that match your existing UI
// - Wire up basic placeholders for products, cart count, etc.

import { auth, db } from "./firebase-config.js";
import {
  collection,
  getDocs,
  query,
  limit
} from "https://www.gstatic.com/firebasejs/11.0.0/firebase-firestore.js";
import {
  onAuthStateChanged,
  signOut
} from "https://www.gstatic.com/firebasejs/11.0.0/firebase-auth.js";

const navbarRoot = document.getElementById("navbarRoot");
const footerRoot = document.getElementById("footerRoot");
const appRoot = document.getElementById("appRoot");
const cartIconRoot = document.getElementById("cartIconRoot");

function renderNavbar(user, cartCount) {
  // This is a minimal static navbar shell.
  // You can refine it to perfectly match templates/navbar.html.
  navbarRoot.innerHTML = `
    <nav class="w-full bg-white shadow-sm sticky top-0 z-40">
      <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <a href="/" class="flex items-center gap-2">
          <span class="font-playfair text-2xl font-bold text-slate-900">G11</span>
          <span class="text-xs uppercase tracking-[0.2em] text-slate-400">Fashion &amp; Toys</span>
        </a>
        <div class="flex items-center gap-4">
          <a href="/" class="text-sm font-medium text-slate-700 hover:text-indigo-600">Home</a>
          <a href="/buy.html" class="text-sm font-medium text-slate-700 hover:text-indigo-600">Shop</a>
          <a href="/offers.html" class="text-sm font-medium text-slate-700 hover:text-indigo-600">Offers</a>
          <a href="/toys.html" class="text-sm font-medium text-slate-700 hover:text-indigo-600">Toys</a>
          ${
            user
              ? `<div class="flex items-center gap-2">
                   <span class="text-xs text-slate-500 hidden sm:inline">Hi, ${user.displayName || user.email}</span>
                   <button id="logoutBtn" class="text-sm font-medium text-slate-700 hover:text-red-500">Logout</button>
                 </div>`
              : `<a href="/login.html" class="text-sm font-medium text-slate-700 hover:text-indigo-600">Login</a>`
          }
        </div>
      </div>
    </nav>
  `;

  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await signOut(auth);
        window.location.href = "/";
      } catch (err) {
        console.error("Logout error", err);
      }
    });
  }
}

function renderFooter() {
  footerRoot.innerHTML = `
    <div class="mt-16 bg-slate-900 text-slate-200 py-10">
      <div class="max-w-6xl mx-auto px-4 flex flex-col md:flex-row justify-between gap-6 text-sm">
        <div>
          <h3 class="font-playfair text-xl mb-2">G11 Fashion &amp; Toys</h3>
          <p class="text-slate-400">Premium kids fashion and toys, curated with love.</p>
        </div>
        <div class="flex gap-6">
          <div>
            <h4 class="font-semibold mb-2">Shop</h4>
            <ul class="space-y-1 text-slate-400">
              <li><a href="/buy" class="hover:text-white">All Products</a></li>
              <li><a href="/offers" class="hover:text-white">Offers</a></li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold mb-2">Support</h4>
            <ul class="space-y-1 text-slate-400">
              <li><a href="/contact" class="hover:text-white">Contact</a></li>
              <li><a href="/about" class="hover:text-white">About</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div class="mt-6 text-center text-xs text-slate-500">
        © ${new Date().getFullYear()} G11 Fashion &amp; Toys. All rights reserved.
      </div>
    </div>
  `;
}

function renderCartIcon(cartCount) {
  cartIconRoot.innerHTML = `
    <div class="fixed bottom-6 right-6 z-40">
      <a href="/cart" class="relative inline-flex items-center justify-center w-14 h-14 rounded-full bg-indigo-600 text-white shadow-lg hover:bg-indigo-700 transition">
        <span class="text-2xl">🛒</span>
        <span class="absolute -top-1 -right-1 min-w-[22px] h-[22px] rounded-full bg-rose-500 text-[11px] flex items-center justify-center px-1 font-semibold">
          ${cartCount ?? 0}
        </span>
      </a>
    </div>
  `;
}

function renderHomeShell() {
  // Home page layout closely matching your Django index.html hero + sections.
  appRoot.innerHTML = `
    <!-- HERO -->
    <section class="relative min-h-screen flex items-center justify-center overflow-hidden">
      <div class="absolute inset-0 z-0">
        <div class="w-full h-full bg-gradient-to-br from-slate-900 via-indigo-900 to-slate-900 opacity-90"></div>
      </div>
      <div class="relative z-10 container mx-auto px-6 text-center">
        <div class="hero-content">
          <div class="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-white/20 bg-white/10 backdrop-blur-sm text-white/90 text-sm font-medium mb-8">
            <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
            New Season Collection 2026
          </div>
          <h1 class="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-black leading-[0.95] tracking-tight mb-8">
            <span class="block text-white">Dress Up.</span>
            <span class="block bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">Play On.</span>
          </h1>
          <p class="text-lg md:text-xl text-white/80 max-w-xl mx-auto mb-4">
            Premium fashion &amp; toys curated for kids who love to explore.
          </p>
          <p class="text-base text-white/60 mb-10">
            Up to <span class="text-amber-400 font-bold">50% OFF</span> &bull; Free delivery over $49
          </p>
          <div class="flex flex-col sm:flex-row gap-4 justify-center">
            <a href="/buy" class="mag-btn group relative inline-flex items-center gap-3 px-9 py-4 bg-white text-slate-900 font-bold rounded-full overflow-hidden transition-all duration-400 hover:shadow-[0_0_40px_rgba(99,102,241,0.45)]">
              <span class="relative z-10 flex items-center gap-2"><i class="bi bi-bag-check text-lg"></i> Shop Now</span>
              <span class="absolute inset-0 bg-gradient-to-r from-indigo-500 to-purple-500 translate-y-full group-hover:translate-y-0 transition-transform duration-500"></span>
              <span class="relative z-10 group-hover:text-white transition-colors duration-300"></span>
            </a>
            <a href="/offers" class="mag-btn inline-flex items-center gap-2 px-9 py-4 border-2 border-white/40 text-white font-bold rounded-full hover:bg-white/15 backdrop-blur-sm transition-all duration-300">
              <i class="bi bi-fire text-amber-400"></i> View Offers
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- HOT DEALS -->
    <section class="py-14 bg-gradient-to-b from-slate-50 to-white" id="hotDeals">
      <div class="container mx-auto px-6">
        <div class="text-center mb-10">
          <span class="inline-flex items-center gap-2 px-4 py-1.5 bg-red-50 text-red-600 font-semibold rounded-full text-sm mb-5">
            <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span> Limited Time
          </span>
          <h2 class="text-4xl md:text-5xl font-bold font-playfair mb-3">Hot Deals</h2>
          <p class="text-slate-500 text-lg">Grab them before they're gone!</p>
        </div>
        <div id="offersGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          <!-- Offers from Firestore will be injected here -->
        </div>
      </div>
    </section>

    <!-- NEW ARRIVALS -->
    <section class="py-14 bg-white" id="newArrivals">
      <div class="container mx-auto px-6">
        <div class="text-center mb-10">
          <span class="inline-flex items-center gap-2 px-4 py-1.5 bg-emerald-50 text-emerald-600 font-semibold rounded-full text-sm mb-5">
            <span class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span> Just Landed
          </span>
          <h2 class="text-4xl md:text-5xl font-bold font-playfair mb-3">New Arrivals</h2>
          <p class="text-slate-500 text-lg">Fresh products just dropped!</p>
        </div>
        <div id="arrivalsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          <!-- New arrivals from Firestore will be injected here -->
        </div>
      </div>
    </section>
  `;
}

async function renderOffers() {
  const container = document.getElementById("offersGrid");
  if (!container) return;
  container.innerHTML = `<div class="col-span-full text-center text-slate-400">Loading deals...</div>`;

  try {
    const snap = await getDocs(query(collection(db, "offers"), limit(12)));
    if (snap.empty) {
      container.innerHTML = `
        <div class="col-span-full text-center py-16">
          <i class="bi bi-inbox text-6xl text-slate-200 mb-4 block"></i>
          <p class="text-slate-400 text-lg">No offers yet. Add some in Firestore.</p>
        </div>`;
      return;
    }

    const cards = [];
    snap.forEach(docSnap => {
      const o = docSnap.data();
      const price2 = o.price2 ?? o.price;
      const price1 = o.price1 ?? null;
      const img = o.imageUrl || "";
      const badge = o.offers_badge || "HOT";
      const stock = o.stock_text || "";
      cards.push(`
        <div class="tilt-card">
          <div class="card-inner bg-white rounded-2xl overflow-hidden shadow-md hover:shadow-2xl transition-shadow duration-500 group">
            <div class="relative overflow-hidden">
              <span class="absolute top-4 left-4 z-10 px-3 py-1 bg-red-500 text-white text-xs font-bold rounded-full shadow-lg">
                ${badge}
              </span>
              <img src="${img}" alt="${o.title || ""}" class="w-full h-64 object-cover transition-transform duration-700 group-hover:scale-110" loading="lazy">
            </div>
            <div class="p-5">
              <h3 class="font-semibold text-slate-800 mb-2 line-clamp-1">
                ${o.title || "Offer"}
              </h3>
              <div class="flex items-center gap-3 mb-2">
                ${price2 ? `<span class="text-xl font-bold text-indigo-600">$${price2}</span>` : ""}
                ${price1 ? `<span class="text-sm text-slate-400 line-through">$${price1}</span>` : ""}
              </div>
              ${stock ? `<span class="inline-block px-2 py-0.5 bg-amber-50 text-amber-700 text-xs rounded-full font-medium">${stock}</span>` : ""}
            </div>
          </div>
        </div>
      `);
    });
    container.innerHTML = cards.join("");
  } catch (err) {
    console.warn("Error loading offers:", err);
    container.innerHTML = `<div class="col-span-full text-center text-red-500">Failed to load offers.</div>`;
  }
}

async function renderArrivals() {
  const container = document.getElementById("arrivalsGrid");
  if (!container) return;
  container.innerHTML = `<div class="col-span-full text-center text-slate-400">Loading new arrivals...</div>`;

  try {
    const snap = await getDocs(query(collection(db, "new_arrivals"), limit(12)));
    if (snap.empty) {
      container.innerHTML = `
        <div class="col-span-full text-center py-16">
          <i class="bi bi-inbox text-6xl text-slate-200 mb-4 block"></i>
          <p class="text-slate-400 text-lg">No new arrivals yet. Add some in Firestore.</p>
        </div>`;
      return;
    }

    const cards = [];
    snap.forEach(docSnap => {
      const a = docSnap.data();
      const img = a.imageUrl || "";
      cards.push(`
        <div class="tilt-card">
          <div class="card-inner bg-white rounded-2xl overflow-hidden shadow-md hover:shadow-2xl transition-shadow duration-500 border border-slate-100 group">
            <div class="relative overflow-hidden">
              <span class="absolute top-4 right-4 z-10 px-3 py-1 bg-emerald-500 text-white text-[11px] font-bold rounded-full">NEW</span>
              <img src="${img}" alt="${a.title || ""}" class="w-full h-56 object-cover transition-transform duration-700 group-hover:scale-110" loading="lazy">
            </div>
            <div class="p-5">
              <span class="text-[11px] text-indigo-600 font-bold uppercase tracking-wider">${a.category || ""}</span>
              <h3 class="font-semibold text-slate-800 mt-1 mb-2 line-clamp-1">
                ${a.title || "New Arrival"}
              </h3>
              <p class="text-sm text-slate-400 mb-4 line-clamp-2">${a.description || ""}</p>
              <div class="flex items-center justify-between">
                <span class="text-xl font-bold text-slate-800">$${a.price ?? ""}</span>
              </div>
            </div>
          </div>
        </div>
      `);
    });
    container.innerHTML = cards.join("");
  } catch (err) {
    console.warn("Error loading arrivals:", err);
    container.innerHTML = `<div class="col-span-full text-center text-red-500">Failed to load new arrivals.</div>`;
  }
}

async function bootstrap() {
  const cartCount = 0; // TODO: load from Firestore (user cart) once schema is defined

  renderFooter();
  renderCartIcon(cartCount);
  renderHomeShell();
  await Promise.all([renderOffers(), renderArrivals()]);

  onAuthStateChanged(auth, (user) => {
    renderNavbar(user, cartCount);
  });
}

bootstrap();

