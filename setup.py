from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

def read(relpath):
	with open(path.join(here, *relpath.split('/')), encoding='utf-8') as f:
		return f.read()

setup(
	name='dns-server',
	version=read('VERSION'),
	description='dns-server',
	url='https://github.com/timbertson/dns-server',

	py_modules=["dns_alias"],

	install_requires=[],

	entry_points={
		'console_scripts': [ 'dns-alias=dns_alias:main' ],
	},
)

