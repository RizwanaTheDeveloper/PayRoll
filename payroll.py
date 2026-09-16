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


def calculate_payroll(employee):
    """
    Returns the monthly breakup for one employee, derived from their
    annual CTC. Does NOT include income tax (TDS) — that's computed
    separately per financial year by tax_engine.py + payroll_history.py,
    since it depends on months already run this FY.
    """
    joining_date = getattr(employee, "JoiningDate", None)
    original_ctc = float(employee.CTC)
    effective_ctc, hikes_applied = get_effective_ctc(original_ctc, joining_date)

    monthly_basic = (effective_ctc * BASIC_OF_CTC) / 12
    house_rent_allowance = monthly_basic * HRA_RATE
    special_allowance = monthly_basic * SPECIAL_ALLOWANCE_RATE
    leave_travel_allowance = monthly_basic * LTA_RATE
    bonus = monthly_basic * BONUS_RATE

    gross_earnings = (
        monthly_basic + house_rent_allowance + special_allowance
        + leave_travel_allowance + bonus
    )

    employee_provident_fund = monthly_basic * EPF_RATE
    professional_tax = PROFESSIONAL_TAX

    return {
        "ctc": effective_ctc,
        "original_ctc": original_ctc,
        "hikes_applied": hikes_applied,
        "basic": monthly_basic,
        "hra": house_rent_allowance,
        "special_allowance": special_allowance,
        "lta": leave_travel_allowance,
        "bonus": bonus,
        "gross_earnings": gross_earnings,
        "professional_tax": professional_tax,
        "epf": employee_provident_fund,
    }
