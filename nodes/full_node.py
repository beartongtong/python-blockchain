from matplotlib.font_manager import json_dump
import numpy as np
import random
import functools
import operator
import json
import uuid
import time
from interruptingcow import timeout
import simpy
from nodes.participating_node import ParticipatingNode
from network.broadcast import broadcast
from network.mini_block import MiniBlock
from network.tx_block import TxBlock
from network.cross_shard_block import CrossShardBlock
from network.block import Block
from network.pipe import Pipe
from factory.transaction import Transaction
from factory.transaction_pool import TransactionPool
from network.consensus.consensus import Consensus
from utils.helper import get_transaction_delay, is_voting_complete, get_shard_neighbours, \
    get_principal_committee_neigbours, is_vote_casted, can_generate_block, has_received_mini_block, \
    is_voting_complete_for_cross_shard_block, is_vote_casted_for_cross_shard_block, \
    received_cross_shard_block_for_first_time, \
    filter_transactions


#class FullNode(ParticipatingNode): 定义了一个名为 FullNode 的类，它继承自 ParticipatingNode 类。这意味着 FullNode 类将继承 ParticipatingNode 类的所有方法和属性。
class FullNode(ParticipatingNode):
    """
    This class models the nodes which will take part in the Blockchain.
    These nodes are the subsets of the participating nodes.
    """
    #def __init__(self, id, env, location, params): 这是 FullNode 类的初始化方法。
    # 它接受四个参数：id（节点的唯一标识符）、env（模拟环境）、location（节点的位置）和params（节点的参数）。
    # 然后，它调用父类（ParticipatingNode）的初始化方法来进行初始化。
    def __init__(self, id, env, location, params):
        super().__init__(id, env, location, params)

        self.node_type = 0
        """ 
        node_type --
            0 - Node is in between re-configuration (slot)
            1 - Principal Committee
            2 - Shard Leader
            3 - Shard Member
            self.shard_id = -1 初始化分片 ID 为 -1，表示该节点尚未分配到任何分片。
            self.shard_leader_id = -1 初始化分片领导的 ID 为 -1，表示该节点尚未有分片领导。
            self.curr_shard_nodes = {} 初始化当前分片节点为空字典。
            self.neighbours_ids = [] 初始化邻居节点 ID 列表为空。
            self.blockchain = [] 初始化区块链为空列表。
            self.shard_leaders = {} 初始化分片领导为空字典。
            self.mini_block_consensus_pool = {} 等等，这些属性主要用于由主委员会处理的逻辑。
        """
        # 负载能力
        self.load_capacity = params["load_capacity"]
        # 当前负载
        self.current_load = 0

        self.shard_id = -1
        self.shard_leader_id = -1
        self.shard_type = 0
        self.curr_shard_nodes = {}
        self.neighbours_ids = []
        self.blockchain = []
        self.shard_leaders = {}

        # Handled by only principal committee
        self.mini_block_consensus_pool = {}
        self.processed_mini_blocks = []
        self.processed_tx_blocks = []
        self.current_tx_blocks = []
        
        # Experimental
        self.pc_leader_id = -1
        self.mini_blocks_vote_pool = []
        self.next_hop_id = -1

        # A-Msign
        self.public_key = None
        self.private_key = None

    #def add_network_parameters(self, curr_shard_nodes, neighbours_ids): 这个方法用于添加网络参数，包括当前分片的节点和邻居节点的 ID。
    # 它还初始化了交易池和管道，并启动了接收区块的进程。
    def add_network_parameters(self, curr_shard_nodes, neighbours_ids):

        self.curr_shard_nodes = curr_shard_nodes #当前分片中的所有节点列表。
        self.neighbours_ids = neighbours_ids #邻居节点的 ID 列表。
        self.transaction_pool = TransactionPool(
            self.env, self.id, neighbours_ids, curr_shard_nodes, self.params
        )
        self.pipes = Pipe(self.env, self.id, self.curr_shard_nodes) #管道
        self.env.process(self.receive_block())

    # def init_shard_leaders(self, leaders): 此方法用于初始化分片领导，接收一个领导者列表作为参数。
    def init_shard_leaders(self, leaders):
        self.shard_leaders = leaders

    # def update_neighbours(self, neighbours_ids): 此方法用于更新节点的邻居节点 ID 列表，并相应更新交易池中的邻居节点 ID 列表。
    def update_neighbours(self, neighbours_ids):
        self.neighbours_ids = neighbours_ids
        self.transaction_pool.neighbours_ids = neighbours_ids

    # 获取对应分片的节点ID
    def get_shard_nodes(self, shard_id):
        return self.params["shard_nodes"][shard_id]


    def get_shard_leaders(self, shard_id):
        return self.params["all_full_nodes"][self.params["shard_nodes"][shard_id][0]].shard_leader_id

    def generate_transactions_batch_size(self):
        """
        Generates transactions in the shard and broadcasts them to the neighbour nodes
        """
        # print("generate_transactions epoch:", self.params["current_epoch"])
        # 首先，方法通过一个条件判断来确保只有分片成员（node_type == 3）和分片领导（node_type == 2）可以生成交易。




        # 如果不是这两种类型的节点尝试调用此方法，将引发一个 RuntimeError。
        if not (self.node_type == 3 or self.node_type == 2):
            raise RuntimeError("Node not allowed to generate transactions.")

        # 标志变量，用于记录是否找到
        found = False
        paired_shard = None
        related_shard = None
        # 要查询的分片标识符
        shard_to_check = self.shard_id
        if self.params["current_epoch"] != 0:


            # 遍历字典中的每一个分片及其相关分片列表
            for shard, related_shards in self.params["Bshard_with_Ishard"].items():
                if shard_to_check in related_shards:
                    found = True
                    # 找到与 shard_to_check 配对的另一个分片标识符
                    related_shard = shard
                    paired_shard = next((shard_id for shard_id in related_shards if shard_id != shard_to_check), None)
                    # print(f"Shard {shard_to_check} exists in the related shards of shard {shard}.")
                    # print(f"The paired shard with {shard_to_check} is {paired_shard}.")
                    break

            # if not found:
                # print(f"Shard {shard_to_check} does not exist in any related shards.")

        while self.env.now < self.params["simulation_time"]:

            if found:
                # print(f"生成桥接分片{related_shard}的交易，{self.shard_id} to {paired_shard}")
                shard_key=(self.shard_id,paired_shard)

                for idx in range(self.params["tx_block_capacity"]):
                    delay = get_transaction_delay(
                        self.params["transaction_mu"], self.params["transaction_sigma"]
                    )
                    yield self.env.timeout(delay)

                    # 随机生成一个交易的价值 value，并根据这个价值和预设的奖励百分比 reward_percentage 来计算交易的奖励 reward。
                    value = np.random.randint(self.params["tx_value_low"], self.params["tx_value_high"])
                    reward = value * self.params["reward_percentage"]

                    # 初始化一个字典 transaction_state，用于跟踪当前分片中每个节点对该交易的状态（在此处初始化为 0）。
                    transaction_state = {key: 0 for key in self.curr_shard_nodes}

                    # 决定该笔交易是否为跨分片交易
                    cross_shard_status = random.random() <= self.params["cross_shard_tx_percentage"]

                    # 生成一个唯一的交易 ID
                    id = str(uuid.uuid4())
                    # 创建一个 Transaction 对象
                    transaction = Transaction(f"T_{self.id}_{id}", self.env.now, value, reward, transaction_state, cross_shard_status)

                    receiver_node_id = random.choice(self.params["shard_nodes"][paired_shard])
                    # receiver_node_id = random.choice(prepare_receiver_node_id)
                    if receiver_node_id == self.id:
                        continue

                    # 确认接收节点的类型和分片
                    if self.params["all_full_nodes"][receiver_node_id].node_type in [2, 3]:
                        if self.params["all_full_nodes"][receiver_node_id].shard_id != self.shard_id:
                            transaction.cross_shard_status = 1
                        else:
                            transaction.cross_shard_status = 0
                        transaction.set_receiver(receiver_node_id)

                    if transaction.receiver is None:
                        receiver_node_id = self.get_intra_shard_random_node_id()
                        transaction.set_receiver(receiver_node_id)

                    # 设置 originate_shard 和 target_shard 属性
                    transaction.set_originate_shard(self.shard_id)
                    transaction.set_target_shard(self.params["all_full_nodes"][receiver_node_id].shard_id)

                    # 更新统计信息
                    self.params["generated_tx_count"] += 1
                    self.params["generated_intra_shard_tx_count"] += 1 - transaction.cross_shard_status
                    self.params["generated_cross_shard_tx_count"] += transaction.cross_shard_status

                    self.params["epoch_generated_tx_count"][self.params['current_epoch']] += 1
                    self.params["epoch_generated_intra_shard_tx_count"][self.params['current_epoch']] += 1 - transaction.cross_shard_status
                    self.params["epoch_generated_cross_shard_tx_count"][self.params['current_epoch']] += transaction.cross_shard_status

                    self.params["epoch_shard_generated_tx_count"][self.params['current_epoch']][self.shard_id] += 1
                    self.params["epoch_shard_generated_intra_shard_tx_count"][self.params['current_epoch']][self.shard_id] += 1 - transaction.cross_shard_status
                    self.params["epoch_shard_generated_cross_shard_tx_count"][self.params['current_epoch']][self.shard_id] += transaction.cross_shard_status

                    # 更新图
                    if self.params["graph"].has_edge(self.id, transaction.receiver):
                        self.params["graph"][self.id][transaction.receiver]['weight'] += 1
                    else:
                        self.params["graph"].add_edge(self.id, transaction.receiver, weight=1)

                    # 打印交易详细信息
                    if self.params["verbose"]:
                        print(
                            "%7.4f" % self.env.now
                            + " : "
                            + "%s added with reward %.2f"
                            % (transaction.id, transaction.reward)
                        )

                    # 确定交易的下一跳节点 ID
                    # neighbour_ids = [self.id if self.next_hop_id == -1 else self.next_hop_id]
                    neighbour_ids = self.get_shard_nodes(related_shard)
                    # 广播交易
                    broadcast(
                        self.env,
                        transaction,
                        "Tx",
                        self.id,
                        neighbour_ids,
                        self.params["all_full_nodes"],
                        self.params
                    )
                    self.params["Node_transaction_generation_num"][self.id] = self.params["Node_transaction_generation_num"][self.id] + 1
                    # print("查看交易数",self.transaction_pool.transactions[shard_key])
            # if not found:
            for i in range(self.params["num_shards"]):
                # 计算下一笔交易的延迟时间
                delay = get_transaction_delay(
                    self.params["transaction_mu"], self.params["transaction_sigma"]
                )
                yield self.env.timeout(delay)

                # 随机生成一个交易的价值 value，并根据这个价值和预设的奖励百分比 reward_percentage 来计算交易的奖励 reward。
                value = np.random.randint(self.params["tx_value_low"], self.params["tx_value_high"])
                reward = value * self.params["reward_percentage"]

                # 初始化一个字典 transaction_state，用于跟踪当前分片中每个节点对该交易的状态（在此处初始化为 0）。
                transaction_state = {key: 0 for key in self.curr_shard_nodes}

                # 决定该笔交易是否为跨分片交易
                cross_shard_status = random.random() <= self.params["cross_shard_tx_percentage"]



                # 生成一个唯一的交易 ID
                id = str(uuid.uuid4())
                # 创建一个 Transaction 对象
                transaction = Transaction(f"T_{self.id}_{id}", self.env.now, value, reward, transaction_state, cross_shard_status)

                # # 确定接收节点
                # if cross_shard_status:
                #     receiver_node_id = self.get_cross_shard_random_node_id()
                # else:
                #     receiver_node_id = self.get_intra_shard_random_node_id()

                # 使用预设的频繁交易节点列表
                # prepare_receiver_node_id = self.params["frequent_transactions_custom"][self.id]
                # prepare_receiver_node_id.append(receiver_node_id)
                receiver_node_id = random.choice(self.params["shard_nodes"][i])
                # receiver_node_id = random.choice(prepare_receiver_node_id)
                if receiver_node_id == self.id:
                    continue

                # 确认接收节点的类型和分片
                if self.params["all_full_nodes"][receiver_node_id].node_type in [2, 3]:
                    if self.params["all_full_nodes"][receiver_node_id].shard_id != self.shard_id:
                        transaction.cross_shard_status = 1
                    else:
                        transaction.cross_shard_status = 0
                    transaction.set_receiver(receiver_node_id)

                if transaction.receiver is None:
                    receiver_node_id = self.get_intra_shard_random_node_id()
                    transaction.set_receiver(receiver_node_id)

                # 设置 originate_shard 和 target_shard 属性
                transaction.set_originate_shard(self.shard_id)
                transaction.set_target_shard(self.params["all_full_nodes"][receiver_node_id].shard_id)

                # 更新统计信息
                self.params["generated_tx_count"] += 1
                self.params["generated_intra_shard_tx_count"] += 1 - transaction.cross_shard_status
                self.params["generated_cross_shard_tx_count"] += transaction.cross_shard_status

                self.params["epoch_generated_tx_count"][self.params['current_epoch']] += 1
                self.params["epoch_generated_intra_shard_tx_count"][self.params['current_epoch']] += 1 - transaction.cross_shard_status
                self.params["epoch_generated_cross_shard_tx_count"][self.params['current_epoch']] += transaction.cross_shard_status

                self.params["epoch_shard_generated_tx_count"][self.params['current_epoch']][self.shard_id] += 1
                self.params["epoch_shard_generated_intra_shard_tx_count"][self.params['current_epoch']][self.shard_id] += 1 - transaction.cross_shard_status
                self.params["epoch_shard_generated_cross_shard_tx_count"][self.params['current_epoch']][self.shard_id] += transaction.cross_shard_status

                # 更新图
                if self.params["graph"].has_edge(self.id, transaction.receiver):
                    self.params["graph"][self.id][transaction.receiver]['weight'] += 1
                else:
                    self.params["graph"].add_edge(self.id, transaction.receiver, weight=1)

                # 打印交易详细信息
                if self.params["verbose"]:
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "%s added with reward %.2f"
                        % (transaction.id, transaction.reward)
                    )

                # 确定交易的下一跳节点 ID
                neighbour_ids = [self.id if self.next_hop_id == -1 else self.next_hop_id]
                # 广播交易
                broadcast(
                    self.env,
                    transaction,
                    "Tx",
                    self.id,
                    neighbour_ids,
                    self.curr_shard_nodes,
                    self.params
                )
                self.params["Node_transaction_generation_num"][self.id] = self.params["Node_transaction_generation_num"][self.id] + 1

    def generate_transactions_batch_size2(self):
        """
        Generates transactions in the shard and broadcasts them to the neighbour nodes
        """
        # print("generate_transactions epoch:", self.params["current_epoch"])
        # 首先，方法通过一个条件判断来确保只有分片成员（node_type == 3）和分片领导（node_type == 2）可以生成交易。




        # 如果不是这两种类型的节点尝试调用此方法，将引发一个 RuntimeError。
        if not (self.node_type == 3 or self.node_type == 2):
            raise RuntimeError("Node not allowed to generate transactions.")

        # 标志变量，用于记录是否找到
        found = False
        paired_shard = None
        related_shard = None
        # 要查询的分片标识符
        shard_to_check = self.shard_id
        # if self.params["current_epoch"] != 0:
        if self.params["chain_mode_type"] == 1:

            # 遍历字典中的每一个分片及其相关分片列表
            for shard, related_shards in self.params["Bshard_with_Ishard"].items():
                if shard_to_check in related_shards:
                    found = True
                    # 找到与 shard_to_check 配对的另一个分片标识符
                    related_shard = shard
                    paired_shard = next((shard_id for shard_id in related_shards if shard_id != shard_to_check), None)
                    # print(f"Shard {shard_to_check} exists in the related shards of shard {shard}.")
                    # print(f"The paired shard with {shard_to_check} is {paired_shard}.")
                    break

            # if not found:
            # print(f"Shard {shard_to_check} does not exist in any related shards.")

        while self.env.now < self.params["simulation_time"]:

            if found:
                # print(f"生成桥接分片{related_shard}的交易，{self.shard_id} to {paired_shard}")
                shard_key=(self.shard_id,paired_shard)

                # for idx in range(self.params["tx_block_capacity"]):
                delay = get_transaction_delay(
                    self.params["transaction_mu"], self.params["transaction_sigma"]
                )
                yield self.env.timeout(delay)

                # 随机生成一个交易的价值 value，并根据这个价值和预设的奖励百分比 reward_percentage 来计算交易的奖励 reward。
                value = np.random.randint(self.params["tx_value_low"], self.params["tx_value_high"])
                reward = value * self.params["reward_percentage"]

                # 初始化一个字典 transaction_state，用于跟踪当前分片中每个节点对该交易的状态（在此处初始化为 0）。
                transaction_state = {key: 0 for key in self.curr_shard_nodes}

                # 决定该笔交易是否为跨分片交易
                cross_shard_status = random.random() <= self.params["cross_shard_tx_percentage"]

                # 生成一个唯一的交易 ID
                id = str(uuid.uuid4())
                # 创建一个 Transaction 对象
                transaction = Transaction(f"T_{self.id}_{id}", self.env.now, value, reward, transaction_state, cross_shard_status)

                receiver_node_id = random.choice(self.params["shard_nodes"][paired_shard])
                # receiver_node_id = random.choice(prepare_receiver_node_id)
                if receiver_node_id == self.id:
                    continue

                # 确认接收节点的类型和分片
                if self.params["all_full_nodes"][receiver_node_id].node_type in [2, 3]:
                    if self.params["all_full_nodes"][receiver_node_id].shard_id != self.shard_id:
                        transaction.cross_shard_status = 1
                    else:
                        transaction.cross_shard_status = 0
                    transaction.set_receiver(receiver_node_id)

                if transaction.receiver is None:
                    receiver_node_id = self.get_intra_shard_random_node_id()
                    transaction.set_receiver(receiver_node_id)

                # 设置 originate_shard 和 target_shard 属性
                transaction.set_originate_shard(self.shard_id)
                transaction.set_target_shard(self.params["all_full_nodes"][receiver_node_id].shard_id)

                # 更新统计信息
                self.params["generated_tx_count"] += 1
                self.params["generated_intra_shard_tx_count"] += 1 - transaction.cross_shard_status
                self.params["generated_cross_shard_tx_count"] += transaction.cross_shard_status

                self.params["epoch_generated_tx_count"][self.params['current_epoch']] += 1
                self.params["epoch_generated_intra_shard_tx_count"][self.params['current_epoch']] += 1 - transaction.cross_shard_status
                self.params["epoch_generated_cross_shard_tx_count"][self.params['current_epoch']] += transaction.cross_shard_status

                self.params["epoch_shard_generated_tx_count"][self.params['current_epoch']][self.shard_id] += 1
                self.params["epoch_shard_generated_intra_shard_tx_count"][self.params['current_epoch']][self.shard_id] += 1 - transaction.cross_shard_status
                self.params["epoch_shard_generated_cross_shard_tx_count"][self.params['current_epoch']][self.shard_id] += transaction.cross_shard_status

                # 更新图
                if self.params["graph"].has_edge(self.id, transaction.receiver):
                    self.params["graph"][self.id][transaction.receiver]['weight'] += 1
                else:
                    self.params["graph"].add_edge(self.id, transaction.receiver, weight=1)

                # 打印交易详细信息
                if self.params["verbose"]:
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "%s added with reward %.2f"
                        % (transaction.id, transaction.reward)
                    )

                # 确定交易的下一跳节点 ID
                # neighbour_ids = [self.id if self.next_hop_id == -1 else self.next_hop_id]
                neighbour_ids = self.get_shard_nodes(related_shard)
                # 广播交易
                broadcast(
                    self.env,
                    transaction,
                    "Tx",
                    self.id,
                    neighbour_ids,
                    self.params["all_full_nodes"],
                    self.params
                )
                self.params["Node_transaction_generation_num"][self.id] = self.params["Node_transaction_generation_num"][self.id] + 1
                    # print("查看交易数",self.transaction_pool.transactions[shard_key])
            # if not found:
            # for i in range(self.params["num_shards"]):

            # 计算下一笔交易的延迟时间
            delay = get_transaction_delay(
                self.params["transaction_mu"], self.params["transaction_sigma"]
            )
            yield self.env.timeout(delay)

            # 随机生成一个交易的价值 value，并根据这个价值和预设的奖励百分比 reward_percentage 来计算交易的奖励 reward。
            value = np.random.randint(self.params["tx_value_low"], self.params["tx_value_high"])
            reward = value * self.params["reward_percentage"]

            # 初始化一个字典 transaction_state，用于跟踪当前分片中每个节点对该交易的状态（在此处初始化为 0）。
            transaction_state = {key: 0 for key in self.curr_shard_nodes}

            # 决定该笔交易是否为跨分片交易
            cross_shard_status = random.random() <= self.params["cross_shard_tx_percentage"]



            # 生成一个唯一的交易 ID
            id = str(uuid.uuid4())
            # 创建一个 Transaction 对象
            transaction = Transaction(f"T_{self.id}_{id}", self.env.now, value, reward, transaction_state, cross_shard_status)

            receiver_node_id = None
            # 确定接收节点
            if cross_shard_status:
                valid_numbers = [i for i in range(0, self.params["num_shards"]-1) if i != self.shard_id]
                random_integer = random.choice(valid_numbers)
                receiver_node_id = random.choice(self.params["shard_nodes"][random_integer])
            else:
                # 获取当前分片中的所有节点
                shard_nodes = self.params["shard_nodes"][self.shard_id]
                receiver_node_id = random.choice(shard_nodes)
                while receiver_node_id == self.id:
                    receiver_node_id = random.choice(shard_nodes)



            # 使用预设的频繁交易节点列表
            # prepare_receiver_node_id = self.params["frequent_transactions_custom"][self.id]
            # prepare_receiver_node_id.append(receiver_node_id)
            # receiver_node_id = random.choice(self.params["shard_nodes"][i])
            # receiver_node_id = random.choice(prepare_receiver_node_id)
            if receiver_node_id == self.id:
                continue

            # 确认接收节点的类型和分片
            if self.params["all_full_nodes"][receiver_node_id].node_type in [2, 3]:
                if self.params["all_full_nodes"][receiver_node_id].shard_id != self.shard_id:
                    transaction.cross_shard_status = 1
                else:
                    transaction.cross_shard_status = 0
                transaction.set_receiver(receiver_node_id)

            if transaction.receiver is None:
                receiver_node_id = self.get_intra_shard_random_node_id()
                transaction.set_receiver(receiver_node_id)

            # 设置 originate_shard 和 target_shard 属性
            transaction.set_originate_shard(self.shard_id)
            transaction.set_target_shard(self.params["all_full_nodes"][receiver_node_id].shard_id)

            # 更新统计信息
            self.params["generated_tx_count"] += 1
            self.params["generated_intra_shard_tx_count"] += 1 - transaction.cross_shard_status
            self.params["generated_cross_shard_tx_count"] += transaction.cross_shard_status

            self.params["epoch_generated_tx_count"][self.params['current_epoch']] += 1
            self.params["epoch_generated_intra_shard_tx_count"][self.params['current_epoch']] += 1 - transaction.cross_shard_status
            self.params["epoch_generated_cross_shard_tx_count"][self.params['current_epoch']] += transaction.cross_shard_status

            self.params["epoch_shard_generated_tx_count"][self.params['current_epoch']][self.shard_id] += 1
            self.params["epoch_shard_generated_intra_shard_tx_count"][self.params['current_epoch']][self.shard_id] += 1 - transaction.cross_shard_status
            self.params["epoch_shard_generated_cross_shard_tx_count"][self.params['current_epoch']][self.shard_id] += transaction.cross_shard_status

            # 更新图
            if self.params["graph"].has_edge(self.id, transaction.receiver):
                self.params["graph"][self.id][transaction.receiver]['weight'] += 1
            else:
                self.params["graph"].add_edge(self.id, transaction.receiver, weight=1)

            # 打印交易详细信息
            if self.params["verbose"]:
                print(
                    "%7.4f" % self.env.now
                    + " : "
                    + "%s added with reward %.2f"
                    % (transaction.id, transaction.reward)
                )

            # 确定交易的下一跳节点 ID
            neighbour_ids = [self.id if self.next_hop_id == -1 else self.next_hop_id]
            # 广播交易
            broadcast(
                self.env,
                transaction,
                "Tx",
                self.id,
                neighbour_ids,
                self.curr_shard_nodes,
                self.params
            )
            self.params["Node_transaction_generation_num"][self.id] = self.params["Node_transaction_generation_num"][self.id] + 1

    def generate_transactions_batch_size3(self):
        """
        Generates transactions in the shard and broadcasts them to the neighbour nodes
        """
        # print("generate_transactions epoch:", self.params["current_epoch"])
        # 首先，方法通过一个条件判断来确保只有分片成员（node_type == 3）和分片领导（node_type == 2）可以生成交易。




        # 如果不是这两种类型的节点尝试调用此方法，将引发一个 RuntimeError。
        if not (self.node_type == 3 or self.node_type == 2):
            raise RuntimeError("Node not allowed to generate transactions.")

        # 标志变量，用于记录是否找到
        found = False
        paired_shard = None
        related_shard = None
        # 要查询的分片标识符
        shard_to_check = self.shard_id
        # if self.params["current_epoch"] != 0:
        if self.params["chain_mode_type"] == 1:

            # 遍历字典中的每一个分片及其相关分片列表
            for shard, related_shards in self.params["Bshard_with_Ishard"].items():
                if shard_to_check in related_shards:
                    found = True
                    # 找到与 shard_to_check 配对的另一个分片标识符
                    related_shard = shard
                    paired_shard = next((shard_id for shard_id in related_shards if shard_id != shard_to_check), None)
                    # print(f"Shard {shard_to_check} exists in the related shards of shard {shard}.")
                    # print(f"The paired shard with {shard_to_check} is {paired_shard}.")
                    break

            # if not found:
            # print(f"Shard {shard_to_check} does not exist in any related shards.")

        while self.env.now < self.params["simulation_time"]:

            if found:
                # print(f"生成桥接分片{related_shard}的交易，{self.shard_id} to {paired_shard}")
                shard_key=(self.shard_id,paired_shard)

                # for idx in range(self.params["tx_block_capacity"]):
                delay = get_transaction_delay(
                    self.params["transaction_mu"], self.params["transaction_sigma"]
                )
                yield self.env.timeout(delay)


                # 创建一个 Transaction 对象
                transaction = self.create_transactionk()

                receiver_node_id = random.choice(self.params["shard_nodes"][paired_shard])
                # receiver_node_id = random.choice(prepare_receiver_node_id)
                if receiver_node_id == self.id:
                    continue

                # 确认接收节点的类型和分片
                if self.params["all_full_nodes"][receiver_node_id].node_type in [2, 3]:
                    if self.params["all_full_nodes"][receiver_node_id].shard_id != self.shard_id:
                        transaction.cross_shard_status = 1
                    else:
                        transaction.cross_shard_status = 0
                    transaction.set_receiver(receiver_node_id)

                if transaction.receiver is None:
                    receiver_node_id = self.get_intra_shard_random_node_id()
                    transaction.set_receiver(receiver_node_id)

                # 设置 originate_shard 和 target_shard 属性
                transaction.set_originate_shard(self.shard_id)
                transaction.set_target_shard(self.params["all_full_nodes"][receiver_node_id].shard_id)

                # 更新统计信息
                self.params["generated_tx_count"] += 1
                self.params["generated_intra_shard_tx_count"] += 1 - transaction.cross_shard_status
                self.params["generated_cross_shard_tx_count"] += transaction.cross_shard_status

                self.params["epoch_generated_tx_count"][self.params['current_epoch']] += 1
                self.params["epoch_generated_intra_shard_tx_count"][self.params['current_epoch']] += 1 - transaction.cross_shard_status
                self.params["epoch_generated_cross_shard_tx_count"][self.params['current_epoch']] += transaction.cross_shard_status

                self.params["epoch_shard_generated_tx_count"][self.params['current_epoch']][self.shard_id] += 1
                self.params["epoch_shard_generated_intra_shard_tx_count"][self.params['current_epoch']][self.shard_id] += 1 - transaction.cross_shard_status
                self.params["epoch_shard_generated_cross_shard_tx_count"][self.params['current_epoch']][self.shard_id] += transaction.cross_shard_status

                # 更新图
                if self.params["graph"].has_edge(self.id, transaction.receiver):
                    self.params["graph"][self.id][transaction.receiver]['weight'] += 1
                else:
                    self.params["graph"].add_edge(self.id, transaction.receiver, weight=1)

                # 打印交易详细信息
                if self.params["verbose"]:
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "%s added with reward %.2f"
                        % (transaction.id, transaction.reward)
                    )

                # 确定交易的下一跳节点 ID
                # neighbour_ids = [self.id if self.next_hop_id == -1 else self.next_hop_id]
                neighbour_ids = self.get_shard_nodes(related_shard)
                # 广播交易
                broadcast(
                    self.env,
                    transaction,
                    "Tx",
                    self.id,
                    neighbour_ids,
                    self.params["all_full_nodes"],
                    self.params
                )
                self.params["Node_transaction_generation_num"][self.id] = self.params["Node_transaction_generation_num"][self.id] + 1
                # print("查看交易数",self.transaction_pool.transactions[shard_key])
            # if not found:
            # for i in range(self.params["num_shards"]):

            # 计算下一笔交易的延迟时间
            delay = get_transaction_delay(
                self.params["transaction_mu"], self.params["transaction_sigma"]
            )
            yield self.env.timeout(delay)



            transaction = self.create_transactionk()

            receiver_node_id = None
            # 确定接收节点
            # if cross_shard_status:
            #     valid_numbers = [i for i in range(0, self.params["num_shards"]-1) if i != self.shard_id]
            #     random_integer = random.choice(valid_numbers)
            #     receiver_node_id = random.choice(self.params["shard_nodes"][random_integer])
            # else:
            #     # 获取当前分片中的所有节点
            #     shard_nodes = self.params["shard_nodes"][self.shard_id]
            #     receiver_node_id = random.choice(shard_nodes)
            #     while receiver_node_id == self.id:
            #         receiver_node_id = random.choice(shard_nodes)

            valid_numbers = [i for i in range(0, self.params["num_shards"]-1) if i != self.shard_id]
            random_integer = random.choice(valid_numbers)
            receiver_node_id = random.choice(self.params["shard_nodes"][random_integer])


            # 使用预设的频繁交易节点列表
            # prepare_receiver_node_id = self.params["frequent_transactions_custom"][self.id]
            # prepare_receiver_node_id.append(receiver_node_id)
            # receiver_node_id = random.choice(self.params["shard_nodes"][i])
            # receiver_node_id = random.choice(prepare_receiver_node_id)
            if receiver_node_id == self.id:
                continue

            # 确认接收节点的类型和分片
            if self.params["all_full_nodes"][receiver_node_id].node_type in [2, 3]:
                if self.params["all_full_nodes"][receiver_node_id].shard_id != self.shard_id:
                    transaction.cross_shard_status = 1
                else:
                    transaction.cross_shard_status = 0
                transaction.set_receiver(receiver_node_id)

            if transaction.receiver is None:
                receiver_node_id = self.get_intra_shard_random_node_id()
                transaction.set_receiver(receiver_node_id)

            # 设置 originate_shard 和 target_shard 属性
            transaction.set_originate_shard(self.shard_id)
            transaction.set_target_shard(self.params["all_full_nodes"][receiver_node_id].shard_id)

            # 更新统计信息
            self.params["generated_tx_count"] += 1
            self.params["generated_intra_shard_tx_count"] += 1 - transaction.cross_shard_status
            self.params["generated_cross_shard_tx_count"] += transaction.cross_shard_status

            self.params["epoch_generated_tx_count"][self.params['current_epoch']] += 1
            self.params["epoch_generated_intra_shard_tx_count"][self.params['current_epoch']] += 1 - transaction.cross_shard_status
            self.params["epoch_generated_cross_shard_tx_count"][self.params['current_epoch']] += transaction.cross_shard_status

            self.params["epoch_shard_generated_tx_count"][self.params['current_epoch']][self.shard_id] += 1
            self.params["epoch_shard_generated_intra_shard_tx_count"][self.params['current_epoch']][self.shard_id] += 1 - transaction.cross_shard_status
            self.params["epoch_shard_generated_cross_shard_tx_count"][self.params['current_epoch']][self.shard_id] += transaction.cross_shard_status

            # 更新图
            if self.params["graph"].has_edge(self.id, transaction.receiver):
                self.params["graph"][self.id][transaction.receiver]['weight'] += 1
            else:
                self.params["graph"].add_edge(self.id, transaction.receiver, weight=1)

            # 打印交易详细信息
            if self.params["verbose"]:
                print(
                    "%7.4f" % self.env.now
                    + " : "
                    + "%s added with reward %.2f"
                    % (transaction.id, transaction.reward)
                )

            # 确定交易的下一跳节点 ID
            neighbour_ids = [self.id if self.next_hop_id == -1 else self.next_hop_id]
            # 广播交易
            broadcast(
                self.env,
                transaction,
                "Tx",
                self.id,
                neighbour_ids,
                self.curr_shard_nodes,
                self.params
            )
            self.params["Node_transaction_generation_num"][self.id] = self.params["Node_transaction_generation_num"][self.id] + 1

    def generate_transactions_batch_size4(self):
        """
        Generates transactions in the shard and broadcasts them to the neighbour nodes
        """
        # print("generate_transactions epoch:", self.params["current_epoch"])
        # 首先，方法通过一个条件判断来确保只有分片成员（node_type == 3）和分片领导（node_type == 2）可以生成交易。




        # 如果不是这两种类型的节点尝试调用此方法，将引发一个 RuntimeError。
        if not (self.node_type == 3 or self.node_type == 2):
            raise RuntimeError("Node not allowed to generate transactions.")

        # 标志变量，用于记录是否找到
        found = False
        paired_shard = None
        related_shard = None
        # 要查询的分片标识符
        shard_to_check = self.shard_id
        # if self.params["current_epoch"] != 0:
        if self.params["chain_mode_type"] == 1 and self.params["run_type"] == 2 :

            # 遍历字典中的每一个分片及其相关分片列表
            for shard, related_shards in self.params["Bshard_with_Ishard"].items():
                if shard_to_check in related_shards:
                    found = True
                    # 找到与 shard_to_check 配对的另一个分片标识符
                    related_shard = shard
                    paired_shard = next((shard_id for shard_id in related_shards if shard_id != shard_to_check), None)
                    # print(f"Shard {shard_to_check} exists in the related shards of shard {shard}.")
                    # print(f"The paired shard with {shard_to_check} is {paired_shard}.")
                    break

            # if not found:
            # print(f"Shard {shard_to_check} does not exist in any related shards.")

        while self.env.now < self.params["simulation_time"]:

            if found:
                # print(f"生成桥接分片{related_shard}的交易，{self.shard_id} to {paired_shard}")
                shard_key=(self.shard_id,paired_shard)

                # for idx in range(self.params["tx_block_capacity"]):
                delay = get_transaction_delay(
                    self.params["transaction_mu"], self.params["transaction_sigma"]
                )
                yield self.env.timeout(delay)


                # 创建一个 Transaction 对象
                transaction = self.create_transactionk()

                receiver_node_id = random.choice(self.params["shard_nodes"][paired_shard])
                # receiver_node_id = random.choice(prepare_receiver_node_id)
                if receiver_node_id == self.id:
                    continue

                # 确认接收节点的类型和分片
                if self.params["all_full_nodes"][receiver_node_id].node_type in [2, 3]:
                    if self.params["all_full_nodes"][receiver_node_id].shard_id != self.shard_id:
                        transaction.cross_shard_status = 1
                    else:
                        transaction.cross_shard_status = 0
                    transaction.set_receiver(receiver_node_id)

                if transaction.receiver is None:
                    receiver_node_id = self.get_intra_shard_random_node_id()
                    transaction.set_receiver(receiver_node_id)

                # 设置 originate_shard 和 target_shard 属性
                transaction.set_originate_shard(self.shard_id)
                transaction.set_target_shard(self.params["all_full_nodes"][receiver_node_id].shard_id)

                # 更新统计信息
                self.params["generated_tx_count"] += 1
                self.params["generated_intra_shard_tx_count"] += 1 - transaction.cross_shard_status
                self.params["generated_cross_shard_tx_count"] += transaction.cross_shard_status

                self.params["epoch_generated_tx_count"][self.params['current_epoch']] += 1
                self.params["epoch_generated_intra_shard_tx_count"][self.params['current_epoch']] += 1 - transaction.cross_shard_status
                self.params["epoch_generated_cross_shard_tx_count"][self.params['current_epoch']] += transaction.cross_shard_status

                self.params["epoch_shard_generated_tx_count"][self.params['current_epoch']][self.shard_id] += 1
                self.params["epoch_shard_generated_intra_shard_tx_count"][self.params['current_epoch']][self.shard_id] += 1 - transaction.cross_shard_status
                self.params["epoch_shard_generated_cross_shard_tx_count"][self.params['current_epoch']][self.shard_id] += transaction.cross_shard_status

                # 更新图
                if self.params["graph"].has_edge(self.id, transaction.receiver):
                    self.params["graph"][self.id][transaction.receiver]['weight'] += 1
                else:
                    self.params["graph"].add_edge(self.id, transaction.receiver, weight=1)

                # 打印交易详细信息
                if self.params["verbose"]:
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "%s added with reward %.2f"
                        % (transaction.id, transaction.reward)
                    )

                # 确定交易的下一跳节点 ID
                # neighbour_ids = [self.id if self.next_hop_id == -1 else self.next_hop_id]
                neighbour_ids = self.get_shard_nodes(related_shard)
                # 广播交易
                broadcast(
                    self.env,
                    transaction,
                    "Tx",
                    self.id,
                    neighbour_ids,
                    self.params["all_full_nodes"],
                    self.params
                )
                self.params["Node_transaction_generation_num"][self.id] = self.params["Node_transaction_generation_num"][self.id] + 1
                # print("查看交易数",self.transaction_pool.transactions[shard_key])
            # if not found:
            # for i in range(self.params["num_shards"]):

            # 计算下一笔交易的延迟时间
            delay = get_transaction_delay(
                self.params["transaction_mu"], self.params["transaction_sigma"]
            )
            yield self.env.timeout(delay)



            transaction = self.create_transactionk()

            valid_numbers = [i for i in range(0, self.params["num_shards"]-1) if i != self.shard_id]
            random_integer = random.choice(valid_numbers)
            receiver_node_id = random.choice(self.params["shard_nodes"][random_integer])


            # 使用预设的频繁交易节点列表
            prepare_receiver_node_id = self.params["frequent_transactions_custom"][self.id]
            prepare_receiver_node_id.append(receiver_node_id)

            while True:
                receiver_node_id = random.choice(prepare_receiver_node_id)
                # 确认接收节点的类型和分片
                if self.params["all_full_nodes"][receiver_node_id].node_type in [2, 3]:
                    if self.params["all_full_nodes"][receiver_node_id].shard_id != self.shard_id:
                        transaction.cross_shard_status = 1
                    else:
                        transaction.cross_shard_status = 0
                    transaction.set_receiver(receiver_node_id)
                    break




            if transaction.receiver is None:
                receiver_node_id = self.get_intra_shard_random_node_id()
                transaction.set_receiver(receiver_node_id)

            # 设置 originate_shard 和 target_shard 属性
            transaction.set_originate_shard(self.shard_id)
            transaction.set_target_shard(self.params["all_full_nodes"][receiver_node_id].shard_id)

            # 更新统计信息
            self.params["generated_tx_count"] += 1
            self.params["generated_intra_shard_tx_count"] += 1 - transaction.cross_shard_status
            self.params["generated_cross_shard_tx_count"] += transaction.cross_shard_status

            self.params["epoch_generated_tx_count"][self.params['current_epoch']] += 1
            self.params["epoch_generated_intra_shard_tx_count"][self.params['current_epoch']] += 1 - transaction.cross_shard_status
            self.params["epoch_generated_cross_shard_tx_count"][self.params['current_epoch']] += transaction.cross_shard_status

            self.params["epoch_shard_generated_tx_count"][self.params['current_epoch']][self.shard_id] += 1
            self.params["epoch_shard_generated_intra_shard_tx_count"][self.params['current_epoch']][self.shard_id] += 1 - transaction.cross_shard_status
            self.params["epoch_shard_generated_cross_shard_tx_count"][self.params['current_epoch']][self.shard_id] += transaction.cross_shard_status

            # 更新图
            if self.params["graph"].has_edge(self.id, transaction.receiver):
                self.params["graph"][self.id][transaction.receiver]['weight'] += 1
            else:
                self.params["graph"].add_edge(self.id, transaction.receiver, weight=1)

            # 打印交易详细信息
            if self.params["verbose"]:
                print(
                    "%7.4f" % self.env.now
                    + " : "
                    + "%s added with reward %.2f"
                    % (transaction.id, transaction.reward)
                )

            # 确定交易的下一跳节点 ID
            neighbour_ids = [self.id if self.next_hop_id == -1 else self.next_hop_id]
            # 广播交易
            broadcast(
                self.env,
                transaction,
                "Tx",
                self.id,
                neighbour_ids,
                self.curr_shard_nodes,
                self.params
            )
            self.params["Node_transaction_generation_num"][self.id] = self.params["Node_transaction_generation_num"][self.id] + 1

    #生成交易
    def generate_transactions(self, mode_type):
        """
        Generates transactions in the shard and broadcasts it to the neighbour nodes
        """

        if mode_type == 1:
            # print("generate_transactions epoch:", self.params["current_epoch"])
            #首先，方法通过一个条件判断来确保只有分片成员（node_type == 3）和分片领导（node_type == 2）可以生成交易。
            # 如果不是这两种类型的节点尝试调用此方法，将引发一个 RuntimeError。
            if not (self.node_type == 3 or self.node_type == 2):
                raise RuntimeError("Node not allowed to generate transactions.")
            print("while外 节点" + self.id + "生成交易", self.curr_shard_nodes.keys())

            if self.node_type == 3 :
                print("当前节点是分片成员")

            if self.node_type == 2 :
                print("当前节点是分片领导")
            num = 0
            # while num < self.params["transaction_generation_num"]:
            while self.env.now < self.params["simulation_time"]:

                # if self.current_load >= self.load_capacity:
                #     # delay = get_transaction_delay(
                #     #     self.params["transaction_mu"], self.params["transaction_sigma"]
                #     # )
                yield self.env.timeout(self.params["Node_processing_delay"][self.id])

                # 在每次循环中，首先通过调用 get_transaction_delay 函数计算下一笔交易的延迟时间。这个函数可能基于某种随机过程来决定每笔交易之间的时间间隔。
                delay = get_transaction_delay(
                    self.params["transaction_mu"], self.params["transaction_sigma"]
                )
                # 使用 yield self.env.timeout(delay) 暂停执行，直到下一次交易的延迟时间过去。这里的 env 是模拟环境，用于控制时间流逝。
                yield self.env.timeout(delay)

                # 接下来，随机生成一个交易的价值 value，并根据这个价值和预设的奖励百分比 reward_percentage 来计算交易的奖励 reward。
                value = np.random.randint(self.params["tx_value_low"], self.params["tx_value_high"])
                reward = value * self.params["reward_percentage"]

                # 初始化一个字典 transaction_state，用于跟踪当前分片中每个节点对该交易的状态（在此处初始化为 0）。
                transaction_state = {}
                for key, value in self.curr_shard_nodes.items():
                    transaction_state[key] = 0

                # 通过比较随机生成的数和预设的跨分片交易百分比 cross_shard_tx_percentage 来决定该笔交易是否为跨分片交易。
                cross_shard_status = random.random() <= self.params["cross_shard_tx_percentage"]




                # 生成一个唯一的交易 ID，使用 uuid.uuid4() 生成一个全局唯一标识符。
                # id = int(1000*round(self.env.now, 3))
                id = str(uuid.uuid4())
                # 创建一个 Transaction 对象，包含交易 ID、当前时间戳、价值、奖励、交易状态和是否为跨分片交易的标志。
                transaction = Transaction(f"T_{self.id}_{id}", self.env.now, value, reward, transaction_state, cross_shard_status)

                # print("cross_shard_status:", cross_shard_status)
                # print("self.get_intra_shard_random_node_id():", self.get_intra_shard_random_node_id())
                # self.get_intra_shard_random_node_id()

                if cross_shard_status:
                    receiver_node_id = self.get_cross_shard_random_node_id()
                    # transaction.set_receiver(receiver_node_id)
                    # transaction.cross_shard_status = 1
                else:
                    receiver_node_id = self.get_intra_shard_random_node_id()
                    # transaction.set_receiver(receiver_node_id)

                prepare_receiver_node_id = self.params["frequent_transactions_custom"][self.id]
                prepare_receiver_node_id.append(receiver_node_id)
                receiver_node_id = random.choice(prepare_receiver_node_id)

                # while transaction.receiver == None:
                #     if self.params["all_full_nodes"][receiver_node_id].node_type == 1:
                #         receiver_node_id = random.choice(prepare_receiver_node_id)
                #     else:
                #         transaction.set_receiver(receiver_node_id)


                if self.params["all_full_nodes"][receiver_node_id].node_type == 2 or self.params["all_full_nodes"][receiver_node_id].node_type == 3:
                    if self.params["all_full_nodes"][receiver_node_id].shard_id != self.shard_id:
                        transaction.cross_shard_status = 1
                    else:
                        transaction.cross_shard_status = 0
                    transaction.set_receiver(receiver_node_id)

                if transaction.receiver == None:
                    receiver_node_id = self.get_intra_shard_random_node_id()
                    transaction.set_receiver(receiver_node_id)



                # for txn in cross_shard_txns:
                #     txn.cross_shard_status = 1
                #     receiver_node_id = self.get_cross_shard_random_node_id()
                #
                #     if self.curr_shard_nodes[receiver_node_id].node_type == 1:
                #         print(self.shard_leaders.keys())
                #         raise RuntimeError(f"Principal committee node {receiver_node_id} can't be a receiver of cross-shard tx for tx {txn.id}")
                #     txn.set_receiver(receiver_node_id)


                # 更新一些参数来跟踪生成的交易数量，包括总交易数、内分片交易数和跨分片交易数。
                self.params["generated_tx_count"] += 1
                self.params["generated_intra_shard_tx_count"] += 1 - cross_shard_status
                self.params["generated_cross_shard_tx_count"] += cross_shard_status

                self.params["epoch_generated_tx_count"][self.params['current_epoch']] += 1
                self.params["epoch_generated_intra_shard_tx_count"][self.params['current_epoch']] += 1 - cross_shard_status
                self.params["epoch_generated_cross_shard_tx_count"][self.params['current_epoch']] += cross_shard_status

                self.params["epoch_shard_generated_tx_count"][self.params['current_epoch']][self.shard_id] += 1
                self.params["epoch_shard_generated_intra_shard_tx_count"][self.params['current_epoch']][self.shard_id] += 1 - cross_shard_status
                self.params["epoch_shard_generated_cross_shard_tx_count"][self.params['current_epoch']][self.shard_id] += cross_shard_status

                # 更新图
                self.params["graph"]
                if  self.params["graph"].has_edge(self.id, transaction.receiver):
                    # 如果边已经存在，则增加权重（即交易次数）
                    self.params["graph"][self.id][transaction.receiver]['weight'] += 1
                else:
                    # 否则，创建一条新的边，并设置权重为 1
                    self.params["graph"].add_edge(self.id, transaction.receiver, weight=1)

                # 如果启用了详细模式（verbose 参数为真），则打印交易的详细信息。
                if self.params["verbose"]:
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "%s added with reward %.2f"
                        % (transaction.id, transaction.reward)
                    )

                # 确定交易的下一跳节点 ID。如果没有指定下一跳（next_hop_id == -1），则使用当前节点的 ID 作为下一跳。
                neighbour_ids = [self.id if self.next_hop_id == -1 else self.next_hop_id]
                # 调用 broadcast 函数将交易广播给邻近的节点。这个函数需要传入环境、交易对象、消息类型、当前节点 ID、邻居节点 ID 列表、当前分片节点和节点参数。
                broadcast(
                    self.env,
                    transaction,
                    "Tx",
                    self.id,
                    neighbour_ids,
                    self.curr_shard_nodes,
                    self.params
                )

                num += 1
                # print("while内 节点" + self.id + "生成交易")
                # self.current_load = self.current_load + 1
                # print("当前系统生成交易数：", self.params["generated_tx_count"])
                self.params["Node_transaction_generation_num"][self.id] = self.params["Node_transaction_generation_num"][self.id] + 1
            # def preprocess_transactions(self):

        if mode_type == 2:
            # print("generate_transactions epoch:", self.params["current_epoch"])
            #首先，方法通过一个条件判断来确保只有分片成员（node_type == 3）和分片领导（node_type == 2）可以生成交易。
            # 如果不是这两种类型的节点尝试调用此方法，将引发一个 RuntimeError。
            if not (self.node_type == 3 or self.node_type == 2):
                raise RuntimeError("Node not allowed to generate transactions.")
            num = 0
            # while num < self.params["transaction_generation_num"]:
            while self.env.now < self.params["simulation_time"]:

                # if self.current_load >= self.load_capacity:
                #     # delay = get_transaction_delay(
                #     #     self.params["transaction_mu"], self.params["transaction_sigma"]
                #     # )
                # yield self.env.timeout(self.params["Node_processing_delay"][self.id])

                # 在每次循环中，首先通过调用 get_transaction_delay 函数计算下一笔交易的延迟时间。这个函数可能基于某种随机过程来决定每笔交易之间的时间间隔。
                delay = get_transaction_delay(
                    self.params["transaction_mu"], self.params["transaction_sigma"]
                )
                # 使用 yield self.env.timeout(delay) 暂停执行，直到下一次交易的延迟时间过去。这里的 env 是模拟环境，用于控制时间流逝。
                yield self.env.timeout(delay)

                # 接下来，随机生成一个交易的价值 value，并根据这个价值和预设的奖励百分比 reward_percentage 来计算交易的奖励 reward。
                value = np.random.randint(self.params["tx_value_low"], self.params["tx_value_high"])
                reward = value * self.params["reward_percentage"]

                # 初始化一个字典 transaction_state，用于跟踪当前分片中每个节点对该交易的状态（在此处初始化为 0）。
                transaction_state = {}
                for key, value in self.curr_shard_nodes.items():
                    transaction_state[key] = 0

                # 通过比较随机生成的数和预设的跨分片交易百分比 cross_shard_tx_percentage 来决定该笔交易是否为跨分片交易。
                cross_shard_status = random.random() <= self.params["cross_shard_tx_percentage"]




                # 生成一个唯一的交易 ID，使用 uuid.uuid4() 生成一个全局唯一标识符。
                # id = int(1000*round(self.env.now, 3))
                id = str(uuid.uuid4())
                # 创建一个 Transaction 对象，包含交易 ID、当前时间戳、价值、奖励、交易状态和是否为跨分片交易的标志。
                transaction = Transaction(f"T_{self.id}_{id}", self.env.now, value, reward, transaction_state, cross_shard_status)

                # print("cross_shard_status:", cross_shard_status)
                # print("self.get_intra_shard_random_node_id():", self.get_intra_shard_random_node_id())
                # self.get_intra_shard_random_node_id()

                if cross_shard_status:
                    receiver_node_id = self.get_cross_shard_random_node_id()
                    # transaction.set_receiver(receiver_node_id)
                    # transaction.cross_shard_status = 1
                else:
                    receiver_node_id = self.get_intra_shard_random_node_id()
                    # transaction.set_receiver(receiver_node_id)

                prepare_receiver_node_id = self.params["frequent_transactions_custom"][self.id]
                prepare_receiver_node_id.append(receiver_node_id)
                receiver_node_id = random.choice(prepare_receiver_node_id)




                if self.params["all_full_nodes"][receiver_node_id].node_type == 2 or self.params["all_full_nodes"][receiver_node_id].node_type == 3:
                    if self.params["all_full_nodes"][receiver_node_id].shard_id != self.shard_id:
                        transaction.cross_shard_status = 1
                    else:
                        transaction.cross_shard_status = 0
                    transaction.set_receiver(receiver_node_id)

                if transaction.receiver == None:
                    receiver_node_id = self.get_intra_shard_random_node_id()
                    transaction.set_receiver(receiver_node_id)

                # 设置 originate_shard 和 target_shard 属性，分别表示交易的来源分片和目标分片。
                transaction.set_originate_shard(self.shard_id)
                transaction.set_target_shard(self.params["all_full_nodes"][receiver_node_id].shard_id)




                # if transaction.originate_shard == transaction.target_shard:
                #     print("这是分片内交易")
                # else:
                #     print("这是跨分片交易")

                # 更新一些参数来跟踪生成的交易数量，包括总交易数、内分片交易数和跨分片交易数。
                self.params["generated_tx_count"] += 1
                self.params["generated_intra_shard_tx_count"] += 1 - transaction.cross_shard_status
                self.params["generated_cross_shard_tx_count"] += transaction.cross_shard_status

                self.params["epoch_generated_tx_count"][self.params['current_epoch']] += 1
                self.params["epoch_generated_intra_shard_tx_count"][self.params['current_epoch']] += 1 - transaction.cross_shard_status
                self.params["epoch_generated_cross_shard_tx_count"][self.params['current_epoch']] += transaction.cross_shard_status

                self.params["epoch_shard_generated_tx_count"][self.params['current_epoch']][self.shard_id] += 1
                self.params["epoch_shard_generated_intra_shard_tx_count"][self.params['current_epoch']][self.shard_id] += 1 - transaction.cross_shard_status
                self.params["epoch_shard_generated_cross_shard_tx_count"][self.params['current_epoch']][self.shard_id] += transaction.cross_shard_status

                # 更新图
                self.params["graph"]
                if  self.params["graph"].has_edge(self.id, transaction.receiver):
                    # 如果边已经存在，则增加权重（即交易次数）
                    self.params["graph"][self.id][transaction.receiver]['weight'] += 1
                else:
                    # 否则，创建一条新的边，并设置权重为 1
                    self.params["graph"].add_edge(self.id, transaction.receiver, weight=1)

                # 如果启用了详细模式（verbose 参数为真），则打印交易的详细信息。
                if self.params["verbose"]:
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "%s added with reward %.2f"
                        % (transaction.id, transaction.reward)
                    )

                # 确定交易的下一跳节点 ID。如果没有指定下一跳（next_hop_id == -1），则使用当前节点的 ID 作为下一跳。
                neighbour_ids = [self.id if self.next_hop_id == -1 else self.next_hop_id]
                # 调用 broadcast 函数将交易广播给邻近的节点。这个函数需要传入环境、交易对象、消息类型、当前节点 ID、邻居节点 ID 列表、当前分片节点和节点参数。
                broadcast(
                    self.env,
                    transaction,
                    "Tx",
                    self.id,
                    neighbour_ids,
                    self.curr_shard_nodes,
                    self.params
                )

                num += 1
                # print("while内 节点" + self.id + "生成交易")
                # self.current_load = self.current_load + 1
                # print("当前系统生成交易数：", self.params["generated_tx_count"])
                self.params["Node_transaction_generation_num"][self.id] = self.params["Node_transaction_generation_num"][self.id] + 1


    #     """
    #     Pre-processes the transactions (done by shard leader)
    #     """

    #     if self.node_type != 2:
    #         raise RuntimeError("Pre-processing can only be performed by the shard leader")

    #     while True:

    #         if self.transaction_pool.transaction_queue.length() >= self.params["tx_block_capacity"]:
    #             # print(f"Queue size of {self.id} = {self.transaction_pool.transaction_queue.length()}")
    #             transactions_list = self.transaction_pool.transaction_queue.pop(self.params["tx_block_capacity"])
    #             num_cross_shard_txns = int(len(transactions_list) * 0.3)
    #             num_intra_shard_txns = len(transactions_list) - num_cross_shard_txns
    #             random.shuffle(transactions_list)

    #             intra_shard_txns = transactions_list[:num_intra_shard_txns]
    #             cross_shard_txns = transactions_list[num_intra_shard_txns:]
                
    #             self.transaction_pool.intra_shard_tx += intra_shard_txns
    #             self.transaction_pool.cross_shard_tx += cross_shard_txns

    #             flag_intra_shard_tx, flag_cross_shard_tx = False, False
    #             if len(self.transaction_pool.intra_shard_tx) >= self.params["tx_block_capacity"]:
    #                 flag_intra_shard_tx = True
                
    #             if len(self.transaction_pool.cross_shard_tx) >= self.params["tx_block_capacity"]:
    #                 flag_cross_shard_tx = True
    
    #             if flag_intra_shard_tx or flag_cross_shard_tx:
    #                 # To-do: Add different type of delay for the pre-processing
    #                 delay = get_transaction_delay(
    #                     self.params["transaction_mu"], self.params["transaction_sigma"]
    #                 )
    #                 yield self.env.timeout(delay)

    #                 if flag_intra_shard_tx:
    #                     intra_shard_txns = self.transaction_pool.intra_shard_tx[ : self.params["tx_block_capacity"]]
    #                     self.transaction_pool.intra_shard_txns = self.transaction_pool.intra_shard_tx[self.params["tx_block_capacity"] : ]
                        
    #                     self.preprocess_intra_shard_transactions(intra_shard_txns)
    #                 if flag_cross_shard_tx:
    #                     cross_shard_txns = self.transaction_pool.cross_shard_tx[ : self.params["tx_block_capacity"]]
    #                     self.transaction_pool.cross_shard_txns = self.transaction_pool.cross_shard_tx[self.params["tx_block_capacity"] : ]

    #                     yield self.env.timeout(delay*40)
    #                     self.preprocess_cross_shard_transactions(cross_shard_txns)

    #         else:       # To avoid code being stuck in an infinite loop
    #             delay = get_transaction_delay(
    #                 self.params["transaction_mu"], self.params["transaction_sigma"]
    #             )
    #             yield self.env.timeout(delay)

    def create_transactionk(self):
        # 随机生成一个交易的价值 value，并根据这个价值和预设的奖励百分比 reward_percentage 来计算交易的奖励 reward。
        value = np.random.randint(self.params["tx_value_low"], self.params["tx_value_high"])
        reward = value * self.params["reward_percentage"]

        # 初始化一个字典 transaction_state，用于跟踪当前分片中每个节点对该交易的状态（在此处初始化为 0）。
        transaction_state = {key: 0 for key in self.curr_shard_nodes}

        # 决定该笔交易是否为跨分片交易
        cross_shard_status = 0
        # 生成一个唯一的交易 ID
        id = str(uuid.uuid4())
        # 创建一个 Transaction 对象
        transaction = Transaction(f"T_{self.id}_{id}", self.env.now, value, reward, transaction_state, cross_shard_status)
        return transaction

    def preprocess_intra_shard_transactions(self):
        """
        Helper function to pre-process intra-shard transactions
        """

        if self.params["chain_mode_type"] == 0:
            # print("调用一次处理分片内交易")
            # 首先，通过 if self.node_type != 2: 检查当前节点是否为分片领导。如果不是，抛出 RuntimeError 异常，因为只有分片领导有权限进行交易的预处理。
            if self.node_type != 2:
                raise RuntimeError("Pre-processing can only be performed by the shard leader")

            while True:
                # 在循环内，首先检查交易池中的内分片交易队列长度是否达到了参数 tx_block_capacity 定义的容量。
                # 如果达到或超过这个容量，就进行交易的预处理；否则，等待一段时间后再检查。
                # 使用 get_transaction_delay 函数计算等待时间，并通过 yield self.env.timeout(delay) 暂停执行，模拟处理交易前的准备时间。

                # print("self.params[tx_block_capacity]:", self.params["tx_block_capacity"])
                # print("self.transaction_pool.intra_shard_tx_queue.length():", self.transaction_pool.intra_shard_tx_queue.length())
                if self.transaction_pool.intra_shard_tx_queue.length() >= self.params["tx_block_capacity"]:
                    delay = get_transaction_delay(
                        self.params["transaction_mu"], self.params["transaction_sigma"]
                    )
                    yield self.env.timeout(delay)

                    # 通过调用 self.transaction_pool.pop_transaction(self.params["tx_block_capacity"], 'intra-shard') 从交易池中提取指定数量的内分片交易。
                    intra_shard_txns = self.transaction_pool.pop_transaction(self.params["tx_block_capacity"], 'intra-shard')
                    # 使用 get_shard_neighbours 函数根据当前分片节点和邻居节点的信息，获取分片内的邻居节点。
                    shard_neighbours = get_shard_neighbours(self.curr_shard_nodes, self.neighbours_ids, self.shard_id)

                    # 遍历当前分片的节点，只选择那些属于当前分片且类型为分片成员（node_type == 3）的节点，用于后续处理。
                    filtered_curr_shard_nodes = []
                    for node_id in self.curr_shard_nodes.keys():
                        if self.curr_shard_nodes[node_id].shard_id == self.shard_id and self.curr_shard_nodes[node_id].node_type == 3:
                            filtered_curr_shard_nodes.append(node_id)

                    # id = int(1000*round(self.env.now, 3))
                    # 使用 uuid.uuid4() 生成一个唯一的标识符作为交易块的 ID。
                    # 创建一个 TxBlock 对象，包含交易块 ID、提取的交易、参数、分片 ID 和过滤后的当前分片节点。
                    id = str(uuid.uuid4())
                    tx_block = TxBlock(f"TB_{self.id}_{id}", intra_shard_txns, self.params, self.shard_id, filtered_curr_shard_nodes)




                    # print("广播分片内交易")

                # 调用 broadcast 函数将交易块广播给分片内的邻居节点。这个过程模拟了分片领导将预处理后的交易块发送给分片内其他节点的过程。
                    broadcast(
                        self.env,
                        tx_block,
                        "Tx-block",
                        self.id,
                        shard_neighbours,
                        self.curr_shard_nodes,
                        self.params
                    )

                # 如果交易池中的交易数量未达到预处理的阈值，则再次计算延迟时间并等待，以避免代码陷入无限循环。
                else:       # To avoid code being stuck in an infinite loop
                    delay = get_transaction_delay(
                        self.params["transaction_mu"], self.params["transaction_sigma"]
                    )
                    yield self.env.timeout(delay)
        if self.params["chain_mode_type"] == 1:
            if self.node_type != 2:
                raise RuntimeError("Pre-processing can only be performed by the shard leader")

            while True:
                # 检查交易池中的内分片交易数量是否达到预处理的阈值
                # intra_shard_tx_count = sum(1 for tx in self.transaction_pool.transactions.values() for t in tx if t.cross_shard_status == 0)
                    # 检查 shard_key 是否存在于 transactions 字典中

                # print("节点 分片:", self.id , self.shard_id)
                # print("循环生成分片内交易块 self.transaction_pool.transactions:", self.transaction_pool.transactions)
                # print("self.transaction_pool.intra_shard_tx_queue.length()",self.transaction_pool.intra_shard_tx_queue.length())
                flag = 0
                # 获取对应分片的交易池
                shard_key = (self.shard_id, self.shard_id)

                if shard_key in self.transaction_pool.transactions:
                    # print("已有交易数量：" ,len(self.transaction_pool.transactions[shard_key]))
                    intra_shard_tx_count = len(self.transaction_pool.transactions[shard_key])
                    if intra_shard_tx_count >= self.params["tx_block_capacity"]:
                        # print("循环生成分片内交易块 2")
                        flag = 1
                        delay = get_transaction_delay(
                            self.params["transaction_mu"], self.params["transaction_sigma"]
                        )
                        yield self.env.timeout(delay)

                        # 从交易池中提取指定数量的内分片交易
                        intra_shard_txns = self.transaction_pool.pop_transaction_with_shardID_dict(self.params["tx_block_capacity"], self.shard_id, self.shard_id)

                        # 获取分片内的邻居节点
                        shard_neighbours = get_shard_neighbours(self.curr_shard_nodes, self.neighbours_ids, self.shard_id)

                        # 只选择属于当前分片且类型为分片成员的节点
                        filtered_curr_shard_nodes = [
                            node_id for node_id in self.curr_shard_nodes.keys()
                            if self.curr_shard_nodes[node_id].shard_id == self.shard_id and self.curr_shard_nodes[node_id].node_type == 3
                        ]

                        # 生成唯一的交易块 ID
                        id = str(uuid.uuid4())

                        # 创建交易块对象
                        tx_block = TxBlock(f"TB_{self.id}_{id}", intra_shard_txns, self.params, self.shard_id, filtered_curr_shard_nodes)

                        # 广播交易块给分片内的邻居节点
                        broadcast(
                            self.env,
                            tx_block,
                            "Tx-block",
                            self.id,
                            shard_neighbours,
                            self.curr_shard_nodes,
                            self.params
                        )

                        # 从交易池中移除已处理的交易
                        for tx in intra_shard_txns:
                            self.transaction_pool.pop_transaction_with_shardID_dict(self.params["tx_block_capacity"], tx.originate_shard, tx.target_shard)

                    else:
                        # print("没有足够的分片内交易，当前交易数", len(self.transaction_pool.transactions[shard_key]))
                        # 如果交易池中的交易数量未达到预处理的阈值，计算延迟时间并等待
                        delay = get_transaction_delay(
                            self.params["transaction_mu"], self.params["transaction_sigma"]
                        )
                        yield self.env.timeout(delay)
                # 如果交易池中的交易数量未达到预处理的阈值，计算延迟时间并等待
                # if flag == 0:
                #     delay = get_transaction_delay(
                #         self.params["transaction_mu"], self.params["transaction_sigma"]
                #     )
                #     yield self.env.timeout(delay)




    def preprocess_cross_shard_transactions(self):
        if self.params["chain_mode_type"] == 0:
            """
            Helper function to pre-process cross-shard transactions
            """
            # print("调用一次处理跨分片交易")
            if self.node_type != 2:
                raise RuntimeError("Pre-processing can only be performed by the shard leader")
            # print("self.params[tx_block_capacity]:", self.params["tx_block_capacity"])

            while True:
                # print("self.transaction_pool.cross_shard_tx_queue.length():", self.transaction_pool.cross_shard_tx_queue.length())
                if self.transaction_pool.cross_shard_tx_queue.length() >= self.params["tx_block_capacity"]:
                    delay = get_transaction_delay(
                        self.params["transaction_mu"], self.params["transaction_sigma"]
                    )
                    yield self.env.timeout(delay)

                    # print("跨分片交易数达到处理阈值")
                    # 通过调用 self.transaction_pool.pop_transaction(self.params["tx_block_capacity"], 'cross-shard') 从交易池中提取指定数量的跨分片交易。
                    cross_shard_txns = self.transaction_pool.pop_transaction(self.params["tx_block_capacity"], 'cross-shard')
                    # 遍历提取的跨分片交易，为每笔交易随机分配一个接收节点（来自不同分片）。
                    # 如果随机选中的接收节点是主委员会节点（node_type == 1），则抛出异常，因为主委员会节点不能接收跨分片交易。
                    for txn in cross_shard_txns:
                        txn.cross_shard_status = 1
                        # receiver_node_id = self.get_cross_shard_random_node_id()
                        # print("receiver_node_id", receiver_node_id)
                        # if self.curr_shard_nodes[receiver_node_id].node_type == 1:
                        #     print(self.shard_leaders.keys())
                        #     raise RuntimeError(f"Principal committee node {receiver_node_id} can't be a receiver of cross-shard tx for tx {txn.id}")
                        # txn.set_receiver(receiver_node_id)

                    # 遍历当前分片的节点，只选择那些属于当前分片且类型为分片成员（node_type == 3）的节点，用于后续处理。
                    filtered_curr_shard_nodes = []
                    for node_id in self.curr_shard_nodes.keys():
                        if self.curr_shard_nodes[node_id].shard_id == self.shard_id and self.curr_shard_nodes[node_id].node_type == 3:
                            filtered_curr_shard_nodes.append(node_id)


                    # 使用 uuid.uuid4() 生成一个唯一的标识符作为交易块的 ID。
                    # 创建一个 CrossShardBlock 对象，包含交易块 ID、提取的跨分片交易、参数、分片 ID 和过滤后的当前分片节点。
                    id = str(uuid.uuid4())
                    cross_shard_block = CrossShardBlock(f"CB_{self.id}_{id}", cross_shard_txns, self.params, self.shard_id, filtered_curr_shard_nodes)
                    neighbour_shard_leaders = list(self.shard_leaders.keys())
                    neighbour_shard_leaders.remove(self.id)
                    # print("广播跨分片交易")
                    # 获取当前分片领导的邻居分片领导列表，从中移除自身的 ID。
                    # 调用 broadcast 函数将跨分片交易块广播给邻居分片领导。这个过程模拟了分片领导将预处理后的跨分片交易块发送给其他分片领导的过程。
                    broadcast(
                        self.env,
                        cross_shard_block,
                        "Cross-shard-block",
                        self.id,
                        neighbour_shard_leaders,
                        self.curr_shard_nodes,
                        self.params
                    )

                else:
                    # To avoid code being stuck in an infinite loop
                    delay = get_transaction_delay(
                        self.params["transaction_mu"], self.params["transaction_sigma"]
                    )
                    yield self.env.timeout(delay)
        if self.params["chain_mode_type"] == 1:
            """
            Helper function to pre-process cross-shard transactions
            """
            if self.node_type != 2:
                raise RuntimeError("Pre-processing can only be performed by the shard leader")

            # if self.shard_type == 2:
                # print("这是BSHARD：", self.shard_id , "对应的ISHARD：" ,self.params["Bshard_with_Ishard"][self.shard_id])
                # Ishard_id_1 = self.params["Bshard_with_Ishard"][self.shard_id][0]
                # Ishard_id_2 = self.params["Bshard_with_Ishard"][self.shard_id][1]
                # print("Ishard_id_1",Ishard_id_1,"Ishard_id_2",Ishard_id_2)

            while True:
                flag = 0
                # print("循环生成跨分片交易块")
                # print("节点 分片:", self.id , self.shard_id)
                # print("循环生成跨分片交易块 self.transaction_pool.transactions:", self.transaction_pool.transactions)
                # print("self.transaction_pool.cross_shard_tx_queue.length()",self.transaction_pool.cross_shard_tx_queue.length())

                # 桥接分片处理跨分片交易
                if self.shard_type == 2:


                    Ishard_id_1 = self.params["Bshard_with_Ishard"][self.shard_id][0]
                    Ishard_id_2 = self.params["Bshard_with_Ishard"][self.shard_id][1]

                    for shard_key in [(Ishard_id_1, Ishard_id_2), (Ishard_id_2, Ishard_id_1)]:
                        # print("进入Bshard循环")
                        if shard_key in self.transaction_pool.transactions and len(self.transaction_pool.transactions[shard_key]) >= 1:
                            # print(f"Bshard处理Ishard {shard_key} 跨分片事务 {len(self.transaction_pool.transactions[shard_key])}")
                            delay = get_transaction_delay(
                                self.params["transaction_mu"], self.params["transaction_sigma"]
                            )
                            yield self.env.timeout(delay)
                            flag = 1

                            cross_shard_txns = self.transaction_pool.pop_transaction_with_shardID_dict(self.params["tx_block_capacity"], *shard_key)

                            for txn in cross_shard_txns:
                                txn.cross_shard_status = 1

                            # filtered_curr_shard_nodes = self.get_filtered_nodes()
                            # id = str(uuid.uuid4())
                            # cross_shard_block = CrossShardBlock(f"CB_{self.id}_{id}", cross_shard_txns, self.params, self.shard_id, filtered_curr_shard_nodes)
                            # neighbour_shard_leaders = list(self.shard_leaders.keys())
                            # neighbour_shard_leaders.remove(self.id)

                            # 获取分片内的邻居节点
                            shard_neighbours = get_shard_neighbours(self.curr_shard_nodes, self.neighbours_ids, self.shard_id)
                            # 只选择属于当前分片且类型为分片成员的节点
                            filtered_curr_shard_nodes = [
                                node_id for node_id in self.curr_shard_nodes.keys()
                                if self.curr_shard_nodes[node_id].shard_id == self.shard_id and self.curr_shard_nodes[node_id].node_type == 3
                            ]

                            # 生成唯一的交易块 ID
                            id = str(uuid.uuid4())

                            # 创建交易块对象
                            tx_block = TxBlock(f"TB_{self.id}_{id}", cross_shard_txns, self.params, self.shard_id, filtered_curr_shard_nodes)

                            # 广播交易块给分片内的邻居节点
                            broadcast(
                                self.env,
                                tx_block,
                                "Tx-block",
                                self.id,
                                shard_neighbours,
                                self.curr_shard_nodes,
                                self.params
                            )
                            # 从交易池中移除已处理的交易
                            for tx in cross_shard_txns:
                                self.transaction_pool.pop_transaction_with_shardID_dict(self.params["tx_block_capacity"], tx.originate_shard, tx.target_shard)


                        # else:
                            # print(f"没有足够的交易{shard_key}，当前交易数", len(self.transaction_pool.transactions[shard_key]))
                            # print("self.transaction_pool.transactions:", self.transaction_pool.transactions)


                for idx in range(self.params["num_shards"]):
                    # print("循环生成跨分片交易块1")
                    if idx != self.shard_id:
                        # 获取对应分片的交易池
                        shard_key = (self.shard_id, idx)
                        if shard_key in self.transaction_pool.transactions:
                            # print("已有交易数量：",len(self.transaction_pool.transactions[shard_key]))
                            if len(self.transaction_pool.transactions[shard_key]) >= self.params["tx_block_capacity"]:
                                delay = get_transaction_delay(
                                    self.params["transaction_mu"], self.params["transaction_sigma"]
                                )
                                yield self.env.timeout(delay)
                                flag = 1
                                # 通过调用 self.transaction_pool.pop_transaction(self.params["tx_block_capacity"], 'cross-shard') 从交易池中提取指定数量的跨分片交易。
                                cross_shard_txns = self.transaction_pool.pop_transaction_with_shardID_dict(self.params["tx_block_capacity"], self.shard_id, idx)
                                # 遍历提取的跨分片交易，为每笔交易随机分配一个接收节点（来自不同分片）。
                                # 如果随机选中的接收节点是主委员会节点（node_type == 1），则抛出异常，因为主委员会节点不能接收跨分片交易。
                                for txn in cross_shard_txns:
                                    txn.cross_shard_status = 1

                                # 遍历当前分片的节点，只选择那些属于当前分片且类型为分片成员（node_type == 3）的节点，用于后续处理。
                                filtered_curr_shard_nodes = []
                                for node_id in self.curr_shard_nodes.keys():
                                    if self.curr_shard_nodes[node_id].shard_id == self.shard_id and self.curr_shard_nodes[node_id].node_type == 3:
                                        filtered_curr_shard_nodes.append(node_id)


                                # 使用 uuid.uuid4() 生成一个唯一的标识符作为交易块的 ID。
                                # 创建一个 CrossShardBlock 对象，包含交易块 ID、提取的跨分片交易、参数、分片 ID 和过滤后的当前分片节点。
                                id = str(uuid.uuid4())
                                cross_shard_block = CrossShardBlock(f"CB_{self.id}_{id}", cross_shard_txns, self.params, self.shard_id, filtered_curr_shard_nodes)

                                # # 如果不是OmniLedger
                                # if self.params["run_type"] != 2:
                                #     neighbour_shard_leaders = list(self.shard_leaders.keys())
                                #     neighbour_shard_leaders.remove(self.id)
                                #     # print("广播跨分片交易")
                                #     # 获取当前分片领导的邻居分片领导列表，从中移除自身的 ID。
                                #     # 调用 broadcast 函数将跨分片交易块广播给邻居分片领导。这个过程模拟了分片领导将预处理后的跨分片交易块发送给其他分片领导的过程。
                                #     broadcast(
                                #         self.env,
                                #         cross_shard_block,
                                #         "Cross-shard-block",
                                #         self.id,
                                #         neighbour_shard_leaders,
                                #         self.curr_shard_nodes,
                                #         self.params
                                #     )
                                # # 如果是OmniLedger，则发给目标分片和起始分片
                                # else:
                                    # shard_key[0]

                                originate_shard_leaderID = self.get_shard_leaders(shard_key[0])
                                target_shard_leaderID  = self.get_shard_leaders(shard_key[1])
                                neighbour_shard_leaders = [
                                    originate_shard_leaderID,
                                    target_shard_leaderID,
                                ]
                                if originate_shard_leaderID in  self.shard_leaders.keys() and target_shard_leaderID in  self.shard_leaders.keys():
                                    # neighbour_shard_leaders = [
                                    #     originate_shard_leaderID,
                                    #     target_shard_leaderID,
                                    # ]

                                    # 获取当前分片领导的邻居分片领导列表，从中移除自身的 ID。
                                    # 调用 broadcast 函数将跨分片交易块广播给邻居分片领导。这个过程模拟了分片领导将预处理后的跨分片交易块发送给其他分片领导的过程。
                                    broadcast(
                                        self.env,
                                        cross_shard_block,
                                        "Cross-shard-block",
                                        self.id,
                                        neighbour_shard_leaders,
                                        self.params["all_full_nodes"],
                                        self.params
                                    )
                                else:
                                    print("neighbour_shard_leaders",neighbour_shard_leaders)
                                    print("self.shard_leaders",self.shard_leaders)
                                    raise RuntimeError("Pre-processing can only be performed by the shard leader")

                            # else:
                            #     print("没有足够的跨分片交易，当前交易数", len(self.transaction_pool.transactions[shard_key]))


                # 如果交易池中的交易数量未达到预处理的阈值，计算延迟时间并等待
                if flag == 0:
                    delay = get_transaction_delay(
                        self.params["transaction_mu"], self.params["transaction_sigma"]
                    )
                    yield self.env.timeout(delay)


            

    def generate_mini_block(self, tx_block, tx_block_type):
        """
        Generate a mini block and broadcast it to the principal committee
        """

        # 通过 if self.node_type != 2: 检查当前节点是否为分片领导。如果不是，抛出 RuntimeError 异常，因为只有分片领导有权限生成和广播小型区块。
        if self.node_type != 2:
            raise RuntimeError("Mini-block can only be generated by the shard leader")
        # 如果传入的交易块 tx_block 尚未处理（即不在 self.processed_tx_blocks 列表中），则将其添加到当前待处理的交易块列表 self.current_tx_blocks 中。
        if tx_block not in self.processed_tx_blocks:

            self.current_tx_blocks.append(tx_block)
            # if self.params["verbose"]:
            #     print(f"[Debug len]: processed_tx_blocks = {len(self.processed_tx_blocks)}")

            # 当 self.current_tx_blocks 中的交易块数量达到或超过了参数 tx_blocks_in_mini_block 定义的阈值时，执行以下步骤：
            if len(self.current_tx_blocks) >= self.params["tx_blocks_in_mini_block"]:
                # To-Do: Maintain already processed tx-blocks list
                # 从 self.current_tx_blocks 中提取指定数量的交易块，添加到已处理的交易块列表 self.processed_tx_blocks 中，
                # 并从 self.current_tx_blocks 中移除这些交易块。
                self.processed_tx_blocks += self.current_tx_blocks[0 : self.params["tx_blocks_in_mini_block"]]
                self.current_tx_blocks = self.current_tx_blocks[self.params["tx_blocks_in_mini_block"] : ]

                # 使用 filter_transactions 函数从提取的交易块中筛选出被接受的交易，基于参数 cutoff_vote_percentage 来决定哪些交易被接受。
                accepted_transactions = filter_transactions(tx_block, tx_block_type, self.params["cutoff_vote_percentage"])
                # accepted_transactions = tx_block.transactions_list

                # 更新统计信息，包括处理的交易总数、内分片交易数和跨分片交易数。
                self.params["processed_tx_count"] += len(tx_block.transactions_list)

                for tx in tx_block.transactions_list:
                    self.params["processed_intra_shard_tx_count"] += 1 - tx.cross_shard_status
                    self.params["processed_cross_shard_tx_count"] += tx.cross_shard_status

                # 更新epoch统计信息，包括处理的交易总数、内分片交易数和跨分片交易数。
                self.params["epoch_processed_tx_count"][self.params["current_epoch"]] += len(tx_block.transactions_list)
                self.params["epoch_shard_processed_tx_count"][self.params["current_epoch"]][self.shard_id] += len(tx_block.transactions_list)
                for tx in tx_block.transactions_list:
                    self.params["epoch_processed_intra_shard_tx_count"][self.params["current_epoch"]] += 1 - tx.cross_shard_status
                    self.params["epoch_processed_cross_shard_tx_count"][self.params["current_epoch"]] += tx.cross_shard_status
                    self.params["epoch_shard_processed_intra_shard_tx_count"][self.params["current_epoch"]][self.shard_id] += 1 - tx.cross_shard_status
                    self.params["epoch_shard_processed_cross_shard_tx_count"][self.params["current_epoch"]][self.shard_id] += tx.cross_shard_status
                # 更新由分片领导者节点生成的迷你区块的数量。
                self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][self.id] = self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][self.id] + 1
                # id = int(1000*round(self.env.now, 3))
                # 使用 uuid.uuid4() 生成一个唯一的标识符作为小型区块的 ID。
                id = str(uuid.uuid4())

                # 创建一个 MiniBlock 对象，包含小型区块的 ID、被接受的交易、参数、分片 ID 和当前时间。
                mini_block = MiniBlock(f"MB_{self.id}_{id}", accepted_transactions, self.params, self.shard_id, self.env.now)
                # 使用 get_principal_committee_neigbours 函数获取主委员会的邻居节点。
                principal_committee_neigbours = get_principal_committee_neigbours(self.curr_shard_nodes, self.neighbours_ids)

                # 调用 broadcast 函数将小型区块广播给主委员会的邻居节点。这个过程模拟了分片领导将处理后的交易信息汇总成小型区块，并通知主委员会的过程。
                broadcast(
                    self.env, 
                    mini_block,
                    "Mini-block", 
                    self.id, 
                    principal_committee_neigbours, 
                    self.curr_shard_nodes, 
                    self.params
                )


    def generate_block(self):
        """
        Generate a block and broadcast it in the entire network
        """

        # 过 if self.node_type != 1: 检查当前节点是否为主委员会节点。如果不是，抛出 RuntimeError 异常，因为只有主委员会节点有权限生成和广播区块。
        if self.node_type != 1:
            raise RuntimeError("Block can only be generated by the Principal Committee")
        
        """ M - 1 (with leader) 领导者模式 """

        """
        Steps -
            1. 分片负责人向主要委员会节点发送迷你块
            2. 主要委员会节点将迷你块发送给分块组长
            3. 组长要求其他 p.c. 节点投票 
               可以通过缓冲来自不同分块的所有迷你块，然后将其广播到网络上进行投票来优化这一步骤。
               将其广播到网络上进行投票。
            4. 领导者获得投票后，将生成区块并向整个网络广播。
            5. p.c. 节点不会向其他 p.c. 节点广播，而是向网络的其他节点广播。
        """

        """ M - 2 (Without leader) 无领导者模式（M - 2）"""
        # Generate block only when each shard has provided with a mini-block and other principal committee nodes 
        # have voted on it


        size_principal_committee = 1 + len(get_principal_committee_neigbours(self.curr_shard_nodes, self.neighbours_ids))
        # print(f"len = {size_principal_committee}")
        # 首先，can_generate_block 函数用于判断是否满足生成新区块的条件。
        # 这通常基于小型区块的共识池（mini_block_consensus_pool）和主委员会的大小（size_principal_committee），
        # 以及系统配置的分片数量（self.params["num_shards"]）。
        if can_generate_block(self.mini_block_consensus_pool, size_principal_committee, self.params["num_shards"]):
            """
            Steps - 
                1. 对迷你区块应用过滤器，并从有效迷你区块收集交易                
                a.从每个分块中只提取最新的迷你块                
                b.修改迷你区块共识池的状态                
                2.更新自己的区块链
                3. 向分片广播区块（待办事项：邻居可能需要调试）
            """
            # if self.params["verbose"]:
            #     print(f"[Debug] - Node {self.id} ready to generate \nPool - {self.mini_block_consensus_pool}")

            # 过滤和收集交易：如果条件满足，方法接着对小型区块进行过滤，
            # 选择有效的小型区块，并从中收集交易。这个过程可能包括选择每个分片最新的小型区块，并基于投票结果确定哪些小型区块被接受。
            # 列表推导式 [ id for id in self.mini_block_consensus_pool ] 遍历字典 self.mini_block_consensus_pool 的所有键
            # （即迷你区块的 ID），并将这些键添加到一个新的列表中。
            self.processed_mini_blocks = [ id for id in self.mini_block_consensus_pool ]
            filtered_mini_blocks = []
            temp_data = {}              # stores latest accepted mini-block corresponding to evey shard
            count_tx_processed = 0

            for key, val in self.mini_block_consensus_pool.items():
                block = val["data"]
                count_tx_processed += len(block.transactions_list)

                # 迷你区块过滤：遍历共识池中的每个小型区块，基于投票结果（net_vote）过滤出被接受的小型区块。
                # 投票机制确保了只有得到多数投票支持的小型区块才会被考虑用于生成新区块。
                net_vote = 0
                for id, curr_vote in val["votes"].items():
                    net_vote += curr_vote if curr_vote else -1
                
                if net_vote > 0:
                    if block.shard_id in temp_data:
                        existing_block = temp_data[block.shard_id]

                        # Select only latest mini-block sent by a shard
                        # if int(block.id[block.id.rfind('_')+1:]) > int(existing_block.id[existing_block.id.rfind('_')+1:]):
                        #     block = existing_block
                        # 选择最新的迷你区块：对于每个分片，只选择最新的小型区块加入到最终的区块中。
                        # 这通过比较生成时间（generation_time）来实现，确保了区块链的实时性和数据的新鲜度。
                        # 这里有问题，block.generation_time > existing_block.generation_time 保存的是旧的数据
                        if block.generation_time > existing_block.generation_time:
                            block = existing_block
                        
                    temp_data[block.shard_id] = block
                    filtered_mini_blocks.append(block)

            # mini_block.transactions_list：对于filtered_mini_blocks中的每一个mini_block，
            # 通过访问其transactions_list属性来获取该小型区块包含的交易列表。每个mini_block都有一个transactions_list属性，该
            # 属性是一个列表，包含了该小型区块中所有的交易。
            #
            # [mini_block.transactions_list for mini_block in filtered_mini_blocks]：这是列表推导式的核心部分。
            # 它遍历filtered_mini_blocks中的每一个mini_block，并对每个mini_block执行mini_block.transactions_list操作，
            # 即提取出该小型区块的交易列表。所有这些交易列表最终被组合成一个新的列表。
            #
            # accepted_transactions：这是最终生成的列表，包含了所有被选中的小型区块中的交易列表。
            # 需要注意的是，accepted_transactions实际上是一个列表的列表，也就是说，每个元素本身也是一个列表，对应于一个小型区块的交易列表。
            accepted_transactions = [ mini_block.transactions_list for mini_block in filtered_mini_blocks ]

            # accepted_transactions = functools.reduce(operator.iconcat, accepted_transactions, [])：
            # 在这行代码中，reduce函数遍历accepted_transactions（这是一个列表的列表，每个元素是一个交易列表）
            # ，并使用operator.iconcat函数来连接这些子列表。[]是初始化累积值，意味着如果accepted_transactions为空，结果将是一个空列表。
            accepted_transactions = functools.reduce(operator.iconcat, accepted_transactions, [])
            
            # id = int(1000*round(self.env.now, 3))
            id = str(uuid.uuid4())
            block = Block(f"B_{self.id}_{id}", accepted_transactions, self.params)
            
            # Update consensus_pool
            # self.mini_block_consensus_pool = {key: temp_dict[key] for key in temp_dict if key in filtered_mini_blocks}：
            # 这行代码是字典推导式（dictionary comprehension）的应用。它遍历temp_dict（即原self.mini_block_consensus_pool）中的每个键（key），
            # 并检查这个键是否存在于filtered_mini_blocks列表中。
            # 如果键（代表一个小型区块的标识符）存在于filtered_mini_blocks中，这意味着该小型区块被选中为有效的，应该保留在新的共识池中。
            # 对于每个满足条件的键，其对应的值（共识信息）被添加到新的字典中。
            # 结果，self.mini_block_consensus_pool现在指向一个新的字典，这个字典只包含那些在filtered_mini_blocks中的键及其对应的值。
            # 这样做的目的是移除那些不再被认为有效或需要的小型区块的共识信息，从而确保self.mini_block_consensus_pool只包含当前共识过程中认为有效的小型区块的信息。
            temp_dict = self.mini_block_consensus_pool
            self.mini_block_consensus_pool = {key: temp_dict[key] for key in temp_dict if key in filtered_mini_blocks} 

            # Update own Blockchain
            self.update_blockchain(block)

            # Broadcast the block to the shards
            # 这有问题，在筛选完领导者节点后又把所有节点加进去了，最后广播还是给所有节点了
            filtered_neigbours = []
            for id in self.neighbours_ids:
                if self.curr_shard_nodes[id].node_type == 2:
                    filtered_neigbours.append(id)
            
            filtered_neigbours = self.neighbours_ids
            broadcast(
                self.env, 
                block,
                "Block", 
                self.id, 
                filtered_neigbours, 
                self.curr_shard_nodes, 
                self.params
            ) 

        else:
            pass
            # if self.params["verbose"]:
            #     print(f"[Debug] - Node {self.id} not ready \nPool - {self.mini_block_consensus_pool}")
    

    def validate_transaction(self, tx):
        """
        Validate transaction
        """
        # To-do: Think on improving it
        return bool(random.getrandbits(1))


    def cast_vote(self, tx_block):
        """
        Cast votes on each tx in tx_block
        """
        # for i in range(10000):
        #     pass

        # 对交易进行投票：函数核心部分遍历tx_block中的transactions_list，这是一个包含该区块所有交易的列表。对于每一笔交易tx：
        #
        # 使用self.validate_transaction(tx)调用验证交易。这个调用返回一个布尔值，表示交易是否有效。
        # 然后，将这个布尔值赋值给tx_block.votes_status[tx.id][self.id]。这里，votes_status是一个字典，
        # 记录了每笔交易的投票情况。tx.id是当前交易的唯一标识符，self.id是当前节点的唯一标识符。这行代码实际上记录了“当前节点对当前交易的投票结果是什么”。
        # To-do: Add vote option when node is unable to validate transaction
        for tx in tx_block.transactions_list:
            tx_block.votes_status[tx.id][self.id] = self.validate_transaction(tx)


    # 函数定义：cast_vote_for_cross_shard_block函数接收一个参数cross_shard_block，这个参数代表一个包含跨分片交易的区块。
    # 目的：函数的目的是遍历cross_shard_block中的所有交易，并根据交易是否与当前分片相关来决定投票结果。
    # 这里，投票结果被用来表示节点对于每笔交易的处理意见，可能是接受、拒绝或弃权。
    def cast_vote_for_cross_shard_block(self, cross_shard_block):
        """
        ...
        """
        # for i in range(10000):
        #     pass

        # To-do: Add vote option when node is unable to validate transaction

        #函数遍历cross_shard_block中的transactions_list，对每一笔交易进行处理。
        for tx in cross_shard_block.transactions_list:
            # 函数开始时，设置了一个默认投票值vote = 2，这里2可能表示弃权或无法决定的意见。
            vote = 2

            # If tx is relevant to this shard, vote for it else discard it by voting 2
            # 函数通过检查交易的接收者是否在当前分片的节点列表（curr_shard_nodes）中来判断交易是否与当前分片相关。
            # 这里，curr_shard_nodes是通过遍历self.curr_shard_nodes字典并检查每个节点的shard_id是否与当前节点的shard_id相匹配来构建的列表。
            curr_shard_nodes = [id for id, node in self.curr_shard_nodes.items() if node.shard_id == self.shard_id]
            # 如果交易的接收者属于当前分片，则调用validate_transaction(tx)来验证交易，并据此设置投票结果。否则，保持默认的投票值2。
            if tx.receiver in curr_shard_nodes:
                vote = self.validate_transaction(tx)

            # 投票结果记录在cross_shard_block.shard_votes_status中。这是一个嵌套字典，首先按分片ID索引，然后按交易ID索引，最后记录每个节点的投票结果。
            # 在这个结构中，self.shard_id表示当前节点的分片ID，tx.id是交易的唯一标识符，self.id是当前节点的唯一标识符。
            # 这样的数据结构允许网络汇总和分析每个分片对每笔交易的投票结果，从而决定交易是否应该被接受。
            cross_shard_block.shard_votes_status[self.shard_id][tx.id][self.id] = vote
    

    # 函数目的：接收并处理不同类型的区块，这些区块可以是分片内的交易区块、跨分片的交易区块、主委员会的小区块，或是最终确认的区块。
    # 消息接收：通过一个无限循环，节点不断地从其消息管道中接收消息。每个接收到的消息被假设为一个区块或区块列表。
    def receive_block(self):
        # print("receive_block_epoch", self.params["current_epoch"])
        """
        Receive -
        (i)   Tx-block sent by the shard leader (for shard nodes),
        (ii)  Mini-block sent by the shard leader (for Principal Committee)
              / principal committee (intra-committee broadcast), or
        (iii) (Final) Block sent by the Principal Committee (for all the nodes)
        接收-
        (I)由分片领导发送的Tx-block(对于分片节点)，
        (ii)分片负责人发送的迷你块(针对主要委员会)
        /主要委员会(委员会内广播)，或
        (iii)由主要委员会发送的(最终)块(对于所有节点)
        """
        # 消息接收：通过一个无限循环，节点不断地从其消息管道中接收消息。每个接收到的消息被假设为一个区块或区块列表。
        while True:
            packeted_message = yield self.pipes.get()
            block = packeted_message.message
            block_type = ""

            """
            Cross-shard Transactions -
                Add processing step for the Cross-shard Block
            """
            # 区块类型判断：通过一系列的isinstance检查，代码确定了接收到的区块类型。这个类型决定了后续的处理流程。
            if isinstance(block, list):                 block_type = "List"  # Mini-blocks
            elif isinstance(block, TxBlock):            block_type = "Tx"   # intra-shard
            elif isinstance(block, CrossShardBlock):    block_type = "Cross-shard"
            elif isinstance(block, MiniBlock):          block_type = "Mini"
            elif isinstance(block, Block):              block_type = "Final"
            elif isinstance(block, Transaction):        block_type = "Transaction"
            else:
                raise RuntimeError("Unknown Block received")


            # self.current_load = self.current_load + 1
            # self.wait_load_capacity()


            # print("节点" + self.id + "接收区块：" + block_type)
            # print(self.id + "当前负载：", self.current_load)
            # 调试信息：如果节点设置为详细模式（self.params["verbose"]为真），则打印出接收到的区块信息。
            if self.params["verbose"]:
                debug_info = [ b.id for b in block ] if isinstance(block, list) else block.id
                print(
                    "%7.4f" % self.env.now
                    + " : "
                    + "Node %s received a %s-block - %s from %s"
                    % (self.id, block_type, debug_info, packeted_message.sender_id)
                )

            # print("节点"+self.id+"收到"+block_type+"区块，开始处理")
            # yield self.env.timeout(self.params["Node_processing_delay"][self.id])
            # print("处理完毕")

            # 列表：如果接收到的是一个区块列表（可能是小区块列表），则调用process_received_mini_blocks_list函数进行处理。
            # 如果当前节点是主委员会的领导，则可能会触发新区块的生成。
            if isinstance(block, list):
                self.process_received_mini_blocks_list(block, packeted_message.sender_id)
                if self.id == self.pc_leader_id:
                    self.generate_block()
                    # delay = self.params["Node_processing_delay"][self.id]
                    # random_number = random.uniform(0.8, 1)
                    # yield self.env.timeout(delay*random_number)

            # 交易区块（TxBlock）：如果接收到交易区块且该区块尚未被处理，则调用process_received_tx_block进行处理。
            elif isinstance(block, TxBlock):
                if block not in self.shard_leader.processed_tx_blocks:
                    self.process_received_tx_block(block, packeted_message.sender_id)
                    # delay = get_transaction_delay(
                    #     self.params["transaction_mu"], self.params["transaction_sigma"]
                    # )
                    delay = self.params["Node_processing_delay"][self.id]
                    random_number = random.uniform(0.1, 0.15)
                    yield self.env.timeout(delay*random_number)
            # 跨分片区块（CrossShardBlock）：如果接收到跨分片区块，首先检查该区块是否与当前分片相关。
            # 如果是第一次接收到该区块，则向其他分片节点广播该区块。之后，根据条件可能会处理该区块。
            elif isinstance(block, CrossShardBlock):
                # **判断区块是否相关**：
                #     - 最初，代码尝试通过检查区块的发起分片ID（`originating_shard_id`）是否与当前节点的分片ID（`self.shard_id`）相同来设置一个标志（`flag`）。
                #     这个检查意在判断该跨分片区块是否对当前分片具有相关性。
                #     - 然后，代码中有一段被注释掉的逻辑，本意是遍历区块中的所有交易，检查它们是否都是跨分片交易（`cross_shard_status`为1）。
                #     如果发现有内部分片（即非跨分片）的交易，则抛出异常。这段逻辑确保了只有合法的跨分片交易被处理。
                #     - 最后，`flag`被直接设为`True`，这意味着不管区块的原始分片ID如何，当前节点都会处理这个区块。这可能是为了简化逻辑或是处于测试目的。
                flag = block.originating_shard_id == self.shard_id
                curr_shard_nodes = [id for id, node in self.curr_shard_nodes.items() if node.shard_id == self.shard_id]
                # for txn in block.transactions_list:
                #     if txn.cross_shard_status != 1 :
                #         raise RuntimeError(f"Intra Shard transaction present in Cross Shard Block")
                #     receiver = txn.receiver
                #     if receiver in curr_shard_nodes:
                #         flag = True
                #         break
                
                flag = True
                # print(f"[Check]: {block.id} has flag = {flag} for {self.id}")
                if flag:        # Cross-shard-block has even 1 tx related to the current shard
                    # 如果这是节点第一次接收到该跨分片区块（通过`received_cross_shard_block_for_first_time`函数检查），
                    # 节点会执行广播准备工作。首先，它从当前分片的节点列表中移除自己，然后向该区块添加用于投票的分片信息（`add_shard_info_for_voting`）。
                    # 这是为了在分片内部对跨分片区块进行投票。
                    if received_cross_shard_block_for_first_time(block, self.shard_id):                        
                        curr_shard_nodes_id = [ node_id for node_id, node in self.curr_shard_nodes.items() if node.shard_id == self.shard_id]
                        curr_shard_nodes_id.remove(self.id)
                        block.add_shard_info_for_voting(self.shard_id, curr_shard_nodes_id)

                        # 接下来，计算一个基于事务延迟的时间（通过`get_transaction_delay`函数），并让节点等待这段时间的0.4倍。这个延迟模拟了现实世界中事务处理和传播的时间。
                        # delay = get_transaction_delay(
                        #     self.params["transaction_mu"], self.params["transaction_sigma"]
                        # )
                        # yield self.env.timeout(delay*0.4)
                        delay = self.params["Node_processing_delay"][self.id]
                        random_number = random.uniform(0.6, 1)

                        if self.params["run_type"] != 2:
                            yield self.env.timeout(delay*random_number)
                        else:
                            # 因为OmniLedger 需要两个分片之间两次确认，所以延迟翻倍
                            yield self.env.timeout(delay*random_number*2)

                        # 然后，节点通过调用`broadcast`函数将这个跨分片区块广播给当前分片内的邻居节点。这一步是确保分片内的所有节点都能接收到并处理这个跨分片区块。
                        shard_neighbours = get_shard_neighbours(self.curr_shard_nodes, self.neighbours_ids, self.shard_id)
                        broadcast(
                            self.env, 
                            block, 
                            "Cross-shard-block", 
                            self.id, 
                            shard_neighbours, 
                            self.curr_shard_nodes, 
                            self.params
                        )
                    # 如果不是第一次接收到该区块，节点将直接处理这个跨分片区块（通过调用`process_received_cross_shard_block`函数
                    else:
                        # delay = get_transaction_delay(
                        #     self.params["transaction_mu"], self.params["transaction_sigma"]
                        # )
                        # yield self.env.timeout(delay*5)
                        self.process_received_cross_shard_block(block, packeted_message.sender_id)

            #小区块（MiniBlock）：如果接收到小区块且该小区块尚未被处理，则调用process_received_mini_block进行处理。
            elif isinstance(block, MiniBlock):
                if block.id not in self.processed_mini_blocks:
                    # print(f"[Test] = current - {block.id}\tProcessed = {self.processed_mini_blocks}")
                    self.process_received_mini_block(block)
                    # delay = self.params["Node_processing_delay"][self.id]
                    # random_number = random.uniform(0.8, 1.2)
                    # yield self.env.timeout(delay*random_number)
                    # generate_block() is triggered whenever mini-block is received by the principal committee node
                    # Although whether block will be generated or not, is handled inside the function
                    """ self.generate_block() """
            # 最终区块（Block）：接收到最终区块时，调用process_received_block进行处理。
            elif isinstance(block, Block):
                self.process_received_block(block)
                # delay = self.params["Node_processing_delay"][self.id]
                # random_number = random.uniform(1, 1.5)
                # yield self.env.timeout(delay*random_number)
            elif isinstance(block, Transaction):

                tx_type = 'intra-shard' if block.cross_shard_status == 0 else 'cross-shard'
                # self.transaction_pool.put_transaction_dict(block, self.location, tx_type)
                self.transaction_pool.put_transaction(block, self.location, tx_type)
                # delay = self.params["Node_processing_delay"][self.id]
                # random_number = random.uniform(1, 1.5)
                # yield self.env.timeout(delay*random_number)
    
    # 这段代码定义了一个分片区块链节点处理接收到的交易区块（Tx-block）的方法。
    # 这个方法考虑了不同类型的节点（如分片领导者、主委员会节点、普通分片节点）以及它们在接收到交易区块时的行为。
    # 下面是对这个函数的详细解释和关键点分析：
    def process_received_tx_block(self, tx_block, sender_id):
        """
        Handle the received Tx-block
        """

        # 首先检查接收到的交易区块是否属于当前节点的分片。如果不是，抛出异常。
        if self.shard_id != tx_block.shard_id:
            raise RuntimeError("Tx-block received by other shard node.")

        #    - 如果节点类型为0，表示节点处于重配置期间，不应接收交易区块，抛出异常。
        #    - 如果节点类型为1，表示节点是主委员会的一部分，不应直接处理交易区块，抛出异常。
        if self.node_type == 0:
            raise RuntimeError("Tx-block received in between re-configuration.")
            # To-do: Complete when dealing with nodes re-configuration (new epoch)
        
        if self.node_type == 1:
            raise RuntimeError("Tx-block received by Principal Committee node.")

        # **投票检查**：通过调用`is_voting_complete`函数检查交易区块的投票是否完成。
        flag = is_voting_complete(tx_block)

        shard_neigbours = get_shard_neighbours(
            self.curr_shard_nodes, self.neighbours_ids, self.shard_id
        )


        # **分片领导者处理**：如果节点类型为2（分片领导者），并且交易区块的投票已完成，打印相关信息并生成小区块。如果投票未完成，抛出异常。
        if self.node_type == 2:
            if flag:
                if self.params["verbose"]:
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "Node %s (Leader) received voted Tx-block %s" % (self.id, tx_block.id)
                    )
                self.generate_mini_block(tx_block, 'intra_shard_tx_block')
            else:
                raise RuntimeError(f"Shard Leader {self.id} received a voted Tx-block {tx_block.id} which is not been voted by all shard nodes.")

        # **普通分片节点处理**：- 如果投票已完成，并且当前节点是普通分片节点（类型为3），则将交易区块广播给下一个节点（通过`next_hop_id`）。
        #    - 如果投票未完成，并且当前节点尚未对该交易区块投票，则进行投票，并根据投票结果决定下一步行动：
        #      - 如果投票完成，则将交易区块只发送给下一个节点。
        #      - 如果投票未完成，则将交易区块广播给除发送者外的所有邻居节点。
        elif self.node_type == 3:
            if flag:
                if self.params["verbose"]:
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "Node %s (shard node) propagated voted Tx-block %s" % (self.id, tx_block.id)
                    )

                broadcast(
                    self.env, 
                    tx_block, 
                    "Tx-block", 
                    self.id, 
                    [ self.next_hop_id ], 
                    self.curr_shard_nodes, 
                    self.params
                )
            else:
                if is_vote_casted(tx_block, self.id) == False:

                    self.cast_vote(tx_block)
                    # print("节点"+self.id+"投票完毕")
                    self.params["Number_of_votes_of_ordinary_segmented_nodes"][self.id] = self.params["Number_of_votes_of_ordinary_segmented_nodes"][self.id] + 1

                    if self.params["verbose"]:
                        print(
                            "%7.4f" % self.env.now
                            + " : "
                            + "Node %s voted for the Tx-block %s" % (self.id, tx_block.id)
                        )

                    # If voting is complete, pass the tx-block to the leader, else broadcast it further in the network
                    neighbours = []
                    if is_voting_complete(tx_block):
                        neighbours = [ self.next_hop_id ]
                        if self.params["verbose"]:
                            print(
                                "%7.4f" % self.env.now
                                + " : "
                                + "Voting for the tx-block %s is complete and node %s sent it on its path to shard leader" % (tx_block.id, self.id)
                            )
                    else:
                        neighbours = shard_neigbours    # Exclude source node
                        neighbours.remove(sender_id)
                    # print("节点"+self.id+"广播交易区块")
                    broadcast(
                        self.env, 
                        tx_block, 
                        "Tx-block", 
                        self.id, 
                        neighbours, 
                        self.curr_shard_nodes, 
                        self.params
                    )

            
    # 目的：处理接收到的迷你区块列表，并在主委员会节点之间进行投票以达成共识。
    # 参数：blocks 是接收到的迷你区块列表，sender_id 是发送这些区块的节点ID。
    def process_received_mini_blocks_list(self, blocks, sender_id):
        """
        Handle the received list of mini-blocks
        """

        # 节点类型验证：首先检查当前节点是否为主委员会节点（node_type = 1）。如果不是，抛出异常，因为只有主委员会节点应处理迷你区块列表的投票。
        if self.node_type != 1:
            raise RuntimeError(f"Mini-block list (voting) received by node other than a principal committee node. Received by node {self.id}.")


        # print("process_received_mini_blocks_list blocks:", blocks)
        # 主委员会领导者处理：
        # 如果当前节点是主委员会的领导者（self.id == self.pc_leader_id），则遍历接收到的迷名区块列表。
        # 对于每个迷你区块，领导者在其mini_block_consensus_pool中记录来自发送节点的投票结果。
        # 这里假设迷你区块的message_data字段包含了来自发送节点对该迷你区块的投票信息。
        if self.id == self.pc_leader_id:
            for mini_block in blocks:
                self.mini_block_consensus_pool[mini_block.id]["votes"][sender_id] = mini_block.message_data[sender_id]

        #     非领导者主委员会节点处理：
        # 对于不是领导者的主委员会节点，遍历接收到的迷你区块列表，并对每个迷你区块进行投票。
        # 投票是基于一个随机数生成器的结果，与预设的阈值（这里为0.5）比较来决定投或不投赞成票。这是一个简化的投票机制，实际应用中可能需要更复杂的逻辑来确定投票结果。
        # 每次投票后，创建一个新的迷你区块对象，包含当前节点的投票结果，并将这些新的迷你区块添加到voted_blocks列表中。
        # 最后，将voted_blocks列表广播给主委员会的领导者，以便进一步处理和最终的共识决定。
        else:
            voted_blocks = []
            for mini_block in blocks:
                consensus_delay_obj = Consensus(1, 1)
                # To-do: Adjust threshold
                threshold = 0.5
                vote = 1 if consensus_delay_obj.get_random_number() > threshold else 0

                new_mini_block = MiniBlock(mini_block.id, mini_block.transactions_list, mini_block.params, mini_block.shard_id, self.env.now)
                new_mini_block.shard_id = mini_block.shard_id

                new_mini_block.message_data[self.id] = vote
                voted_blocks.append(new_mini_block)

                self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][self.id] = self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][self.id] + 1

            broadcast(
                self.env, 
                voted_blocks, 
                "Mini-blocks-voting", 
                self.id, 
                [ self.pc_leader_id ], 
                self.curr_shard_nodes, 
                self.params
            )

    # 目的：在主委员会节点中处理接收到的迷你区块，包括进行投票和决策是否广播该区块。
    # 参数：block 是接收到的迷你区块。
    def process_received_mini_block(self, block):
        """
        Handle the received mini-block
        """
        # print("接收到mini-block")
        # 节点类型验证：首先检查当前节点是否为主委员会节点（node_type = 1）。如果不是，抛出异常，因为只有主委员会节点应处理迷你区块。
        if self.node_type != 1:
            raise RuntimeError(f"Mini-block received by node other than a principal committee node. Received by node {self.id}.")

        # 领导者节点：如果当前节点是主委员会的领导者，并且接收到的迷你区块尚未被处理过（即不在processed_mini_blocks列表中），则执行以下操作：
        """ M - 1 (With leader) """
        if block not in self.processed_mini_blocks:
            if self.id == self.pc_leader_id:
                # 将迷你区块添加到mini_blocks_vote_pool列表中，用于后续的投票和共识过程。
                self.mini_blocks_vote_pool.append(block)
                # print(f"Debug: Initializing block {block.id}")
                # 在mini_block_consensus_pool中为该迷你区块初始化投票记录，包括存储区块数据和初始化投票字典
                self.mini_block_consensus_pool[block.id] = {}
                self.mini_block_consensus_pool[block.id]["data"] = block
                self.mini_block_consensus_pool[block.id]["votes"] = {}

                # 对该迷你区块进行投票，投票结果基于随机数生成器与预设阈值（0.5）的比较得出。
                consensus_delay_obj = Consensus(1, 1)
                # To-do: Adjust threshold
                threshold = 0.5
                # 随机数大于 0.5 的概率大约是 0.6915 或者 69.15%
                vote = 1 if consensus_delay_obj.get_random_number() > threshold else 0
                self.mini_block_consensus_pool[block.id]["votes"][self.id] = vote
                # print("广播mini-block")
                # 如果mini_blocks_vote_pool的大小达到了分片数（params["num_shards"]），
                # 则向主委员会的其他节点广播这些迷你区块进行投票，并清空投票池以准备下一轮。
                if len(self.mini_blocks_vote_pool) == self.params["num_shards"]:
                    principal_committee_neigbours = get_principal_committee_neigbours(self.curr_shard_nodes, self.neighbours_ids)
                    broadcast(
                        self.env, 
                        self.mini_blocks_vote_pool, 
                        "Mini-blocks-voting", 
                        self.id, 
                        principal_committee_neigbours, 
                        self.curr_shard_nodes, 
                        self.params
                    )

                    self.mini_blocks_vote_pool = []

            # 非领导者节点：如果当前节点不是领导者，则直接将迷名区块广播给主委员会的领导者，以便进行集中处理和投票。
            # 因为接收者就是主委员会节点，所以他的邻居也是朱委会节点
            # 最后，将处理过的迷你区块添加到processed_mini_blocks列表中，以避免重复处理。
            else:
                broadcast(
                    self.env, 
                    block, 
                    "Mini-block-consensus", 
                    self.id, 
                    [ self.pc_leader_id ], 
                    self.curr_shard_nodes,
                    self.params
                )
            
            self.processed_mini_blocks.append(block)

        """ M - 2 (Without leader)
        if not block.publisher_info:                  # MiniBlock received from the shard leader
            self.mini_block_consensus_pool[block.id] = {}
            self.mini_block_consensus_pool[block.id]["data"] = block
            self.mini_block_consensus_pool[block.id]["votes"] = {}

            principal_committee_neigbours = get_principal_committee_neigbours(self.curr_shard_nodes, self.neighbours_ids)
            for neighbour_id in principal_committee_neigbours:
                self.mini_block_consensus_pool[block.id]["votes"][neighbour_id] = -1
                # -1 = No vote received
            
            # To-do: Adjust mu and sigma for conensus delay; yielding not working
            consensus_delay_obj = Consensus(1, 1)
            # yield self.env.timeout(consensus_delay_obj.get_consensus_time())

            # To-do: Adjust threshold
            threshold = 0.5
            vote = 1 if consensus_delay_obj.get_random_number() > threshold else 0

            # Add own vote for this mini-block
            self.mini_block_consensus_pool[block.id]["votes"][self.id] = vote

            # Add meta-data to the mini-block before the broadcast
            block.publisher_info["id"] = self.id
            block.publisher_info["vote"] = vote
            
            # print(f"bugs = {get_principal_committee_neigbours(self.curr_shard_nodes, self.neighbours_ids)}")
            broadcast(
                self.env, 
                block, 
                "Mini-block-consensus", 
                self.id, 
                get_principal_committee_neigbours(self.curr_shard_nodes, self.neighbours_ids),
                self.curr_shard_nodes, 
                self.params,
            )

        else:       # MiniBlock received from the principal committee neighbor
            
            # Pseudo-code:

            # Update the publisher's (or sender's) vote to own consensus_pool
            # If receiving mini-block for the first time {
            #     a. Cast vote for the block and add it to its own pool
            #     b. Broadcast it to other neighbour nodes to let them know your own vote
            # }
            # else {
            #     a. Filter the neighbours which haven't casted their vote
            #     b. Broadcast it to only thos neighbours
            # }
            

            if has_received_mini_block(self.mini_block_consensus_pool, block.id):
                # Add publisher's vote in its own data copy
                self.mini_block_consensus_pool[block.id]["votes"][block.publisher_info["id"]] = block.publisher_info["vote"]
                
                # Filter the neighbours who have already voted for the mini-block
                principal_committee_neigbours = get_principal_committee_neigbours(self.curr_shard_nodes, self.neighbours_ids)
                filtered_neighbour_ids = [ id for id in principal_committee_neigbours if id not in self.mini_block_consensus_pool[block.id] ]
                filtered_neighbour_ids += [ id for id, vote in self.mini_block_consensus_pool[block.id].items() if vote == -1 ]
                
                # Add meta-data to the mini-block before the broadcast
                prev_publisher_id = block.publisher_info["id"]
                block.publisher_info["id"] = self.id
                block.publisher_info["vote"] = self.mini_block_consensus_pool[block.id]["votes"][self.id]
                
                if filtered_neighbour_ids:
                    # print(f"[Debug for - {self.id} = {filtered_neighbour_ids}")
                    # print(f"More info - {self.mini_block_consensus_pool}")
                    # print(f"[Filter Debug] - {filtered_neighbour_ids} {self.id}")
                    block.message_data = [ self.id ]
                    broadcast(
                        self.env, 
                        block, 
                        "Mini-block-consensus", 
                        self.id, 
                        filtered_neighbour_ids,
                        self.curr_shard_nodes, 
                        self.params,
                    )
                else:
                    if block.message_data and prev_publisher_id == block.message_data[0]:
                        # print(f"Meta = {block.message_data}")
                        block.message_data = []
                        broadcast(
                            self.env, 
                            block, 
                            "Mini-block-consensus", 
                            self.id, 
                            [ prev_publisher_id ],
                            self.curr_shard_nodes, 
                            self.params,
                        )
            else:
                # print(f"[Debug] - {self.mini_block_consensus_pool}")
                # print(f"Contd. - {block.id}")
                self.mini_block_consensus_pool[block.id] = {}
                self.mini_block_consensus_pool[block.id]["data"] = block
                self.mini_block_consensus_pool[block.id]["votes"] = {}

                # Add publisher's vote in its own data copy
                self.mini_block_consensus_pool[block.id]["votes"][block.publisher_info["id"]] = block.publisher_info["vote"]

                # Add own vote for the mini-block if vote not yet casted
                if self.id not in self.mini_block_consensus_pool[block.id]["votes"]:
                    consensus_delay_obj = Consensus(1, 1)
                    # yield self.env.timeout(consensus_delay_obj.get_consensus_time())

                    # To-do: Adjust threshold
                    threshold = 0.5
                    vote = 1 if consensus_delay_obj.get_random_number() > threshold else 0
                    self.mini_block_consensus_pool[block.id]["votes"][self.id] = vote
                
                # Add meta-data to the mini-block before the broadcast
                block.publisher_info["id"] = self.id
                block.publisher_info["vote"] = self.mini_block_consensus_pool[block.id]["votes"][self.id]
                
                # print(f"bugs = {get_principal_committee_neigbours(self.curr_shard_nodes, self.neighbours_ids)}")
                broadcast(
                    self.env, 
                    block, 
                    "Mini-block-consensus", 
                    self.id, 
                    get_principal_committee_neigbours(self.curr_shard_nodes, self.neighbours_ids),
                    self.curr_shard_nodes, 
                    self.params,
                )
            """
            
    # 这行定义了一个名为process_received_block的方法，它接收两个参数：self和block。
    # self代表类的实例本身，是在类的方法中自动传入的，而block可能是一个代表区块的数据结构，比如字典、列表或是一个自定义对象。

    def process_received_block(self, block):
        # 判断区块是否已存在:
        # 这行代码检查接收到的区块block是否不在当前实例的blockchain属性中。
        # 这里的blockchain可能是一个列表或集合，用来存储已经接收或生成的区块。
        if block not in self.blockchain:
            # 更新区块链:
            # 如果接收到的区块block不在blockchain中，这行代码将调用update_blockchain方法来更新当前实例的区块链，
            # 将新的区块加入到区块链中。这可能涉及到验证区块的合法性、计算哈希值等操作。
            self.update_blockchain(block)

            broadcast(
                self.env, 
                block,
                "Block", 
                self.id, 
                self.neighbours_ids,
                self.curr_shard_nodes, 
                self.params
            ) 


    def process_received_cross_shard_block(self, cross_shard_block, sender_id):
        """
        Handle the received Cross-shard-block
        """
        # 首先，根据节点的类型（node_type），这段代码会检查是否允许处理跨分片区块。
        # 如果node_type为0，表示节点处于重配置阶段，不应接收跨分片区块，将抛出一个运行时错误。
        # 如果node_type为1，表示节点是主委员会（Principal Committee）的一部分，也不应接收跨分片区块，同样抛出错误。
        if self.node_type == 0:
            raise RuntimeError("Cross-shard-block received in between re-configuration.")
            
        if self.node_type == 1:
            raise RuntimeError("Cross-shard-block received by Principal Committee node.")    

        # 通过调用is_voting_complete_for_cross_shard_block函数，
        # 检查对于该跨分片区块的投票是否已经完成。这个函数可能会检查所有必要的节点是否已对该区块进行了投票。
        flag = is_voting_complete_for_cross_shard_block(cross_shard_block, self.shard_id)
            
        # print(f"[Check] = For {cross_shard_block.id}, {self.id} has {self.shard_id} and {cross_shard_block.originating_shard_id}")
        # 根据当前节点的分片ID（shard_id）与区块的原始分片ID（originating_shard_id）进行比较，决定如何处理该跨分片区块。
        # 如果两者相同，并且投票已完成，节点将执行一系列操作，包括生成一个包含跨分片交易的迷你区块（mini-block）。
        if self.shard_id == cross_shard_block.originating_shard_id:
            if flag:
                # print(f"Votes status -\n{print(json.dumps(cross_shard_block.shard_votes_status, indent=4))}")
                shard_leader_map = {}
                tx_map = {}
                for leader_id, leader in self.shard_leaders.items():
                    shard_leader_map[leader.shard_id] = leader_id

                for tx in cross_shard_block.transactions_list:
                    tx_map[tx.id] = tx

                """ To Resolve
                for shard_id, tx_info in cross_shard_block.shard_votes_status.items():
                    # print(json.dumps(tx_info, indent=4))
                    for tx_id, tx_status in tx_info.items():
                        relevant_nodes_flag = self.shard_leaders[shard_leader_map[shard_id]].curr_shard_nodes[tx_map[tx_id].receiver].shard_id != shard_id
                        for _, node_vote in tx_status.items():
                            if not relevant_nodes_flag and (node_vote == -1):
                                # print(relevant_nodes_flag)
                                # print(tx_status, tx_map[tx_id].receiver)
                                raise RuntimeError(f"Cross-shard-block {cross_shard_block.id} received by the leader {self.id} of originating shard is not completely voted.")
                            
                            # (a and not b) or (not a and b) = bool(a) ^ bool(b) 
                            if relevant_nodes_flag ^ (node_vote == 2):
                                # print(f"Receiver node = {tx_map[tx_id].receiver},\n \
                                # tx_id = {tx_id}, \n \
                                # originating shard = {cross_shard_block.originating_shard_id},\n \
                                # current shard = {shard_id},\n \
                                # flag = {relevant_nodes_flag},\n \
                                # vote = {node_vote}")
                                raise RuntimeError(f"Cross-shard-block {cross_shard_block.id} has improper voting done by the shards.")
                """

                if self.params["verbose"]:
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "Node %s (Leader) received voted cross-shard-block %s which originated in its own shard" % (self.id, cross_shard_block.id)
                    )
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "Node %s (Leader) generating mini-block consisting of cross-shard tx" % (self.id)
                    )

                # Generate mini-block consisting of cross-shard-blocks
                self.generate_mini_block(cross_shard_block, 'cross_shard_tx_block')
        # 如果两者不同，根据节点类型（node_type）有不同的处理逻辑：
        else:
            shard_neigbours = get_shard_neighbours(
                self.curr_shard_nodes, self.neighbours_ids, self.shard_id
            )
            # 如果是分片领导者（node_type为2），并且投票完成，会将该区块广播给原始分片的领导者。
            if self.node_type == 2:
                if flag:
                    if self.params["verbose"]:
                        print(
                            "%7.4f" % self.env.now
                            + " : "
                            + "Node %s (Leader) received voted Cross-shard-block %s but it didn't originate in its own shard" % (self.id, cross_shard_block.id)
                        )
                    
                    neighbours_list = [ node.id for node in self.shard_leaders.values() if node.shard_id == cross_shard_block.originating_shard_id]
                    # print(f"[Debug] - Sending {cross_shard_block.id} to {neighbours_list} and originating shard = {cross_shard_block.originating_shard_id}")
                    broadcast(
                        self.env, 
                        cross_shard_block, 
                        "Voted-Cross-shard-block", 
                        self.id, 
                        neighbours_list, 
                        self.curr_shard_nodes, 
                        self.params
                    )
                else:
                    # print(f"Cross-shard-block originated in the shard {cross_shard_block.originating_shard_id} and is currently in {self.shard_id}")
                    print("是分片领导者（node_type为2），并且投票未完成")
                    raise RuntimeError(f"Shard Leader {self.id} received a voted Cross-shard-block {cross_shard_block.id} which is not been voted by all shard nodes.")
            # 如果是普通分片节点（node_type为3），根据投票情况，可能会对区块投票，并根据投票结果决定是直接发送给分片领导者还是广播给更多节点。
            elif self.node_type == 3:
                if flag:
                    if self.params["verbose"]:
                        print(
                            "%7.4f" % self.env.now
                            + " : "
                            + "Node %s (shard node) propagated voted Cross-shard-block %s" % (self.id, cross_shard_block.id)
                        )

                    broadcast(
                        self.env, 
                        cross_shard_block, 
                        "Cross-shard-block", 
                        self.id, 
                        [ self.next_hop_id ], 
                        self.curr_shard_nodes, 
                        self.params
                    )
                else:
                    if is_vote_casted_for_cross_shard_block(cross_shard_block, self.shard_id, self.id) == False:
                        # print(f"Debug - Id is {cross_shard_block.id} \nVotes = {cross_shard_block.shard_votes_status[self.shard_id]}")
                        # 处理过程中，根据不同情况使用broadcast函数广播跨分片区块或者使用cast_vote_for_cross_shard_block函数对区块进行投票。
                        self.cast_vote_for_cross_shard_block(cross_shard_block)
                        # yield self.env.timeout(self.params["Node_processing_delay"][self.id])
                        self.params["Number_of_votes_of_ordinary_segmented_nodes"][self.id] = self.params["Number_of_votes_of_ordinary_segmented_nodes"][self.id] + 1
                        # print(f"Debug - Id is {cross_shard_block.id} \nVotes = {json.dumps(cross_shard_block.shard_votes_status[self.shard_id], indent=4)}")
                        if self.params["verbose"]:
                            print(
                                "%7.4f" % self.env.now
                                + " : "
                                + "Node %s voted for the Cross-shard-block %s" % (self.id, cross_shard_block.id)
                            )

                        # If voting is complete, pass the Cross-shard-block to the leader, else broadcast it further in the network
                        neighbours = []
                        if is_voting_complete_for_cross_shard_block(cross_shard_block, self.shard_id):
                            neighbours = [ self.next_hop_id ]
                            if self.params["verbose"]:
                                print(
                                    "%7.4f" % self.env.now
                                    + " : "
                                    + "Voting for the Cross-shard-block %s is complete and node %s sent it on its path to shard leader" % (cross_shard_block.id, self.id)
                                )
                        else:
                            neighbours = shard_neigbours    # Exclude source node
                            neighbours.remove(sender_id)

                        # print(f"Sourav {self.id} - {is_voting_complete_for_cross_shard_block(cross_shard_block, self.shard_id)} and list is \n {cross_shard_block.shard_votes_status[self.shard_id]}")
                        broadcast(
                            self.env, 
                            cross_shard_block, 
                            "Cross-shard-block", 
                            self.id, 
                            neighbours, 
                            self.curr_shard_nodes, 
                            self.params
                        )


    def update_blockchain(self, block):
        # 添加区块到区块链： 通过 self.blockchain.append(block)，
        # 将传入的 block 添加到节点维护的 blockchain 列表的末尾。这个操作表示将新的区块加入到该节点的本地区块链副本中。
        self.blockchain.append(block)

        # 如果节点是分片领导者，那么执行 self.params["chain"] = self.blockchain。
        # 这一步将节点的 blockchain 属性（即其维护的区块链副本）赋值给 self.params 字典中的 "chain" 键。
        # 这可能是为了在节点的其他操作中方便地访问当前的区块链状态，或者是为了记录、监控、或与其他系统组件共享当前的区块链状态。
        if self.node_type == 2:
            self.params["chain"] = self.blockchain




    def get_cross_shard_random_node_id(self):
        # # 初始化跨分片领导者
        # cross_shard_leader = self.shard_leaders[self.id]
        # # 循环 while(cross_shard_leader.id == self.id): 确保选中的 cross_shard_leader 不是当前节点自身。
        # # 如果是，则通过 random.choice(list(self.shard_leaders.values()))
        # # 从所有分片领导者中随机选择一个，直到这个领导者不是自己。
        # while(cross_shard_leader.id == self.id):
        #     cross_shard_leader = random.choice(list(self.shard_leaders.values()))
        # # 这行代码从选中的跨分片领导者的当前分片中筛选出所有节点，确保这些节点属于该跨分片领导者的分片。
        # curr_shard_nodes = [node for node in cross_shard_leader.curr_shard_nodes.values() if node.shard_id == cross_shard_leader.shard_id]
        # # 首先随机选择一个节点作为 cross_shard_node。
        # cross_shard_node = random.choice(curr_shard_nodes)
        # # 然后，通过循环 while(cross_shard_node.node_type == 2): 检查如果所选节点是领导者节点（node_type == 2），
        # # 则重新随机选择，直到选中的节点不是领导者节点。
        # while(cross_shard_node.node_type == 2):
        #     cross_shard_node = random.choice(curr_shard_nodes)
        # # 最后，返回所选非领导者节点的 ID。
        # return cross_shard_node.id
        """
        从不属于当前节点所在分片的其他节点中随机选择一个节点的 ID。
        """
        current_shard_id = self.shard_id
        all_full_nodes = self.params["all_full_nodes"]

        # 获取所有符合条件的节点的 ID
        filtered_cross_shard_nodes = [
            node_id
            for node_id, node in all_full_nodes.items()
            if node.shard_id != current_shard_id and node.node_type == 3
        ]

        # 如果存在符合条件的节点，则从中随机选择一个
        if filtered_cross_shard_nodes:
            return random.choice(filtered_cross_shard_nodes)
        else:
            # 如果没有符合条件的节点，可以选择返回 None 或者抛出异常等处理方式
            return None  # 或者抛出异常等处理方式

    def get_intra_shard_random_node_id(self):
        # 遍历当前分片的节点，只选择那些属于当前分片且类型为分片成员（node_type == 3）的节点，用于后续处理。
        filtered_curr_shard_nodes = []
        for node_id in self.curr_shard_nodes.keys():
            if self.curr_shard_nodes[node_id].shard_id == self.shard_id and self.curr_shard_nodes[node_id].node_type == 3:
                filtered_curr_shard_nodes.append(node_id)

        # 首先随机选择一个节点作为 cross_shard_node。
        intra_shard_node = random.choice(filtered_curr_shard_nodes)


        return intra_shard_node


    def update_current_load(self, current_load):
        self.current_load = current_load

    def update_load_capacity(self, load_capacity):
        self.load_capacity = load_capacity

    def wait_load_capacity(self):
        while self.current_load >= self.load_capacity:
            # print(self.id + "当前负载已满，等待下一次生成交易")
            # print(self.id + "self.current_load", self.current_load)
            # print(self.id + "self.load_capacity", self.load_capacity)
            delay = get_transaction_delay(
                self.params["transaction_mu"], self.params["transaction_sigma"]
            )
            yield self.env.timeout(50)
            # time.sleep(0.1)
            # 输出当前的 self.current_load
            print("节点" + self.id + "当前负载:", self.current_load)

            if self.current_load >= self.load_capacity:
                print("节点" + self.id + "处理完一个交易，当前负载减1")
                self.current_load = self.current_load - 1
            else:
                break