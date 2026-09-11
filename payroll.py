HRA_RATE = 0.25
SPECIAL_ALLOWANCE_RATE = 0.10
LTA_RATE = 0.05
BONUS_RATE = 0.05
EPF_RATE = 0.12
PROFESSIONAL_TAX = 200
def calculate_payroll(employee):
    basic = float(employee.BasicSalary)
    house_rent_allowance = basic * HRA_RATE
    special_allowance = basic * SPECIAL_ALLOWANCE_RATE
    leave_travel_allowance = basic * LTA_RATE
    bonus = basic * BONUS_RATE
    gross_earnings = basic+ house_rent_allowance+ special_allowance+ leave_travel_allowance+ bonus
    employee_provident_fund = basic * EPF_RATE
    professional_tax = PROFESSIONAL_TAX
    annual_gross = gross_earnings * 12
    if annual_gross <= 700000:
        tds = 0
    else:
        taxable_amount = annual_gross - 700000
        annual_tds = taxable_amount * 0.10
        tds = annual_tds / 12
    total_deductions = professional_tax+ employee_provident_fund+ tds
    net_salary = gross_earnings- total_deductions
    return {
        "basic": basic,
        "hra": house_rent_allowance,
        "special_allowance":special_allowance,
        "lta":leave_travel_allowance,
        "bonus":bonus,
        "gross_earnings":gross_earnings,
        "professional_tax":professional_tax,
        "epf":employee_provident_fund,
        "tds":tds,
        "total_deductions":total_deductions,
        "net_salary":net_salary
    }