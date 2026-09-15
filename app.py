from flask import Flask, redirect, render_template, request, url_for, flash, abort
from employees import get_employees, get_employee, add_employee
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
    full_name = (request.form.get("full_name") or "").strip()
    basic_salary = request.form.get("basic_salary")

    if not full_name or not basic_salary:
        flash("Name and Basic Salary are required.", "error")
        return redirect(url_for("index"))

    try:
        basic_salary = float(basic_salary)
    except ValueError:
        flash("Basic Salary must be a valid number.", "error")
        return redirect(url_for("index"))

    if basic_salary <= 0:
        flash("Basic Salary must be greater than zero.", "error")
        return redirect(url_for("index"))

    add_employee(full_name, basic_salary)
    flash(f"Employee “{full_name}” added successfully.", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)