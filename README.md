# 🚀 KidZone & G11 Ecommerce Platform

A premium, full-stack ecommerce solution built with **Django**, designed for high performance, scalability, and an exceptional user experience. This platform features a modern **Glassmorphism UI**, real-time interactivity, and a robust AI-integrated backend.

---

## 🌟 Key Features

### 🛒 Shopping Experience
- **Live Search**: AJAX-powered real-time product discovery across all categories.
- **Dynamic Catalog**: Specialized sections for Kids, Men, Women, and Toys with multi-table support.
- **Product Variants**: Full support for sizes, colors, and dynamic pricing updates.
- **Quick View**: Instant product inspection via AJAX modals without page reloads.
- **Persistent Cart**: Seamless cart-to-account merging using custom middleware.

### 💳 Payments & Fulfillment
- **Stripe Integration**: Secure, PCI-compliant credit card processing.
- **Flexible Checkout**: Supports both Stripe and **Cash on Delivery (COD)**.
- **Order Tracking**: Visual timeline tracking from "Pending" to "Delivered."
- **Inventory Management**: Real-time stock tracking with automated low-stock alerts.

### 🎁 Loyalty & Engagement
- **Tiered Loyalty System**: Gamified user experience with **Bronze, Silver, and Gold** tiers.
- **AI Chatbot**: Intelligent customer support powered by **Google Gemini** and **Groq AI**.
- **Stock Alerts**: "Notify Me" functionality for out-of-stock items.
- **Return Management**: Self-service return portal with 30-day window validation.

### 🛡️ Security & Performance
- **Cloudinary Integration**: Optimized image delivery and secure media storage.
- **Security Hardening**: CSRF protection on all AJAX endpoints, HSTS, and XSS filtering.
- **Middleware**: Custom error handling and session-to-account cart transfer logic.

---

## 💻 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Django 6.0.3 (Python) |
| **Frontend** | HTML5, Vanilla CSS3 (Custom Glassmorphism), JavaScript (ES6+) |
| **AI** | Google Gemini API, Groq Cloud API |
| **Database** | MySQL / PostgreSQL (via dj-database-url) |
| **Payments** | Stripe API |
| **Media** | Cloudinary (Production Storage) |
| **Static Files** | Whitenoise (Compressed serving) |

---

## 📂 Project Structure

```text
├── accounts/               # User authentication & Google OAuth
├── myapp/                  # Core ecommerce logic (Products, Orders, Loyalty)
│   ├── middleware.py       # Custom Cart & Error handling logic
│   ├── context_processors.py# Global template data (Cart count, etc.)
│   └── models.py           # Relational database architecture
├── static/                 # CSS (Navbar, Glassmorphism), JS, & Assets
├── templates/              # Professional HTML5 templates
├── myproject/              # Project settings & URL routing
└── manage.py               # Django entry point
```

---

## 🚀 Installation & Setup

### 1. Clone & Environment
```bash
git clone https://github.com/G-N-Deshan/Ecommerce-Project-cloths-toys.git
cd Ecommerce-Project-cloths-toys
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables (`.env`)
Create a `.env` file in the root directory:
```env
DEBUG=True
SECRET_KEY=your_django_secret
DATABASE_URL=mysql://user:pass@localhost/db_name

# Payments
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# AI Keys
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key

# Media & Email
CLOUDINARY_URL=cloudinary://...
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

### 3. Initialize Database
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## 📸 Screenshots
*(Add your stunning screenshots here to showcase the Glassmorphism UI!)*

---

## 📄 License & Credits
Distributed under the MIT License. See `LICENSE` for more information.

**Developed with ❤️ by G.N. Deshan & Team**
