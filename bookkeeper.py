import threading
import uuid
import ast
import hou
import cPickle
import client
import asyncore
import zlib
import re


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
        self.run = True
        self.thread = threading.Thread(target=self.runLoop)
        self.thread.start()

    def close(self):
        self.run = False
        self.thread.join()
        self.client.close()

    def runLoop(self):
        while self.run:
            asyncore.loop(1, count=2)

    def generateBookKeeper(self):
        allNodes = hou.node('/').recursiveGlob('*')
        bookKeeper = hou.node('/obj').createNode('subnet', 'bookkeeper')
        bookKeeper.setSelectableInViewport(False)
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
                              self.flagChange)
        node.addEventCallback((hou.nodeEventType.NameChanged,),
                              self.renameNode)

    def partialBind(self, node):
        node.addEventCallback((hou.nodeEventType.InputRewired,),
                              self.inputRewired)
        node.addEventCallback((hou.nodeEventType.ParmTupleChanged,),
                              self.parmChanged)
        node.addEventCallback((hou.nodeEventType.FlagChanged,),
                              self.flagChange)
        node.addEventCallback((hou.nodeEventType.NameChanged,),
                              self.renameNode)

    def generateUUID(self, node, id=None):
        if id is None:
            id = uuid.uuid4().hex
        node.setUserData('uuid', id)
        return id

    def getID(self, node):
        id = node.userData('uuid')
        if id is None:
            id = self.recoverID(node)
        return id

    def recoverID(self, node):
        booking = self.loadBook()
        searchPath = node.path()
        nodeId = None
        for id, path in booking.items():
            if path == searchPath:
                nodeId = id
                self.generateUUID(node, id)
        if nodeId is None:
            # raise Exception('Node recover failed for node ', node.path())
            pass
        return nodeId

    def childNodeCreated(self, **kwargs):
        node = kwargs['node']
        newNode = kwargs['child_node']
        self.addBooking(newNode)
        nodeType = newNode.type().name()
        # newNode.isInsideLockedHDA() seems to borken.
        if newNode.type().definition() is None:
            self.bind(newNode)
        else:
            self.partialBind(newNode)

        if self.getID(node) is None or self.getID(newNode) is None:
            raise Exception('No id found on node. ',
                            node.name(), newNode.name())

        args = (self.getID(node), self.getID(newNode), nodeType,
                newNode.name())
        self.client.sendCommand('create', args)

    def childNodeDeleted(self, **kwargs):
        node = kwargs['child_node']
        id = self.getID(node)
        self.removeBooking(node)
        self.client.sendCommand('delete', id)

    def renameNode(self, **kwargs):
        node = kwargs['node']
        name = node.name()
        id = self.getID(node)
        self.addBooking(node, id)
        self.updatePaths(node)
        self.client.sendCommand('rename', (id, name))

    def updatePaths(self, node):
        if node.type().definition() is None:
            for n in node.children():
                id = self.getID(n)
                self.addBooking(n, id)
                if len(n.children()) > 0:
                    self.updatePaths(n)

    def rename(self, args):
        node = self.getNode(args[0])
        node.setName(args[1])
        self.addBooking(node, args[0])
        self.updatePaths(node)

    def flagChange(self, **kwargs):
        node = kwargs['node']
        category = node.type().category().name()
        if category == 'Vop':
            return
        flags = list()
        displayFlag = str(node.isDisplayFlagSet())
        flags.append(displayFlag)
        if category == 'Sop':
            renderFlag = str(node.isRenderFlagSet())
            bypassFlag = str(node.isBypassed())
            flags.append(renderFlag)
            flags.append(bypassFlag)
        id = self.getID(node)
        args = [id, category]
        args.extend(flags)
        self.client.sendCommand('flagChanged', tuple(args))

    def flagChanged(self, args):
        node = self.getNode(args[0])
        category = args[1]
        flag = True if args[2] == 'True' else False
        node.setDisplayFlag(flag)
        if category == 'Sop':
            flag = True if args[3] == 'True' else False
            node.setRenderFlag(flag)
            flag = True if args[4] == 'True' else False
            node.bypass(flag)

    def parmChanged(self, **kwargs):
        parm = kwargs['parm_tuple']

        if parm is None:
            return

        self.cleanReferences(parm)
        value = list()
        for p in parm:
            if len(p.keyframes()) > 0:
                value.append('k')
                tmp = str([k.asCode() for k in p.keyframes()])
                value.append(tmp)
            elif isinstance(p.eval(), hou.Ramp):
                value.append('r')
                value.append(p.asCode())
            elif isinstance(p.eval(), str):
                value.append('s')
                value.append(p.unexpandedString())
            else:
                value.append('v')
                value.append(str(p.eval()))

        # value = parm.asCode(True)
        node = parm.node()
        id = self.getID(node)
        args = (id, parm.name(), '-_-'.join(value))
        self.client.sendCommand('changeParm', args)

    def cleanExpression(self, expr, node):
        stringIter = re.finditer(r'"/.*"', expr)
        for string in stringIter:
            relPath = '"$' + self.client.name.upper() + string.group(0)[1:]
            expr = expr.replace(string.group(0), relPath)
        return expr

    def handleString(self, parm):
        node = parm.node()
        for p in parm:
            keyframes = p.keyframes()
            if len(p.keyframes()) == 1:
                self.handleKeyframe(p, keyframes, node)
            try:
                oldVal = p.unexpandedString()
                newVal = self.cleanExpression(oldVal, p.node())
                if oldVal == newVal:
                    return
                p.set(newVal)
            except:
                pass

    def handleNonString(self, parm):
        node = parm.node()
        for p in parm:
            keyframes = p.keyframes()
            if len(keyframes) == 1:
                self.handleKeyframe(p, keyframes, node)

    def handleKeyframe(self, p, keyframes, node):
        key = keyframes[0]
        clean = self.cleanExpression(p.expression(), node)
        try:
            key.setExpression(clean)
            p.setKeyframe(key)
        except:
            pass

    def cleanReferences(self, parm):
        parmTemplate = parm.parmTemplate()
        if not parmTemplate.type().name() == 'String':
            self.handleNonString(parm)
            return
        elif not parmTemplate.stringType() == hou.stringParmType.NodeReference:
            self.handleString(parm)
            return
        self.handleNodeRef(parm)

    def handleNodeRef(self, parm):
        node = parm.node()
        for p in parm:
            try:
                if p.unexpandedString().startswith('$'):
                    continue
            except:
                pass
            value = p.eval()
            targetNode = node.node(value)
            if targetNode is None:
                return
            newValue = node.relativePathTo(targetNode)
            if value == newValue:
                return
            p.set(newValue)

    def inputRewired(self, **kwargs):
        node = kwargs['node']
        input = kwargs['input_index']
        nodeId = self.getID(node)
        if nodeId is None:
            raise Exception('Node {0} has no id.'.format(node.path()))
        if len(node.inputConnections()) > 0:
            if input == -1:
                connectors = node.inputConnections()
                input = connectors.index(connectors[input])
            else:
                connectors = node.inputConnectors()[input]
            if len(connectors) == 0:
                args = (nodeId, 'None', str(input), '0')
                self.client.sendCommand('rewire', args)
                return
            for connector in connectors:
                inputNode = self.getID(connector.inputNode())
                inIndex = connector.inputIndex()
                outIndex = connector.outputIndex()
                args = (nodeId, inputNode, str(inIndex), str(outIndex))
                self.client.sendCommand('rewire', args)
            return
        else:
            args = (nodeId, 'None', '0', '0')

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
        hou_node = self.getNode(id)
        parm = hou_node.parmTuple(args[1])
        values = args[2]
        data = values.split('-_-')
        if parm is None:
            return
        self.handleParm(parm, data)

    def handleParm(self, parm, data):
        for i in range(len(parm)):
            switch = data[0]
            del data[0]
            value = data[0]
            del data[0]

            lock = parm[i].isLocked()
            parm[i].lock(False)
            if switch == 'v':
                parm[i].set(int(value) if value.isdigit() else value)
            elif switch == 'r':
                print value
            elif switch == 's':
                parm[i].set(value)
            elif switch == 'k':
                keyframes = ast.literal_eval(value)
                for key in keyframes:
                    hou_keyframe = None
                    exec(key)
                    parm[i].setKeyframe(hou_keyframe)
            parm[i].lock(lock)

    def create(self, args):
        parentID = args[0]
        nodeID = args[1]
        nodeType = args[2]
        name = args[3]
        booking = self.loadBook()
        parentNode = hou.node(booking[parentID])
        hou.setUpdateMode(hou.updateMode.Manual)
        if parentNode is None:
            raise Exception('Something went really wrong.')
        if nodeType == 'vopmaterial':
            newNode = parentNode.createNode(nodeType, name,
                                            run_init_scripts=False)
        else:
            newNode = parentNode.createNode(nodeType, name)
        if newNode.type().category().name() == 'Object':
            newNode.setSelectableInViewport(False)
        hou.setUpdateMode(hou.updateMode.AutoUpdate)
        self.addBooking(newNode, nodeID)

    def push(self, args):
        pass  # print args

    def pull(self, args):
        pass  # print args

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
        oldPath = code[3]
        for i in range(len(code)):
            if code[i].startswith('opadd -e -n img'):
                # code[i] = code[i].rpartition(' ')[0] + ' img'
                code[i] = code[i].replace('img', 'cop2net', 1)
            if code[i] == oldPath:
                code[i] = code[i].replace(oldPath, 'opcf ' + userNode.path())
        revised = '\n'.join(code)
        hou.hscript('source ' + revised)
        # revised = '\n'.join(code[2:])
        # revised = revised.replace('"img"', '"cop2net"')
        # exec(revised)
        del hou_node
        if parentName == 'obj':
            userNode.node('obj/bookkeeper').setDisplayFlag(False)
            userNode.node('obj/ipr_camera').hide(False)
            [n.destroy() for n in userNode.node('obj/bookkeeper').children()]
            for n in userNode.node('obj').children():
                n.setSelectableInViewport(False)
        self.bookNewNodes(userNode)

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
        name = args[0]
        userNode = bookKeeper.createNode('subnet', name)
        userNode.setSelectableInViewport(False)
        self.addBooking(userNode)
        objNode = userNode.createNode('subnet', 'obj')
        objNode.setSelectableInViewport(False)
        self.addBooking(objNode, refDict['obj'])
        self.addBooking(userNode.createNode('ropnet', 'out'), refDict['out'])
        self.addBooking(userNode.createNode('chopnet', 'ch'), refDict['ch'])
        self.addBooking(userNode.createNode('cop2net', 'img'), refDict['img'])
        self.addBooking(userNode.createNode('popnet', 'part'), refDict['part'])
        self.addBooking(userNode.createNode('shopnet', 'shop'),
                        refDict['shop'])
        self.addBooking(userNode.createNode('vopnet', 'vex'), refDict['vex'])
        hou.hscript('setenv {0} = {1}'.format(name.upper(), userNode.path()))

    def fullRequest(self, args):
        callArgs = '{0}|__|{1}'.format(self.client.name, str(self.globalDict))
        self.client.sendToUser(args, '/createUser {0}'.
                               format(callArgs))
        topLevelNetwork = hou.node('/').glob('*')
        for node in topLevelNetwork:
            code = hou.hscript('opscript -r ' + node.path())[0]
            # node.asCode(recurse=True)
            self.client.sendToUser(args, '/rebuild {0}|__|{1}|__|{2}'.
                                   format(self.client.name,
                                          code, node.name()))

    def fullPublish(self, args):
        topLevel = hou.node('/').glob('*')
        for node in topLevel:
            code = hou.hscript('opscript -r ' + node.path())[0]
            # node.asCode(recurse=True)
            self.client.sendCommand('rebuild', '{0}|__|{1}|__|{2}'.
                                    format(self.client.name,
                                           code, node.name()))

    def pasteBinary(self, args):
        nodeId = args[0]
        parentId = args[1]
        data = zlib.decompress(args[2])
        outputs = args[3]
        outputList = ast.literal_eval(outputs)

        f = open(hou.expandString('$TEMP/SOP_copy.cpio'), 'wb')
        f.write(data)
        f.close()

        self.getNode(nodeId).destroy()
        parent = self.getNode(parentId)
        hou.pasteNodesFromClipboard(parent)
        if outputList[0] == 'None':
            return

        node = self.getNode(nodeId)
        for output in outputList:
            outData = ast.literal_eval(output)
            outNode = self.getNode(outData[0])
            outIndex = int(outData[1])
            inIndex = int(outData[2])
            outNode.setInput(inIndex, node, outIndex)
