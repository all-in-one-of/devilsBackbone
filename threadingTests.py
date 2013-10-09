import threading
import hdefereval


def p(**k):
    node = k['child_node']
    t = threading.Thread(target=test, args=(node,))
    t.start()


def k(**k):
    node = k['child_node']
    hdefereval.executeDefered(test, node)


def test(node):
    node.cook(True)
    state = node.creatorState()
    if state == '':
        print 'Not created from gallery.'
    else:
        print state
