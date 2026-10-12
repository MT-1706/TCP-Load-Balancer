#!/usr/bin/env python
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import time
import sys

def build_sdn_socket_topology():
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, build=False)

    info('*** Adding Central SDN Controller\n')
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    info('*** Adding OpenFlow Core Infrastructure Switch\n')
    s1 = net.addSwitch('s1')

    info('*** Provisioning Dedicated Host Topology Nodes (4 Servers Cluster)\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24') 
    h2 = net.addHost('h2', ip='10.0.0.2/24') 
    h3 = net.addHost('h3', ip='10.0.0.3/24') 
    h4 = net.addHost('h4', ip='10.0.0.4/24') 
    h5 = net.addHost('h5', ip='10.0.0.5/24') 
    h6 = net.addHost('h6', ip='10.0.0.6/24') 

    info('*** Linking Infrastructure Interfaces\n')
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.addLink(h4, s1)
    net.addLink(h5, s1)
    net.addLink(h6, s1)

    info('*** Activating Emulation Network Link Layer\n')
    net.build()
    c0.start()
    s1.start([c0])

    info('*** Stabilizing network control plane entries...\n')
    time.sleep(3)

    info('*** Deploying Socket Application Components within Node Namespaces\n')
    # Change 'adaptive' to 'static' here when you want to switch load balancing algorithms
    mode = sys.argv[1] if len(sys.argv) > 1 else "adaptive"
    h2.cmd(f'python3 -u gateway.py {mode} > gateway_output.log 2>&1 &')
    time.sleep(1)

    h3.cmd('python3 -u backend_server.py 6001 > worker_6001_output.log 2>&1 &')
    h4.cmd('python3 -u backend_server.py 6002 > worker_6002_output.log 2>&1 &')
    h5.cmd('python3 -u backend_server.py 6003 > worker_6003_output.log 2>&1 &')
    h6.cmd('python3 -u backend_server.py 6004 > worker_6004_output.log 2>&1 &')

    info('*** Gathering health telemetry and populating SDN flow maps...\n')
    time.sleep(4)

    info('\n=== SYSTEM OPERATIONAL ===\n')
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    build_sdn_socket_topology()
