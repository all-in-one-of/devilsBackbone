#! /bin/python2.7
import asyncore
import collections
import dispatch
import logging
import socket
import tempfile
import os.path as path
import threading


class Identity:

    def __init__(self, address, socket):
        self.address = address
        self.socket = socket


class RemoteClient(dispatch.Dispatcher):

    def __init__(self, host, socket, address, name=None):
        self.lock = threading.Lock()
        self.sendLock = threading.Lock()
        self.ac_in_buffer_size = 4096
        self.ac_out_buffer_size = 4096
        dispatch.Dispatcher.__init__(self, socket)
        self.host = host
        self.identity = Identity(address, socket)
        self.inbox = collections.deque()
        self.outbox = str()
        self.name = name
        self.set_terminator(';_term_;')

    def say(self, msg):
        self.push(msg)

    def collect_incoming_data(self, data):
        self.inbox.append(data)

    def found_terminator(self):
        self.lock.acquire()
        try:
            tmp = self.inbox
            self.outbox = ''.join(tmp)
            self.inbox.clear()
            self.processData()
        finally:
            self.lock.release()

    def processData(self):
        client_message = self.outbox
        self.outbox = str()
        client_message = client_message.strip(';_term_;')

        if (str(client_message).startswith('/') or
                str(client_message).startswith('->') or
                str(client_message).startswith('|^|')):
            self.handle_command(client_message)

        else:
            self.host.broadcastToOthers(self.identity, '{0} said {1}'.
                                        format(self.name, client_message))

    def handle_command(self, client_message):
        if str(client_message).startswith('/name'):
            args = str(client_message).split(' ', 1)[1]
            self.name = args.split('|__|')[0]

            args = '/createUser {0}|__|{1};_term_;'.format(
                self.name,
                args.split('|__|')[1])

            self.host.broadcastCommandToOthers(self.identity.address, args)

            self.host.requestUsers(self.identity)
            self.host.publish(self.identity)
            return

        elif str(client_message).startswith('/'):
            self.host.broadcastCommandToOthers(
                self.identity.address, client_message + ';_term_;')

        elif str(client_message).startswith('|^|'):
            message = client_message.split('|__|')
            addr = str(self.identity.address)
            message.append(addr)
            client_message = '|__|'.join(message)
            self.host.broadcastCommandToOthers(
                self.identity.address, client_message + ';_term_;')

        elif str(client_message).startswith('->'):
            msg = client_message[2:]
            add, message = msg.split(' ', 1)
            address = (add.split('|__|')[0], int(add.split('|__|')[1]))
            sender = str(self.identity.address)
            args = message.split('|__|')
            args.append(sender)
            message = '|__|'.join(args)
            self.host.publishToUser(address, message)


class Host(asyncore.dispatcher):

    logging.basicConfig(filename=path.join(tempfile.gettempdir(),
                        'server.log'), level=logging.INFO)

    log = logging.getLogger('Host')

    def __init__(self, address=('', 80)):
        # self.log.propagate = False
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.listen(True)
        self.remote_clients = dict()

    def handle_accept(self):
        socket, addr = self.accept()
        self.log.info('Accepted client at {0}'.format(addr))
        self.remote_clients[addr] = RemoteClient(self, socket, addr)

    def broadcast(self, message):
        self.log.info('Broadcasting message: {0}'.format(message))
        for remoteClient in self.remote_clients.values():
            remoteClient.say(message)

    def broadcastCommand(self, cmd, message):
        self.log.info('Broadcasting command: {0}, message: {1}'.
                      format(cmd, message))
        for remoteClient in self.remote_clients.values():
            remoteClient.say('/{0} {1}'.format(cmd, message))

    def broadcastToOthers(self, address, message):
        self.log.info('Broadcasting to others: {0}'.format(message))
        for remoteClient in self.remote_clients.values():
            if remoteClient.identity is address:
                continue
            remoteClient.say(message)

    def publishToUser(self, address, message):
        self.log.info('Publishing to address {0}, with message {1}'.
                      format(address, message))
        self.sendToAddress(address, message + ';_term_;')

    def sendToAddress(self, address, message):
        self.log.info('Sending data {0} to address: {1}'.
                      format(message, address))
        for remoteClient in self.remote_clients.values():
            if remoteClient.identity.address == address:
                self.log.info('Client {0} found.'.format(address))
                remoteClient.say(message)

    def broadcastCommandToOthers(self, address, cmd):
        self.log.info('Broadcasting command to others: {0}'.format(cmd))
        for remoteClient in self.remote_clients.values():
            if remoteClient.identity.address == address:
                continue
            remoteClient.say(cmd)

    def requestUsers(self, identity):
        self.log.info('Requesting user data from other clients.')
        cmd = '/fullRequest {0}|__|{1};_term_;'.format(identity.address[0],
                                                       identity.address[1])
        self.broadcastCommandToOthers(identity.address, cmd)

    def publish(self, identity):
        self.log.info('Publishing data to other clients.')
        cmd = '/fullPublish {0}|__|{1};_term_;'.format(identity.address[0],
                                                       identity.address[1])
        self.sendToAddress(identity.address, cmd)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info('Creating host')
    host = Host(address=('', 5001))
    logging.info('Loop starts')
    try:
        asyncore.loop()
    except:
        logging.info('Quitting the loop.')
