def match(string, sep=('[', ']')):
    stack = list()
    for i, c in enumerate(string):
        if c == sep[0]:
            stack.append(i)
        elif c == sep[1] and stack:
            start = stack.pop()
            yield (len(stack), string[start + 1:i])


import threading
import time
import datetime

nextCall = time.time()
inc = 3


def testFun():
    global nextCall
    global inc
    nextCall = nextCall + inc
    print datetime.datetime.now()
    threading.Timer(nextCall - time.time(), testFun).start()

testFun()
