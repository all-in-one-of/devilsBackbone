'''
Copyright (c) 2013, Nikola Wuttke
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the Project nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

import zlib
import binascii
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
        path = os.path.join(hou.expandString('$HOUDINI_TEMP_DIR'),
                            'SOP_copy.cpio')
        f = open(path, 'rb')
        data = f.read()
        f.close()
        zData = binascii.b2a_base64(zlib.compress(data, 9))
        nodeId = node.userData('uuid')
        parentId = node.parent().userData('uuid')
        return (nodeId, parentId, zData, str(outputData))

    def pasteBinary(self, rawData):
        data = zlib.decompress(binascii.a2b_base64(rawData))

        path = os.path.join(hou.expandString('$HOUDINI_TEMP_DIR'),
                            'SOP_copy.cpio')
        f = open(path, 'wb')
        f.write(data)
        f.close()

    def packOtl(self, path):
        f = open(path, 'rb')
        data = f.read()
        f.close()

        data = zlib.compress(data, 9)
        return binascii.b2a_base64(data)

    def saveOtl(self, data):
        path = tempfile.mkstemp(suffix='.otl')[1]
        f = open(path, 'wb')
        data = binascii.a2b_base64(data)
        f.write(zlib.decompress(data))
        f.close()
        return path
