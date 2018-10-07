import trio
import socket
import sys
from lxml import etree, objectify

_obs_xsd = '/home/cbe-master/realfast/soft/evla_mcast/evla_mcast/xsd/observe/Observation.xsd'
_obs_parser = objectify.makeparser(schema=etree.XMLSchema(file=_obs_xsd)) 

async def receiver(client_stream):
    print("receiver: started!")
    while True:
        data = await client_stream.receive_some(10000)
        obs = objectify.fromstring(data, parser=_obs_parser)
        print("Read obs configId={0}, seq={1}".format(obs.attrib['configId'], obs.attrib['seq']))
        if not data:
            print("receiver: connection closed")
            sys.exit()


async def listen(group, port):
    addrinfo = socket.getaddrinfo(group, None)[0]
    mreq = socket.inet_pton(addrinfo[0], addrinfo[4][0]) + struct.pack('=I', socket.INADDR_ANY)
    s0 = trio.socket.socket(family=addrinfo[0], type=socket.SOCK_DGRAM)
    print(type(s0))
    stream = await trio.SocketStream(s0)
    s0.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    async with stream:
        async with trio.open_nursery() as nursery:
            print("Starting receiver")
            nursery.start_soon(receiver, stream)

trio.run(listen, '239.192.3.2', 53001)
