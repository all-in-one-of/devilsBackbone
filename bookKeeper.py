import uuid
import ast
import hou
import cPickle
import client
import asyncore


class NetworkManager:

    def __init__(self, address, port, name):
        if hou.node('/obj/bookkeeper') is None:
            self.generateBookKeeper()

        self.globalDict = dict()
        self.globalDict['obj'] = self.getID(hou.node('/obj'))
        self.globalDict['ch'] = self.getID(hou.node('/ch'))
        self.globalDict['vex'] = self.getID(hou.node('/vex'))
        self.globalDict['shop'] = self.getID(hou.node('/shop'))
        self.globalDict['img'] = self.getID(hou.node('/img'))
        self.globalDict['part'] = self.getID(hou.node('/part'))
        self.globalDict['out'] = self.getID(hou.node('/out'))
        self._changedParmTuple = list()

        self.client = client.Client((address, port), name, self)
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

    def addBooking(self, node, id=None):
        booking = self.loadBook()
        id = self.generateUUID(node, id)
        booking[id] = node.path()
        self.storeBook(booking)

    def loadBook(self):
        bookKeeper = hou.node('/obj/bookkeeper')
        return cPickle.loads(bookKeeper.userData('booking'))

    def storeBook(self, booking):
        bookKeeper = hou.node('/obj/bookkeeper')
        bookKeeper.setUserData('booking', cPickle.dumps(booking))

    def getNode(self, id):
        booking = self.loadBook()
        path = booking.get(id)
        if path is None:
            return None

        return hou.node(path)

    def removeBooking(self, node):
        id = self.getID(node)
        booking = self.loadBook()
        del booking[id]
        self.storeBook(booking)

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

    def partialBind(self, node):
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
        self.addBooking(newNode)
        # newNode.isInsideLockedHDA() seems to borken.
        if newNode.type().definition() is None:
            self.bind(newNode)
        else:
            self.partialBind(newNode)

        self.client.sendCommand('create',
                               (self.getID(node), self.getID(newNode),
                                newNode.type().name()))

    def childNodeDeleted(self, **kwargs):
        node = kwargs['child_node']
        id = self.getID(node)
        self.removeBooking(node)
        self.client.sendCommand('delete', id)

    def renameNode(self, **kwargs):
        pass  # print kwargs

    def viewChange(self, **kwargs):
        pass  # print kwargs

    def parmChanged(self, **kwargs):
        parm = kwargs['parm_tuple']
        if parm is None:
            print kwargs
            return

        node = parm.node()
        id = self.getID(node)
        value = str(parm.eval())
        args = (id, parm.name(), value)
        self.client.sendCommand('changeParm', args)

    def inputRewired(self, **kwargs):
        node = kwargs['node']
        input = kwargs['input_index']

        if len(node.inputs()) == 0:
            newInput = 'None'
            outIndex = 0
            args = (self.getID(node), newInput,
                    str(input), str(outIndex))
        else:
            newInput = node.inputs()[input]
            if newInput is None:
                newInput = 'None'
                outIndex = 0
            else:
                outIndex = newInput.outputs().index(node)
                newInput = self.getID(newInput)

            args = (self.getID(node), newInput,
                    str(input), str(outIndex))

        self.client.sendCommand('rewire', args)

    def rewire(self, args):
        node = self.getNode(args[0])
        inputNode = args[1]
        inIndex = int(args[2])
        outIndex = int(args[3])

        if inputNode == 'None':
            node.setInput(inIndex, None)
            return

        inputNode = self.getNode(inputNode)
        node.setInput(inIndex, inputNode, outIndex)

    def changeParm(self, args):
        id = args[0]
        parmName = args[1]
        if 'hou.Ramp' in args[2]:
            return
        value = ast.literal_eval(args[2])
        node = self.getNode(id)

        node.parmTuple(parmName).set(value)

    def create(self, args):
        parentID = args[0]
        nodeID = args[1]
        nodeType = args[2]
        booking = self.loadBook()
        parentNode = hou.node(booking[parentID])
        if parentNode is None:
            raise Exception('Something went really wrong.')
        self.addBooking(parentNode.
                        createNode(nodeType, run_init_scripts=False), nodeID)

    def push(self, args):
        pass  # print args

    def pull(self, args):
        print args

    def delete(self, args):
        id = args[0]
        node = self.getNode(id)
        self.removeBooking(node)
        node.destroy()

    def rebuild(self, args):
        user = args[0]
        userNode = hou.node('/obj/bookkeeper/{0}'.format(user))
        parentName = args[2]
        hou_node = userNode.node(parentName)
        code = str(args[1]).split('\n')
        revised = '\n'.join(code[2:])
        revised = revised.replace('"img"', '"cop2net"')
        exec(revised)
        self.bookNewNodes(userNode)
        del hou_node

    def bookNewNodes(self, node):
        booking = self.loadBook()
        allNodes = node.recursiveGlob('*')

        for n in allNodes:
            id = self.getID(n)
            booking[id] = n.path()

        self.storeBook(booking)

    def createUser(self, args):
        bookKeeper = hou.node('/obj/bookkeeper')
        refDict = ast.literal_eval(args[1])
        userNode = bookKeeper.createNode('subnet', args[0])
        self.addBooking(userNode)
        self.addBooking(userNode.createNode('subnet', 'obj'), refDict['obj'])
        self.addBooking(userNode.createNode('ropnet', 'out'), refDict['out'])
        self.addBooking(userNode.createNode('chopnet', 'ch'), refDict['ch'])
        self.addBooking(userNode.createNode('cop2net', 'img'), refDict['img'])
        self.addBooking(userNode.createNode('popnet', 'part'), refDict['part'])
        self.addBooking(userNode.createNode('shopnet', 'shop'),
                        refDict['shop'])
        self.addBooking(userNode.createNode('vopnet', 'vex'), refDict['vex'])

    def fullRequest(self, args):
        callArgs = '{0}|__|{1}'.format(self.client.name, str(self.globalDict))
        self.client.sendToUser(args, '/createUser {0}'.
                               format(callArgs))
        topLevelNetwork = hou.node('/').glob('*')
        for node in topLevelNetwork:
            self.client.sendToUser(args, '/rebuild {0}|__|{1}|__|{2}'.
                                   format(self.client.name,
                                          node.asCode(recurse=True),
                                          node.name()))

    def fullPublish(self, args):
        topLevel = hou.node('/').glob('*')
        print 'fullPublish called ', args
        for node in topLevel:
            self.client.sendCommand('rebuild', '{0}|__|{1}|__|{2}'.
                                    format(self.client.name,
                                           node.asCode(recurse=True),
                                           node.name()))
