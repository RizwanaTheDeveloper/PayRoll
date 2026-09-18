import mssql_python


def get_connection():

    connection = mssql_python.connect(
        "Server=.\\SQLEXPRESS;"
        "Database=PayrollDB;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

    return connection