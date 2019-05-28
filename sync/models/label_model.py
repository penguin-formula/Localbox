import sqlite3
from sync.database import database_execute


# class Blob:
#     """Automatically encode a binary string."""
#     def __init__(self, s):
#         self.s = s

#     def _quote(self):
#         return "'%s'" % sqlite3.binary(self.s)


def delete_client_data(label):
    sql = 'delete from sites where site=?'
    database_execute(sql, (label,))
    sql = 'delete from keys where site=?'
    database_execute(sql, (label,))

def create_server_data(server):
    sql = "INSERT INTO servers (label, url, picture) VALUES (?, ?, ?);"
    database_execute(sql, (server.label, server.url, server.picture))

def get_server_data():
    sql = "SELECT label, url, picture FROM servers;"
    cursor = database_execute(sql)
    return cursor