"""
author: @aoyalowo
"""

import pandas as pd
import numpy as np
import os
import sqlite3
import argparse
import time
import functools
import re
import logging

logging.basicConfig(level=logging.INFO)

def parse_args():
    """ Create command line interface for entering command line arguments.

    Returns
    -------
    parsedArgs: Parser object
        Object for holding parsed command line arguments

    """
    now = time.strftime("%Y-%m-%dT%H-%M-%S")
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    parser.add_argument('-o','--output',default="{}_ER.db".format(now), nargs='?')

    parsedArgs = parser.parse_args()

    return parsedArgs

def read_data(file, conn):
    df = pd.read_csv(file, parse_dates={"timestamp":[0]})

    patt = "[0-9]_([a-zA-Z]+)[0-9-_]*[a-zA-Z0-9-]*.txt"
    m = re.search(patt,file)
    label = m.group(1)

    logging.info("Exporting {} to db".format(label))

    df.to_sql(label, conn, flavor='sqlite',if_exists="replace")

    c = conn.cursor()

    ixlabel = 'ix_{}_timestamp'.format(label)

    sql = ("CREATE INDEX {} ON {} (timestamp)".format(ixlabel,label))
    c.execute(sql)
    c.close()

    logging.info("{} export complete".format(label))



def main():
    args = parse_args()
    direc = args.directory
    files = os.listdir(direc)

    prepend_path = functools.partial(os.path.join,direc)

    conn = sqlite3.connect(args.output)

    fileName = list(map(prepend_path,files))

    for file in fileName: read_data(file, conn)

    conn.close()
    # conn.row_factory = sqlite3.Row
    # c = conn.cursor()
    # v = conn.cursor()

if __name__ == '__main__':
    main()
