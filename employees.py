from database import get_connection


# ============================================================
# EMPLOYEE COLUMNS
# ============================================================

# The quoted aliases preserve the exact names expected by
# the rest of the Flask application:
#
# employee.EmployeeCode
# employee.FullName
# employee.CTC
# employee.RegimeOpted
# employee.WorkingDays
# etc.

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
    WorkingDays AS "WorkingDays",
    IsActive AS "IsActive"
"""


# ============================================================
# READ ALL EMPLOYEES
# ============================================================

def get_employees():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(f"""
            SELECT
                {EMPLOYEE_COLUMNS}
            FROM Employees
            WHERE IsActive = 1
            ORDER BY EmployeeCode
        """)

        employees = cursor.fetchall()

        return employees

    finally:

        cursor.close()
        connection.close()


# ============================================================
# READ ONE EMPLOYEE
# ============================================================

def get_employee(employee_code):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(f"""
            SELECT
                {EMPLOYEE_COLUMNS}
            FROM Employees
            WHERE EmployeeCode = %s
        """, (
            employee_code,
        ))

        employee = cursor.fetchone()

        return employee

    finally:

        cursor.close()
        connection.close()


# ============================================================
# CREATE EMPLOYEE
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
    regime_opted,
    working_days
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # ========================================================
        # FIND NEXT EMPLOYEE NUMBER
        # ========================================================

        cursor.execute("""
            SELECT COALESCE(
                MAX(
                    CASE
                        WHEN EmployeeCode ~ '^EMP[0-9]+$'
                        THEN CAST(
                            SUBSTRING(EmployeeCode FROM 4)
                            AS INTEGER
                        )
                        ELSE NULL
                    END
                ),
                0
            )
            FROM Employees
        """)

        result = cursor.fetchone()

        last_number = result[0] if result else 0

        next_number = last_number + 1

        employee_code = f"EMP{next_number:03d}"


        # ========================================================
        # INSERT EMPLOYEE
        # ========================================================

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
                WorkingDays,
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
            working_days,
            1
        ))


        # ========================================================
        # COMMIT
        # ========================================================

        connection.commit()

        return employee_code


    except Exception:

        connection.rollback()

        raise


    finally:

        cursor.close()
        connection.close()



# ============================================================
# UPDATE EMPLOYEE
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
    regime_opted,
    working_days
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
                RegimeOpted = %s,
                WorkingDays = %s
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
            working_days,
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
# DELETE EMPLOYEE
# ============================================================

def delete_employee(employee_code):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            DELETE FROM Employees
            WHERE EmployeeCode = %s
        """, (
            employee_code,
        ))


        connection.commit()

        return cursor.rowcount > 0


    except Exception:

        connection.rollback()

        raise


    finally:

        cursor.close()
        connection.close()