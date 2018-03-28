import threading
import heapq

class PriorityQueue:
    """thread safe priority queue with minimum rank value as highest priority, itemd can be positive integers or strings or user definied class objects"""
    def __init__(self):
        """We keep a dictionary that holds item ids so we can check for duplicate item in addItem() in our priority queue in O(1) running time but with O(n) extra memory"""
        self.ItemHashList = {}
        self.ItemList = []
        self.lock = threading.Lock()

    def addToList(self, List):
        """Add list of items to priority queue, each item in 'List' argument is a tuple, tuple is defined as (rank, item)"""
        for item in List:
            self.addItem(item[1], item[0])

    def addItem(self, item, rank):
        """Add an item with its rank to the priority queue list, if the item does not already exist in the list"""
        with self.lock:
            if self.ItemHashList.get(item, -1) == -1:
                self.ItemHashList[item] = None
                if rank < 0:
                    rank = 0
                heapq.heappush(self.ItemList, (rank, item))

    def getItem(self):
        """returns a tuple with (rank, item) if priority queue list is not empty else returns None"""
        with self.lock:
            if self.isEmpty():
                return None
            else:
                returnval = heapq.heappop(self.ItemList)
                self.ItemHashList.pop(returnval[1])
                return returnval

    def pollTillAvailable(self):
        """For use in a multithreaded script, it polls priority queue in an loop until an item is available"""
        item = self.getItem()
        while item is None:
            item = self.getItem()

        return item

    def isEmpty(self):
        """Returns true if priority queue is empty, else returns false"""
        return not bool(len(self.ItemList))