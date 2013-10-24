import asyncore
import collections


class Dispatcher(asyncore.dispatcher):

    def __init__(self, socket=None):
        self.ac_in_buffer = 4096
        self.ac_out_buffer = 4096
        asyncore.dispatcher.__init__(self, socket)
        self.queue = collections.deque()
        self.currentMsg = str()
        self.terminator = 0
        self.lastMessage = str()

    def set_terminator(self, term):
        self.terminator = term

    def found_terminator(self):
        raise NotImplementedError('Please implement found_terminator.')

    def collect_incoming_data(self, data):
        raise NotImplementedError('Please implement collect_incoming_data.')

    def handle_read(self):
        msg = self.recv(self.ac_in_buffer)
        self.lastMessage += msg

        if self.terminator in self.lastMessage:
            mesgs = self.lastMessage
            while self.terminator in mesgs:
                m = mesgs.split(self.terminator, 1)
                self.collect_incoming_data(m[0])
                self.found_terminator()
                mesgs = m[1]
            self.lastMessage = mesgs

    def handle_write(self):
        pass

    def handle_close(self):
        self.close()

    def _send(self):
        while self.currentMsg is not str() or len(self.queue) != 0:

            if self.currentMsg == str():
                try:
                    self.currentMsg = self.queue.popleft()
                except:
                    return

            if self.currentMsg is None:
                # self.handle_close()
                return

            length = self.send(self.currentMsg)
            self.currentMsg = self.currentMsg[length:]

    def push(self, data):
        if len(data) > self.ac_in_buffer:
            for i in xrange(0, len(data), self.ac_out_buffer):
                self.queue.append(data[i:i + self.ac_out_buffer])
        else:
            self.queue.append(data)
        self._send()
