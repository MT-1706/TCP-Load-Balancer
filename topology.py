#!/usr/bin/env python
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import time

def build_sdn_socket_topology():
    # 1. Initialize network with an external SDN OpenFlow controller hook
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, build=False)

    info('*** Adding Central SDN Controller\n')
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    info('*** Adding OpenFlow Core Infrastructure Switch\n')
    s1 = net.addSwitch('s1')

    info('*** Provisioning Dedicated Host Topology Nodes\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24') # Client Node
    h2 = net.addHost('h2', ip='10.0.0.2/24') # Gateway / SDN Load Balancer Broker
    h3 = net.addHost('h3', ip='10.0.0.3/24') # Backend Compute Worker Server 1
    h4 = net.addHost('h4', ip='10.0.0.4/24') # Backend Compute Worker Server 2

    info('*** Linking Infrastructure Interfaces\n')
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.addLink(h4, s1)

    info('*** Activating Emulation Network Link Layer\n')
    net.build()
    c0.start()
    s1.start([c0])

    # Wait for OpenFlow rules to establish communication links
    info('*** Stabilizing network control plane entries...\n')
    time.sleep(3)

    # 2. Automated Execution Matrix (Fulfills exact reproduction criteria)
    info('*** Deploying Socket Application Components within Node Namespaces\n')
   
    # Boot the Gateway broker on h2 in adaptive mode
    info('[+] Spawning Intelligent Load Balancing Gateway on h2...\n')
    h2.cmd('python3 gateway.py adaptive > gateway_output.log 2>&1 &')
    time.sleep(1)

    # Boot backend compute servers on h3 and h4
    info('[+] Spawning Backend Worker Server 6001 on h3...\n')
    h3.cmd('python3 backend_server.py 6001 > worker_6001_output.log 2>&1 &')
   
    info('[+] Spawning Backend Worker Server 6002 on h4...\n')
    h4.cmd('python3 backend_server.py 6002 > worker_6002_output.log 2>&1 &')

    # Allow heartbeats to stabilize tracking structures
    info('*** Gathering health telemetry and populating SDN flow maps...\n')
    time.sleep(4)

    # 3. Enter Interactivity Mode
    info('\n=== SYSTEM OPERATIONAL ===\n')
    info('You are now in the Mininet CLI prompt. Every host is isolated.\n')
    info('To launch the client benchmarking pipeline workload from host h1, run:\n')
    info('   mininet> h1 python3 client.py\n\n')
   
    CLI(net)

    info('*** Tearing down infrastructure emulations safely...\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    build_sdn_socket_topology()
