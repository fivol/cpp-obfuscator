#!/bin/python3

import argparse

from code_obfuscator import CppCodeObfuscator

parser = argparse.ArgumentParser(description='Obfuscate c++ code')
parser.add_argument('filename', help='Input *.cpp filename')
parser.add_argument('-o', metavar='output', default='a.cpp',
                    help='Output code filename. Default a.cpp', required=False)


def main(args):
    obfuscator = CppCodeObfuscator.from_file(args.filename)
    obfuscator.obfuscate()
    obfuscator.write_file(args.o)


if __name__ == '__main__':
    main(parser.parse_args())
