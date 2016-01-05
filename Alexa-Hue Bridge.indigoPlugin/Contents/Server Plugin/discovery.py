import socket
import time
import threading
import uuid

BCAST_IP = "239.255.255.250"
UPNP_PORT = 1900
BROADCAST_INTERVAL = 10  # Seconds between upnp broadcast
M_SEARCH_REQ_MATCH = "M-SEARCH"
UUID = uuid.uuid1()
TIMEOUT = 60 * 2  # Default seconds that the broadcaster and responder will run before automatically shutting down

# Need to substitute: 
# {"broadcast_ip": BCAST_IP, "upnp_port": UPNP_PORT, "server_ip": Server IP, "server_port": Server Port, "uuid": UUID}
broadcast_packet = """NOTIFY * HTTP/1.1
HOST: %(broadcast_ip)s:%(upnp_port)s
CACHE-CONTROL: max-age=100
LOCATION: http://%(server_ip)s:%(server_port)s/description.xml
SERVER: AlexaHueBridge/0.1.0, UPnP/1.0, IpBridge/1.7.0
NTS: ssdp:alive
NT: uuid:2f402f80-da50-11e1-9b23-001788101fe2
USN: uuid:2f402f80-da50-11e1-9b23-001788101fe2

"""

# Need to substitute: {"server_ip": Server IP, "server_port": Server Port, "uuid": UUID}
# response_packet = """HTTP/1.1 200 OK
# CACHE-CONTROL: max-age=100
# EXT:
# LOCATION: http://%(server_ip)s:%(server_port)s/description.xml
# SERVER: AlexaHueBridge/0.1.0, UPnP/1.0, IpBridge/1.7.0
# ST: urn:schemas-upnp-org:device:basic:1
# USN: uuid:%(uuid)s
#
# """
response_packet = """HTTP/1.1 200 OK
CACHE-CONTROL: max-age=100
EXT:
LOCATION: http://%(server_ip)s:%(server_port)s/description.xml
SERVER: FreeRTOS/7.4.2, UPnP/1.0, IpBridge/1.7.0
ST: urn:schemas-upnp-org:device:basic:1
USN: uuid:2f402f80-da50-11e1-9b23-001788101fe2

"""

class Broadcaster(threading.Thread):
    def __init__(self, host, port, debug_log, timeout=TIMEOUT):
        threading.Thread.__init__(self)
        self.interrupted = False
        self._host = host
        self._port = port
        self.debug_log = debug_log
        self.debug_log("Broadcaster.__init__ is running")
        self._timeout = timeout
        broadcast_data = {"broadcast_ip": BCAST_IP, 
                          "upnp_port": UPNP_PORT, 
                          "server_ip": host, 
                          "server_port": port, 
                          "uuid": UUID}
        self.broadcast_packet = broadcast_packet % broadcast_data

    def run(self):
        self.debug_log("Broadcaster.run called")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)
        start_time = time.time()
        end_time = start_time + (self._timeout * 60)
        while True:
            sock.sendto(self.broadcast_packet, (BCAST_IP, UPNP_PORT))
            for x in range(BROADCAST_INTERVAL):
                time.sleep(1)
                if time.time() > end_time:
                    self.debug_log("Broadcaster thread timed out")
                    self.stop()
                if self.interrupted:
                    sock.close()
                    return

    def stop(self):
        self.debug_log("Broadcaster thread stopped")
        self.interrupted = True

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        self._host = host

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        self._port = port

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout

class Responder(threading.Thread):
    def __init__(self, host, port, debug_log, timeout=TIMEOUT):
        threading.Thread.__init__(self)
        self.interrupted = False
        self._host = host
        self._port = port
        self.debug_log = debug_log
        self.debug_log("Responder.__init__ is running")
        self._timeout = timeout
        response_data = {"server_ip": host, 
                         "server_port": port, 
                         "uuid": UUID}
        self.response_packet = response_packet % response_data

    def run(self):
        self.debug_log("Responder.run called")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.bind(('', UPNP_PORT))
        sock.setsockopt(socket.IPPROTO_IP, 
                        socket.IP_ADD_MEMBERSHIP, 
                        socket.inet_aton(BCAST_IP) + socket.inet_aton(self._host))
        sock.settimeout(1)
        start_time = time.time()
        end_time = start_time + (self._timeout * 60)
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                if time.time() > end_time:
                    self.debug_log("Responder thread timed out")
                    self.stop()
                    raise socket.error
            except socket.error:
                if self.interrupted:
                    sock.close()
                    return
            else:
                if M_SEARCH_REQ_MATCH in data:
                    self.respond(addr)

    def stop(self):
        self.debug_log("Responder thread stopped")
        self.interrupted = True

    def respond(self, addr):
        self.debug_log("Responder.respond called from address %s\n%s" % (str(addr), self.response_packet))
        output_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        output_socket.sendto(self.response_packet, addr)
        output_socket.close()

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        self._host = host

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        self._port = port

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout

