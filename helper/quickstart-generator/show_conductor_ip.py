#!/usr/bin/env python3

import argparse
from base64 import b64decode
from gzip import decompress
import json
import sys
import xml.etree.ElementTree as ET


def parse_arguments():
    """Get commandline arguments."""
    parser = argparse.ArgumentParser(
        description='Show conductor ip of a quickstart file')
    parser.add_argument('--quickstart', '-q', required=True,
                        help='quickstart file')
    return parser.parse_args()


def error(*messages):
    """Show error message and quit."""
    print('Error:', *messages)
    sys.exit(1)


def read_quickstart_file(filename):
    """Write a quickstart document in json format to file."""
    try:
        with open(filename) as fd:
            j = json.load(fd)
            return j
    except:
        raise

def main():
    args = parse_arguments()
    quickstart = read_quickstart_file(args.quickstart)
    try:
        b = quickstart.get('c')
        xml = decompress(b64decode(b))
        root = ET.fromstring(xml)
        for authority in root.findall('{http://128technology.com/t128/config/authority-config}authority'):
            for elem in authority.findall('{http://128technology.com/t128/config/authority-config}conductor-address'):
                print(elem.text)
    except:
        error('No conductor IP found in quickstart file.')


if __name__ == '__main__':
    main()
