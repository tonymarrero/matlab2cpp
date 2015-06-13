#!/usr/bin/env python

import supplement
import utils

import os
import imp
import argparse

from treebuilder import Treebuilder
from supplement import set_variables, get_variables, str_variables
from utils import translate, qtranslate, qsupplement, build

def create_parser():

    parser = argparse.ArgumentParser(
        description="A tool for converting Matlab code to C++")
        # "usage: %prog [options] matlab_file.m"

    parser.add_argument("filename",
            help="File containing valid Matlab code.")

    parser.add_argument("-t", '--tree-view', action="store_true",
            help="View the token tree and some of its attributes")
    parser.add_argument("-s", '--suggestion', action="store_true",
            help="Use suggestions automatically")
    parser.add_argument("-r", '--reset', action="store_true",
            help="Force reset on configuration")
    parser.add_argument("-d", '--disp', action="store_true",
            help="Display process output")
    parser.add_argument("-c", '--comments', action="store_true",
            help="Strip comments from file")
    parser.add_argument("-l", '--line', type=int, dest="line",
            help="Only display single code line")

    return parser


def main(args):

    path = os.path.abspath(args.filename)
    dirname = os.path.dirname(path) + os.path.sep
    os.chdir(dirname)

    if args.disp:
        print "building tree..."

    builder = Treebuilder(dirname, args.disp, args.comments, args.suggestion)

    filenames = [os.path.basename(path)]

    stack = []
    while filenames:

        filename = filenames.pop(0)
        if filename in stack:
            continue

        if args.disp:
            print "loading", filename

        stack.append(filename)

        unassigned = builder.load(filename)
        for i in xrange(len(unassigned)-1, -1, -1):

            if os.path.isfile(unassigned[i] + ".m"):
                unassigned[i] = unassigned[i] + ".m"

            if not os.path.isfile(unassigned[i]):
                # TODO error for unassigned
                del unassigned[i]

        filenames.extend(unassigned)

        if os.path.isfile(filename + ".py") and not args.reset:

            cfg = imp.load_source("cfg", filename + ".py")
            scope = cfg.scope

            types, suggestions = supplement.get_variables(builder.project[-1])
            for name in types.keys():
                if name in scope:
                    for key in scope[name].keys():
                        types[name][key] = scope[name][key]
            supplement.set_variables(builder.project[-1], types)

    if args.disp:
        print "configure tree"

    builder.configure()

    if args.disp:
        print builder.project.summary()
        print "generate translation"

    for program in builder.project[2:]:
        program.translate_tree(args)
    builder.project[0].translate_tree(args)
    builder.project[1].translate_tree(args)

    filename = builder.project[2].name

    library = str(builder.project[0])
    if library:

        if args.disp:
            print "creating library..."

        f = open(filename + ".h", "w")
        f.write(library)
        f.close()

    elif args.reset and os.path.isfile(filename+".h"):
        os.remove(filename+".h")

    errors = str(builder.project[1])
    if errors:

        if args.disp:
            print "creating error-log..."

        f = open(filename + ".log", "w")
        f.write(errors)
        f.close()

    elif args.reset and os.path.isfile(filename+".log"):
        os.remove(filename+".log")


    first = True
    for program in builder.project[2:]:

        types, suggestions = supplement.get_variables(program)
        program["str"] = program["str"].replace("__percent__", "%")

        annotation = supplement.str_variables(types, suggestions)

        filename = program.name
        f = open(filename + ".py", "w")
        f.write(annotation)
        f.close()

        if args.disp:
            print "writing translation..."

        f = open(filename + ".cpp", "w")
        f.write(str(program))
        f.close()

        if os.path.isfile(filename+".pyc"):
            os.remove(filename+".pyc")

        if first:

            first = False

            if args.tree_view:
                print utils.node_summary(builder.project, args)
            elif args.line:
                nodes = utils.flatten(program, False, False, False)
                for node_ in nodes:
                    if node_.line == args.line and node_.cls != "Block":
                        print node_["str"]
                        break
            else:
                print program["str"]

