import asyncore
import logging
import socket
import collections
from threading import Thread


MAX_MESSAGE_LENGTH = 1024


class Client(asyncore.dispatcher):

    def __init__(self, host_address, name):
        asyncore.dispatcher.__init__(self)
        self.log = logging. getLogger('Client ({0})'.format(name))
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = name
        self.log.info('Connecting to host at {0}'.format(host_address))
        self.connect(host_address)
        # self.say('/name {0}'.format(name))
        self.outbox = collections.deque()
        self.writeHandler = Thread(target=self.wait_for_message)
        self.writeHandler.start()

    def wait_for_message(self):
        while True:
            msg = raw_input('--> ')
            if msg == '/quit':
                self.close()
                return
            else:
                self.say(msg)

    def say(self, message):
        self.outbox.append(message)
        self.log.info('Enqueued message: {0}'.format(message))

    def handle_write(self):
        if not self.outbox:
            return

        message = self.outbox.popleft()
        if len(message) > MAX_MESSAGE_LENGTH:
            raise ValueError('Message too long')
        self.send(message)

    def handle_read(self):
        message = self.recv(MAX_MESSAGE_LENGTH)
        self.log.info('Received message: {0}'.format(message))


if __name__ == '__main__':
    client = Client(('127.0.0.1', 5001), 'Niki')
    try:
        asyncore.loop()
    except:
        client.writeHandler.join()
