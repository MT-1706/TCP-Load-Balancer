from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet
from os_ken.lib import hub
import time

class SimpleSDNController(app_manager.OSKenApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSDNController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.port_stats_previous = {}
        self.port_rates = {}
        self.monitor_thread = hub.spawn(self._monitor)
    def _monitor(self):
        while True:
            for datapath in self.datapaths.values():
                parser = datapath.ofproto_parser
                req = parser.OFPPortStatsRequest(
                    datapath,
                    0,
                    datapath.ofproto.OFPP_ANY,
                    datapath.ofproto.OFPP_ANY
                )
                datapath.send_msg(req)

            hub.sleep(5)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Send unknown packets to the controller.
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                   ofproto.OFPCML_NO_BUFFER)
        ]

        self.add_flow(datapath, 0, match, actions)

        self.logger.info(
            "Switch %s connected to SDN controller",
            datapath.id
        )

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        instructions = [
            parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                actions
            )
        ]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=instructions
        )

        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None:
            return

        src = eth.src
        dst = eth.dst

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # Learn where the source MAC address is located.
        self.mac_to_port[dpid][src] = in_port

        # If destination is known, forward directly.
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            # Otherwise flood to all switch ports.
            out_port = ofproto.OFPP_FLOOD

        actions = [
            parser.OFPActionOutput(out_port)
        ]

        # Install a flow for known destinations.
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst
            )

            self.add_flow(
                datapath,
                1,
                match,
                actions
            )

        data = None

        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )

        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        datapath = ev.msg.datapath
        dpid = datapath.id
        now = time.time()

        for stat in ev.msg.body:
            port_no = stat.port_no
            key = (dpid, port_no)

            current = {
                "rx_bytes": stat.rx_bytes,
                "tx_bytes": stat.tx_bytes,
                "time": now
            }

            previous = self.port_stats_previous.get(key)

            if previous is not None:
                elapsed = now - previous["time"]

                if elapsed > 0:
                    rx_rate = max(
                        0, current["rx_bytes"] - previous["rx_bytes"]
                    ) * 8 / elapsed

                    tx_rate = max(
                        0, current["tx_bytes"] - previous["tx_bytes"]
                    ) * 8 / elapsed

                    self.port_rates[key] = {
                        "rx_bps": rx_rate,
                        "tx_bps": tx_rate
                    }

                    self.logger.info(
                        "NETWORK RATE | Switch=%s Port=%s | RX=%.2f Mbps TX=%.2f Mbps",
                        dpid,
                        port_no,
                        rx_rate / 1_000_000,
                        tx_rate / 1_000_000
                    )

            self.port_stats_previous[key] = current
