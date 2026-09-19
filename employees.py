from database import get_connection


# Keep the exact attribute names expected by app.py and payroll.py.
# The quoted aliases are important because PostgreSQL normally
# converts unquoted column names to lowercase.
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

        employees = cursor.fetchall()
        return employees

    finally:
        cursor.close()
        connection.close()


def get_employee(employee_code):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(f"""
            SELECT {EMPLOYEE_COLUMNS}
            FROM Employees
            WHERE EmployeeCode = %s
        """, (employee_code,))

        employee = cursor.fetchone()
        return employee

    finally:
        cursor.close()
        connection.close()


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
        # PostgreSQL equivalent of the old SQL Server TRY_CAST.
        #
        # Example:
        # EMP001 -> 1
        # EMP010 -> 10
        #
        # NULLIF prevents an empty value from being cast to INTEGER.
        cursor.execute("""
            SELECT MAX(
                CAST(
                    NULLIF(REPLACE(EmployeeCode, 'EMP', ''), '')
                    AS INTEGER
                )
            )
            FROM Employees
        """)

        result = cursor.fetchone()
        last_number = result[0]

        next_number = 1 if last_number is None else last_number + 1

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

        updated = cursor.rowcount > 0
        return updated

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def delete_employee(employee_code):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM Employees
            WHERE EmployeeCode = %s
        """, (employee_code,))

        connection.commit()

        deleted = cursor.rowcount > 0
        return deleted

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()