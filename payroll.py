from datetime import date, datetime, timedelta

HRA_RATE = 0.25
SPECIAL_ALLOWANCE_RATE = 0.10
LTA_RATE = 0.05
BONUS_RATE = 0.05
EPF_RATE = 0.12
PROFESSIONAL_TAX = 200

HIKE_RATE = 0.03            # 3% hike
HIKE_INTERVAL_MONTHS = 6    # every 6 months of service


def current_ist_str():
    """Today's date in IST, e.g. '15 Sep 2026'. No external timezone deps."""
    ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
    return ist_time.strftime("%d %b %Y")


def _months_between(start_date, end_date):
    """Whole months elapsed from start_date to end_date."""
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day < start_date.day:
        months -= 1
    return max(months, 0)


def get_hike_count(joining_date):
    """Number of completed 6-month periods since joining."""
    if not joining_date:
        return 0
    months_served = _months_between(joining_date, date.today())
    return months_served // HIKE_INTERVAL_MONTHS


def get_effective_basic_salary(base_salary, joining_date):
    """
    Base salary after compounding a 3% hike for every completed
    6-month period of service since JoiningDate.
    Returns (effective_salary, number_of_hikes_applied).
    """
    hikes = get_hike_count(joining_date)
    salary = float(base_salary)
    for _ in range(hikes):
        salary *= (1 + HIKE_RATE)
    return round(salary, 2), hikes


def calculate_payroll(employee):
    joining_date = getattr(employee, "JoiningDate", None)
    original_basic = float(employee.BasicSalary)
    basic, hikes_applied = get_effective_basic_salary(original_basic, joining_date)

    house_rent_allowance = basic * HRA_RATE
    special_allowance = basic * SPECIAL_ALLOWANCE_RATE
    leave_travel_allowance = basic * LTA_RATE
    bonus = basic * BONUS_RATE

    gross_earnings = basic + house_rent_allowance + special_allowance + leave_travel_allowance + bonus

    employee_provident_fund = basic * EPF_RATE
    professional_tax = PROFESSIONAL_TAX

    annual_gross = gross_earnings * 12
    if annual_gross <= 700000:
        tds = 0
    else:
        taxable_amount = annual_gross - 700000
        annual_tds = taxable_amount * 0.10
        tds = annual_tds / 12

    total_deductions = professional_tax + employee_provident_fund + tds
    net_salary = gross_earnings - total_deductions

    return {
        "basic": basic,
        "original_basic": original_basic,
        "hikes_applied": hikes_applied,
        "hra": house_rent_allowance,
        "special_allowance": special_allowance,
        "lta": leave_travel_allowance,
        "bonus": bonus,
        "gross_earnings": gross_earnings,
        "professional_tax": professional_tax,
        "epf": employee_provident_fund,
        "tds": tds,
        "total_deductions": total_deductions,
        "net_salary": net_salary,
    }
