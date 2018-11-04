#!/usr/bin/env python

import cmd
import sys
import uuid
import pprint
import sqlite3


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

sqlite3.register_converter('GUID', lambda b: uuid.UUID(bytes_le=b))
sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)


class QueryShell(cmd.Cmd):
    intro = "Enter a query or 'q' to quit."
    prompt = '> '
    connection = None
    cursor = None

    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.connection = sqlite3.connect(self.filename, detect_types=sqlite3.PARSE_DECLTYPES)
        self.connection.row_factory = make_dicts
        self.cursor = self.connection.cursor()

    def do_q(self, arg):
        return self.do_quit(arg)

    def do_EOF(self, arg):
        return self.do_quit(arg)

    def do_quit(self, arg):
        self.close()
        return True

    def default(self, line):
        try:
            self.cursor.execute(line)
        except sqlite3.Error as e:
            print(e)
        else:
            pprint.pprint(self.cursor.fetchall())

    def close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.connection:
            self.connection.close()
            self.connection = None


def usage(program):
    sys.exit(f'Usage: python3 {program} DBFILE')

if __name__ == '__main__':
    argc = len(sys.argv)
    if argc != 2:
        usage(sys.argv[0])

    shell = QueryShell(sys.argv[1])
    shell.cmdloop()
#!/usr/bin/env python

import cmd
import sys
import uuid
import pprint
import sqlite3


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

sqlite3.register_converter('GUID', lambda b: uuid.UUID(bytes_le=b))
sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)


class QueryShell(cmd.Cmd):
    intro = "Enter a query or 'q' to quit."
    prompt = '> '
    connection = None
    cursor = None

    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.connection = sqlite3.connect(self.filename, detect_types=sqlite3.PARSE_DECLTYPES)
        self.connection.row_factory = make_dicts
        self.cursor = self.connection.cursor()

    def do_q(self, arg):
        return self.do_quit(arg)

    def do_EOF(self, arg):
        return self.do_quit(arg)

    def do_quit(self, arg):
        self.close()
        return True

    def default(self, line):
        try:
            self.cursor.execute(line)
        except sqlite3.Error as e:
            print(e)
        else:
            pprint.pprint(self.cursor.fetchall())

    def close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.connection:
            self.connection.close()
            self.connection = None


def usage(program):
    sys.exit(f'Usage: python3 {program} DBFILE')

if __name__ == '__main__':
    argc = len(sys.argv)
    if argc != 2:
        usage(sys.argv[0])

    shell = QueryShell(sys.argv[1])
    shell.cmdloop()


