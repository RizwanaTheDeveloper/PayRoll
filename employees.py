from database import get_connection
def get_employees():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT EmployeeCode,FullName,Designation,BasicSalary
        FROM Employees
        WHERE IsActive = 1
        ORDER BY EmployeeCode
         """)
    employees = cursor.fetchall()
    cursor.close()
    connection.close()
    return employees
def get_employee(employee_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT EmployeeCode,FullName,Designation,BasicSalary
        FROM Employees
        WHERE EmployeeCode = ? """, (employee_id,))
    employee = cursor.fetchone()
    cursor.close()
    connection.close()
    return employee
def add_employee(full_name, basic_salary):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT MAX(
            TRY_CAST(
                REPLACE(EmployeeCode, 'EMP', '')
                AS INT
            )
        )
        FROM Employees
    """)
    last_number = cursor.fetchone()[0]
    if last_number is None:
        next_number = 1
    else:
        next_number = last_number + 1
    employee_code = f"EMP{next_number:03d}"
    cursor.execute("""
        INSERT INTO Employees
        (
            EmployeeCode,
            FullName,
            Designation,
            BasicSalary,
            IsActive
        )
        VALUES (?, ?, ?, ?, ?)
    """,
    (
        employee_code,
        full_name,
        "Employee",
        basic_salary,
        1
    ))
    connection.commit()
    cursor.close()
    connection.close()