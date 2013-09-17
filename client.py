import asyncore
import asynchat
import sys
import logging
import socket
import collections


class Client(asynchat.async_chat):

    def __init__(self, host_address, name, manager):
        asynchat.async_chat.__init__(self)
        self.log = logging. getLogger('Client ({0})'.format(name))
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = name
        self.log.info('Connecting to host at {0}'.format(host_address))
        self.connect(host_address)
        self.outbox = str()
        self.inbox = collections.deque()
        self.manager = manager
        self.set_terminator(';')
        self.sendCommand('name', (name, str(manager.globalDict)))

    def found_terminator(self):
        self.outbox = ''.join(self.inbox)
        self.inbox.clear()
        self.processData()

    def collect_incoming_data(self, data):
        self.inbox.append(data)

    def say(self, message):
        self.push(message)
        self.log.info('Enqueued message: {0}'.format(message))

    def sendCommand(self, command, msg):
        if isinstance(msg, tuple):
            msg = '|'.join(msg)
        self.say('/{0} {1};'.format(command, msg))
        self.log.info('Enqueued command: /{0} {1};'.format(command, msg))

    def sendToUser(self, address, command):
        tmpAddress = list(address)
        address = '{0}|{1}'.format(tmpAddress[0], tmpAddress[1])
        self.say('->{0} {1};'.format(address, command))

    def processData(self):
        message = self.outbox

        if str(message).startswith('/') or message.startswith('->'):
            self.handle_command(message)
            return

        sys.stdout.write('Received message: {0}\n'.format(message))
        sys.stdout.write('--> ')
        sys.stdout.flush()

    def handle_command(self, cmd):
        cmds = cmd.split('/', 1)
        cmds = [command for command in cmds if len(command) > 0]
        for cmd in cmds:
            command = cmd.split(' ', 1)[0]
            args = cmd.split(' ', 1)[1].split('|')
            self.call_command(command, args)

    def call_command(self, command, args):
        try:
            call = getattr(self.manager, command)
            call(args)

        except Exception, e:
            print command, args, e


if __name__ == '__main__':
    try:
        client = Client(('127.0.0.1', 5001), sys.argv[1])
        asyncore.loop()
    except:
        client.writeHandler.join()
