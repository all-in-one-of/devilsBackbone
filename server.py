import asyncore
import collections
import logging
import socket


MAX_MESSAGE_LENGTH = 8192


class Identity:

    def __init__(self, address, socket):
        self.address = address
        self.socket = socket


class RemoteClient(asyncore.dispatcher):

    def __init__(self, host, socket, address, name=None):
        asyncore.dispatcher.__init__(self, socket)
        self.host = host
        self.identity = Identity(address, socket)
        self.outbox = collections.deque()
        self.name = name

    def say(self, message):
        self.outbox.append(message)

    def handle_read(self):
        client_message = self.recv(MAX_MESSAGE_LENGTH)

        if (str(client_message).startswith('/') or
                str(client_message).startswith('->')):
            self.handle_command(client_message)

        else:
            self.host.broadcastToOthers(self.identity, '{0} said {1}'.
                                        format(self.name, client_message))
        # self.host.broadcast('{0} said {1}'.format(self.name, client_message))

    def handle_command(self, client_message):
        rawMsg = str(client_message).split(';')
        rawMsg = [m for m in rawMsg if len(m) > 0]
        for client_message in rawMsg:
            if str(client_message).startswith('/name'):
                self.name = str(client_message).split()[1]
                args = '/createUser {0}|{1}|{2}'.format(
                    self.name,
                    self.identity.address[0],
                    self.identity.address[1])

                self.host.broadcastCommandToOthers(self.identity, args)

                self.host.requestUsers(self.identity)
                self.host.publish(self.identity)
                return

            elif str(client_message).startswith('/'):
                self.host.broadcastCommandToOthers(
                    self.identity, client_message)

            elif str(client_message).startswith('->'):
                msg = client_message[2:]
                add, message = msg.split(' ', 1)
                address = (add.split('|')[0], int(add.split('|')[1]))
                self.host.publishToUser(address, message)

    def handle_write(self):
        if not self.outbox:
            return

        message = self.outbox.popleft()
        if len(message) > MAX_MESSAGE_LENGTH:
            # raise ValueError('Message too long')
            self.outbox.append(message[MAX_MESSAGE_LENGTH - 1:])
        self.send(message[:MAX_MESSAGE_LENGTH - 1])


class Host(asyncore.dispatcher):

    log = logging.getLogger('Host')

    def __init__(self, address=('localhost', 0)):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.listen(True)
        self.remote_clients = dict()

    def handle_accept(self):
        socket, addr = self.accept()
        self.log.info('Accepted client at {0}'.format(addr))
        self.remote_clients[addr] = RemoteClient(self, socket, addr)

    def handle_read(self):
        self.log.info('Received message: {0}'.format(self.read()))

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
        self.sendToAddress(address, message)

    def sendToAddress(self, address, message):
        self.log.info('Sending data {0} to address: {1}'.
                      format(address, message))
        for remoteClient in self.remote_clients.values():
            if remoteClient.identity.address == address:
                remoteClient.say(message)

    def broadcastCommandToOthers(self, address, cmd):
        self.log.info('Broadcasting command to others: {0}'.format(cmd))
        for remoteClient in self.remote_clients.values():
            if remoteClient.identity is address:
                continue
            remoteClient.say(cmd)

    def requestUsers(self, identity):
        self.log.info('Requesting user data from other clients.')
        cmd = '/fullRequest {0}|{1}'.format(identity.address[0],
                                            identity.address[1])
        self.broadcastCommandToOthers(identity, cmd)

    def publish(self, identity):
        self.log.info('Publishing data to other clients.')
        cmd = '/fullPublish {0}|{1}'.format(identity.address[0],
                                            identity.address[1])
        self.broadcastCommandToOthers(identity, cmd)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info('Creating host')
    host = Host(address=('127.0.0.1', 5001))
    logging.info('Loop starts')
    try:
        asyncore.loop()
    except:
        logging.info('Quitting the loop.')
