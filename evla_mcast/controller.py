# controller.py -- P. Demorest 2017/05

import logging
import asyncore

from . import mcast_clients
from .evla_config import EVLAConfig

import rfpipe

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
        config = EVLAConfig(obs=obs,vci=self.vci[cfgid])
        if dsid not in self.scans.keys():
            self.scans[dsid] = []
        self.scans[dsid].append(config)
        logging.info('got %s scan for %s.%d.%d' % (config.scan_intent,
            config.datasetId, config.scanNo, config.subscanNo))

    def add_vci(self,vci):
        self.vci[vci.attrib['configId']] = vci

    def add_ant(self,ant):
        self.ant[ant.attrib['datasetId']] = ant


class realfast_controller(Controller):

    def __init__(self):
        super(realfast_controller, self).__init__()

    def add_obs(self, obs):
        """ Triggered when obs comes in.
        Downstream logic starts here.
        """

        dsid = obs.attrib['datasetId']
        cfgid = obs.attrib['configId']
        config = EVLAConfig(obs=obs,vci=self.vci[cfgid])

        if dsid not in self.scans.keys():
            self.scans[dsid] = []
        self.scans[dsid].append(config)
        logging.info('got %s scan for %s.%d.%d' % (config.scan_intent,
            config.datasetId, config.scanNo, config.subscanNo))

        meta = rfpipe.metadata.config_metadata(config)
        logging.info('{0}'.format(meta))

        st = rfpipe.state.State(preffile='~/lustre_workdir/realfast.yml', inmeta=meta, inprefs={'nsegment':1, 'maxdm': 1000})

        logging.info('{0}'.format(st))
