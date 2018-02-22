#!/usr/bin/env python
from setuptools import setup, find_packages

setup(name='evla_mcast',
      version='0.1',
      description='Receive and handle EVLA multicast messages',
      author='Paul Demorest',
      author_email='pdemores@nrao.edu',
      url='https://github.com/demorest/evla_mcast/',
      install_requires=['lxml'],
      packages=find_packages(exclude=('tests',)),
      package_data={'evla_mcast': ['xsd/*.xsd','xsd/vci/*.xsd','xsd/observe/*.xsd']},
     )
