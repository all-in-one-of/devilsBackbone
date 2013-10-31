import zlib
import os
import hou
import tempfile


class BinaryHandler:
    _binaryNodes = ['edit', 'paint', 'sculpt']

    def handleBinary(self, node):
        if node.type().name() not in BinaryHandler._binaryNodes:
            return False

        self.node = node
        if node.path().startswith('/obj/bookkeeper'):
            return False

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
        path = os.path.join(hou.expandString('$HOUDINI_TEMP_DIR'), 'SOP_copy.cpio')
        f = open(path, 'rb')
        data = f.read()
        f.close()
        zData = str(zlib.compress(data, 9))
        nodeId = node.userData('uuid')
        parentId = node.parent().userData('uuid')
        return (nodeId, parentId, zData, str(outputData))

    def pasteBinary(self, rawData):
        data = zlib.decompress(rawData)

        path = os.path.join(hou.expandString('$HOUDINI_TEMP_DIR'), 'SOP_copy.cpio')
        f = open(path, 'wb')
        f.write(data)
        f.close()

    def packOtl(self, path):
        f = open(path, 'rb')
        data = f.read()
        f.close()

        # return str(zlib.compress(data, 9))
        return str(data)

    def saveOtl(self, data):
        path = tempfile.mkstemp(suffix='.otl')[1]
        f = open(path, 'wb')
        f.write(data)
        # f.write(zlib.decompress(data))
        f.close()
        return path
