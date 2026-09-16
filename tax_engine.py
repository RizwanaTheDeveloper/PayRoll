"""
Income tax calculation for FY 2025-26 (AY 2026-27), confirmed against
the Budget 2025 slabs for both regimes.

IMPORTANT SIMPLIFICATION: HRA and LTA exemptions under the Old Regime
are NOT applied here, since claiming them correctly requires additional
inputs this system doesn't collect (actual rent paid, whether the city
is metro/non-metro, travel bills for LTA, etc.). The Old Regime figures
below only subtract the flat Standard Deduction before applying slabs,
which will overstate Old Regime tax for anyone who would otherwise
claim those exemptions. If your organization needs accurate Old Regime
exemptions, that requires a proper compliance/payroll product — this is
a reasonable approximation for an internal tool, not a substitute for one.
"""

NEW_REGIME_SLABS = [
    (400000, 0.00),
    (800000, 0.05),
    (1200000, 0.10),
    (1600000, 0.15),
    (2000000, 0.20),
    (2400000, 0.25),
    (float("inf"), 0.30),
]
NEW_REGIME_STANDARD_DEDUCTION = 75000
NEW_REGIME_REBATE_LIMIT = 1200000
NEW_REGIME_REBATE_MAX = 60000

OLD_REGIME_SLABS = [
    (250000, 0.00),
    (500000, 0.05),
    (1000000, 0.20),
    (float("inf"), 0.30),
]
OLD_REGIME_STANDARD_DEDUCTION = 50000
OLD_REGIME_REBATE_LIMIT = 500000
OLD_REGIME_REBATE_MAX = 12500

CESS_RATE = 0.04


def _slab_tax(taxable_income, slabs):
    tax = 0.0
    lower = 0.0
    for upper, rate in slabs:
        if taxable_income > lower:
            portion = min(taxable_income, upper) - lower
            tax += portion * rate
            lower = upper
        else:
            break
    return tax


def calculate_annual_tax(annual_gross_salary, regime="New"):
    """
    Full FY tax breakdown for one employee, given their estimated
    annual gross salary (Basic + HRA + Special Allowance + LTA + Bonus,
    annualized).
    """
    regime = (regime or "New").strip().title()
    if regime == "Old":
        slabs = OLD_REGIME_SLABS
        standard_deduction = OLD_REGIME_STANDARD_DEDUCTION
        rebate_limit = OLD_REGIME_REBATE_LIMIT
        rebate_max = OLD_REGIME_REBATE_MAX
    else:
        regime = "New"
        slabs = NEW_REGIME_SLABS
        standard_deduction = NEW_REGIME_STANDARD_DEDUCTION
        rebate_limit = NEW_REGIME_REBATE_LIMIT
        rebate_max = NEW_REGIME_REBATE_MAX

    annual_taxable_salary = round(annual_gross_salary, 2)                       # (C)
    net_taxable_income = round(max(annual_taxable_salary - standard_deduction, 0), 2)  # (E)

    tds_at_normal_rate = _slab_tax(net_taxable_income, slabs)

    if net_taxable_income <= rebate_limit:
        rebate = min(tds_at_normal_rate, rebate_max)
        tax_on_taxable_income = max(tds_at_normal_rate - rebate, 0)
    else:
        # Marginal relief: tax payable can never exceed income over the rebate limit
        excess_income = net_taxable_income - rebate_limit
        if tds_at_normal_rate > excess_income:
            tax_on_taxable_income = excess_income
            rebate = tds_at_normal_rate - excess_income
        else:
            rebate = 0.0
            tax_on_taxable_income = tds_at_normal_rate

    education_cess = round(tax_on_taxable_income * CESS_RATE, 2)
    net_tax = round(tax_on_taxable_income + education_cess, 2)

    return {
        "regime": regime,
        "annual_taxable_salary": annual_taxable_salary,
        "standard_deduction": standard_deduction,
        "net_taxable_income": net_taxable_income,
        "tds_at_normal_rate": round(tds_at_normal_rate, 2),
        "rebate": round(rebate, 2),
        "tax_on_taxable_income": round(tax_on_taxable_income, 2),
        "education_cess": education_cess,
        "net_tax": net_tax,
    }
