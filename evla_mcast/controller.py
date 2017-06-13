# controller.py -- P. Demorest 2017/05

import logging
import asyncore

from . import mcast_clients
from .scan_config import ScanConfig

class Controller(object):

    def __init__(self):
        self.obs_client = mcast_clients.ObsClient(self)
        self.ant_client = mcast_clients.AntClient(self)
        self.scans = {} # lists of scans per datasetId
        self.vci = {}
        self.ant = {}

    def run(self):
        try:
            asyncore.loop()
        except KeyboardInterrupt:
            logging.info('got SIGINT, exiting.')

    def add_obs(self,obs):
        dsid = obs.attrib['datasetId']
        cfgid = obs.attrib['configId']
        config = ScanConfig(obs=obs,vci=self.vci[cfgid])
        if dsid not in self.scans.keys():
            self.scans[dsid] = []
        if dsid in self.ant.keys():
            config.set_ant(self.ant[dsid])
        self.scans[dsid].append(config)
        nscan = len(self.scans[dsid])
        if nscan>1:
            # Set the stop time of the previous scan to the start time
            # of the new scan.  This implicitly assumes the list of
            # scans is in time order.  We might want to add a sort
            # to ensure this is true.  The only time things get confusing
            # is at the start of an observation where two Obs docs
            # come out ~simultaneously.
            if self.scans[dsid][nscan-2].stopTime is not None:
                logging.warning(
                        'previous scan %s already has a stopTime' % (
                            config.scanId))
            self.scans[dsid][nscan-2].stopTime = config.startTime
        logging.info('got %s scan for %s' % (config.scan_intent, config.scanId))
        self.handle_config(config)

    def add_vci(self,vci):
        self.vci[vci.attrib['configId']] = vci

    def add_ant(self,ant):
        self.ant[ant.attrib['datasetId']] = ant

    def handle_config(self,config):
        # Implement in derived class..
        pass
