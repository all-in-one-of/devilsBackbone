import uuid
import hou
import cPickle


def generateBookKeeper():
    allNodes = hou.node('/').recursiveGlob('*')
    bookKeeper = hou.node('/obj').createNode('subnet', 'bookkeeper')
    booking = dict()

    for node in allNodes:
        id = node.userData('uuid')
        if id is None:
            id = generateUUID(node)

        booking[id] = node.path()
        bind(node)

    bookKeeper.setUserData('booking', cPickle.dumps(booking))


def addBooking(node):
    booking = loadBook()
    id = generateUUID(node)
    booking[id] = node.path()
    bookKeeper.setUserData('booking', cPickle.dumps(booking))


def loadBook():
    bookKeeper = hou.node('/obj/bookkeeper')
    return cPickle.loads(bookKeeper.userData('booking'))


def storeBook(booking):
    bookKeeper = hou.node('/obj/bookkeeper')
    bookKeeper.setUserData('booking', cPickle.dumps(booking))


def removeBooking(node):
    id = getID(node)
    booking = loadBook()
    booking.remove(id)


def bind(node):
    node.addEvent((hou.nodeEventType.ChildCreated,), childNodeCreated)
    node.addEvent((hou.nodeEventType.ChildDeleted,), childNodeDeleted)
    node.addEvent((hou.nodeEventType.InputRewired,), inputRewired)
    node.addEvent((hou.nodeEventType.ParmTupleChanged,), parmChanged)
    node.addEvent((hou.nodeEventType.FlagChanged,), viewChange)
    node.addEvent((hou.nodeEventType.NameChanged,), renameNode)


def generateUUID(node, id=None):
    if id is None:
        id = uuid.uuid4().hex
    node.setUserData('uuid', id)
    return id


def getID(node):
    return node.userData('uuid')


def childNodeCreated(**kwargs):
    node = kwargs['node']
    newNode = kwargs['child_node']
    addBooking(newNode)
    bind(newNode)

    client.sendCommand('create', (getID(node), getID(newNode), newNode.type()))

    print kwargs


def childNodeDeleted(**kwargs):
    print kwargs


def renameNode(**kwargs):
    print kwargs


def viewChange(**kwargs):
    print kwargs


def parmChanged(**kwargs):
    print kwargs


def inputRewired(**kwargs):
    print kwargs
