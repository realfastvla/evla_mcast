#!/usr/bin/env python

from distutils.core import setup

setup(name='evla_mcast',
      version='0.0',
      description='Receive and handle EVLA multicast messages',
      author='Paul Demorest',
      author_email='pdemores@nrao.edu',
      url='http://github.com/demorest/evla_mcast',
      packages=['evla_mcast'],
      package_data={'evla_mcast': ['xsd/*.xsd','xsd/vci/*.xsd','xsd/observe/*.xsd']},
     )
