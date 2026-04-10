"""Centralized URL constants for LabLedger backend.

This file keeps route strings in one place for both Django URL wiring and
internal audit scripts that call API endpoints.
"""

# Root URL patterns (LabLedger/urls.py)
ROOT_ADMIN = "predator/"
ROOT_HEALTH = ""
ROOT_APP_INFO = "api/app-info/"
ROOT_VERIFY_AUTH = "verify-auth/"
ROOT_AUTH_INCLUDE = "auth/"
ROOT_CENTER_DETAILS_INCLUDE = "center-details/"
ROOT_DIAGNOSIS_INCLUDE = "diagnosis/"
ROOT_TOKEN = "api/token/"
ROOT_TOKEN_REFRESH = "api/token/refresh/"
ROOT_TOKEN_VERIFY = "api/token/verify/"

# authentication/urls.py
AUTH_STAFFS = "staffs/"
AUTH_LOGOUT = "logout/"
AUTH_STAFF_ROUTER = "staff"
AUTH_RESET_PASSWORD_SUFFIX = "reset_password/"

# center_detail/urls.py
CENTER_DETAIL_ROUTER = "center-detail"
CENTER_SUBSCRIPTION_PLAN_ROUTER = "subscription-plan"
CENTER_ACTIVE_SUBSCRIPTION_ROUTER = "active-subscription"
CENTER_SUBSCRIPTION_PLAN_CONTEXT = "subscription-plan-context/"

# diagnosis/urls.py
DIAG_BILL_ROUTER = "bill"
DIAG_PATIENT_REPORT_ROUTER = "patient-report"
DIAG_DOCTOR_ROUTER = "doctor"
DIAG_DIAGNOSIS_TYPE_ROUTER = "diagnosis-type"
DIAG_SAMPLE_TEST_REPORT_ROUTER = "sample-test-report"
DIAG_FRANCHISE_NAME_ROUTER = "franchise-name"
DIAG_REFERRAL_STAT_ROUTER = "referral-stat"
DIAG_BILL_CHART_STAT_ROUTER = "bill-chart-stat"
DIAG_PENDING_REPORTS_ROUTER = "pending-reports"
DIAG_CATEGORIES_ROUTER = "categories"

DIAG_AUDIT_LOGS = "audit-logs/"
DIAG_REPORT_QUOTA_SUMMARY = "report-quota-summary/"
DIAG_DOCTOR_INCENTIVES = "doctors/<int:doctor_id>/incentives/"
DIAG_DOCTOR_GROWTH_STATS = "doctors/<int:doctor_id>/growth-stats/"
DIAG_BILLS_GROWTH_STATS = "bills/growth-stats/"
DIAG_INCENTIVES = "incentives/"

# Absolute API paths for scripts/tests
API_TOKEN = "/api/token/"
API_TOKEN_REFRESH = "/api/token/refresh/"
API_AUTH_STAFFS = "/auth/staffs/staff/"
API_DIAGNOSIS_BILL = "/diagnosis/bill/"
API_DIAGNOSIS_BILL_GROWTH_STATS = "/diagnosis/bills/growth-stats/"
API_DIAGNOSIS_INCENTIVES = "/diagnosis/incentives/"
API_DIAGNOSIS_REFERRAL_STAT = "/diagnosis/referral-stat/"
API_DIAGNOSIS_REPORT_QUOTA_SUMMARY = "/diagnosis/report-quota-summary/"


def api_center_detail_by_id(center_id: int) -> str:
    return f"/center-details/center-detail/{center_id}/"


def api_auth_staff_by_id(user_id: int) -> str:
    return f"{API_AUTH_STAFFS}{user_id}/"


def api_auth_staff_reset_password(user_id: int) -> str:
    return f"{api_auth_staff_by_id(user_id)}{AUTH_RESET_PASSWORD_SUFFIX}"


def api_bill_by_id(bill_id: int) -> str:
    return f"/diagnosis/bill/{bill_id}/"


def api_doctor_incentives(doctor_id: int) -> str:
    return f"/diagnosis/doctors/{doctor_id}/incentives/"


def api_doctor_growth_stats(doctor_id: int) -> str:
    return f"/diagnosis/doctors/{doctor_id}/growth-stats/"