from flask import Flask, redirect, render_template, request, url_for
from employees import get_employees, get_employee, add_employee
from payroll import calculate_payroll
app = Flask(__name__)
@app.route("/")
def index():
    employees = get_employees()
    return render_template("index.html",employees=employees)
@app.route("/generate-payroll/<EmployeeCode>")
def generate_payroll(EmployeeCode):
    employee = get_employee(EmployeeCode)
    if not employee:
        return "Employee not found", 404
    payroll = calculate_payroll(employee)
    return render_template("payroll.html",employee=employee,payroll=payroll)
@app.route("/add a employee", methods=["POST"])
def add_employee_route():
    full_name = request.form.get("full_name")
    basic_salary = request.form.get("basic_salary")
    if not full_name or not basic_salary:
        return "Name and Basic Salary are required", 400
    try:
        basic_salary = float(basic_salary)
    except ValueError:
        return "Basic Salary must be a number", 400
    if basic_salary <= 0:
        return "Basic Salary must be greater than zero", 400
    add_employee(full_name, basic_salary)
    return redirect(url_for("index"))
if __name__ == "__main__":
    app.run(debug=True)