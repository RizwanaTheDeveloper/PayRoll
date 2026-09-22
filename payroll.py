"""
Payroll calculation module (India) — improved version.

Fixes vs. the original payroll.py:
  1. Proper slab-based TDS for both Old and New tax regimes (instead of a
     flat 10% above 7L).
  2. Section 87A rebate applied correctly (nil tax up to the rebate limit).
  3. Employer PF contribution added, with the statutory PF wage ceiling
     (Rs 15,000) applied — configurable if the employer opts for "PF on
     full basic".
  4. HRA tax exemption calculated per Income Tax rules (least of: actual
     HRA received, rent paid − 10% of basic, 50%/40% of basic for
     metro/non-metro) rather than just adding HRA as a taxable component.
  5. Pro-rating for Loss of Pay (LOP) / days worked.
  6. Inputs and rates are still simplified for demo purposes — always
     verify against current CBDT slabs, your state's Professional Tax
     schedule, and your company's actual PF/HRA policy before using this
     for real payroll.
"""

import calendar
from datetime import date, datetime, timedelta
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Configurable constants — these change with each Union Budget / state rules
# and should ideally live in a settings table, not hardcoded.
# ---------------------------------------------------------------------------

HRA_RATE = 0.25
SPECIAL_ALLOWANCE_RATE = 0.10
LTA_RATE = 0.05
BONUS_RATE = 0.05

EPF_EMPLOYEE_RATE = 0.12
EPF_EMPLOYER_RATE = 0.12
PF_WAGE_CEILING = 15000  # statutory ceiling; many employers apply PF only up to this basic

PROFESSIONAL_TAX_MONTHLY = 200  # varies by state; this is a common flat approximation

# New regime slabs (FY 2024-25 style structure). Update annually.
NEW_REGIME_SLABS = [
    (300000, 0.00),
    (600000, 0.05),
    (900000, 0.10),
    (1200000, 0.15),
    (1500000, 0.20),
    (float("inf"), 0.30),
]
NEW_REGIME_REBATE_LIMIT = 700000  # Sec 87A: nil tax if taxable income <= this

# Old regime slabs (simplified, assumes < 60 years old).
OLD_REGIME_SLABS = [
    (250000, 0.00),
    (500000, 0.05),
    (1000000, 0.20),
    (float("inf"), 0.30),
]
OLD_REGIME_REBATE_LIMIT = 500000
STANDARD_DEDUCTION = 50000

CESS_RATE = 0.04  # Health & Education Cess on tax


@dataclass
class PayrollInputs:
    basic_salary: float
    days_in_month: int = 30
    days_paid: int = 30          # for LOP / pro-rating
    rent_paid_monthly: float = 0.0
    is_metro: bool = False
    tax_regime: str = "new"      # "new" or "old"
    pf_on_full_basic: bool = False  # if False, PF capped at PF_WAGE_CEILING


def _slab_tax(annual_taxable_income: float, slabs) -> float:
    """Compute tax from a slab table of (upper_bound, rate) tuples."""
    tax = 0.0
    lower = 0.0
    for upper, rate in slabs:
        if annual_taxable_income > lower:
            taxable_in_slab = min(annual_taxable_income, upper) - lower
            tax += taxable_in_slab * rate
            lower = upper
        else:
            break
    return tax


def _annual_tds(annual_gross: float, regime: str) -> float:
    if regime == "new":
        taxable = max(annual_gross - STANDARD_DEDUCTION, 0)
        if taxable <= NEW_REGIME_REBATE_LIMIT:
            return 0.0
        tax = _slab_tax(taxable, NEW_REGIME_SLABS)
    else:
        taxable = max(annual_gross - STANDARD_DEDUCTION, 0)
        if taxable <= OLD_REGIME_REBATE_LIMIT:
            return 0.0
        tax = _slab_tax(taxable, OLD_REGIME_SLABS)

    tax *= (1 + CESS_RATE)  # add cess
    return tax


def _hra_exemption(basic: float, hra_received: float, rent_paid: float, is_metro: bool) -> float:
    """Least of: HRA received, rent paid - 10% of basic, 50%/40% of basic."""
    if rent_paid <= 0:
        return 0.0
    pct = 0.50 if is_metro else 0.40
    return max(0.0, min(
        hra_received,
        rent_paid - 0.10 * basic,
        basic * pct,
    ))


def current_ist_str():
    """Return today's date in India Standard Time for payslip display."""
    ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
    return ist_time.strftime("%d %b %Y")


def _calculate_payroll_inputs(inputs: PayrollInputs) -> dict:
    prorate_factor = inputs.days_paid / inputs.days_in_month

    basic = inputs.basic_salary * prorate_factor
    house_rent_allowance = inputs.basic_salary * HRA_RATE * prorate_factor
    special_allowance = inputs.basic_salary * SPECIAL_ALLOWANCE_RATE * prorate_factor
    leave_travel_allowance = inputs.basic_salary * LTA_RATE * prorate_factor
    bonus = inputs.basic_salary * BONUS_RATE * prorate_factor

    gross_earnings = basic + house_rent_allowance + special_allowance + leave_travel_allowance + bonus

    # --- PF ---
    pf_wage = inputs.basic_salary if inputs.pf_on_full_basic else min(inputs.basic_salary, PF_WAGE_CEILING)
    employee_pf = pf_wage * EPF_EMPLOYEE_RATE
    employer_pf = pf_wage * EPF_EMPLOYER_RATE

    # --- Professional Tax ---
    professional_tax = PROFESSIONAL_TAX_MONTHLY if inputs.days_paid > 0 else 0

    # --- HRA exemption (only relevant/available under the Old regime) ---
    hra_exempt = 0.0
    if inputs.tax_regime == "old":
        hra_exempt = _hra_exemption(basic, house_rent_allowance, inputs.rent_paid_monthly, inputs.is_metro)

    # --- TDS ---
    monthly_taxable_gross = gross_earnings - hra_exempt
    annual_gross_for_tax = monthly_taxable_gross * 12
    annual_tds = _annual_tds(annual_gross_for_tax, inputs.tax_regime)
    tds = annual_tds / 12

    total_deductions = professional_tax + employee_pf + tds
    net_salary = gross_earnings - total_deductions

    return {
        "basic": round(basic, 2),
        "hra": round(house_rent_allowance, 2),
        "hra_exempt": round(hra_exempt, 2),
        "special_allowance": round(special_allowance, 2),
        "lta": round(leave_travel_allowance, 2),
        "bonus": round(bonus, 2),
        "gross_earnings": round(gross_earnings, 2),
        "professional_tax": round(professional_tax, 2),
        "employee_epf": round(employee_pf, 2),
        "employer_epf": round(employer_pf, 2),
        "tds": round(tds, 2),
        "total_deductions": round(total_deductions, 2),
        "net_salary": round(net_salary, 2),
        "tax_regime": inputs.tax_regime,
        "days_paid": inputs.days_paid,
    }


def calculate_payroll(employee_or_inputs) -> dict:
    """Calculate payroll for Flask employee rows or PayrollInputs."""
    if isinstance(employee_or_inputs, PayrollInputs):
        return _calculate_payroll_inputs(employee_or_inputs)

    employee = employee_or_inputs
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    monthly_basic = float(employee.CTC) * 0.40 / 12
    working_days = getattr(employee, "WorkingDays", None)
    days_paid = days_in_month if working_days is None else max(
        0, min(int(working_days), days_in_month)
    )
    regime = (getattr(employee, "RegimeOpted", None) or "New").lower()

    payroll = _calculate_payroll_inputs(PayrollInputs(
        basic_salary=monthly_basic,
        days_in_month=days_in_month,
        days_paid=days_paid,
        tax_regime=regime,
    ))
    full_month = _calculate_payroll_inputs(PayrollInputs(
        basic_salary=monthly_basic,
        days_in_month=days_in_month,
        days_paid=days_in_month,
        tax_regime=regime,
    ))

    payroll["epf"] = payroll["employee_epf"]
    payroll["gross_earnings_full"] = full_month["gross_earnings"]
    return payroll


if __name__ == "__main__":
    # quick sanity check
    result = calculate_payroll(PayrollInputs(
        basic_salary=50000,
        rent_paid_monthly=15000,
        is_metro=True,
        tax_regime="old",
    ))
    for k, v in result.items():
        print(f"{k}: {v}")