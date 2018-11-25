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
        self.temp_cost_D = deepcopy(cost_D)
        #TODO: set up the routing table for connected hosts
        self.rt_tbl_D = deepcopy(cost_D) #self.calculate_costs(cost_D) # {destination: {router: cost}}
        print('%s: Initialized routing table' % self)
        self.print_routes()

    ## Print routing table
    def print_routes(self):
        routers = []
        hosts = []

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
        for neighbor in sort_rt:
            rt_tbl += "╤══════"
        # Prints router names horizontally
        rt_tbl += "╕\n|%-6s" % self.name
        for neighbor in sort_rt:
            rt_tbl += "|%6s" % neighbor
        rt_tbl += "|\n├──────"
        for neighbor in sort_rt:
            rt_tbl += "├──────"
        rt_tbl += "┤\n"
        for router in routers:
            rt_tbl += "|%-6s" % router
            for dest in hosts:
                if dest == router: # if trying to go to self
                    rt_tbl += "|%6s" % "0"
                    continue
                if router == self.name:
                    if dest in self.rt_tbl_D:
                        my_intf = list(self.rt_tbl_D[dest].keys())[0]
                        rt_tbl += "|%6s" % self.rt_tbl_D[dest][my_intf]
                else:
                    if 'rts' in self.rt_tbl_D[router]:
                        if dest in self.rt_tbl_D[router]['rts']:
                            my_intf = list(self.rt_tbl_D[router]['rts'][dest].keys())[0]
                            rt_tbl += "|%6s" % self.rt_tbl_D[router]['rts'][dest][my_intf]
                        else:
                            total_cost = self.calculate_cost(router, dest)
                            rt_tbl += "|%6s" % total_cost
                    else:
                        if dest in self.rt_tbl_D[router]:
                            rt_tbl += "|%6s" % dest
                        else:
                            total_cost = self.calculate_cost(router, dest)
                            rt_tbl += "|%6s" % total_cost
            rt_tbl += "|\n"
            if router != routers[len(routers)-1]:
                for neighbor in sort_rt:
                    rt_tbl += "├──────"
                rt_tbl += "├──────┤\n"

        # prints bottom border
        rt_tbl += "╘══════"
        for neighbor in sort_rt:
            rt_tbl += "╧══════"
        rt_tbl += "╛"
        print(rt_tbl)
        #print(self.cost_D)
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
            self.intf_L[1].put(p.to_byte_S(), 'out', True)
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
        print("in send_routes", self.cost_D)
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
#TODO: Change some of this logic, so that it only updates if the costs have changed.
# not always updating
        print('%s: Received routing update %s from interface %d' % (self, p, i))
        routes = json.loads(p.data_S)
        for key in routes: # key is the router it's coming from
            self.rt_tbl_D[key]['rts'] = routes[key]
        # adding the values to the routing table by themselves
            for val in routes[key]:
                if val not in self.cost_D or (val in self.rt_tbl_D and routes[key][val] != self.rt_tbl_D[val]):
                    print(val, end = "")
                    print(routes[key][val])
                    updated_intf = list(self.temp_cost_D[key].keys())[0]
                    print(updated_intf)
                    current_intf = list(routes[key][val].keys())[0]
                    updated_cost = routes[key][val][current_intf] + self.temp_cost_D[key][updated_intf]

                    self.temp_cost_D[val] = {str(updated_intf):updated_cost}
                    self.rt_tbl_D[val] = {str(updated_intf):updated_cost}
        print(self, "self.temp_cost_D after update: ", self.temp_cost_D)
        print(self, "self.cost_D after update: ", self.cost_D)
        print(self, "rt_tbl_D after update: ", self.rt_tbl_D)

        dests = []
        routers = []
        for nbr in self.temp_cost_D:
            if "R" in str(nbr):
                routers.append(nbr)
            dests.append(nbr)

        for router in routers:
            if router == self.name:
                self.temp_cost_D[router] = {'0': 0}
                self.rt_tbl_D[router] = {'0': 0}
            for dest in dests:
                if dest not in self.temp_cost_D and 'R' not in dest:
                    intf = list(self.temp_cost_D[dest].keys())[0]
                    router_dist = self.temp_cost_D[router][list(self.temp_cost_D[router].keys())[0]]
                    host_dist = self.temp_cost_D[dest][list(self.temp_cost_D[dest].keys())[0]]
                    total_cost = router_dist + host_dist
                    self.temp_cost_D[dest] = {str(intf):total_cost}
                    self.rt_tbl_D[dest] = {str(intf):total_cost}

            # if 'rts' in self.temp_cost_D[router]:
            #     del self.temp_cost_D[router]['rts']

        temp_copy_self = deepcopy(self.cost_D)
        temp_copy_self[self.name] = self.temp_cost_D[self.name]
        print("\nTemp_copy_self", temp_copy_self)
        print("self.temp_cost_D", self.temp_cost_D, end="\n\n")
        if self.temp_cost_D != temp_copy_self: # there were some changes made
            self.cost_D = self.temp_cost_D
            for router in routers:
                if router != self.name:
                    intf = list(self.cost_D[router].keys())[0]
                    self.send_routes(int(intf))
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
