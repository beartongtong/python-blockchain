import threading

import numpy as np
from heapq import heappush, heappop, heapify
from network.broadcast import broadcast
from factory.transaction import Transaction
from utils.helper import get_transmission_delay
from utils.priority_queue import PriorityQueue

# class PriorityQueue:
#     def __init__(self):
#         self.heap = []
#
#     def insert(self, item, priority):
#         heappush(self.heap, (-priority, item))
#
#     def get(self, count):
#         result = []
#         for _ in range(count):
#             if self.heap:
#                 result.append(heappop(self.heap)[1])
#         return result
#
#     def is_present(self, item):
#         return any(item == x[1] for x in self.heap)
#
#     def length(self):
#         return len(self.heap)
#
#     def peek_all(self):
#         """Return all items in the queue without removing them."""
#         return [item for _, item in self.heap]
#
#     def remove(self, item):
#         """Remove an item from the queue."""
#         self.heap = [(p, i) for p, i in self.heap if i != item]
#         heapify(self.heap)

class TransactionPool:
    """
    Transaction pool for a full node
    """

    def __init__(self, env, id, neighbours_ids, nodes, params):
        self.env = env
        self.id = id
        self.neighbours_ids = neighbours_ids
        self.params = params
        self.nodes = nodes
        # intra_shard_tx_queue: 一个优先级队列，用于存储同一个分片内的交易。优先级队列可以根据某种标准（如费用、时间戳等）对交易进行排序。
        # cross_shard_tx_queue: 另一个优先级队列，用于存储跨分片的交易。
        self.intra_shard_tx_queue = PriorityQueue()
        self.cross_shard_tx_queue = PriorityQueue()
        # prev_transactions: 一个列表，用于存储该节点已知的先前交易记录。
        # intra_shard_tx: 一个列表，用于存储该节点处理或生成的同分片内的交易。
        # cross_shard_tx: 一个列表，用于存储该节点处理或生成的跨分片交易。
        self.prev_transactions = []
        self.intra_shard_tx = []
        self.cross_shard_tx = []
        self.transactions = {}
        self.prev_transactions = []
        self.lock = threading.Lock()
        self.init_transactions()

    def init_transactions(self):
        """
        Initialize the transaction pool with a set of transactions
        """
        for i in range(self.params["num_shards"]):
            for j in range(self.params["num_shards"]):
                shard_key = (i, j)
                self.transactions[shard_key] = []

    def get_transaction(self, transaction_count, tx_type):
        """
        Return transaction_count number of Transactions. 
        Returns top transactions based on tx reward.
        这是一个文档字符串（docstring），用于解释方法的功能。这个方法返回指定数量的交易，
        这些交易是基于交易奖励（可能是费用、优先级等）排序的。
        """
        if tx_type == 'intra-shard':
            return self.intra_shard_tx_queue.get(transaction_count)
        elif tx_type == 'cross-shard':
            return self.cross_shard_tx_queue.get(transaction_count)
        else:
            raise RuntimeError("Unknown transaction type specified")


    def pop_transaction(self, transaction_count, tx_type):
        """
        Remove transactions from transaction pool. 
        Called when transactions are added by a received block or a block is mined.
        这个方法从交易池中删除指定数量的交易，这通常在一个新的区块被接收并加入到区块链，或者一个新的区块被挖掘出来时发生。
        """
        popped_transactions = None
        # 如果 tx_type 是 'intra-shard'，则从 intra_shard_tx_queue（同分片交易的优先级队列）中删除指定数量的交易。
        # 如果 tx_type 是 'cross-shard'，则从 cross_shard_tx_queue（跨分片交易的优先级队列）中删除指定数量的交易。
        if tx_type == 'intra-shard':
            popped_transactions = self.intra_shard_tx_queue.pop(transaction_count)
        elif tx_type == 'cross-shard':
            popped_transactions = self.cross_shard_tx_queue.pop(transaction_count)
        else:
            raise RuntimeError("Unknown transaction type specified")
        # 这行代码将被删除的交易添加到 prev_transactions 列表中。这可能用于跟踪节点已处理的交易，或者用于在需要时恢复这些交易。
        self.prev_transactions.append(popped_transactions)
        return popped_transactions

    # 接收三个参数：transaction（要处理的交易对象），source_location（交易源位置），和 tx_type（交易类型）。
    # 这个方法模拟了区块链网络中的节点如何处理接收到的交易：首先验证交易类型，计算从源到目的地的延迟，
    # 根据交易类型选择交易队列，并在满足条件的情况下将交易添加到队列中。最后，将交易广播到网络中的其他节点。
    def put_transaction(self, transaction, source_location, tx_type):
        """
        Add received transaction to the transaction pool and broadcast further
        """
        # 如果交易类型既不是 intra-shard（同分片）也不是 cross-shard（跨分片），则抛出一个运行时错误，表示指定了未知的交易类型。
        if not tx_type == 'intra-shard' and not tx_type == 'cross-shard':
            raise RuntimeError("Unknown transaction type specified")

        # 计算从源位置到当前节点位置的传输延迟。
        dest_location = self.nodes[self.id].location
        delay = get_transmission_delay(source_location, dest_location)

        # 根据交易类型选择相应的交易队列。
        curr_queue = self.intra_shard_tx_queue if tx_type == 'intra-shard' else self.cross_shard_tx_queue
        yield self.env.timeout(delay)  # 在模拟环境中等待计算出的延迟时间。
        if ( # 如果交易既不在当前队列中也不在之前处理过的交易列表中，则将其添加到当前队列。
            not curr_queue.is_present(transaction)
            and transaction not in self.prev_transactions
        ):

            curr_queue.insert(transaction)
            shard_key = (transaction.originate_shard, transaction.target_shard)
            self.transactions[shard_key].append(transaction)
            # 广播交易到邻居节点。如果当前节点没有下一跳节点（next_hop_id == -1），则只会将交易广播给自己，否则将其广播给下一跳节点。
            curr_node = self.nodes[self.id]
            neighbour_ids = [self.id if curr_node.next_hop_id == -1 else curr_node.next_hop_id]
            broadcast(self.env, transaction, "Tx", self.id, neighbour_ids, self.nodes, self.params)

            # 如果参数中启用了详细模式（verbose），则打印交易被当前节点接受的日志。
            if self.params["verbose"]:
                print(
                    "%7.4f : %s accepted by %s"
                    % (self.env.now, transaction.id, self.id)
                )
            # print(" self.intra_shard_tx_queue.qsize():",  self.intra_shard_tx_queue.qsize())
            # queue_size = self.intra_shard_tx_queue.length()
            # print(f"intra_shard_tx_queue队列当前的数据长度为: {queue_size}")
            # queue_size = self.cross_shard_tx_queue.length()
            # print(f"cross_shard_tx_queue队列当前的数据长度为: {queue_size}")
            # curr_node = self.nodes[self.id]
            # if curr_node.node_type == 2:
            #     print(f"Leader of the shard {curr_node.shard_id} is {self.id} and has {self.transaction_queue.length()} transactions")


    def put_transaction_dict(self, transaction, source_location, tx_type):
        """
        Add received transaction to the transaction pool and broadcast further
        """
        # 如果交易类型既不是 intra-shard（同分片）也不是 cross-shard（跨分片），则抛出一个运行时错误，表示指定了未知的交易类型。
        if not tx_type == 'intra-shard' and not tx_type == 'cross-shard':
            raise RuntimeError("Unknown transaction type specified")

        # 计算从源位置到当前节点位置的传输延迟。
        dest_location = self.nodes[self.id].location
        delay = get_transmission_delay(source_location, dest_location)

        # 根据交易类型选择相应的交易队列。
        curr_queue = self.intra_shard_tx_queue if tx_type == 'intra-shard' else self.cross_shard_tx_queue
        yield self.env.timeout(delay)  # 在模拟环境中等待计算出的延迟时间。
        if ( # 如果交易既不在当前队列中也不在之前处理过的交易列表中，则将其添加到当前队列。
                not curr_queue.is_present(transaction)
                and transaction not in self.prev_transactions
        ):
            # 必须得有curr_queue.insert(transaction)，不然fullnode那边会是空数据
            curr_queue.insert(transaction)
            shard_key = (transaction.originate_shard, transaction.target_shard)
            self.transactions[shard_key].append(transaction)
            # 广播交易到邻居节点。如果当前节点没有下一跳节点（next_hop_id == -1），则只会将交易广播给自己，否则将其广播给下一跳节点。
            curr_node = self.nodes[self.id]
            neighbour_ids = [self.id if curr_node.next_hop_id == -1 else curr_node.next_hop_id]
            broadcast(self.env, transaction, "Tx", self.id, neighbour_ids, self.nodes, self.params)

            # 如果参数中启用了详细模式（verbose），则打印交易被当前节点接受的日志。
            if self.params["verbose"]:
                print(
                    "%7.4f : %s accepted by %s"
                    % (self.env.now, transaction.id, self.id)
                )
            # print(" self.intra_shard_tx_queue.qsize():",  self.intra_shard_tx_queue.qsize())
            # queue_size = self.intra_shard_tx_queue.length()
            # print(f"intra_shard_tx_queue队列当前的数据长度为: {queue_size}")
            # queue_size = self.cross_shard_tx_queue.length()
            # print(f"cross_shard_tx_queue队列当前的数据长度为: {queue_size}")
            # curr_node = self.nodes[self.id]
            # if curr_node.node_type == 2:
            #     print(f"Leader of the shard {curr_node.shard_id} is {self.id} and has {self.transaction_queue.length()} transactions")
    def get_transaction_dict(self, transaction_count, tx_type ,originate_shard, target_shard):
        """
        Return transaction_count number of Transactions.
        Returns top transactions based on tx reward.
        """
        filtered_transactions = []
        for key, tx_list in self.transactions.items():
            for tx in tx_list:
                if (tx.cross_shard_status == 0 and tx_type == 'intra-shard') or (tx.cross_shard_status == 1 and tx_type == 'cross-shard'):
                    filtered_transactions.append(tx)

        sorted_transactions = sorted(filtered_transactions, key=lambda tx: tx.reward, reverse=True)
        return sorted_transactions[:transaction_count]

    def pop_transaction_with_shardID_dict(self, transaction_count, originate_shard, target_shard):


        """
        Remove transactions from transaction pool based on originate_shard and target_shard.
        """
        # 因为之前的curr_queue.insert(transaction)问题，所以清空了数据
        self.intra_shard_tx_queue.pop(self.intra_shard_tx_queue.length())
        self.cross_shard_tx_queue.pop(self.cross_shard_tx_queue.length())
        shard_key = (originate_shard, target_shard)
        popped_transactions = []
        if shard_key in self.transactions:
            for transaction in self.transactions[shard_key]:
                popped_transactions.append(transaction)
                if len(popped_transactions) >= transaction_count:
                    break

            self.transactions[shard_key] = [tx for tx in self.transactions[shard_key] if tx not in popped_transactions]

        self.prev_transactions.extend(popped_transactions)
        return popped_transactions





