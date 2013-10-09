import threading


def p(**k):
    node = k['child_node']
    t = threading.Thread(target=test, args=(node,))
    t.start()


def test(node):
    node.cook(True)
    print node.creatorState()
