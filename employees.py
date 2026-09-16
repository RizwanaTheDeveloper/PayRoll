from database import get_connection


def get_employees():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT EmployeeCode, FullName, Department, Designation,
               JoiningDate, BasicSalary, IsActive
        FROM Employees
        WHERE IsActive = 1
        ORDER BY EmployeeCode
    """)
    employees = cursor.fetchall()
    cursor.close()
    connection.close()
    return employees


def get_employee(employee_code):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT EmployeeCode, FullName, Department, Designation,
               JoiningDate, BasicSalary, IsActive
        FROM Employees
        WHERE EmployeeCode = ?
    """, (employee_code,))
    employee = cursor.fetchone()
    cursor.close()
    connection.close()
    return employee


def add_employee(full_name, department, designation, joining_date, basic_salary):
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
    next_number = 1 if last_number is None else last_number + 1
    employee_code = f"EMP{next_number:03d}"

    cursor.execute("""
        INSERT INTO Employees
            (EmployeeCode, FullName, Department, Designation, JoiningDate, BasicSalary, IsActive)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        employee_code,
        full_name,
        department,
        designation,
        joining_date,
        basic_salary,
        1
    ))

    connection.commit()
    cursor.close()
    connection.close()
    return employee_code


def update_employee(employee_code, full_name, department, designation, joining_date, basic_salary):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE Employees
        SET FullName    = ?,
            Department  = ?,
            Designation = ?,
            JoiningDate = ?,
            BasicSalary = ?
        WHERE EmployeeCode = ?
    """, (
        full_name,
        department,
        designation,
        joining_date,
        basic_salary,
        employee_code
    ))
    connection.commit()
    updated = cursor.rowcount > 0
    cursor.close()
    connection.close()
    return updated


def delete_employee(employee_code):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM Employees WHERE EmployeeCode = ?", (employee_code,))
    connection.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    connection.close()
    return deleted
