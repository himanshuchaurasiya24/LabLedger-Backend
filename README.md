# 🧪 LabLedger - Diagnostic Center Report & Incentive Software

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Django REST Framework](https://img.shields.io/badge/DRF-ff1709?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)

A modern desktop application built with **Flutter** and **Django REST Framework**, designed to streamline diagnostic report generation, handle multi-center operations, and manage staff incentives efficiently.

👉 **To download the latest release of the LabLedger App, go to:** [https://github.com/himanshuchaurasiya24/LabLedger/releases](https://github.com/himanshuchaurasiya24/LabLedger/releases)

---

## 🔑 Key Features

* **Comprehensive Bill & Report Management**
  Easily create, view, and manage test reports and billing data.

* **Advanced PDF Generation Engine**
  Generate customized, professional Doctor Incentive reports with 3 dynamic layout options. Includes visual status indicators (e.g., automated red-coding for negative balances) and native OS file-save prompts.

* **SMS Gateway Integration**
  Integrated local SMS gateway for messaging, including an in-app securely authenticated prompt to download the required Gateway APK directly from your private server.

* **Integrated Doctor & Patient Database**
  Maintain accurate and searchable records of doctors and patients.

* **Dynamic Dashboard with Analytics**
  Visualize key metrics through interactive charts and summaries.

* **Secure Authentication**
  Uses **SimpleJWT** for token-based authentication and API security.

* **Modern UI Design**
  Clean, responsive Material 3 interface featuring a beautiful, fluid glassmorphism design language, adaptive layouts, and a professional color palette.

---

## 🛠️ Tech Stack

| Layer      | Technology                  |
|------------|------------------------------|
| Frontend   | Flutter (Desktop/Web/App)    |
| Backend    | Django REST Framework (Python)|
| Database   | PostgreSQL                   |
| Auth       | Django Authentication / JWT  |

---

## 🧩 Installation Instructions

### 1. Clone the repository (first)
You should clone the backend repository before running any setup steps so all scripts resolve paths correctly.

```bash
git clone https://github.com/himanshuchaurasiya24/LabLedger-Backend.git
cd LabLedger-Backend
```

### 2. Prerequisites
- Python 3.10+
- PostgreSQL Server installed and running

### 3. Environment Variables Configuration
You **must** create a `.env` file in the root directory (where `manage.py` is located) before creating the database user. Use the same value for `DB_PASSWORD` later when you run the database setup command.

```ini
# Core Settings
DJANGO_SECRET_KEY=your_secure_random_secret_key
DEBUG=True
USE_HTTPS=False
ALLOWED_HOSTS=127.0.0.1,localhost

# CORS Policy
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost,http://127.0.0.1
CORS_ALLOW_CREDENTIALS=False

# Localization
LANGUAGE_CODE=en-us
TIME_ZONE=Asia/Kolkata

# JWT Authentication
ACCESS_TOKEN_LIFETIME_MINUTES=5
REFRESH_TOKEN_LIFETIME_DAYS=1

# Application Config
MINIMUM_APP_VERSION=3.0.0
REPORT_LINK_EXPIRY_HOURS=6
MAX_UPLOAD_SIZE_MB=5
FRONTEND_URL=http://localhost:3000
DJANGO_LOG_LEVEL=INFO

# Email Settings (SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_email_app_password

# Security Headers
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# PostgreSQL Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=labledger
DB_USER=labledger_user
DB_PASSWORD=your_secure_db_password_here
DB_HOST=localhost
DB_PORT=5432
```

### 4. Database Setup (PostgreSQL)
If you do not have PostgreSQL installed, you must first download and install it from the [Official PostgreSQL Website](https://www.postgresql.org/download/).

The setup scripts below create the PostgreSQL database and user required by LabLedger. They read `DB_PASSWORD` from your existing `.env` file, resolve the project root automatically, and prompt for the PostgreSQL `postgres` superuser password when needed.

#### Windows (PowerShell)

From the project root, run the PowerShell setup script:

```powershell
& .\scripts\setup_database.ps1
```

The script will create the database, sync the app user password from `.env`, and handle the schema grant when required.

#### Linux (Ubuntu/Debian)

From the project root, run the Bash setup script:

```bash
bash ./scripts/setup_database.sh
```

The script will create the database, sync the app user password from `.env`, and handle the schema grant when required.

### 5. Backend Setup (Django)

```bash
# Create and activate virtual environment
python -m venv env
# On Windows: env\Scripts\activate
# On Linux/Mac: source env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 6. Run Migrations & Server
Once the `.env` file and PostgreSQL database are ready:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

---

*Note: For production deployments, ensure `DEBUG=False` and update the `CORS_ALLOWED_ORIGINS` and `ALLOWED_HOSTS` to your specific domain.*
