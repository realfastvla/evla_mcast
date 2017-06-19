# controller.py -- P. Demorest 2017/05

import logging
import asyncore

from . import mcast_clients
from .scan_config import ScanConfig

class Controller(object):

    def __init__(self):
        self.obs_client = mcast_clients.ObsClient(self)
        self.ant_client = mcast_clients.AntClient(self)
        self.queued_scans = {}  # lists of scans per datasetId
        self.handled_scans = {} # lists of scans per datasetId
        self.vci = {} # key is configId
        self.ant = {} # key is datasetId

        # The required info before handle_config is called.
        # Redefine in derived classes as needed
        self.scans_require = ['obs','vci','ant','stop']

    def run(self):
        try:
            asyncore.loop()
        except KeyboardInterrupt:
            logging.info('got SIGINT, exiting.')

    def add_obs(self,obs):
        dsid = obs.attrib['datasetId']
        cfgid = obs.attrib['configId']

        # Generate the scan config object for this scan
        config = ScanConfig(obs=obs, vci=self.vci[cfgid],
                requires=self.scans_require)

        # Init lists if they are not there
        if dsid not in self.queued_scans.keys():
            self.queued_scans[dsid] = []
            self.handled_scans[dsid] = []

        # Set the antenna info if we have it
        if dsid in self.ant.keys():
            config.set_ant(self.ant[dsid])

        # Update the stop times of any queued scans that start 
        # before this one.  Does it ever make sense to update the 
        # already-handled scans?
        for scan in self.queued_scans[dsid]:
            if ((scan.startTime<config.startTime) and 
                    ((scan.stopTime is None) 
                        or (scan.stopTime>config.startTime))):
                scan.stopTime = config.startTime

        # Add the new scan to the queue
        self.queued_scans[dsid].append(config)
        logging.info('queued %s scan for %s' % (config.scan_intent, 
            config.scanId))

        # Handle any complete scans from queue
        self.clean_queue(dsid)

    def add_vci(self,vci):
        self.vci[vci.attrib['configId']] = vci

    def add_ant(self,ant):
        dsid = ant.attrib['datasetId']
        self.ant[dsid] = ant
        # Update anything in the queue that does not yet have antenna info
        if dsid in self.queued_scans.keys():
            for scan in self.queued_scans[dsid]:
                if not scan.has_ant: 
                    scan.set_ant(ant)
        # Handle any now-complete scans in the queue
        self.clean_queue(dsid)

    def clean_queue(self,dsid):
        # Calls handle_config on any queued scans that now have complete
        # info available.  Moves these from the queue into the list of
        # already-handled scans.
        if dsid not in self.queued_scans.keys(): return
        complete = [s for s in self.queued_scans[dsid] if s.is_complete()]
        for scan in complete:
            logging.info('handling complete scan %s' % scan.scanId)
            self.handle_config(scan)
            self.handled_scans[dsid].append(scan)
            self.queued_scans[dsid].remove(scan)

    def handle_config(self,config):
        # Implement in derived class..
        pass
