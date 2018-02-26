from __future__ import print_function, division, absolute_import, unicode_literals
from builtins import bytes, dict, object, range, map, input, str
from future.utils import itervalues, viewitems, iteritems, listvalues, listitems
from io import open

import logging
import asyncore

from . import mcast_clients
from .scan_config import ScanConfig


class Dataset(object):
    # This is a simple data structure class for keeping track of scans that
    # have run or are queued to run for a given dataset (subarray).

    def __init__(self, datasetId):
        self.datasetId = datasetId
        self.queued = []   # List of queued ScanConfig objects
        self.handled = []  # List of handled ScanConfig objects
        self.ant = None    # The antenna property table
        self.stopTime = None  # Final end time of the SB, once known


class Controller(object):

    def __init__(self):
        self.obs_client = mcast_clients.ObsClient(self)
        self.ant_client = mcast_clients.AntClient(self)
        self._datasets = {}  # key is datasetId
        self.vci = {}       # key is configId

        # The required info before handle_config is called.
        # Redefine in derived classes as needed
        self.scans_require = ['obs', 'vci', 'ant', 'stop']

    def run(self):
        try:
            asyncore.loop()
        except KeyboardInterrupt:
            logging.info('Exiting controller...')

    def dataset(self, dsid):
        if dsid not in list(self._datasets.keys()):
            self._datasets[dsid] = Dataset(dsid)
        return self._datasets[dsid]

    def add_obs(self, obs):
        dsid = obs.attrib['datasetId']
        cfgid = obs.attrib['configId']
        ds = self.dataset(dsid)

        # Generate the scan config object for this scan
        config = ScanConfig(obs=obs, vci=self.vci[cfgid],
                            requires=self.scans_require)

        # Set the antenna info if we have it
        if ds.ant is not None:
            config.set_ant(ds.ant)

        # Update the stop times of any queued scans that start
        # before this one.  Does it ever make sense to update the
        # already-handled scans?
        for scan in ds.queued:
            if ((scan.startTime < config.startTime) and
                    ((scan.stopTime is None)
                        or (scan.stopTime > config.startTime))):
                scan.stopTime = config.startTime

        # The end of an SB is marked by a special Observation document
        # with source name FINISH, and intent suppress_data=True.  Check
        # for this here.  This scan does not produce any data, it just
        # sets the end time of the previous scan, and triggers and final
        # end-of-SB processing.
        is_finish = (config.source == 'FINISH')

        # Add the new scan to the queue, unless it's a FINISH
        if not is_finish:
            ds.queued.append(config)
            logging.debug('Queued scan {0}, scan {1}.'
                          .format(config.scan_intent, config.scanId))

        # Handle any complete scans from queue
        self.clean_queue(ds)

        # If this was a finish scan, update the dataset stop time,
        # call handle_finish() for any cleanup/etc actions, and then
        # remove the dataset from the list.
        # TODO: Apparently multiple FINISH scan messages sometimes happen.
        # Figure out best way to deal with this.
        if is_finish:
            logging.debug('Finishing dataset {0}'.format(ds.datasetId))
            ds.stopTime = config.startTime
            self.handle_finish(ds)
            self._datasets.pop(ds.datasetId)

    def add_vci(self, vci):
        self.vci[vci.attrib['configId']] = vci

    def add_ant(self, ant):
        dsid = ant.attrib['datasetId']
        ds = self.dataset(dsid)
        ds.ant = ant
        # Update anything in the queue that does not yet have antenna info
        for scan in ds.queued:
            if not scan.has_ant:
                scan.set_ant(ant)
        # Handle any now-complete scans in the queue
        self.clean_queue(ds)

    def clean_queue(self, ds):
        # Calls handle_config on any queued scans that now have complete
        # info available.  Moves these from the queue into the list of
        # already-handled scans.
        complete = [s for s in ds.queued if s.is_complete()]
        for scan in complete:
            logging.debug('Handling complete scan {0}'.format(scan.scanId))
            self.handle_config(scan)
            ds.handled.append(scan)
            ds.queued.remove(scan)

        # XXX for testing, remove:
        for s in ds.queued:
            logging.debug('Queued %s start=%.6f stop=%.6f' % (
                s.scanId, s.startTime,
                s.stopTime if s.stopTime is not None else 0.0))
        for s in ds.handled:
            logging.debug('handled %s start=%.6f stop=%.6f' % (
                s.scanId, s.startTime,
                s.stopTime if s.stopTime is not None else 0.0))

    def handle_config(self, config):
        # Implement in derived class.  This will be called with the
        # ScanConfig object as argument every time a scan with complete
        # metadata is received.
        pass

    def handle_finish(self, dataset):
        # Implement in derived class.  This will be called with the
        # Dataset object as an argument whenever the FINISH scan
        # has been received.  The Dataset.stopTime attribute will
        # give the final end time of the SB (note, this can be earlier
        # than some of the scan end times if there has been an abort).
        pass
