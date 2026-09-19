from datetime import date

from database import get_connection


# ============================================================
# FINANCIAL YEAR
# ============================================================

def financial_year_bounds(reference_date=None):
    """Indian financial year: 1 April to 31 March."""

    reference_date = reference_date or date.today()

    if reference_date.month >= 4:
        start = date(reference_date.year, 4, 1)
        end = date(reference_date.year + 1, 3, 31)
    else:
        start = date(reference_date.year - 1, 4, 1)
        end = date(reference_date.year, 3, 31)

    return start, end


def fy_label(reference_date=None):
    start, end = financial_year_bounds(reference_date)

    return f"{start.year} - {end.year}"


# ============================================================
# GET MONTH RECORD
# ============================================================

def get_month_record(employee_code, month, year):
    """
    Returns the stored MonthlyTDS for this employee/month,
    or None if no record exists.
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT MonthlyTDS AS "MonthlyTDS"
            FROM PayrollHistory
            WHERE EmployeeCode = %s
              AND PayMonth = %s
              AND PayYear = %s
        """, (
            employee_code,
            month,
            year
        ))

        row = cursor.fetchone()

        if row:
            return float(row.MonthlyTDS)

        return None

    finally:
        cursor.close()
        connection.close()


# ============================================================
# RECORD MONTH
# ============================================================

def record_month(employee_code, month, year, monthly_tds):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO PayrollHistory
            (
                EmployeeCode,
                PayMonth,
                PayYear,
                MonthlyTDS
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
        """, (
            employee_code,
            month,
            year,
            monthly_tds
        ))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ============================================================
# FINANCIAL YEAR SUMMARY
# ============================================================

def get_fy_summary(employee_code, reference_date=None):
    """
    Returns:

        (
            tax_deducted_till_date,
            executions_done,
            executions_left
        )

    for the financial year containing reference_date.
    """

    start, end = financial_year_bounds(reference_date)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT MonthlyTDS AS "MonthlyTDS"
            FROM PayrollHistory
            WHERE EmployeeCode = %s
              AND (
                    (PayYear = %s AND PayMonth >= 4)
                    OR
                    (PayYear = %s AND PayMonth <= 3)
                  )
        """, (
            employee_code,
            start.year,
            end.year
        ))

        rows = cursor.fetchall()

        tax_deducted = round(
            sum(float(row.MonthlyTDS) for row in rows),
            2
        )

        executions_done = len(rows)

        executions_left = max(
            12 - executions_done,
            0
        )

        return (
            tax_deducted,
            executions_done,
            executions_left
        )

    finally:
        cursor.close()
        connection.close()