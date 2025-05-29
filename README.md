# 🧪 Diagnostic Center Report & Incentive Software (Windows)

A modern desktop application for Windows, built with **Flutter** and **Django REST Framework**, designed to streamline diagnostic report generation and manage staff incentives efficiently.

---

## 🚀 Features

- 📄 Generate and manage diagnostic test reports
- 💰 Calculate and track staff incentives
- 🔐 Role-based access (admin, doctor, lab staff)
- 📁 Export reports in PDF format
- 🖥️ Optimized for Windows Desktop
- ⚙️ Fast REST API backend with Django

---

## 🛠️ Tech Stack

| Layer      | Technology                  |
|------------|------------------------------|
| Frontend   | Flutter (Windows Desktop)    |
| Backend    | Django REST Framework (Python) |
| Database   | SQLite / PostgreSQL          |
| Auth       | Django Authentication / JWT  |

---

## 🧩 Installation Instructions

### 1. Backend Setup (Django)
```bash
git clone https://github.com/yourusername/yourproject.git](https://github.com/himanshuchaurasiya24/LabLedger-Backend.git
cd LabLedger-Backend

python -m venv env
env\Scripts\activate  # On Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

