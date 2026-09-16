from datetime import datetime
from flask import Flask, redirect, render_template, request, url_for, flash, abort

from employees import get_employees, get_employee, add_employee, update_employee, delete_employee
from payroll import calculate_payroll, current_ist_str

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-key"  # required for flash()


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
    # Indian grouping: last 3 digits, then groups of 2
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
    basic_salary_raw = form.get("basic_salary")

    if not full_name or not basic_salary_raw or not joining_date_raw:
        return None, "Full Name, Joining Date, and Basic Salary are required."

    try:
        basic_salary = float(basic_salary_raw)
    except ValueError:
        return None, "Basic Salary must be a valid number."

    if basic_salary <= 0:
        return None, "Basic Salary must be greater than zero."

    try:
        joining_date = datetime.strptime(joining_date_raw, "%Y-%m-%d").date()
    except ValueError:
        return None, "Joining Date must be a valid date (YYYY-MM-DD)."

    return {
        "full_name": full_name,
        "department": department or None,
        "designation": designation or None,
        "joining_date": joining_date,
        "basic_salary": basic_salary,
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
    return render_template(
        "payroll.html",
        employee=employee,
        payroll=payroll,
        generated_at=generated_at,
    )


@app.route("/add-employee", methods=["POST"])
def add_employee_route():
    data, error = _parse_employee_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("index"))

    add_employee(
        data["full_name"],
        data["department"],
        data["designation"],
        data["joining_date"],
        data["basic_salary"],
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
            EmployeeCode,
            data["full_name"],
            data["department"],
            data["designation"],
            data["joining_date"],
            data["basic_salary"],
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
