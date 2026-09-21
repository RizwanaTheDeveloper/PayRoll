import calendar
from datetime import date, datetime, timedelta

# CTC breakup assumption: Basic Salary is 40% of annual CTC (a common
# convention in Indian payroll). Everything else is a percentage of
# Basic, same ratios as before. Adjust these if your company's actual
# structure differs.
BASIC_OF_CTC = 0.40
HRA_RATE = 0.25
SPECIAL_ALLOWANCE_RATE = 0.10
LTA_RATE = 0.05
BONUS_RATE = 0.05
EPF_RATE = 0.12
PROFESSIONAL_TAX = 200

HIKE_RATE = 0.03            # 3% hike
HIKE_INTERVAL_MONTHS = 6    # every 6 months of service, applied to CTC


def current_ist_str():
    """Today's date in IST, e.g. '15 Sep 2026'. No external timezone deps."""
    ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
    return ist_time.strftime("%d %b %Y")


def _months_between(start_date, end_date):
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day < start_date.day:
        months -= 1
    return max(months, 0)


def get_hike_count(joining_date):
    if not joining_date:
        return 0
    months_served = _months_between(joining_date, date.today())
    return months_served // HIKE_INTERVAL_MONTHS


def get_effective_ctc(base_ctc, joining_date):
    """Annual CTC after compounding a 3% hike every 6 months of service."""
    hikes = get_hike_count(joining_date)
    ctc = float(base_ctc)
    for _ in range(hikes):
        ctc *= (1 + HIKE_RATE)
    return round(ctc, 2), hikes


def calculate_payroll(employee, reference_date=None):
    """
    Returns the monthly breakup for one employee, derived from their
    annual CTC. Does NOT include income tax (TDS) — that's computed
    separately per financial year by tax_engine.py + payroll_history.py,
    since it depends on months already run this FY.

    Earnings are prorated against the employee's WorkingDays for the
    month: the payslip's actual monthly figures (basic, hra, gross
    earnings, epf, net salary) scale down if fewer days were worked
    than the calendar month has. The FULL-month figures (suffixed
    "_full") are kept unprorated and are what should be used to
    annualize for tax purposes (annual tax shouldn't dip just because
    one month had a short attendance count).
    """
    reference_date = reference_date or date.today()

    joining_date = getattr(employee, "JoiningDate", None)
    original_ctc = float(employee.CTC)
    effective_ctc, hikes_applied = get_effective_ctc(original_ctc, joining_date)

    # ------------------------------------------------------------
    # FULL-MONTH FIGURES (unprorated — used for annual tax estimate)
    # ------------------------------------------------------------
    monthly_basic_full = (effective_ctc * BASIC_OF_CTC) / 12
    hra_full = monthly_basic_full * HRA_RATE
    special_allowance_full = monthly_basic_full * SPECIAL_ALLOWANCE_RATE
    lta_full = monthly_basic_full * LTA_RATE
    bonus_full = monthly_basic_full * BONUS_RATE

    gross_earnings_full = (
        monthly_basic_full + hra_full + special_allowance_full
        + lta_full + bonus_full
    )

    # ------------------------------------------------------------
    # PRORATION — based on WorkingDays vs. days in the current month
    # ------------------------------------------------------------
    days_in_month = calendar.monthrange(reference_date.year, reference_date.month)[1]

    working_days_raw = getattr(employee, "WorkingDays", None)
    if working_days_raw is None:
        # No attendance recorded yet — assume a full month so payroll
        # can still be generated (and so proration_factor stays 1.0).
        working_days = days_in_month
    else:
        working_days = max(0, min(int(working_days_raw), days_in_month))

    proration_factor = (working_days / days_in_month) if days_in_month else 1.0

    monthly_basic = monthly_basic_full * proration_factor
    house_rent_allowance = hra_full * proration_factor
    special_allowance = special_allowance_full * proration_factor
    leave_travel_allowance = lta_full * proration_factor
    bonus = bonus_full * proration_factor

    gross_earnings = (
        monthly_basic + house_rent_allowance + special_allowance
        + leave_travel_allowance + bonus
    )

    # EPF is a percentage of Basic actually paid, so it prorates too.
    employee_provident_fund = monthly_basic * EPF_RATE
    # Professional Tax is a flat statutory slab, not prorated by attendance.
    professional_tax = PROFESSIONAL_TAX

    return {
        "ctc": effective_ctc,
        "original_ctc": original_ctc,
        "hikes_applied": hikes_applied,

        "working_days": working_days,
        "days_in_month": days_in_month,
        "proration_factor": round(proration_factor, 4),

        # Actual, prorated figures for this month's payslip
        "basic": monthly_basic,
        "hra": house_rent_allowance,
        "special_allowance": special_allowance,
        "lta": leave_travel_allowance,
        "bonus": bonus,
        "gross_earnings": gross_earnings,
        "professional_tax": professional_tax,
        "epf": employee_provident_fund,

        # Unprorated full-month figures, for annualizing tax estimates
        "basic_full": monthly_basic_full,
        "hra_full": hra_full,
        "special_allowance_full": special_allowance_full,
        "lta_full": lta_full,
        "bonus_full": bonus_full,
        "gross_earnings_full": gross_earnings_full,
    }