#!/usr/bin/env python
from __future__ import print_function
import binascii,socket,struct,os

from dnslib import DNSRecord, QTYPE, RR, A, RCODE
from dnslib.server import DNSServer,DNSHandler,BaseResolver,DNSLogger,UDPServer

def is_ip(addr):
	try:
		a,b,c,d = map(int, addr.split('.'))
		return True
	except ValueError as e:
		return False

def process_alias(alias):
	try:
		name, dest = alias.split('=', 1)
	except ValueError as e:
		print("Can't parse alias %s" % (alias,), file=sys.stderr)
		raise e
	if is_ip(dest):
		get_dest = lambda: dest
	else:
		# resolve dest at lookup time
		get_dest = lambda: socket.gethostbyname(dest)
	return (name, get_dest)

class ProxyResolver(BaseResolver):
	def __init__(self, aliases):
		self.aliases = list(map(process_alias, aliases))
		super(ProxyResolver, self).__init__()

	def resolve(self,request,handler):
		# import pdb; pdb.set_trace()

		reply = request.reply()

		for q in request.questions:
			qname = request.q.qname
			qtype = request.q.qtype
			try:
				for name,get_dest in self.aliases:
					if qname.matchGlob(name) and (qtype in (QTYPE.A,QTYPE.ANY,QTYPE.CNAME)):
						a = RR(qname, rdata=A(get_dest()), ttl=10)
						reply.add_answer(a)
						break # first match wins
			except Exception as e:
				print("Got error: %s" % (e,), file=sys.stderr)
				reply.rr = []

		# If no answers, report NXDOMAIN
		if not reply.rr:
			reply.header.rcode = getattr(RCODE,'NXDOMAIN')
		return reply

class SocketInheritingUDPServer(UDPServer):
	"""A UDPServer subclass that takes over an inherited socket from systemd"""
	def __init__(self, address_info, handler, fd, bind_and_activate=True):
		UDPServer.__init__(self,
		# super(SocketInheritingUDPServer, self).__init__(
			address_info,
			handler,
			bind_and_activate=False
		)
		self.socket = socket.fromfd(fd, self.address_family, self.socket_type)
		if bind_and_activate:
			# NOTE: systemd provides ready-bound sockets, so we only need to activate:
			self.server_activate()

class Server(DNSServer):
	def __init__(self, **k):
		if os.environ.get('LISTEN_PID', 'null') == str(os.getpid()):
			# use socket activation
			print("Using socket activation", file=sys.stderr)
			assert int(os.environ['LISTEN_FDS']) == 1
			def make_server(address_info, handler):
				return SocketInheritingUDPServer(address_info, handler, 3)
			k['server'] = make_server
		super(Server, self).__init__(**k)

if __name__ == '__main__':
	import argparse,sys,time

	p = argparse.ArgumentParser(description="DNS Proxy")
	p.add_argument("--port","-p",type=int,default=5053,
					metavar="<port>",
					help="Local proxy port (default:5053)")
	p.add_argument("--address","-a",default="localhost",
					metavar="<address>",
					help="Local proxy listen address (default:localhost)")

	p.add_argument("--log",default="request,reply,truncated,error",
					help="Log hooks to enable (default: +request,+reply,+truncated,+error,-recv,-send,-data)")
	p.add_argument("--log-prefix",action='store_true',default=False,
					help="Log prefix (timestamp/handler/resolver) (default: False)")
	p.add_argument("aliases", nargs="*", help="aliases, of the form <pattern>=<dest>."
		" Pattern may include globs (e.g *.example.com matches example.com and foo.example.com)."
		" Dest may be an IP address or hostname (looked up at resolve time using the system DNS resolver)"
		" You may specify additional aliases via $DNS_ALIAS (colon-separated)."
	)

	args = p.parse_args()

	for alias in os.environ.get('DNS_ALIAS', '').split(':'):
		alias = alias.strip()
		if not alias: continue
		args.aliases.append(alias)

	if not args.aliases:
		print("WARN: No aliases given", file=sys.stderr)

	print("Starting Proxy Resolver (%s:%d)" % (
						args.address or "*",args.port,), file=sys.stderr)
	print("Aliases:" +
			"".join(["\n  %s" % (alias,) for alias in args.aliases]),
			file=sys.stderr)

	resolver = ProxyResolver(args.aliases)
	handler = DNSHandler
	logger = DNSLogger(args.log,args.log_prefix)

	udp_server = Server(
		resolver=resolver,
		port=args.port,
		address=args.address,
		logger=logger,
		handler=handler)
	udp_server.start_thread()

	while udp_server.isAlive():
		time.sleep(1)


