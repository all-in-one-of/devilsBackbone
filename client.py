import asynchat
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
        self.set_terminator(';__;')
        self.sendCommand('name', (name, str(manager.globalDict)))

    def close(self):
        self.log.info('Closing session.')
        self.close_when_done()

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
            msg = '|__|'.join(msg)
        self.say('/{0} {1};__;'.format(command, msg))

    def sendToUser(self, address, command):
        tmpAddress = list(address)
        address = '{0}|__|{1}'.format(tmpAddress[0], tmpAddress[1])
        self.say('->{0} {1};__;'.format(address, command))

    def processData(self):
        message = self.outbox

        if str(message).startswith('/'):
            self.handle_command(message)
            return

        self.log.info('Received message: {0}\n'.format(message))
        self.log.info('--> ')

    def handle_command(self, cmd):
        cmds = cmd.split('/', 1)
        cmds = [command for command in cmds if len(command) > 0]
        for cmd in cmds:
            command = cmd.split(' ', 1)[0]
            args = cmd.split(' ', 1)[1].split('|__|')
            self.call_command(command, args)

    def call_command(self, command, args):
        try:
            call = getattr(self.manager, command)
            call(args)

        except Exception, e:
            print command, args, e
