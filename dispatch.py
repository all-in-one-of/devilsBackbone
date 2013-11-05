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
        bSize = self.ac_out_buffer_size
        if self.currentMsg == str():
            try:
                self.currentMsg = self.queue.popleft()
                if self.currentMsg is None:
                    self.handle_close()
                    return False
                for i in xrange(0, len(self.currentMsg), bSize):
                    self.buf.append(self.currentMsg[i:i + bSize])
            except:
                return False
        return True

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

        # length = self.send(self.currentMsg)
        # self.currentMsg = self.currentMsg[length:]
        return

    def push(self, data):
        self.queue.append(data)
        if self.currentMsg == str():
            self._prepareSend()
            self._send()
