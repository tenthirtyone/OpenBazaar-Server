"""
Copyright (c) 2014 Brian Muller
Copyright (c) 2015 OpenBazaar
"""
import heapq

from operator import itemgetter
from protos import objects


class Node(object):
    def __init__(self, node_id, ip=None, port=None, signed_pubkey=None,
                 relay_node=None, nat_type=None, vendor=False):
        self.id = node_id
        self.ip = ip
        self.port = port
        self.signed_pubkey = signed_pubkey
        self.relay_node = relay_node
        self.nat_type = nat_type
        self.vendor = vendor
        self.long_id = long(node_id.encode('hex'), 16)

    def getProto(self):
        node_address = objects.Node.IPAddress()
        node_address.ip = self.ip
        node_address.port = self.port

        n = objects.Node()
        n.guid = self.id
        n.signedPublicKey = self.signed_pubkey
        n.natType = self.nat_type
        n.nodeAddress.MergeFrom(node_address)
        n.vendor = self.vendor

        if self.relay_node is not None:
            relay_address = objects.Node.IPAddress()
            relay_address.ip = self.relay_node[0]
            relay_address.port = self.relay_node[1]
            n.relayAddress.MergeFrom(relay_address)

        return n

    def sameHomeAs(self, node):
        return self.ip == node.ip and self.port == node.port

    def distanceTo(self, node):
        """
        Get the distance between this node and another.
        """
        return self.long_id ^ node.long_id

    def __iter__(self):
        """
        Enables use of Node as a tuple - i.e., tuple(node) works.
        """
        return iter([self.id, self.ip, self.port])

    def __repr__(self):
        return repr([self.long_id, self.ip, self.port])

    def __str__(self):
        return "%s:%s" % (self.ip, str(self.port))


class NodeHeap(object):
    """
    A heap of nodes ordered by distance to a given node.
    """

    def __init__(self, node, maxsize):
        """
        Constructor.

        @param node: The node to measure all distnaces from.
        @param maxsize: The maximum size that this heap can grow to.
        """
        self.node = node
        self.heap = []
        self.contacted = set()
        self.maxsize = maxsize

    def remove(self, peerIDs):
        """
        Remove a list of peer ids from this heap.  Note that while this
        heap retains a constant visible size (based on the iterator), it's
        actual size may be quite a bit larger than what's exposed.  Therefore,
        removal of nodes may not change the visible size as previously added
        nodes suddenly become visible.
        """
        peerIDs = set(peerIDs)
        if len(peerIDs) == 0:
            return
        nheap = []
        for distance, node in self.heap:
            if node.id not in peerIDs:
                heapq.heappush(nheap, (distance, node))
        self.heap = nheap

    def getNodeById(self, node_id):
        for _, node in self.heap:
            if node.id == node_id:
                return node
        return None

    def allBeenContacted(self):
        return len(self.getUncontacted()) == 0

    def getIDs(self):
        return [n.id for n in self]

    def markContacted(self, node):
        self.contacted.add(node.id)

    def popleft(self):
        if len(self) > 0:
            return heapq.heappop(self.heap)[1]
        return None

    def push(self, nodes):
        """
        Push nodes onto heap.

        @param nodes: This can be a single item or a C{list}.
        """
        if not isinstance(nodes, list):
            nodes = [nodes]

        for node in nodes:
            if node not in self:
                distance = self.node.distanceTo(node)
                heapq.heappush(self.heap, (distance, node))

    def __len__(self):
        return min(len(self.heap), self.maxsize)

    def __iter__(self):
        nodes = heapq.nsmallest(self.maxsize, self.heap)
        return iter(map(itemgetter(1), nodes))

    def __contains__(self, node):
        # pylint: disable=unused-variable
        for distance, n in self.heap:
            if node.id == n.id:
                return True
        return False

    def getUncontacted(self):
        return [n for n in self if n.id not in self.contacted]
