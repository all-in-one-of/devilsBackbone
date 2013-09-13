import asyncore
import sys
import logging
import socket
import collections
from threading import Thread


MAX_MESSAGE_LENGTH = 4096


class Client(asyncore.dispatcher):

    def __init__(self, host_address, name, manager):
        asyncore.dispatcher.__init__(self)
        self.log = logging. getLogger('Client ({0})'.format(name))
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = name
        self.log.info('Connecting to host at {0}'.format(host_address))
        self.connect(host_address)
        self.outbox = collections.deque()
        self.writeHandler = Thread(target=self.wait_for_message)
        self.writeHandler.start()
        self.sendCommand('name', name)
        self.manager = manager

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

    def sendCommand(self, command, msg):
        if isinstance(msg, tuple):
            msg = '|'.join(msg)
        self.outbox.append('/{0} {1}'.format(command, msg))
        self.log.info('Enqueued command: /{0} {1}'.format(command, msg))

    def handle_write(self):
        if not self.outbox:
            return

        message = self.outbox.popleft()
        if len(message) > MAX_MESSAGE_LENGTH:
            raise ValueError('Message too long')
        self.send(message)

    def handle_read(self):
        message = self.recv(MAX_MESSAGE_LENGTH)

        if str(message)[0] == '/':
            self.handle_command(message)
            return

        sys.stdout.write('Received message: {0}\n'.format(message))
        sys.stdout.write('--> ')
        sys.stdout.flush()

    def handle_command(self, cmd):
        cmds = cmd.split('/')
        cmds = [command for command in cmds if len(command) > 0]
        for cmd in cmds:
            command = cmd.split()[0]
            args = cmd.split()[1].split('|')

            if command == 'create':
                self.manager.create(args)
            elif command == 'createUser':
                self.manager.createUser(args)
            elif command == 'push':
                self.manager.push(args)
            elif command == 'pull':
                self.manager.pull(args)
            else:
                print command, args


if __name__ == '__main__':
    try:
        client = Client(('127.0.0.1', 5001), sys.argv[1])
        asyncore.loop()
    except:
        client.writeHandler.join()
