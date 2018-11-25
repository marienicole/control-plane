import queue
import threading
import json
from copy import deepcopy

## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)

    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None

    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)


## Implements a network layer packet.
class NetworkPacket:
    ## packet encoding lengths
    dst_S_length = 5
    prot_S_length = 1

    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S

    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()

    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise('%s: unknown prot_S option: %s' %(self, self.prot_S))
        byte_S += self.data_S
        return byte_S

    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0 : NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length : NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise('%s: unknown prot_S field: %s' %(self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length : ]
        return self(dst, prot_S, data_S)




## Implements a network host for receiving and transmitting data
class Host:

    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination

    ## called when printing the object
    def __str__(self):
        return self.addr

    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out') #send packets always enqueued successfully

    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))

    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return



## Implements a multi-interface router
class Router:

    ##@param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        #save neighbors and interfeces on which we connect to them
        self.cost_D = deepcopy(cost_D)    # {neighbor: {interface: cost}}
        #TODO: set up the routing table for connected hosts
        self.rt_tbl_D = deepcopy(cost_D) #self.calculate_costs(cost_D) # {destination: {router: cost}}
        print('%s: Initialized routing table' % self)
        self.print_routes()

    ## Print routing table
    def print_routes(self):
        routers = []
        hosts = []

        if self.name in self.rt_tbl_D:
            for nbr in self.rt_tbl_D[self.name]:
                if "R" in str(nbr):
                    routers.append(nbr)
                hosts.append(nbr)
        else:
            for nbr in self.rt_tbl_D:
                if "R" in str(nbr):
                    routers.append(nbr)
                hosts.append(nbr)

        routers = sorted(routers)
        hosts = sorted(hosts)

        #TODO: print the routes as a two dimensional table
        sort_rt = sorted(self.rt_tbl_D)
        # Prints top border
        rt_tbl = "╒══════"
        for neighbor in hosts:
            rt_tbl += "╤══════"
        # Prints router names horizontally
        rt_tbl += "╕\n|%-6s" % self.name
        for neighbor in hosts:
            rt_tbl += "|%6s" % neighbor
        rt_tbl += "|\n├──────"
        for neighbor in hosts:
            rt_tbl += "├──────"
        rt_tbl += "┤\n"
        for router in routers:
            rt_tbl += "|%-6s" % router
            if router not in self.rt_tbl_D:
                for host in hosts:
                    rt_tbl += "|%6s" % "~"
                rt_tbl += "|\n"
                if router != routers[len(routers)-1]:
                    for host in hosts:
                        rt_tbl += "├──────"
                    rt_tbl += "├──────┤\n"
                continue

            cur_r = self.rt_tbl_D[router]
            for dest in hosts:
                if dest == router: # if trying to go to self
                    rt_tbl += "|%6s" % "0"
                    continue
                else:
                    if dest in cur_r:
                        my_intf = list(cur_r[dest].keys())[0]
                        rt_tbl += "|%6s" % cur_r[dest][my_intf]
                    else:
                        total_cost = self.calculate_cost(router, dest)
                        rt_tbl += "|%6s" % total_cost
            rt_tbl += "|\n"
            if router != routers[len(routers)-1]:
                for neighbor in hosts:
                    rt_tbl += "├──────"
                rt_tbl += "├──────┤\n"

        # prints bottom border
        rt_tbl += "╘══════"
        for neighbor in hosts:
            rt_tbl += "╧══════"
        rt_tbl += "╛"
        print(rt_tbl)
        print()

    def calculate_cost(self, router, dest):
        router_dist = list(self.rt_tbl_D[router].keys())[0]
        router_dist = self.rt_tbl_D[router][router_dist]

        host_dist = list(self.rt_tbl_D[dest].keys())[0]
        host_dist = self.rt_tbl_D[dest][host_dist]

        total_cost = router_dist + host_dist

        return total_cost

    ## called when printing the object
    def __str__(self):
        return self.name


    ## look through the content of incoming interfaces and
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            #get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            #if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p,i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))


    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            # TODO: Here you will need to implement a lookup into the
            # forwarding table to find the appropriate outgoing interface
            # for now we assume the outgoing interface is 1
            #out_intf = self.cost_D[p.dst]
            #print(out_intf)
            intf = 0
            routers = []
            costs = []
            i = 0
            if p.dst not in self.cost_D:
                for rtr in self.rt_tbl_D:
                    if p.dst in self.rt_tbl_D[rtr]:
                        routers[i] = rtr
                        intf = list(self.rt_tbl_D[rtr][p.dst].keys())[0]
                        costs[i] = self.rt_tbl_D[rtr][intf]
                        i += 1
                cheapest = costs.index(min(costs))
                cheapest = routers[cheapest]
                intf = list(self.rt_tbl_D[cheapest][p.dst].keys())[0]

            else:
                intf = list(self.cost_D[p.dst].keys())[0]

            self.intf_L[int(intf)].put(p.to_byte_S(), 'out', True)
            print('%s: forwarding packet "%s" from interface %d to %d' % \
                (self, p, i, 1))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        # TODO: Send out a routing table update
        #create a routing table update packet
        my_routes = {}
        my_routes[self.name] = self.cost_D
        p = NetworkPacket(0, 'control', json.dumps(my_routes))
        try:
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        temp_cost_D = deepcopy(self.cost_D)
        print('%s: Received routing update %s from interface %d' % (self, p, i))
        routes = json.loads(p.data_S)
        for key in routes:
            updates = routes[key]
            incoming_router = key
            self.rt_tbl_D[key] = {}
            self.rt_tbl_D[key] = routes[key]
            self.rt_tbl_D[self.name] = {}
        updated = False
        for dest in updates:
            # if destination does not exist in temp_cost_D
            if dest not in temp_cost_D:
                updated = True
                intf = list(temp_cost_D[incoming_router].keys())[0]
                cost = temp_cost_D[incoming_router][intf] + updates[dest][list(updates[dest].keys())[0]]
                temp_cost_D[dest] = {str(intf):cost}
                self.rt_tbl_D[self.name][dest] = {str(intf):cost}

            elif dest != self.name:
                intf = list(temp_cost_D[dest].keys())[0]
                self.rt_tbl_D[self.name][dest] = {str(intf):temp_cost_D[dest][intf]}
                temp_cost_D[dest] = {str(intf):temp_cost_D[dest][intf]}

            elif dest == self.name:
                self.rt_tbl_D[self.name][self.name] = {'0': 0}
                temp_cost_D[dest] = {'0': 0}

            self.cost_D = temp_cost_D

        routers = []
        for nbr in temp_cost_D:
            if "R" in str(nbr):
                routers.append(nbr)

        if updated:
            for router in routers:
                if router != self.name:
                    intf = list(self.cost_D[router].keys())[0]
                    self.send_routes(int(intf)) # send update to everyone except who updated you?
        #TODO: add logic to update the routing tables and
        # possibly send out routing updates


    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return
