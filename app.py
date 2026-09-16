from datetime import datetime, date
from flask import Flask, redirect, render_template, request, url_for, flash, abort

from employees import get_employees, get_employee, add_employee, update_employee, delete_employee
from payroll import calculate_payroll, current_ist_str
from tax_engine import calculate_annual_tax
from payroll_history import get_month_record, record_month, get_fy_summary, fy_label

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-key"  # required for flash()

COMPANY_NAME = "5Gen Educon Private Limited"


@app.context_processor
def inject_company_name():
    return {"company_name": COMPANY_NAME}


@app.template_filter("inr")
def inr_filter(value):
    """Format a number as Indian Rupees with Indian digit grouping (1,23,456.78)."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    negative = value < 0
    value = abs(value)
    whole, _, decimal = f"{value:.2f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = ",".join([head[max(i - 2, 0):i] for i in range(len(head), 0, -2)][::-1])
        whole = f"{head},{tail}"
    result = f"₹{whole}.{decimal}"
    return f"-{result}" if negative else result


def _parse_employee_form(form):
    """Shared validation for both the add and edit forms."""
    full_name = (form.get("full_name") or "").strip()
    department = (form.get("department") or "").strip()
    designation = (form.get("designation") or "").strip()
    joining_date_raw = (form.get("joining_date") or "").strip()
    ctc_raw = form.get("ctc")
    pan = (form.get("pan") or "").strip().upper()
    pf_uan = (form.get("pf_uan") or "").strip()
    account_number = (form.get("account_number") or "").strip()
    ifsc_code = (form.get("ifsc_code") or "").strip().upper()
    regime_opted = (form.get("regime_opted") or "New").strip()

    if not full_name or not ctc_raw or not joining_date_raw:
        return None, "Full Name, Joining Date, and CTC are required."

    try:
        ctc = float(ctc_raw)
    except ValueError:
        return None, "CTC must be a valid number."

    if ctc <= 0:
        return None, "CTC must be greater than zero."

    try:
        joining_date = datetime.strptime(joining_date_raw, "%Y-%m-%d").date()
    except ValueError:
        return None, "Joining Date must be a valid date (YYYY-MM-DD)."

    if regime_opted not in ("New", "Old"):
        regime_opted = "New"

    return {
        "full_name": full_name,
        "department": department or None,
        "designation": designation or None,
        "joining_date": joining_date,
        "ctc": ctc,
        "pan": pan or None,
        "pf_uan": pf_uan or None,
        "account_number": account_number or None,
        "ifsc_code": ifsc_code or None,
        "regime_opted": regime_opted,
    }, None


@app.route("/")
def index():
    employees = get_employees()
    return render_template("index.html", employees=employees)


@app.route("/generate-payroll/<EmployeeCode>")
def generate_payroll(EmployeeCode):
    employee = get_employee(EmployeeCode)
    if not employee:
        abort(404)

    payroll = calculate_payroll(employee)
    generated_at = current_ist_str()

    today = date.today()
    month, year = today.month, today.year

    annual_gross = payroll["gross_earnings"] * 12
    regime = getattr(employee, "RegimeOpted", None) or "New"
    tax = calculate_annual_tax(annual_gross, regime)

    existing_tds = get_month_record(EmployeeCode, month, year)
    if existing_tds is not None:
        monthly_tds = existing_tds
    else:
        tax_deducted_before, _, executions_left_before = get_fy_summary(EmployeeCode, today)
        remaining_including_this = max(executions_left_before, 1)
        monthly_tds = round(
            max(tax["net_tax"] - tax_deducted_before, 0) / remaining_including_this, 2
        )
        record_month(EmployeeCode, month, year, monthly_tds)

    tax_deducted_till_date, executions_done, executions_left = get_fy_summary(EmployeeCode, today)

    payroll["tds"] = monthly_tds
    payroll["total_deductions"] = payroll["professional_tax"] + payroll["epf"] + monthly_tds
    payroll["net_salary"] = payroll["gross_earnings"] - payroll["total_deductions"]

    return render_template(
        "payroll.html",
        employee=employee,
        payroll=payroll,
        tax=tax,
        generated_at=generated_at,
        fy_label=fy_label(today),
        tax_deducted_till_date=tax_deducted_till_date,
        executions_left=executions_left,
    )


@app.route("/add-employee", methods=["POST"])
def add_employee_route():
    data, error = _parse_employee_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("index"))

    add_employee(
        data["full_name"], data["department"], data["designation"],
        data["joining_date"], data["ctc"], data["pan"], data["pf_uan"],
        data["account_number"], data["ifsc_code"], data["regime_opted"],
    )
    flash(f"Employee “{data['full_name']}” added successfully.", "success")
    return redirect(url_for("index"))


@app.route("/edit-employee/<EmployeeCode>", methods=["GET", "POST"])
def edit_employee_route(EmployeeCode):
    employee = get_employee(EmployeeCode)
    if not employee:
        abort(404)

    if request.method == "POST":
        data, error = _parse_employee_form(request.form)
        if error:
            flash(error, "error")
            return redirect(url_for("edit_employee_route", EmployeeCode=EmployeeCode))

        update_employee(
            EmployeeCode, data["full_name"], data["department"], data["designation"],
            data["joining_date"], data["ctc"], data["pan"], data["pf_uan"],
            data["account_number"], data["ifsc_code"], data["regime_opted"],
        )
        flash(f"Employee “{data['full_name']}” updated successfully.", "success")
        return redirect(url_for("index"))

    return render_template("edit_employee.html", employee=employee)


@app.route("/delete-employee/<EmployeeCode>", methods=["POST"])
def delete_employee_route(EmployeeCode):
    employee = get_employee(EmployeeCode)
    if not employee:
        abort(404)

    delete_employee(EmployeeCode)
    flash(f"Employee “{employee.FullName}” deleted.", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
