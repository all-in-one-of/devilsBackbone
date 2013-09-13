import uuid
import hou
import cPickle
import client
import asyncore


class NetworkManager:

    def __init__(self, address, port, name):
        self.client = client.Client((address, port), name, self)
        if hou.node('/obj/bookkeeper') is None:
            self.generateBookKeeper()

        asyncore.loop()

    def generateBookKeeper(self):
        allNodes = hou.node('/').recursiveGlob('*')
        bookKeeper = hou.node('/obj').createNode('subnet', 'bookkeeper')
        booking = dict()

        for node in allNodes:
            id = node.userData('uuid')
            if id is None:
                id = self.generateUUID(node)

            booking[id] = node.path()
            self.bind(node)

        bookKeeper.setUserData('booking', cPickle.dumps(booking))

    def addBooking(self, node):
        booking = self.loadBook()
        id = self.generateUUID(node)
        booking[id] = node.path()
        self.storeBook(booking)

    def loadBook(self):
        bookKeeper = hou.node('/obj/bookkeeper')
        return cPickle.loads(bookKeeper.userData('booking'))

    def storeBook(self, booking):
        bookKeeper = hou.node('/obj/bookkeeper')
        bookKeeper.setUserData('booking', cPickle.dumps(booking))

    def removeBooking(self, node):
        id = self.getID(node)
        booking = self.loadBook()
        booking.remove(id)

    def bind(self, node):
        node.addEventCallback((hou.nodeEventType.ChildCreated,),
                              self.childNodeCreated)
        node.addEventCallback((hou.nodeEventType.ChildDeleted,),
                              self.childNodeDeleted)
        node.addEventCallback((hou.nodeEventType.InputRewired,),
                              self.inputRewired)
        node.addEventCallback((hou.nodeEventType.ParmTupleChanged,),
                              self.parmChanged)
        node.addEventCallback((hou.nodeEventType.FlagChanged,),
                              self.viewChange)
        node.addEventCallback((hou.nodeEventType.NameChanged,),
                              self.renameNode)

    def generateUUID(self, node, id=None):
        if id is None:
            id = uuid.uuid4().hex
        node.setUserData('uuid', id)
        return id

    def getID(self, node):
        return node.userData('uuid')

    def childNodeCreated(self, **kwargs):
        node = kwargs['node']
        newNode = kwargs['child_node']
        # newNode.isInsideLockedHDA() seems to borken.
        if newNode.type().definition() is None:
            self.bind(newNode)

        self.addBooking(newNode)
        self.client.sendCommand('create',
                               (self.getID(node), self.getID(newNode),
                                newNode.type().name()))

    def childNodeDeleted(self, **kwargs):
        pass  # print kwargs

    def renameNode(self, **kwargs):
        pass  # print kwargs

    def viewChange(self, **kwargs):
        pass  # print kwargs

    def parmChanged(self, **kwargs):
        pass  # print kwargs

    def inputRewired(self, **kwargs):
        pass  # print kwargs

    def create(self, args):
        pass  # print args

    def push(self, args):
        pass  # print args

    def pull(self, args):
        print args
