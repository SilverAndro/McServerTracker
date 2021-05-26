# Requires
import json
import re
import select
import socket
import struct
import sys
import time

# Load the existing data
openFile = open('data.json', 'r')
data = json.load(openFile)
dataarray = data['ComputerIDs']

port = 4445                  # Port to listen on
bufferSize = 2048            # How big the buffer is
# How many seconds to collect multicasts for (servers multicast every 3 seconds)
timeout = 7
MCAST_GRP = '224.0.2.60'     # Where to listen for multicasts
portRegex = re.compile("((?:\d+\.){1,8}\d+:?)?(\d+)")

# Holds what servers we have seen before so they dont show up twice in the list
seenAddresses = []

# Set up the socket
# AF_INET - (address, port) tuple
# SOCK_DGRAM - Datagram socket
# IPPROTO_UDP - Sets socket to UDP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
s.bind(('', port))
s.setblocking(0)

start_time = time.time()

print("Waiting for LAN multicasts...")
print("----------" * 4)
while True:
    current_time = time.time()
    (read, written, exceptions) = select.select([s], [], [s], 0.5)
    for r in read:
        # Get data from buffer
        msg, peer = r.recvfrom(bufferSize)
        # Address is an (address, port) tuple
        address = peer[0]
        # Make sure we havent seen it before (this session)
        if not address in seenAddresses:
            # Grab hostname and port
            try:
                hostname = socket.gethostbyaddr(address)[0]
            except:
                hostname = "Could not retrieve Hostname"
            # Clean up the input and extract the info
            after = str(msg).split("[AD]")
            # Check for server port
            groups = portRegex.search(after[1])
            serverport = groups.group(2)
            postnetty = False
            if groups.group(1) == None:
                print("Post-netty multicast")
                postnetty = True
            else:
                print("Pre-netty multicast")

            print(re.sub(r'\[AD\].*\[/AD\]',   # Pattern
                         "",                   # Replace with
                         "Server found: " +    # String to match and replace over
                         msg.decode(
                             "utf-8").replace("[MOTD]", "").replace("[/MOTD]", "")
                         ),
                  "\nAt address: " +
                  address + ":" + str(serverport),
                  "\nHost name: " +
                  hostname,
                  "\n" + "----------" * 4
                  )
            seenAddresses.append(address)

            # Add some default info if this host hasnt been seen before
            if not hostname in dataarray.keys():
                dataarray[hostname] = []
            servername = re.sub(r'\[AD\].*\[/AD\]',
                                "",
                                msg.decode(
                                    "utf-8").replace("[MOTD]", "").replace("[/MOTD]", "")
                                )
            datacombined = {
                "address": address + ":" + str(serverport),
                "name": servername,
                "post_netty": postnetty
            }
            knownabout = False
            # Push it to out JSON based object
            for known in dataarray[hostname]:
                if known['address'] == datacombined['address'] and known['name'] == datacombined['name']:
                    knownabout = True
            if not knownabout:
                dataarray[hostname].append(datacombined)

    if len(exceptions) > 0 or current_time < start_time:
        sys.exit(1)
    if current_time >= start_time + timeout:
        break

# Dump data to file (with nice formatting)
print("Dumping data to file")
with open('data.json', 'w') as f:
    json.dump(data, f, indent=4)
print("Dumped data")
print("----------" * 4)
