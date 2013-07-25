#!/usr/bin/env python

# This script interprets the test output from a buildtest

from __future__ import print_function
import sys

GTESTPASS = '[       OK ]'
GTESTFAIL = '[  FAILED  ]'
PNOSEFAIL = 'FAIL: '

def interpret_tests(fname):

    # Try to open file
    try:
        buildoutput = open(fname).readlines()
    except:
        # Larger outputs are compressed in bz2
        import bz2
        buildoutput = bz2.BZ2File(fname+'.bz2').readlines()

    # Metrics
    gtest_pass = list()
    gtest_fail = list()
    pnose_fail = list()
    pnose_total = 0 # can only count these?
    
    in_tests = False
    for line in buildoutput:
        # continue until we get to 'make run_tests'
        if not in_tests:
            if line.find('make run_tests') > -1:
                in_tests = True
            else:
                continue

        # A line with I: indicates our test running is done
        #  and things are getting cleaned up
        if line.find('I:') > -1:
            break

        # This is part of the tests, echo to our own log for ease of developer
        print(line.rstrip())

        # Is this a gtest pass?
        if line.find(GTESTPASS) > -1:
            name = line[line.find(GTESTPASS)+len(GTESTPASS)+1:].split(' ')[0]
            gtest_pass.append(name)
        # How about a gtest fail?
        if line.find(GTESTFAIL) > -1:
            name = line[line.find(GTESTFAIL)+len(GTESTPASS)+1:].split(' ')[0]
            gtest_fail.append(name)
        # pnose fail?
        if line.find(PNOSEFAIL) > -1:
            name = line.split(' ')[2].rstrip()
            pnose_fail.append(name)
        # is this our total for python?
        if line.find('Ran ') > -1:
            pnose_total += int(line.split(' ')[1])

    # determine if we failed
    passed = len(gtest_pass) + pnose_total - len(pnose_fail)
    failed = len(gtest_fail) + len(pnose_fail)
    if failed > 0:
        s = 'Failed '+str(failed)+' of '+str(passed+failed)+' tests.'
        print('*'*len(s))
        print(s)
        for test in gtest_fail + pnose_fail:
            print('  failed: '+test)
        exit(-1)
    else:
        print('Passed '+str(passed)+' tests.')

if __name__=="__main__":
    if len(sys.argv) < 3:
        print('')
        print('Usage: buildtest_interpret.py tests <file>')
        print('')
        exit(-1)
    interpret_tests(sys.argv[2])
