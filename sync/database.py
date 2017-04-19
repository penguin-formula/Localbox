"""
Database implementation class
"""

from .defaults import SYNCINI_PATH
from .defaults import DATABASE_PATH
from sqlite3 import Binary

from logging import getLogger
from os.path import exists
from os.path import expandvars
from os.path import dirname
from os import makedirs

try:
    from ConfigParser import ConfigParser
    from ConfigParser import NoSectionError
    from ConfigParser import NoOptionError
except ImportError:
    from configparser import ConfigParser  # pylint: disable=F0401,W0611
    from configparser import NoSectionError  # pylint: disable=F0401
    from configparser import NoOptionError  # pylint: disable=F0401

try:
    from MySQLdb import connect as mysql_connect
    from MySQLdb import Error as MySQLError
except ImportError:
    mysql_connect = None

from sqlite3 import Error as SQLiteError
from sqlite3 import connect as sqlite_connect

WARNINGS_ENABLED = False


def warning_no_database_section(error):
    if WARNINGS_ENABLED:
        getLogger(__name__).warning("%s in '%s'",
                                    error.message, SYNCINI_PATH)


class DatabaseError(Exception):
    """
    An error related to the database has occurred
    """
    pass


def get_sql_log_dict():
    """
    get logging dictionary related to the database
    """
    parser = ConfigParser()
    parser.read(SYNCINI_PATH)
    try:
        dbtype = parser.get('database', 'type')
    except (NoSectionError, NoOptionError) as error:
        warning_no_database_section(error)

        dbtype = "sqlite"
    if dbtype in ['sqlite', 'sqlite3']:
        try:
            ip_address = parser.get('database', 'filename')
        except (NoSectionError, NoOptionError) as error:
            warning_no_database_section(error)
            ip_address = DATABASE_PATH
    else:
        ip_address = parser.get('database', 'hostname')
    return {'ip': ip_address, 'user': '', 'path': 'database/'}


def database_execute(command, params=None):
    """
    Function to execute a sql statement on the database. Executes the right
    backend and makes sure '?' is replaced for the local substitution variable
    if needed.
    @param command the sql command to execute
    @param params a list of tuple of values to substitute in command
    @returns a list of dictionaries representing the sql result
    """
    getLogger(__name__).debug("database_execute(" + command + ", " +
                              str(params) + ")", extra=get_sql_log_dict())
    parser = ConfigParser()
    parser.read(SYNCINI_PATH)
    try:
        dbtype = parser.get('database', 'type')
    except (NoSectionError, NoOptionError) as error:
        warning_no_database_section(error)
        dbtype = 'sqlite'

    if dbtype == "mysql":
        if mysql_execute is None:
            exit("Trying to use a MySQL database without python-MySQL module.")
        command = command.replace('?', '%s')
        return mysql_execute(command, params)

    elif (dbtype in ["sqlite3", "sqlite"]):
        return sqlite_execute(command, params)
    else:
        raise DatabaseError("Unknown database type, cannot continue")


def sqlite_execute(command, params=None):
    """
    Function to execute a sql statement on the mysql database. This function is
    called by the database_execute function when the sqlite backend is set in
    the configuration file
    @param command the sql command to execute
    @param params a list of tuple of values to substitute in command
    @returns a list of dictionaries representing the sql result
    """
    # NOTE mostly copypasta'd from mysql_execute, may be a better way
    try:
        parser = ConfigParser()
        parser.read(SYNCINI_PATH)
        try:
            filename = parser.get('database', 'filename')
        except (NoSectionError, NoOptionError) as error:
            warning_no_database_section(error)
            filename = DATABASE_PATH

        init_db = not exists(expandvars(filename))
        # make sure the folder in which the database is saved exists
        if init_db and not exists(dirname(filename)):
            makedirs(dirname(filename))
        connection = sqlite_connect(filename)
        connection.text_factory = Binary
        cursor = connection.cursor()
        if init_db:
            for sql in ('CREATE TABLE sites (site char(255), client_id'
                        ' char(255), client_secret char(255), user char(255), token char(255));',
                        'CREATE TABLE keys (site char(255), user char(255),'
                        ' fingerprint char(40));'):
                if sql != "" and sql is not None:
                    cursor.execute(sql)
                    connection.commit()
        if params:
            cursor.execute(command, params)
        else:
            cursor.execute(command)
        connection.commit()

        final_result = []
        for l in cursor.fetchall():
            final_result.append(list(map(lambda i: i.obj.decode('utf-8') if hasattr(i, 'decode') else str(i), l)))
        return final_result
    except SQLiteError as sqlerror:
        getLogger(__name__).exception(sqlerror)
        raise DatabaseError("SQLite Error: %s" % (sqlerror.args[0]))
    except (NoSectionError, NoOptionError) as error:
        getLogger(__name__).exception(error)
        raise DatabaseError("Please configure the database section"
                            " in the ini file")
    except TypeError as error:
        getLogger(__name__).exception(error)
        raise DatabaseError("Please configure the 'filename' parameter"
                            " in the [database] section in the ini file")
    finally:
        try:
            if connection:
                connection.close()
        except UnboundLocalError as error:
            getLogger(__name__).exception(error)


def mysql_execute(command, params=None):
    """
    Function to execute a sql statement on the mysql database. This function is
    called by the database_execute function when the mysql backend is set in
    the configuration file.
    @param command the sql command to execute
    @param params a list of tuple of values to substitute in command
    @returns a list of dictionaries representing the sql result
    """
    parser = ConfigParser()
    parser.read(SYNCINI_PATH)
    try:
        host = parser.get('database', 'hostname')
        user = parser.get('database', 'username')
        pawd = parser.get('database', 'password')
        dbse = parser.get('database', 'database')
        port = parser.getint('database', 'port')
        connection = mysql_connect(host=host, port=port, user=user,
                                   passwd=pawd, db=dbse)
        cursor = connection.cursor()
        cursor.execute(command, params)
        connection.commit()
        return cursor.fetchall()
    except MySQLError as mysqlerror:
        string = "MySQL Error: %d: %s" % (mysqlerror.args[0],
                                          mysqlerror.args[1])
        getLogger(__name__).debug(string, extra=get_sql_log_dict())
    finally:
        try:
            if connection:
                connection.close()
        except UnboundLocalError as error:
            getLogger(__name__).exception(error)
