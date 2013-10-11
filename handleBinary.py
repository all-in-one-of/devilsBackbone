import zlib
import hou


class BinaryHandler:
    _binaryNodes = ['edit', 'paint', 'sculpt']

    def __init__(self, node, client):
        if node.type().name() not in BinaryHandler._binaryNodes:
            return

        self.node = node
        self.client = client
        outputs = node.outputConnections()
        outputData = list()
        if len(outputs) == 0:
            outputData.append('None')
        else:
            for output in outputs:
                childNode = output.outputNode()
                outIndex = output.outputIndex()
                inIndex = output.inputIndex()
                outputData.append(str((childNode.userData('uuid'),
                                       outIndex, inIndex)))
        hou.copyNodesToClipboard((node,))
        f = open(hou.expandString('$TEMP/SOP_copy.cpio'), 'rb')
        data = f.read()
        f.close()
        zData = zlib.compress(data)
        nodeId = node.userData('uuid')
        parentId = node.parent().userData('uuid')
        args = (nodeId, parentId, zData, str(outputData))
        self.client('pasteBinary', args)
