'''
Copyright (c) 2013, Nikola Wuttke
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the Project nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

import asyncore
import collections


class Dispatcher(asyncore.dispatcher):

    def __init__(self, socket=None):
        self.ac_in_buffer_size = 8192
        self.ac_out_buffer_size = 8192
        asyncore.dispatcher.__init__(self, socket)
        self.queue = collections.deque()
        self.buf = collections.deque()
        self.msg = str()
        self.currentMsg = str()
        self.terminator = None
        self.lastMessage = str()

    def set_terminator(self, term):
        self.terminator = term

    def found_terminator(self):
        raise NotImplementedError('Please implement found_terminator.')

    def collect_incoming_data(self, data):
        raise NotImplementedError('Please implement collect_incoming_data.')

    def readable(self):
        return 1

    def writable(self):
        return self.currentMsg != '' or self.msg != '' or (not self.connected)

    def handle_read(self):
        msg = self.recv(self.ac_in_buffer_size)
        self.lastMessage += msg

        while self.lastMessage:
            lt = len(self.terminator)
            index = self.lastMessage.find(self.terminator)
            if index != -1:
                if index > 0:
                    self.collect_incoming_data(self.lastMessage[:index])
                self.lastMessage = self.lastMessage[index + lt:]
                self.found_terminator()
            else:
                self.collect_incoming_data(self.lastMessage[:-lt])
                self.lastMessage = self.lastMessage[-lt:]
                break

    def handle_write(self):
        self._send()

    def handle_close(self):
        # raise asyncore.ExitNow('Client is done.')
        self.close()

    def close_when_done(self):
        self.queue.append(None)
        if self.currentMsg == str():
            self._send()

    def _prepareSend(self):
        if self.currentMsg == str():
            bSize = self.ac_out_buffer_size
            try:
                self.currentMsg = self.queue.popleft()
                if self.currentMsg is None:
                    self.handle_close()
                    return False
                for i in xrange(0, len(self.currentMsg), bSize):
                    self.buf.append(self.currentMsg[i:i + bSize])
            except:
                return
        return

    def _send(self):
        if self.msg == str():
            try:
                self.msg = self.buf.popleft()
            except:
                self.currentMsg = str()
                self._prepareSend()
                try:
                    self.msg = self.buf.popleft()
                except:
                    return

        length = self.send(self.msg)
        self.msg = self.msg[length:]

    def push(self, data):
        self.queue.append(data)
        if self.currentMsg == str():
            self._prepareSend()
            self._send()
