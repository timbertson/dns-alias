dns-alias is a tiny DNS server for developer use.

It's kind of like messing about with /etc/hosts, but:

 - you can have wildcard entries
 - the destination can be any hostname, not just a fixed IP address
 - you don't have to be root
 - it's stateless (no config files, just run it with the arguments you need)

Example use:

	dns-alias '*.test.example.com=vm1.local' '*.self=127.0.0.1'

 - Requests for test.example.com (and foo.test.example.com, etc)
will all resolve to the IP address of vm1.local
(as resolved by your system's hostname resolution).

 - Requests for *.self will always return 127.0.0.1.

---

Currently it responds with a big ol' shrug if you ask it about domains that you
don't have aliases for. And it probably isn't a very speedy DNS server. Some
day it will proxy to a real upstream DNS server, but right now you should
probably only send it certain queries, like with the following dnsmasq config:

    server=/dev.example.com/127.0.0.1#5053

