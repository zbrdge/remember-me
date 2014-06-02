# Use libkeepass to read keepass2 files
# on the CLI.

# No real proper param handling right now,
# or much else.
# Usage: python2.7.x kpread.py <keepass2.dbx> <entry title>

# Output: JSON with UserName, URL, Password (possibly protected),
#   and Title

import libkeepass, sys
from getpass import *

filename = sys.argv[1]
passwd = getpass("Password: ")
entry = sys.argv[2]

with libkeepass.open(filename, password=passwd) as kdb:
    # print parsed element tree as xml
    n = kdb.obj_root.Root.iter()
    for child in n:
        if child.text == entry:
                print "{"
                print "  \"%s\" : \"%s\"," % ("Title", child.text)
                while child.text != "URL":
                    child = n.next()
                child = n.next()

                print "  \"%s\" : \"%s\"," % ("URL", child.text)
                while child.text != "UserName":
                    child = n.next()
                child = n.next()

                print "  \"%s\" : \"%s\"," % ("UserName", child.text)
                while child.text != "Password":
                    child = n.next()
                child = n.next()

                print "  \"%s\" : \"%s\"," % ("Password", child.text)
                print "}"
