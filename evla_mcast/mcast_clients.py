#! /usr/bin/env python

# mcast_clients.py -- P. Demorest, 2015/02
#
# Based on code originally in async_mcast.py by PD and S. Ransom
#
# These classes set up networking, and parse incoming Obs and VCI 
# documents into appropriate data structures.

import os
import struct
import logging
import asyncore, socket
import urllib
from lxml import etree, objectify

_install_dir = os.path.abspath(os.path.dirname(__file__))
_xsd_dir = os.path.join(_install_dir, 'xsd')

_obs_xsd = os.path.join(_xsd_dir,'observe','Observation.xsd')
_obs_parser = objectify.makeparser(schema=etree.XMLSchema(file=_obs_xsd))

_vci_xsd = os.path.join(_xsd_dir,'vci','vciRequest.xsd')
_vci_parser = objectify.makeparser(schema=etree.XMLSchema(file=_vci_xsd))

_ant_xsd = os.path.join(_xsd_dir,'observe','AntennaPropertyTable.xsd')
_ant_parser = objectify.makeparser(schema=etree.XMLSchema(file=_ant_xsd))

class McastClient(asyncore.dispatcher):
    """Generic class to receive the multicast XML docs."""

    def __init__(self, group, port, name=""):
        asyncore.dispatcher.__init__(self)
        self.name = name
        self.group = group
        self.port = port
        addrinfo = socket.getaddrinfo(group, None)[0]
        self.create_socket(addrinfo[0], socket.SOCK_DGRAM)
        self.set_reuse_addr()
        self.bind(('',port))
        mreq = socket.inet_pton(addrinfo[0],addrinfo[4][0]) \
                + struct.pack('=I', socket.INADDR_ANY)
        self.socket.setsockopt(socket.IPPROTO_IP, 
                socket.IP_ADD_MEMBERSHIP, mreq)
        self.read = None
        logging.debug('%s listening on group=%s port=%d' % (self.name,
            self.group, self.port))

    def handle_connect(self):
        logging.debug('connect %s group=%s port=%d' % (self.name, 
            self.group, self.port))

    def handle_close(self):
        logging.debug('close %s group=%s port=%d' % (self.name, 
            self.group, self.port))

    def writeable(self):
        return False

    def handle_read(self):
        self.read = self.recv(100000)
        logging.debug('read ' + self.name + ' ' + self.read)
        try:
            self.parse()
        except Exception as e:
            logging.exception("error handling '%s' message" % self.name)

    def handle_error(self, type, val, trace):
        logging.error('unhandled exception: ' + repr(val))

class ObsClient(McastClient):
    """Receives Observation XML.

    If the controller input is given, the controller.add_obs(obs) method will
    be called for every document received.

    If use_configUrl is true, the VCI will be retrieved from the url given
    in the Observation document, parsed, and controller.add_vci(vci) will
    be called if a controller exists.
    """

    def __init__(self,controller=None,use_configUrl=False):
        McastClient.__init__(self,'239.192.3.2',53001,'obs')
        self.controller = controller
        self.use_configUrl = use_configUrl

    def parse(self):
        obs = objectify.fromstring(self.read,parser=_obs_parser)
        logging.info("read obs configId='%s' seq=%s" % (obs.attrib['configId'],
            obs.attrib['seq']))
        logging.debug('Obs data structure:\n' + objectify.dump(obs))
        if self.use_configUrl:
            url = obs.attrib['configUrl']
            logging.info("retrieve vci from '%s'" % url)
            try:
                vciread = urllib.urlopen(url).read()
                logging.debug('retrieved vci ' + vciread)
                vci = objectify.fromstring(vciread,parser=_vci_parser)
                logging.debug('VCI data structure:\n' + objectify.dump(vci))
                if self.controller is not None:
                    self.controller.add_vci(vci)
            except Exception as e:
                logging.exception("error retrieving VCI from '%s'" % url)
        if self.controller is not None:
            self.controller.add_obs(obs)

class VCIClient(McastClient):
    """Receives VCI and AntennaProperties XML.
    
    If the controller input is given, the controller.add_vci(vci) method will
    be called for every document received.
    """

    def __init__(self,controller=None):
        McastClient.__init__(self,'239.192.3.1',53000,'vci')
        self.controller = controller

    def parse(self):

        # VCI and AntennaProperties come via the same multicast channel
        # for some reason.  First try parsing this as a VCI, then 
        # try as an AntennaProperties doc.
        result = None
        for parser in (_vci_parser, _ant_parser):
            try:
                result = objectify.fromstring(self.read,parser=parser)
            except etree.XMLSyntaxError:
                pass

        if result is None:
            logging.info("read an unrecognized message, ignoring.")
        else:
            # Figure out which type of message we got
            if hasattr(result, 'stationInputOutput'):
                logging.info("read vci configId='%s'" % 
                        result.attrib['configId'])
                # TODO probably remove this since vci is not multicast now..
                #if self.controller is not None:
                #    self.controller.add_vci(result)
            elif hasattr(result, 'AntennaProperties'):
                logging.info("read ant datasetId='%s'" % 
                        result.attrib['datasetId'])
                if self.controller is not None:
                    self.controller.add_ant(result)

        logging.debug('VCI/Ant data structure:\n' + objectify.dump(result))


# This is how these would be used in a program.  Note that no controller
# is passed, so the only action taken here is to print log messages when
# each XML document comes in.
if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)-15s %(levelname)8s %(message)s",
            level=logging.DEBUG)
    vci_client = VCIClient()
    obs_client = ObsClient(use_configUrl=True)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        # Just exit without the trace barf on control-C
        logging.info('got SIGINT, exiting')