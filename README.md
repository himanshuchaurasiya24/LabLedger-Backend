# 🧪 Diagnostic Center Report & Incentive Software (Windows)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Django REST Framework](https://img.shields.io/badge/DRF-ff1709?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
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

### 1. Backend Setup (Django) - Ensure you have python installed before you run this code
```bash
git clone https://github.com/himanshuchaurasiya24/LabLedger-Backend.git
cd LabLedger-Backend
python -m venv env
env\Scripts\activate
pip install -r requirement.txt
python manage.py migrate
python manage.py runserver



