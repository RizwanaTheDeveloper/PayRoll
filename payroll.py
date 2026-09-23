import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo

HRA_RATE = 0.25
SPECIAL_ALLOWANCE_RATE = 0.10
LTA_RATE = 0.05
BONUS_RATE = 0.05
EPF_RATE = 0.12
PROFESSIONAL_TAX = 200  # standard flat monthly professional tax slab

RATE_MULTIPLIER = 1 + HRA_RATE + SPECIAL_ALLOWANCE_RATE + LTA_RATE + BONUS_RATE


def current_ist_str():
    """Human-readable current time in IST, used as the payslip's 'Generated On'."""
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    return now.strftime("%d %b %Y, %I:%M %p IST")


def calculate_payroll(employee):
    """
    Calculate this month's payroll for `employee`, using the standard
    "calendar day method" most Indian software companies use:

        Per Day Salary = Full Month Gross Salary / Calendar Days in Month
        Earned (Worked-Days) Salary = Per Day Salary x Days Present

    employee.CTC is treated as the annual gross salary (Basic + HRA +
    Special Allowance + LTA + Bonus, annualized) — matching what
    tax_engine.calculate_annual_tax expects as its input. Basic is
    backed out of CTC using the same fixed rates the other allowances
    are calculated from, so gross_earnings_full * 12 always equals CTC.

    IMPORTANT: there is exactly ONE proration step in this function —
    the per-day-rate multiplication below. Every other earnings figure
    (basic, hra, special_allowance, lta, bonus) is derived by splitting
    that already-prorated earned salary back into its components, so
    they can never drift out of sync with each other or get scaled
    twice.
    """
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]

    working_days = employee.WorkingDays
    if working_days is None:
        working_days = days_in_month
    working_days = max(0, min(int(working_days), days_in_month))

    proration_factor = (working_days / days_in_month) if days_in_month else 1.0

    # --- Full-month (unprorated) figures — basis for the annual tax
    #     estimate, which shouldn't shrink just because one month was
    #     short on attendance ---
    annual_ctc = float(employee.CTC)
    monthly_gross_full = annual_ctc / 12
    basic_full = monthly_gross_full / RATE_MULTIPLIER
    hra_full = basic_full * HRA_RATE
    special_allowance_full = basic_full * SPECIAL_ALLOWANCE_RATE
    lta_full = basic_full * LTA_RATE
    bonus_full = basic_full * BONUS_RATE
    gross_earnings_full = (
        basic_full + hra_full + special_allowance_full + lta_full + bonus_full
    )

    # --- The single proration step ---
    per_day_salary = gross_earnings_full / days_in_month if days_in_month else 0
    worked_days_salary = per_day_salary * working_days  # == gross_earnings_full * proration_factor

    # --- Split the earned salary back into its components, in the
    #     same ratios as the full-month figures ---
    basic = basic_full * proration_factor
    hra = hra_full * proration_factor
    special_allowance = special_allowance_full * proration_factor
    lta = lta_full * proration_factor
    bonus = bonus_full * proration_factor
    gross_earnings = basic + hra + special_allowance + lta + bonus  # == worked_days_salary

    employee_provident_fund = basic * EPF_RATE
    professional_tax = PROFESSIONAL_TAX if working_days > 0 else 0

    # tds/total_deductions/net_salary below are placeholders — app.py's
    # payslip-building logic recalculates and overwrites all three
    # using the annualized tax engine plus FY-to-date TDS already
    # deducted. They're included here just so the dict is complete if
    # this function is ever used standalone. IMPORTANT: wherever
    # net_salary is recomputed downstream, it MUST be
    # gross_earnings - total_deductions (both using the values in
    # THIS dict), not values pulled from a stale snapshot — otherwise
    # working-day changes won't show up in the final payable amount.
    tds = 0
    total_deductions = professional_tax + employee_provident_fund + tds
    net_salary = gross_earnings - total_deductions

    return {
        "basic_full": basic_full,
        "hra_full": hra_full,
        "special_allowance_full": special_allowance_full,
        "lta_full": lta_full,
        "bonus_full": bonus_full,
        "gross_earnings_full": gross_earnings_full,
        "basic": basic,
        "hra": hra,
        "special_allowance": special_allowance,
        "lta": lta,
        "bonus": bonus,
        "gross_earnings": gross_earnings,
        "professional_tax": professional_tax,
        "epf": employee_provident_fund,
        "tds": tds,
        "total_deductions": total_deductions,
        "net_salary": net_salary,
        "working_days": working_days,
        "days_in_month": days_in_month,
        "proration_factor": proration_factor,
        "per_day_salary": per_day_salary,
        "worked_days_salary": worked_days_salary,
    }