# import zlib
import hou
# import hashlib
import client


class BinaryHandler:
    _binaryNodes = ['edit', 'paint', 'sculpt']

    def __init__(self, node):
        if node.type().name() not in BinaryHandler._binaryNodes:
            return

        self.node = node
        self.client = client.getClient()
        hou.copyNodesToClipboard((node,))
        f = open(hou.expandString('$TEMP/SOP_copy.cpio'), 'rb')
        data = f.read()
        f.close()
        nodeId = node.userData('uuid')
        parentId = node.parent().userData('uuid')
        args = (nodeId, parentId, data)
        self.client('pasteBinary', args)
