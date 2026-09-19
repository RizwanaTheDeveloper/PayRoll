from database import get_connection


# These aliases preserve the exact attribute names expected by app.py
# and payroll.py, such as employee.FullName and employee.CTC.
EMPLOYEE_COLUMNS = """
    EmployeeCode AS "EmployeeCode",
    FullName AS "FullName",
    Department AS "Department",
    Designation AS "Designation",
    JoiningDate AS "JoiningDate",
    CTC AS "CTC",
    PAN AS "PAN",
    PFUAN AS "PFUAN",
    AccountNumber AS "AccountNumber",
    IFSCCode AS "IFSCCode",
    RegimeOpted AS "RegimeOpted",
    IsActive AS "IsActive"
"""


# ============================================================
# READ - GET ALL EMPLOYEES
# ============================================================

def get_employees():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(f"""
            SELECT {EMPLOYEE_COLUMNS}
            FROM Employees
            WHERE IsActive = 1
            ORDER BY EmployeeCode
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


# ============================================================
# READ - GET ONE EMPLOYEE
# ============================================================

def get_employee(employee_code):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(f"""
            SELECT {EMPLOYEE_COLUMNS}
            FROM Employees
            WHERE EmployeeCode = %s
        """, (employee_code,))

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


# ============================================================
# CREATE - ADD EMPLOYEE
# ============================================================

def add_employee(
    full_name,
    department,
    designation,
    joining_date,
    ctc,
    pan,
    pf_uan,
    account_number,
    ifsc_code,
    regime_opted
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Find the highest existing employee number.
        #
        # EMP001 -> 1
        # EMP002 -> 2
        # EMP010 -> 10
        #
        # PostgreSQL version of the old SQL Server TRY_CAST.
        cursor.execute("""
            SELECT MAX(
                CAST(
                    NULLIF(
                        REPLACE(EmployeeCode, 'EMP', ''),
                        ''
                    ) AS INTEGER
                )
            )
            FROM Employees
        """)

        result = cursor.fetchone()
        last_number = result[0]

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
                Department,
                Designation,
                JoiningDate,
                CTC,
                PAN,
                PFUAN,
                AccountNumber,
                IFSCCode,
                RegimeOpted,
                IsActive
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            employee_code,
            full_name,
            department,
            designation,
            joining_date,
            ctc,
            pan,
            pf_uan,
            account_number,
            ifsc_code,
            regime_opted,
            1
        ))

        connection.commit()

        return employee_code

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ============================================================
# UPDATE - EDIT EMPLOYEE
# ============================================================

def update_employee(
    employee_code,
    full_name,
    department,
    designation,
    joining_date,
    ctc,
    pan,
    pf_uan,
    account_number,
    ifsc_code,
    regime_opted
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE Employees
            SET
                FullName = %s,
                Department = %s,
                Designation = %s,
                JoiningDate = %s,
                CTC = %s,
                PAN = %s,
                PFUAN = %s,
                AccountNumber = %s,
                IFSCCode = %s,
                RegimeOpted = %s
            WHERE EmployeeCode = %s
        """, (
            full_name,
            department,
            designation,
            joining_date,
            ctc,
            pan,
            pf_uan,
            account_number,
            ifsc_code,
            regime_opted,
            employee_code
        ))

        connection.commit()

        return cursor.rowcount > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ============================================================
# DELETE - DELETE EMPLOYEE
# ============================================================

def delete_employee(employee_code):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM Employees
            WHERE EmployeeCode = %s
        """, (employee_code,))

        connection.commit()

        return cursor.rowcount > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()