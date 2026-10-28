# Django talks to MySQL through the "MySQLdb" module (provided by mysqlclient).
# On some computers (mostly Windows) mysqlclient is hard to install.
# If it is missing, fall back to PyMySQL, which is pure Python and behaves the same.
try:
    import MySQLdb  # noqa: F401  (mysqlclient is installed - nothing else to do)
except ImportError:
    try:
        import pymysql

        pymysql.install_as_MySQLdb()
    except ImportError:
        # Neither driver is installed. Django will show a clear error message.
        pass
