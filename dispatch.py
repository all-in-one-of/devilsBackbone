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

    def set_terminator(self, term):
        self.terminator = term

    def found_terminator(self):
        raise NotImplementedError('Please implement found_terminator.')

    def collect_incoming_data(self, data):
        raise NotImplementedError('Please implement collect_incoming_data.')

    def handle_read(self):
        msg = self.recv(self.ac_in_buffer)

        if self.terminator in msg:
            mesgs = msg.split(self.terminator)
            for m in mesgs:
                self.collect_incoming_data(m)
                self.found_terminator()
        else:
            self.collect_incoming_data(msg)

    def handle_write(self):
        if self.currentMsg is str() and len(self.queue) == 0:
            return

        if self.currentMsg == str():
            self.currentMsg = self.queue.popleft()

        length = self.send(self.currentMsg)
        self.currentMsg = self.currentMsg[length:]

    def push(self, data):
        self.queue.append(data)

    def handle_close(self):
        self.close()
