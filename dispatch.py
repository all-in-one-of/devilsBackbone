import asyncore
import collections


class Dispatcher(asyncore.dispatcher):

    def __init__(self, socket=None):
        self.ac_in_buffer = 4096
        self.ac_out_buffer = 4096
        asyncore.dispatcher.__init__(self, socket)
        self.queue = collections.deque()
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
        return self.queue or (not self.connected)

    def handle_read(self):
        msg = self.recv(self.ac_in_buffer)
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
        self.close()

    def _send(self):
        while self.currentMsg is not str() or len(self.queue) != 0:

            if self.currentMsg == str():
                try:
                    self.currentMsg = self.queue.popleft()
                except:
                    return

            data = buffer(self.currentMsg, 0, self.ac_out_buffer)
            length = self.send(data)
            self.currentMsg = self.currentMsg[length:]
            return

    def push(self, data):
        if len(data) > self.ac_in_buffer:
            for i in xrange(0, len(data), self.ac_out_buffer):
                self.queue.append(data[i:i + self.ac_out_buffer])
        else:
            self.queue.append(data)
        self._send()
