# from time import time
import numpy as np
import time
import random

from nodes.participating_node import ParticipatingNode
from nodes.full_node import FullNode
from network.pipe import Pipe
from utils.spanning_tree import SpanningTree
from utils.helper import assign_next_hop_to_leader, get_load_capacity_delay, get_deal_delay
import networkx as nx
import community
class Network:
    """
    This class models the backbone of the entire blockchain network.
    """

    # 初始化了一个对象的多个属性。这个构造函数接收三个参数：name、env 和 params。这些参数被用来初始化类的属性，并执行一些初始设置，如添加参与节点。下面是对这个构造函数中的关键部分的解释：
    #
    # 初始化基本属性：
    #
    # self.name: 对象的名称。
    # self.env: 环境变量，可能用于控制或模拟的环境。
    # self.params: 一个包含多个配置参数的字典。
    # 从参数字典中获取特定的设置：
    #
    # self.locations: 从 params 字典中获取“locations”。
    # self.num_nodes: 从 params 字典中获取节点数量（'num_nodes'）。
    # 初始化一些空的或预设的容器：
    #
    # self.participating_nodes: 初始化为空列表，用于存储参与节点。
    # self.full_nodes: 初始化为空字典，可能用于存储完整节点的信息。
    # self.principal_committee_node_ids: 初始化为空列表，可能用于存储主委员会节点的 ID。
    # self.shard_nodes: 初始化为空列表，可能用于存储分片节点。
    # self.pipes: 初始化为空字典，可能用于存储管道（或通信渠道）。
    # 添加参与节点：
    #
    # self.add_participating_nodes(params["num_nodes"]): 调用 add_participating_nodes 方法，将基于 params 中提供的节点数量添加参与节点。
    # 这个构造函数的设计表明，它是为了初始化一个可能用于分布式系统或区块链网络中的节点管理或网络模拟的对象。params 字典预计包含了初始化这个对象所需的所有配置选项，包括节点数量、位置等信息。
    # def __init__(self, name, env, params):
    def __init__(self, name, params):
        self.name = name
        # self.env = env
        self.params = params
        self.locations = params["locations"]
        self.participating_nodes = []
        self.full_nodes = {}
        self.principal_committee_node_ids = []
        self.shard_nodes = []
        self.pipes = {}
        self.num_nodes = params['num_nodes']
        # self.add_participating_nodes(params["num_nodes"])
        self.load_capacity = {}

    # 如果没有传入节点数量，那么num_nodes为20
    def add_participating_nodes(self, num_nodes=20):
        """
        Add the participating nodes - nodes which want to be 
        part of the network (may contain) Sybil identities.
        """
        graph = nx.Graph()  # 创建一个无向图
        self.params["graph"] = graph

        # 节点id是截至目前的序列号 添加参与节点
        for id in range(num_nodes):
            location = np.random.choice(self.locations, size=1)[0]
            self.participating_nodes.append(ParticipatingNode(
                id,
                self.env,
                location,
                self.params
            ))
            if bool(self.params["verbose"]) and self.params["verbose"] == "elaborate":
                print(
                    "%7.4f" % self.env.now
                    + " : "
                    + "%s added at location %s"
                    % ("PN%d" % id, location)
                )

    # 这个函数 execute_sybil_resistance_mechanism 是 Network 类的一个方法，用于执行防 Sybil 攻击的机制。
    # 具体来说，它使用了一种简单的方法来随机选择一些节点作为全节点（full nodes）。
    #
    # Sybil 攻击是一种网络攻击，攻击者创建大量伪造的节点，试图在网络中获得主导地位。
    # 为了防止这种攻击，网络需要一种机制来限制节点的数量或权重。在这个函数中，这种机制是通过随机选择一些节点作为全节点来实现的。
    #
    # 以下是这个函数的详细解释：
    #
    # 首先，它创建一个掩码 mask，这是一个由 0 和 1 组成的数组，长度为节点的数量。
    # 数组中的每个元素都是随机选择的，选择 0 和 1 的概率都是 0.5。
    #
    # 然后，它遍历所有的节点。对于每个节点，如果掩码对应的元素为 1，那么它就将这个节点转换为全节点。
    # 全节点的创建使用了 FullNode 类，这个类的定义没有在这段代码中给出，
    # 但可以推测它可能是 Network 的一个子类或相关类，用于表示具有更多权力或责任的节点。
    #
    # 如果参数字典中的 verbose 为 True，那么它还会打印一条消息，表示这个节点已经进入了网络。
    #
    # 对于掩码对应的元素为 0 的节点，这个函数目前并没有做任何处理，
    # 但在 else 分支中留有一个占位符，表示可能会添加一些处理被拒绝的节点的代码。
    #
    # 这个函数的主要作用是随机选择一些节点作为全节点，以此作为防止 Sybil 攻击的一种简单机制。
    # 这种机制的效果可能并不理想，因为它并没有考虑节点的行为或贡献，只是简单地随机选择。在实际的网络中，
    # 可能需要使用更复杂的机制，比如基于节点的行为、贡献或抵押的权益证明（Proof of Stake）机制。

    # execute_sybil_resistance_mechanism：这个函数旨在实现一个Sybil抵抗机制，即通过某种机制筛选节点，决定哪些节点可以成为全节点（full nodes）。
    def execute_sybil_resistance_mechanism(self):       # Sybil Resistance: https://en.wikipedia.org/wiki/Sybil_attack

        
        # participating_node_ids = list(self.participating_nodes.keys())

        # Dummy mechanism: currently we are choosing nodes at random and converting them to full nodes
        # 随机选择机制：
        #
        # 您使用了 numpy 的 random.choice 函数来随机选择哪些节点可以成为全节点。这里的概率 p=[0, 1] 应该是一个错误，
        # 因为这意味着所有节点都将被选中。正确的概率分配可能是类似 p=[0.9, 0.1]（90% 的概率不被选中，10% 的概率被选中）。
        mask = np.random.choice([0, 1], size=(self.num_nodes,), p=[0, 1])

        for idx in range(self.num_nodes):
            curr_participating_node = self.participating_nodes[idx]

            # 遍历所有节点，根据随机生成的掩码（mask）决定哪些节点成为全节点。
            # 如果掩码为 1，当前节点被升级为全节点，并存储在 self.full_nodes 字典中。
            # 如果有必要（self.params["verbose"] 为 True），则打印相关信息，显示节点转换的状态。
            if mask[idx] == 1:
                curr_id = curr_participating_node.id
                curr_participating_node.params["load_capacity"] = (int(round(get_load_capacity_delay(curr_participating_node.params["transaction_processing_mu"], curr_participating_node.params["transaction_processing_sigma"]))))

                # print("curr_participating_node.params[load_capacity]:", curr_participating_node.params["load_capacity"])

                self.full_nodes["FN%d" % curr_id] = FullNode(
                    "FN%d" % curr_id,
                    # curr_participating_node.env,
                    self.env,
                    curr_participating_node.location,
                    curr_participating_node.params
                )
                # 给随机数设置新的种子，防止每次运行时生成相同的随机数
                np.random.seed(None)
                self.params["Node_processing_delay"][f"FN{curr_id}"] = (int(round(get_deal_delay(self.params["delay_mu"], self.params["delay_sigma"]))))
                self.load_capacity["FN%d" % curr_id] = curr_participating_node.params["load_capacity"]
                if bool(self.params["verbose"]):
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "%s entered the network from location %s"
                        % ("FN%d" % curr_id, curr_participating_node.location)
                    )
            else:
            # rejected nodes are looged here
                pass
        # print("self.load_capacity info:")
        # for key, value in self.load_capacity.items():
        #     print(f"{key}: {value}")

    def run_epoch(self):
        """
        Start executing a fresh epoch
        """

        self.start_time = time.time()
        # 这行代码记录了时代开始的时间。假设 self.env.now 返回当前的模拟时间或真实时间，这个时间点被记录为网络配置的开始时间。
        self.params["network_config_start_time"] = self.env.now

        print("开始分片")
        # 调用 partition_nodes 方法对节点进行分区。这可能涉及到根据节点的特性或网络的需求将节点分配到不同的组或分片中。
        self.partition_nodes(7)

        print("为节点设置频繁交易节点")
        # 为节点设置频繁交易节点
        self.get_frequent_transactions_custom()

        print("节点之间建立网络连接")
        # 通过调用 establish_network_connections 方法，在节点之间建立网络连接。
        # 这可能包括设置节点间的通信通道、交换必要的连接信息等，以确保网络中的节点可以相互通信。
        self.establish_network_connections()

        # 在完成网络配置和连接建立后，记录开始允许生成交易的时间点。这个时间点标志着网络开始处理交易。
        self.params["tx_start_time"] = self.env.now

        print("开始生成交易")
        # 调用 allow_transactions_generation 方法允许在网络中生成交易。
        # 这可能意味着网络开始接受用户或系统生成的交易，准备进行交易的验证、传播和打包等处理。
        self.allow_transactions_generation()
        # 最后，通过调用 display_network_info 方法，显示当前网络的状态信息。
        # 这可能包括网络的结构、节点的分布、连接状态等，用于监控和调试网络的运行状况。
        self.display_network_info()

        print("开始运行模拟器")
        # 运行模拟器，直到达到指定的模拟时间。
        self.env.run(until=self.env.now + self.params["simulation_time"])

        self.stop_time = time.time()

        if self.params["num_epochs"]-1 == self.params["current_epoch"]:
            #打印当前时期运行信息
            self.display_epoch_info()
        else:
            print("Epoch %d completed" % self.params["current_epoch"])
            print(self.params["num_epochs"])






    # 这段代码定义了一个名为 partition_nodes 的函数，其目的是在一个分布式系统或区块链网络中对节点进行分区，
    # 将它们划分为主委员会（Principal Committee）、领导者（Leaders）和分片成员（Shard Members）。
    def partition_nodes(self, mode_type):
        """
        Partititon the nodes in the network into principal committee, leaders
        and shard members
        """
        if self.params["current_epoch"] == 0:
            if self.params["run_type"] == 1:
                # Add members to the Principal Committee randomly
                # 随机选择主委员会成员：
                #
                # 首先，将所有全节点的键（假设是节点ID）列表化并随机打乱。
                # 根据 self.params["principal_committee_size"]（主委员会的预定大小比例）
                # 计算出主委员会应有的节点数，并从打乱后的节点列表中选取前N个节点作为主委员会成员。
                nodes = list(self.full_nodes.keys())
                np.random.shuffle(nodes)
                num_principal_committe_nodes = int(len(nodes) * self.params["principal_committee_size"])
                self.principal_committee_node_ids = nodes[0: num_principal_committe_nodes]

                # Randomly select the leader of the principal committee
                # 从主委员会成员中随机选取一个节点作为主委员会的领导者。
                principal_committee_leader = random.choice(self.principal_committee_node_ids)

                # 遍历主委员会成员的ID，将每个成员的 node_type 设置为 1（代表是主委员会成员），并记录主委员会领导者的ID。
                for node_id in self.principal_committee_node_ids:
                    self.full_nodes[node_id].node_type = 1
                    # self.principal_committee_node[node_id] = self.full_nodes[node_id]
                    self.full_nodes[node_id].pc_leader_id = principal_committee_leader
                    # self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"]["FN%d" % node_id] = 0
                    # self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                    self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][f"{node_id}"] = 0
                # Allot nodes to different shards
                # 除去被选为主委员会成员的节点后，剩余的节点被分配到不同的分片中。
                # 通过 np.array_split 方法将这些节点平均分配到 self.params["num_shards"] 指定的分片数量中。
                shard_nodes = nodes[num_principal_committe_nodes:]
                shard_groups = np.array_split(shard_nodes, self.params["num_shards"])


                # 对于每个分片，随机选择一个分片领导者（node_type 设置为 2），
                # 其余节点作为分片成员（node_type 设置为 3），并记录各自的分片ID和分片领导者ID。
                for idx in range(self.params["num_shards"]):
                    # Randomly select the shard leader
                    shard_leader_id = np.random.choice(shard_groups[idx])
                    self.full_nodes[shard_leader_id].node_type = 2
                    # self.params["Node_transaction_generation_num"]["FN%d" % shard_leader_id] = 0
                    self.params["Node_transaction_generation_num"][f"{shard_leader_id}"] = 0
                    # self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"]["FN%d" % shard_leader_id] = 0
                    self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][f"{shard_leader_id}"] = 0
                    for node_id in shard_groups[idx]:
                        self.full_nodes[node_id].shard_id = idx
                        self.full_nodes[node_id].shard_leader_id = shard_leader_id

                        if node_id != shard_leader_id:
                            self.full_nodes[node_id].node_type = 3
                            # self.params["Node_transaction_generation_num"]["FN%d" % node_id] = 0
                            # self.params["Number_of_votes_of_ordinary_segmented_nodes"]["FN%d" % node_id] = 0
                            self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                            self.params["Number_of_votes_of_ordinary_segmented_nodes"][f"{node_id}"] = 0

                # 将分片组信息转换为列表形式，方便后续处理。
                self.shard_nodes = [shards.tolist() for shards in shard_groups]

                # for id, node in self.full_nodes.items():
                #     if id not in self.principal_committee_node_ids:
                #         self.shard_nodes[node.shard_id - 1].append(node.id)
            if self.params["run_type"] == 2:
                # 随机选择主委员会成员
                nodes = list(self.full_nodes.keys())
                np.random.shuffle(nodes)
                num_principal_committe_nodes = int(len(nodes) * self.params["principal_committee_size"])
                self.principal_committee_node_ids = nodes[:num_principal_committe_nodes]

                # 随机选择主委员会领导者
                principal_committee_leader = random.choice(self.principal_committee_node_ids)

                # 设置主委员会成员的类型和领导者信息
                for node_id in self.principal_committee_node_ids:
                    self.full_nodes[node_id].node_type = 1
                    self.full_nodes[node_id].pc_leader_id = principal_committee_leader
                    self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][f"{node_id}"] = 0

                # 平均分配普通节点到分片
                shard_nodes = nodes[num_principal_committe_nodes:]
                shard_groups = np.array_split(shard_nodes, self.params["num_shards"])
                self.shard_nodes = [shard.tolist() for shard in shard_groups]  # 将 NumPy 数组转换为普通列表

                # 随机选举桥接分片和独立分片
                num_b_shards = int(len(self.shard_nodes) * 0.3)  # 桥接分片的数量应为总分片数的30%
                b_shard_indices = random.sample(range(len(self.shard_nodes)), num_b_shards)
                independent_shard_indices = [idx for idx in range(len(self.shard_nodes)) if idx not in b_shard_indices]

                # 分配桥接分片处理的独立分片交易
                Bshard_with_Ishard = {}
                for b_shard_idx in b_shard_indices:
                    if independent_shard_indices:
                        Bshard_with_Ishard[b_shard_idx] = independent_shard_indices[:2]
                        independent_shard_indices = independent_shard_indices[2:]

                # 为桥接分片设置类型
                for b_shard_idx in b_shard_indices:
                    for node_id in self.shard_nodes[b_shard_idx]:
                        self.full_nodes[node_id].shard_type = 2  # 设定为桥接分片类型

                # 对于剩下的分片，设置为独立分片
                for idx, shard in enumerate(self.shard_nodes):
                    if idx not in b_shard_indices:
                        for node_id in shard:
                            self.full_nodes[node_id].shard_type = 1  # 设定为独立分片类型

                self.params["Bshard_with_Ishard"] = Bshard_with_Ishard

                print("Bshard_with_Ishard:", self.params["Bshard_with_Ishard"])

                # 在完成最终检查后，有了最终的分片结果再为每个分片选择分片领导者
                for idx, shard in enumerate(self.shard_nodes):
                    # 从当前分片中选择处理延迟最小的节点作为分片领导者
                    shard_leader_id = min(shard, key=lambda node_id: self.params['Node_processing_delay'][node_id])

                    # 设置分片领导者的信息
                    self.full_nodes[shard_leader_id].node_type = 2
                    self.params["Node_transaction_generation_num"][f"{shard_leader_id}"] = 0
                    self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][f"{shard_leader_id}"] = 0

                    # 设置分片成员的信息
                    for node_id in shard:
                        self.full_nodes[node_id].shard_id = idx
                        self.full_nodes[node_id].shard_leader_id = shard_leader_id

                        if node_id != shard_leader_id:
                            if idx in b_shard_indices:
                                # 如果是桥接分片，则设置为桥接分片类型
                                self.full_nodes[node_id].shard_type = 2
                            else:
                                # 如果是独立分片，则设置为独立分片类型
                                self.full_nodes[node_id].shard_type = 1
                            self.full_nodes[node_id].node_type = 3
                            self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                            self.params["Number_of_votes_of_ordinary_segmented_nodes"][f"{node_id}"] = 0


                # for id, node in self.full_nodes.items():
                #     if id not in self.principal_committee_node_ids:
                #         self.shard_nodes[node.shard_id - 1].append(node.id)
            if self.params["run_type"] == 3:
                # Add members to the Principal Committee randomly
                # 随机选择主委员会成员：
                #
                # 首先，将所有全节点的键（假设是节点ID）列表化并随机打乱。
                # 根据 self.params["principal_committee_size"]（主委员会的预定大小比例）
                # 计算出主委员会应有的节点数，并从打乱后的节点列表中选取前N个节点作为主委员会成员。
                nodes = list(self.full_nodes.keys())
                np.random.shuffle(nodes)
                num_principal_committe_nodes = int(len(nodes) * self.params["principal_committee_size"])
                self.principal_committee_node_ids = nodes[0: num_principal_committe_nodes]

                # Randomly select the leader of the principal committee
                # 从主委员会成员中随机选取一个节点作为主委员会的领导者。
                principal_committee_leader = random.choice(self.principal_committee_node_ids)

                # 遍历主委员会成员的ID，将每个成员的 node_type 设置为 1（代表是主委员会成员），并记录主委员会领导者的ID。
                for node_id in self.principal_committee_node_ids:
                    self.full_nodes[node_id].node_type = 1
                    # self.principal_committee_node[node_id] = self.full_nodes[node_id]
                    self.full_nodes[node_id].pc_leader_id = principal_committee_leader
                    # self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"]["FN%d" % node_id] = 0
                    # self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                    self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][f"{node_id}"] = 0
                # Allot nodes to different shards
                # 除去被选为主委员会成员的节点后，剩余的节点被分配到不同的分片中。
                # 通过 np.array_split 方法将这些节点平均分配到 self.params["num_shards"] 指定的分片数量中。
                shard_nodes = nodes[num_principal_committe_nodes:]
                shard_groups = np.array_split(shard_nodes, self.params["num_shards"])


                # 对于每个分片，随机选择一个分片领导者（node_type 设置为 2），
                # 其余节点作为分片成员（node_type 设置为 3），并记录各自的分片ID和分片领导者ID。
                for idx in range(self.params["num_shards"]):
                    # Randomly select the shard leader
                    shard_leader_id = np.random.choice(shard_groups[idx])
                    self.full_nodes[shard_leader_id].node_type = 2
                    # self.params["Node_transaction_generation_num"]["FN%d" % shard_leader_id] = 0
                    self.params["Node_transaction_generation_num"][f"{shard_leader_id}"] = 0
                    # self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"]["FN%d" % shard_leader_id] = 0
                    self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][f"{shard_leader_id}"] = 0
                    for node_id in shard_groups[idx]:
                        self.full_nodes[node_id].shard_id = idx
                        self.full_nodes[node_id].shard_leader_id = shard_leader_id

                        if node_id != shard_leader_id:
                            self.full_nodes[node_id].node_type = 3
                            # self.params["Node_transaction_generation_num"]["FN%d" % node_id] = 0
                            # self.params["Number_of_votes_of_ordinary_segmented_nodes"]["FN%d" % node_id] = 0
                            self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                            self.params["Number_of_votes_of_ordinary_segmented_nodes"][f"{node_id}"] = 0

                # 将分片组信息转换为列表形式，方便后续处理。
                self.shard_nodes = [shards.tolist() for shards in shard_groups]

                # for id, node in self.full_nodes.items():
                #     if id not in self.principal_committee_node_ids:
                #         self.shard_nodes[node.shard_id - 1].append(node.id)
        else:
            if mode_type == 1:
                print("根据节点延迟分片")
                # 获取所有节点的处理延迟信息
                nodes_with_latency = [
                    (node_id, self.params['Node_processing_delay'][node_id])
                    for node_id in self.params['Node_processing_delay'].keys()
                ]

                # 根据处理延迟从小到大排序节点
                sorted_nodes = sorted(nodes_with_latency, key=lambda x: x[1])

                # 计算主委员会应有的节点数
                num_principal_committe_nodes = int(len(sorted_nodes) * self.params["principal_committee_size"])

                # 分配前 num_principal_committe_nodes 个节点作为主委员会成员
                self.principal_committee_node_ids = [node_id for node_id, _ in sorted_nodes[:num_principal_committe_nodes]]

                # 随机选择一个主委员会成员作为主委员会领导者
                principal_committee_leader = random.choice(self.principal_committee_node_ids)

                # 设置主委员会成员的类型和领导者信息
                for node_id, _ in sorted_nodes[:num_principal_committe_nodes]:
                    self.full_nodes[node_id].node_type = 1
                    self.full_nodes[node_id].pc_leader_id = principal_committee_leader
                    self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][f"{node_id}"] = 0

                # 剩余节点用于分片
                remaining_nodes = [node_id for node_id, _ in sorted_nodes[num_principal_committe_nodes:]]

                # 将剩余节点按照延迟顺序分配到分片中
                shard_groups = [[] for _ in range(self.params["num_shards"])]
                for idx, node_id in enumerate(remaining_nodes):
                    shard_id = idx % self.params["num_shards"]
                    shard_groups[shard_id].append(node_id)

                # 对于每个分片，选择处理延迟最小的节点作为分片领导者
                for idx in range(self.params["num_shards"]):
                    # 从当前分片中选择处理延迟最小的节点作为分片领导者
                    shard_leader_id = min(shard_groups[idx], key=lambda node_id: self.params['Node_processing_delay'][node_id])
                    self.full_nodes[shard_leader_id].node_type = 2
                    self.params["Node_transaction_generation_num"][f"{shard_leader_id}"] = 0
                    self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][f"{shard_leader_id}"] = 0

                    # 设置分片成员的信息
                    for node_id in shard_groups[idx]:
                        self.full_nodes[node_id].shard_id = idx
                        self.full_nodes[node_id].shard_leader_id = shard_leader_id

                        if node_id != shard_leader_id:
                            self.full_nodes[node_id].node_type = 3
                            self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                            self.params["Number_of_votes_of_ordinary_segmented_nodes"][f"{node_id}"] = 0

                # 将分片组信息转换为列表形式，方便后续处理。
                self.shard_nodes = [shards for shards in shard_groups]
            if mode_type == 2:
                # 应用Louvain方法来检测社区
                partition = community.best_partition(self.params["graph"], weight='weight')

                # 获取所有节点的处理延迟信息
                nodes_with_latency = [
                    (node_id, self.params['Node_processing_delay'][node_id])
                    for node_id in self.params['Node_processing_delay'].keys()
                ]

                # 根据处理延迟从小到大排序节点
                sorted_nodes = sorted(nodes_with_latency, key=lambda x: x[1])

                # 计算主委员会应有的节点数
                num_principal_committe_nodes = int(len(sorted_nodes) * self.params["principal_committee_size"])

                # 分配前 num_principal_committe_nodes 个节点作为主委员会成员
                self.principal_committee_node_ids = [node_id for node_id, _ in sorted_nodes[:num_principal_committe_nodes]]

                # 随机选择一个主委员会成员作为主委员会领导者
                principal_committee_leader = random.choice(self.principal_committee_node_ids)

                # 设置主委员会成员的类型和领导者信息
                for node_id, _ in sorted_nodes[:num_principal_committe_nodes]:
                    self.full_nodes[node_id].node_type = 1
                    self.full_nodes[node_id].pc_leader_id = principal_committee_leader
                    self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][f"{node_id}"] = 0

                # 根据社区检测结果分配分片
                shard_groups = {}
                for node_id, community_id in partition.items():
                    if community_id not in shard_groups:
                        shard_groups[community_id] = []
                    shard_groups[community_id].append(node_id)

                # 去除成为主委员会成员的节点
                for committee_node in self.principal_committee_node_ids:
                    for group in shard_groups.values():
                        if committee_node in group:
                            group.remove(committee_node)

                # 对于每个分片，选择处理延迟最小的节点作为分片领导者
                for idx, shard in enumerate(shard_groups.values()):
                    # 从当前分片中选择处理延迟最小的节点作为分片领导者
                    shard_leader_id = min(shard, key=lambda node_id: self.params['Node_processing_delay'][node_id])
                    self.full_nodes[shard_leader_id].node_type = 2
                    self.params["Node_transaction_generation_num"][f"{shard_leader_id}"] = 0
                    self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][f"{shard_leader_id}"] = 0

                    # 设置分片成员的信息
                    for node_id in shard:
                        self.full_nodes[node_id].shard_id = idx
                        self.full_nodes[node_id].shard_leader_id = shard_leader_id

                        if node_id != shard_leader_id:
                            self.full_nodes[node_id].node_type = 3
                            self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                            self.params["Number_of_votes_of_ordinary_segmented_nodes"][f"{node_id}"] = 0

                # 将分片组信息转换为列表形式，方便后续处理。
                self.shard_nodes = [shards for shards in shard_groups.values()]
            if mode_type == 3:
                     # 应用Louvain方法来检测社区
                partition = community.best_partition(self.params["graph"], weight='weight')

                # 获取所有节点的处理延迟信息
                nodes_with_latency = [
                    (node_id, self.params['Node_processing_delay'][node_id])
                    for node_id in self.params['Node_processing_delay'].keys()
                ]

                # 根据处理延迟从小到大排序节点
                sorted_nodes = sorted(nodes_with_latency, key=lambda x: x[1])

                # 计算主委员会应有的节点数
                num_principal_committe_nodes = int(len(sorted_nodes) * self.params["principal_committee_size"])

                # 分配前 num_principal_committe_nodes 个节点作为主委员会成员
                self.principal_committee_node_ids = [node_id for node_id, _ in sorted_nodes[:num_principal_committe_nodes]]

                # 随机选择一个主委员会成员作为主委员会领导者
                principal_committee_leader = random.choice(self.principal_committee_node_ids)

                # 设置主委员会成员的类型和领导者信息
                for node_id, _ in sorted_nodes[:num_principal_committe_nodes]:
                    self.full_nodes[node_id].node_type = 1
                    self.full_nodes[node_id].pc_leader_id = principal_committee_leader
                    self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][f"{node_id}"] = 0

                # 根据社区检测结果分配分片
                shard_groups = {}
                for node_id, community_id in partition.items():
                    if community_id not in shard_groups:
                        shard_groups[community_id] = []
                    shard_groups[community_id].append(node_id)

                # 去除成为主委员会成员的节点
                for committee_node in self.principal_committee_node_ids:
                    for group in shard_groups.values():
                        if committee_node in group:
                            group.remove(committee_node)

                # 将分片组信息转换为列表形式，方便后续处理。
                self.shard_nodes = [shards for shards in shard_groups.values()]

                # 动态调整分片大小
                # 定义一个阈值来判断是否需要分割或合并分片
                load_threshold = self.params.get("load_threshold", 100)  # 假设每分钟超过100个交易则认为过载
                min_nodes_per_shard = 4  # 每个分片至少包含4个节点

                # 检测每个分片的负载
                shard_loads = {}
                for shard_idx, shard in enumerate(self.shard_nodes):
                    # 计算分片的负载
                    subgraph = self.params["graph"].subgraph(shard)
                    load = subgraph.size(weight='weight')
                    shard_loads[shard_idx] = load

                # 根据负载情况调整分片
                # 分割过载的分片
                for shard_idx, load in shard_loads.items():
                    if load > load_threshold and len(self.shard_nodes[shard_idx]) > min_nodes_per_shard:
                        # 分割分片
                        subgraph = self.params["graph"].subgraph(self.shard_nodes[shard_idx])
                        new_partitions = community.best_partition(subgraph, weight='weight')

                        new_shards = {}
                        for node_id, community_id in new_partitions.items():
                            if community_id not in new_shards:
                                new_shards[community_id] = []
                            new_shards[community_id].append(node_id)

                        # 确保新分片至少包含4个节点
                        valid_new_shards = [shard for shard in new_shards.values() if len(shard) >= min_nodes_per_shard]

                        # 更新分片列表
                        del self.shard_nodes[shard_idx]
                        self.shard_nodes.extend(valid_new_shards)

                # 合并轻载的分片
                merged_shards = []
                for shard_idx, load in shard_loads.items():
                    if load < load_threshold / 2 and len(self.shard_nodes[shard_idx]) < min_nodes_per_shard:
                        merged_shards.append(shard_idx)

                # 合并选定的轻载分片
                while len(merged_shards) >= 2:
                    first_shard = merged_shards.pop(0)
                    second_shard = merged_shards.pop(0)
                    if len(self.shard_nodes[first_shard]) + len(self.shard_nodes[second_shard]) >= min_nodes_per_shard:
                        self.shard_nodes[first_shard].extend(self.shard_nodes[second_shard])
                        del self.shard_nodes[second_shard]

                # 最终检查是否有任何分片节点数不足的情况
                # 并进行必要的合并
                final_merged_shards = [idx for idx, shard in enumerate(self.shard_nodes) if len(shard) < min_nodes_per_shard]
                while final_merged_shards:
                    first_shard = final_merged_shards.pop(0)
                    second_shard = final_merged_shards.pop(0)
                    self.shard_nodes[first_shard].extend(self.shard_nodes[second_shard])
                    del self.shard_nodes[second_shard]

                # 在完成最终检查后，有了最终的分片结果再为每个分片选择分片领导者
                for idx, shard in enumerate(self.shard_nodes):
                    # 从当前分片中选择处理延迟最小的节点作为分片领导者
                    shard_leader_id = min(shard, key=lambda node_id: self.params['Node_processing_delay'][node_id])

                    # 设置分片领导者的信息
                    self.full_nodes[shard_leader_id].node_type = 2
                    self.params["Node_transaction_generation_num"][f"{shard_leader_id}"] = 0
                    self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][f"{shard_leader_id}"] = 0

                    # 设置分片成员的信息
                    for node_id in shard:
                        self.full_nodes[node_id].shard_id = idx
                        self.full_nodes[node_id].shard_leader_id = shard_leader_id

                        if node_id != shard_leader_id:
                            self.full_nodes[node_id].node_type = 3
                            self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                            self.params["Number_of_votes_of_ordinary_segmented_nodes"][f"{node_id}"] = 0
            if mode_type == 4:
                        # 应用Louvain方法来检测社区
                partition = community.best_partition(self.params["graph"], weight='weight')

                # 获取所有节点的处理延迟信息
                nodes_with_latency = [
                    (node_id, self.params['Node_processing_delay'][node_id])
                    for node_id in self.params['Node_processing_delay'].keys()
                ]

                # 根据处理延迟从小到大排序节点
                sorted_nodes = sorted(nodes_with_latency, key=lambda x: x[1])

                # 计算主委员会应有的节点数
                num_principal_committe_nodes = int(len(sorted_nodes) * self.params["principal_committee_size"])

                # 分配前 num_principal_committe_nodes 个节点作为主委员会成员
                self.principal_committee_node_ids = [node_id for node_id, _ in sorted_nodes[:num_principal_committe_nodes]]

                # 随机选择一个主委员会成员作为主委员会领导者
                principal_committee_leader = random.choice(self.principal_committee_node_ids)

                # 设置主委员会成员的类型和领导者信息
                for node_id, _ in sorted_nodes[:num_principal_committe_nodes]:
                    self.full_nodes[node_id].node_type = 1
                    self.full_nodes[node_id].pc_leader_id = principal_committee_leader
                    self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][f"{node_id}"] = 0

                # 根据社区检测结果分配分片
                shard_groups = {}
                for node_id, community_id in partition.items():
                    if community_id not in shard_groups:
                        shard_groups[community_id] = []
                    shard_groups[community_id].append(node_id)

                # 去除成为主委员会成员的节点
                for committee_node in self.principal_committee_node_ids:
                    for group in shard_groups.values():
                        if committee_node in group:
                            group.remove(committee_node)

                # 将分片组信息转换为列表形式，方便后续处理。
                self.shard_nodes = [shards for shards in shard_groups.values()]

                # 动态调整分片大小
                # 定义一个阈值来判断是否需要分割或合并分片
                min_nodes_per_shard = 4  # 每个分片至少包含4个节点

                # 检测每个分片的负载
                shard_loads = {}
                for shard_idx, shard in enumerate(self.shard_nodes):
                    # 计算分片的负载
                    subgraph = self.params["graph"].subgraph(shard)
                    load = subgraph.size(weight='weight')
                    shard_loads[shard_idx] = load

                # 计算平均负载
                average_load = sum(shard_loads.values()) / len(shard_loads)

                # 动态设置负载阈值
                load_threshold = average_load * self.params.get("load_threshold_multiplier", 1.5)  # 假设超过平均负载的1.5倍则认为过载

                # 根据负载情况调整分片
                # 分割过载的分片
                for shard_idx, load in shard_loads.items():
                    if load > load_threshold and len(self.shard_nodes[shard_idx]) > min_nodes_per_shard:
                        # 分割分片
                        subgraph = self.params["graph"].subgraph(self.shard_nodes[shard_idx])
                        new_partitions = community.best_partition(subgraph, weight='weight')

                        new_shards = {}
                        for node_id, community_id in new_partitions.items():
                            if community_id not in new_shards:
                                new_shards[community_id] = []
                            new_shards[community_id].append(node_id)

                        # 确保新分片至少包含4个节点
                        valid_new_shards = [shard for shard in new_shards.values() if len(shard) >= min_nodes_per_shard]

                        # 更新分片列表
                        del self.shard_nodes[shard_idx]
                        self.shard_nodes.extend(valid_new_shards)

                # 合并轻载的分片
                merged_shards = []
                for shard_idx, load in shard_loads.items():
                    if load < load_threshold / 2 and len(self.shard_nodes[shard_idx]) < min_nodes_per_shard:
                        merged_shards.append(shard_idx)

                # 合并选定的轻载分片
                while len(merged_shards) >= 2:
                    first_shard = merged_shards.pop(0)
                    second_shard = merged_shards.pop(0)
                    if len(self.shard_nodes[first_shard]) + len(self.shard_nodes[second_shard]) >= min_nodes_per_shard:
                        self.shard_nodes[first_shard].extend(self.shard_nodes[second_shard])
                        del self.shard_nodes[second_shard]

                # 最终检查是否有任何分片节点数不足的情况
                # 并进行必要的合并
                final_merged_shards = [idx for idx, shard in enumerate(self.shard_nodes) if len(shard) < min_nodes_per_shard]
                while final_merged_shards:
                    first_shard = final_merged_shards.pop(0)
                    second_shard = final_merged_shards.pop(0)
                    self.shard_nodes[first_shard].extend(self.shard_nodes[second_shard])
                    del self.shard_nodes[second_shard]

                # 在完成最终检查后，有了最终的分片结果再为每个分片选择分片领导者
                for idx, shard in enumerate(self.shard_nodes):
                    # 从当前分片中选择处理延迟最小的节点作为分片领导者
                    shard_leader_id = min(shard, key=lambda node_id: self.params['Node_processing_delay'][node_id])

                    # 设置分片领导者的信息
                    self.full_nodes[shard_leader_id].node_type = 2
                    self.params["Node_transaction_generation_num"][f"{shard_leader_id}"] = 0
                    self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][f"{shard_leader_id}"] = 0

                    # 设置分片成员的信息
                    for node_id in shard:
                        self.full_nodes[node_id].shard_id = idx
                        self.full_nodes[node_id].shard_leader_id = shard_leader_id

                        if node_id != shard_leader_id:
                            self.full_nodes[node_id].node_type = 3
                            self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                            self.params["Number_of_votes_of_ordinary_segmented_nodes"][f"{node_id}"] = 0
            if mode_type == 5:
                # 应用Louvain方法来检测社区
                partition = community.best_partition(self.params["graph"], weight='weight')

                # 获取所有节点的处理延迟信息
                nodes_with_latency = [
                    (node_id, self.params['Node_processing_delay'][node_id])
                    for node_id in self.params['Node_processing_delay'].keys()
                ]

                # 根据处理延迟从小到大排序节点
                sorted_nodes = sorted(nodes_with_latency, key=lambda x: x[1])

                # 计算主委员会应有的节点数
                num_principal_committe_nodes = int(len(sorted_nodes) * self.params["principal_committee_size"])

                # 分配前 num_principal_committe_nodes 个节点作为主委员会成员
                self.principal_committee_node_ids = [node_id for node_id, _ in sorted_nodes[:num_principal_committe_nodes]]

                # 随机选择一个主委员会成员作为主委员会领导者
                principal_committee_leader = random.choice(self.principal_committee_node_ids)

                # 设置主委员会成员的类型和领导者信息
                for node_id, _ in sorted_nodes[:num_principal_committe_nodes]:
                    self.full_nodes[node_id].node_type = 1
                    self.full_nodes[node_id].pc_leader_id = principal_committee_leader
                    self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][f"{node_id}"] = 0

                # 根据社区检测结果分配分片
                shard_groups = {}
                for node_id, community_id in partition.items():
                    if community_id not in shard_groups:
                        shard_groups[community_id] = []
                    shard_groups[community_id].append(node_id)

                # 去除成为主委员会成员的节点
                for committee_node in self.principal_committee_node_ids:
                    for group in shard_groups.values():
                        if committee_node in group:
                            group.remove(committee_node)

                # 将分片组信息转换为列表形式，方便后续处理。
                self.shard_nodes = [shards for shards in shard_groups.values()]

                # 动态调整分片大小
                # 定义一个阈值来判断是否需要分割或合并分片
                min_nodes_per_shard = 4  # 每个分片至少包含4个节点

                # 检测每个分片的负载
                shard_loads = {}
                for shard_idx, shard in enumerate(self.shard_nodes):
                    # 计算分片的负载
                    subgraph = self.params["graph"].subgraph(shard)
                    load = subgraph.size(weight='weight')
                    shard_loads[shard_idx] = load

                # 计算平均负载
                average_load = sum(shard_loads.values()) / len(shard_loads)

                # 动态设置负载阈值
                load_threshold = average_load * self.params.get("load_threshold_multiplier", 1.5)  # 假设超过平均负载的1.5倍则认为过载

                # 根据负载情况调整分片
                # 分割过载的分片
                for shard_idx, load in shard_loads.items():
                    if load > load_threshold and len(self.shard_nodes[shard_idx]) > min_nodes_per_shard:
                        # 分割分片
                        subgraph = self.params["graph"].subgraph(self.shard_nodes[shard_idx])
                        new_partitions = community.best_partition(subgraph, weight='weight')

                        new_shards = {}
                        for node_id, community_id in new_partitions.items():
                            if community_id not in new_shards:
                                new_shards[community_id] = []
                            new_shards[community_id].append(node_id)

                        # 确保新分片至少包含4个节点
                        valid_new_shards = [shard for shard in new_shards.values() if len(shard) >= min_nodes_per_shard]

                        # 更新分片列表
                        del self.shard_nodes[shard_idx]
                        self.shard_nodes.extend(valid_new_shards)

                # 合并轻载的分片
                merged_shards = []
                for shard_idx, load in shard_loads.items():
                    if load < load_threshold / 2 and len(self.shard_nodes[shard_idx]) < min_nodes_per_shard:
                        merged_shards.append(shard_idx)

                # 合并选定的轻载分片
                while len(merged_shards) >= 2:
                    first_shard = merged_shards.pop(0)
                    second_shard = merged_shards.pop(0)
                    if len(self.shard_nodes[first_shard]) + len(self.shard_nodes[second_shard]) >= min_nodes_per_shard:
                        self.shard_nodes[first_shard].extend(self.shard_nodes[second_shard])
                        del self.shard_nodes[second_shard]

                # 最终检查是否有任何分片节点数不足的情况
                # 并进行必要的合并
                final_merged_shards = [idx for idx, shard in enumerate(self.shard_nodes) if len(shard) < min_nodes_per_shard]
                while final_merged_shards:
                    first_shard = final_merged_shards.pop(0)
                    second_shard = final_merged_shards.pop(0)
                    self.shard_nodes[first_shard].extend(self.shard_nodes[second_shard])
                    del self.shard_nodes[second_shard]

                # 计算每个分片的延迟
                shard_delays = {}
                for idx, shard in enumerate(self.shard_nodes):
                    shard_delay = sum([self.params['Node_processing_delay'][node_id] for node_id in shard])
                    shard_delays[idx] = shard_delay

                # 计算延迟最低的分片作为桥接分片
                num_b_shards = int(len(self.shard_nodes) * 0.3)  # 桥接分片的数量应为总分片数的30%

                # 按照延迟升序排序分片
                sorted_shards_by_delay = sorted(shard_delays.items(), key=lambda x: x[1])

                # 前 num_b_shards 个延迟最低的分片成为桥接分片
                b_shard_indices = [idx for idx, _ in sorted_shards_by_delay[:num_b_shards]]
                print("b_shard_indices:", b_shard_indices)
                print("sorted_shards_by_delay",sorted_shards_by_delay)
                # 计算延迟最高的30%的独立分片
                independent_shard_delays = {idx: delay for idx, delay in shard_delays.items() if idx not in b_shard_indices}
                num_high_delay_independent_shards = int(len(independent_shard_delays) * 1)
                sorted_independent_shards_by_delay = sorted(independent_shard_delays.items(), key=lambda x: x[1], reverse=True)
                high_delay_independent_shard_indices = [idx for idx, _ in sorted_independent_shards_by_delay[:num_high_delay_independent_shards]]
                print("high_delay_independent_shard_indices:", high_delay_independent_shard_indices)
                print("sorted_independent_shards_by_delay:", sorted_independent_shards_by_delay)
                # 分配桥接分片处理的独立分片交易
                Bshard_with_Ishard = {}
                for b_shard_idx in b_shard_indices:
                    # 每个桥接分片处理两个高延迟独立分片的交易
                    if high_delay_independent_shard_indices:
                        Bshard_with_Ishard[b_shard_idx] = high_delay_independent_shard_indices[:2]
                        high_delay_independent_shard_indices = high_delay_independent_shard_indices[2:]

                # 为桥接分片设置类型
                for b_shard_idx in b_shard_indices:
                    for node_id in self.shard_nodes[b_shard_idx]:
                        self.full_nodes[node_id].shard_type = 2  # 设定为桥接分片类型

                # 对于剩下的分片，设置为独立分片
                for idx, shard in enumerate(self.shard_nodes):
                    if idx not in b_shard_indices:
                        for node_id in shard:
                            self.full_nodes[node_id].shard_type = 1  # 设定为独立分片类型

                self.params["Bshard_with_Ishard"] = Bshard_with_Ishard

                print("Bshard_with_Ishard:", self.params["Bshard_with_Ishard"])
                # 在完成最终检查后，有了最终的分片结果再为每个分片选择分片领导者
                for idx, shard in enumerate(self.shard_nodes):
                    # 从当前分片中选择处理延迟最小的节点作为分片领导者
                    shard_leader_id = min(shard, key=lambda node_id: self.params['Node_processing_delay'][node_id])

                    # 设置分片领导者的信息
                    self.full_nodes[shard_leader_id].node_type = 2
                    self.params["Node_transaction_generation_num"][f"{shard_leader_id}"] = 0
                    self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][f"{shard_leader_id}"] = 0

                    # 设置分片成员的信息
                    for node_id in shard:
                        self.full_nodes[node_id].shard_id = idx
                        self.full_nodes[node_id].shard_leader_id = shard_leader_id

                        if node_id != shard_leader_id:
                            if idx in b_shard_indices:
                                # 如果是桥接分片，则设置为桥接分片类型
                                self.full_nodes[node_id].shard_type = 2
                                # self.full_nodes[node_id].transactions_to_process = Bshard_with_Ishard.get(idx, [])
                            else:
                                # 如果是独立分片，则设置为独立分片类型
                                self.full_nodes[node_id].shard_type = 1
                                self.full_nodes[node_id].transactions_to_process = []
                            self.full_nodes[node_id].node_type = 3
                            self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                            self.params["Number_of_votes_of_ordinary_segmented_nodes"][f"{node_id}"] = 0
            if mode_type == 6:
                # 应用 Louvain 方法来检测社区
                partition = community.best_partition(self.params["graph"], weight='weight')

                # 获取所有节点的处理延迟信息
                nodes_with_latency = [
                    (node_id, self.params['Node_processing_delay'][node_id])
                    for node_id in self.params['Node_processing_delay'].keys()
                ]

                # 根据处理延迟从小到大排序节点
                sorted_nodes = sorted(nodes_with_latency, key=lambda x: x[1])

                # 计算主委员会应有的节点数
                num_principal_committe_nodes = int(len(sorted_nodes) * self.params["principal_committee_size"])

                # 分配前 num_principal_committe_nodes 个节点作为主委员会成员
                self.principal_committee_node_ids = [node_id for node_id, _ in sorted_nodes[:num_principal_committe_nodes]]

                # 随机选择一个主委员会成员作为主委员会领导者
                principal_committee_leader = random.choice(self.principal_committee_node_ids)

                # 设置主委员会成员的类型和领导者信息
                for node_id, _ in sorted_nodes[:num_principal_committe_nodes]:
                    self.full_nodes[node_id].node_type = 1
                    self.full_nodes[node_id].pc_leader_id = principal_committee_leader
                    self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][f"{node_id}"] = 0

                # 根据社区检测结果分配分片
                shard_groups = {}
                for node_id, community_id in partition.items():
                    if community_id not in shard_groups:
                        shard_groups[community_id] = []
                    shard_groups[community_id].append(node_id)

                # 去除成为主委员会成员的节点
                for committee_node in self.principal_committee_node_ids:
                    for group in shard_groups.values():
                        if committee_node in group:
                            group.remove(committee_node)

                # 将分片组信息转换为列表形式，方便后续处理。
                self.shard_nodes = [shards for shards in shard_groups.values()]
                print("社区检测结果 后的分片组信息:", self.shard_nodes)
                print("len(self.shard_nodes):", len(self.shard_nodes))
                # 动态调整分片大小
                # 定义一个阈值来判断是否需要分割或合并分片
                min_nodes_per_shard = 4  # 每个分片至少包含4个节点

                # 检测每个分片的负载
                shard_loads = {}
                for shard_idx, shard in enumerate(self.shard_nodes):
                    # 计算分片的负载
                    subgraph = self.params["graph"].subgraph(shard)
                    load = subgraph.size(weight='weight')
                    shard_loads[shard_idx] = load

                # 计算平均负载
                average_load = sum(shard_loads.values()) / len(shard_loads)

                # 动态设置负载阈值
                load_threshold = average_load * self.params.get("load_threshold_multiplier", 1.5)  # 假设超过平均负载的1.5倍则认为过载

                print("负载阈值 load_threshold:", load_threshold)
                # 分割过载的分片
                to_split = []
                for shard_idx, load in shard_loads.items():
                    if load > load_threshold and len(self.shard_nodes[shard_idx]) > min_nodes_per_shard:
                        print("分片{}负载过载，需要分割".format(shard_idx))
                        print("分片{}负载:{}".format(shard_idx, load))
                        to_split.append(shard_idx)

                for shard_idx in to_split:
                    # 分割分片
                    subgraph = self.params["graph"].subgraph(self.shard_nodes[shard_idx])
                    new_partitions = community.best_partition(subgraph, weight='weight')

                    new_shards = {}
                    for node_id, community_id in new_partitions.items():
                        if community_id not in new_shards:
                            new_shards[community_id] = []
                        new_shards[community_id].append(node_id)
                    print("分片{}分割后的社区划分:{}".format(shard_idx, new_partitions))


                    # 确保新分片至少包含4个节点
                    valid_new_shards = [shard for shard in new_shards.values() if len(shard) >= min_nodes_per_shard]

                    # 更新分片列表
                    del self.shard_nodes[shard_idx]
                    self.shard_nodes.extend(valid_new_shards)

                    # 更新 shard_loads
                    del shard_loads[shard_idx]
                    for new_shard in valid_new_shards:
                        new_subgraph = self.params["graph"].subgraph(new_shard)
                        new_load = new_subgraph.size(weight='weight')
                        shard_loads[len(self.shard_nodes) - 1] = new_load

                # # 合并轻载的分片
                merged_shards = []
                for shard_idx, load in shard_loads.items():
                    if load < load_threshold / 5 and len(self.shard_nodes[shard_idx]) < min_nodes_per_shard:
                        print("分片{}负载过低，需要合并".format(shard_idx))
                        print("分片{}负载:{}".format(shard_idx, load))
                        merged_shards.append(shard_idx)

                # 合并选定的轻载分片
                while len(merged_shards) >= 2:
                    first_shard = merged_shards.pop(0)
                    second_shard = merged_shards.pop(0)
                    print("合并分片{}和分片{}".format(first_shard, second_shard))
                    if len(self.shard_nodes[first_shard]) + len(self.shard_nodes[second_shard]) >= min_nodes_per_shard:
                        self.shard_nodes[first_shard].extend(self.shard_nodes[second_shard])
                        del self.shard_nodes[second_shard]
                        del shard_loads[second_shard]

                # 最终检查是否有任何分片节点数不足的情况
                # 并进行必要的合并
                final_merged_shards = [idx for idx, shard in enumerate(self.shard_nodes) if len(shard) < min_nodes_per_shard]
                while final_merged_shards:
                    first_shard = final_merged_shards.pop(0)
                    second_shard = final_merged_shards.pop(0)
                    self.shard_nodes[first_shard].extend(self.shard_nodes[second_shard])
                    print("最终检查: 合并分片{}和分片{}".format(first_shard, second_shard))
                    del self.shard_nodes[second_shard]

                # 计算每个分片的延迟
                shard_delays = {}
                for idx, shard in enumerate(self.shard_nodes):
                    shard_delay = sum([self.params['Node_processing_delay'][node_id] for node_id in shard])
                    shard_delays[idx] = shard_delay

                # 计算延迟最低的分片作为桥接分片
                num_b_shards = int(len(self.shard_nodes) * 0.3)  # 桥接分片的数量应为总分片数的30%

                # 按照延迟升序排序分片
                sorted_shards_by_delay = sorted(shard_delays.items(), key=lambda x: x[1])

                # 前 num_b_shards 个延迟最低的分片成为桥接分片
                b_shard_indices = [idx for idx, _ in sorted_shards_by_delay[:num_b_shards]]
                print("b_shard_indices:", b_shard_indices)
                print("sorted_shards_by_delay", sorted_shards_by_delay)

                # 计算所有独立分片
                all_independent_shard_indices = [idx for idx in shard_delays.keys() if idx not in b_shard_indices]

                # 按延迟从高到低排序所有独立分片
                sorted_all_independent_shards_by_delay = sorted(all_independent_shard_indices, key=lambda x: shard_delays[x], reverse=True)

                # 分配桥接分片处理的独立分片交易
                Bshard_with_Ishard = {}
                for b_shard_idx in b_shard_indices:
                    # 每个桥接分片处理两个独立分片的交易
                    assigned_shards = []
                    for _ in range(2):
                        if sorted_all_independent_shards_by_delay:
                            assigned_shard = sorted_all_independent_shards_by_delay.pop(0)
                            assigned_shards.append(assigned_shard)
                    Bshard_with_Ishard[b_shard_idx] = assigned_shards

                # 确保每个桥接分片至少分配到一个独立分片
                for b_shard_idx in b_shard_indices:
                    if not Bshard_with_Ishard[b_shard_idx]:
                        # 如果没有分配到独立分片，随机选择一个独立分片
                        available_independent_shards = [idx for idx in shard_delays.keys() if idx not in b_shard_indices]
                        if available_independent_shards:
                            Bshard_with_Ishard[b_shard_idx].append(random.choice(available_independent_shards))

                # 为桥接分片设置类型
                for b_shard_idx in b_shard_indices:
                    for node_id in self.shard_nodes[b_shard_idx]:
                        self.full_nodes[node_id].shard_type = 2  # 设定为桥接分片类型

                # 对于剩下的分片，设置为独立分片
                for idx, shard in enumerate(self.shard_nodes):
                    if idx not in b_shard_indices:
                        for node_id in shard:
                            self.full_nodes[node_id].shard_type = 1  # 设定为独立分片类型

                self.params["Bshard_with_Ishard"] = Bshard_with_Ishard

                print("Bshard_with_Ishard:", self.params["Bshard_with_Ishard"])

                # 在完成最终检查后，有了最终的分片结果再为每个分片选择分片领导者
                for idx, shard in enumerate(self.shard_nodes):
                    # 从当前分片中选择处理延迟最小的节点作为分片领导者
                    shard_leader_id = min(shard, key=lambda node_id: self.params['Node_processing_delay'][node_id])

                    # 设置分片领导者的信息
                    self.full_nodes[shard_leader_id].node_type = 2
                    self.params["Node_transaction_generation_num"][f"{shard_leader_id}"] = 0
                    self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][f"{shard_leader_id}"] = 0

                    # 设置分片成员的信息
                    for node_id in shard:
                        self.full_nodes[node_id].shard_id = idx
                        self.full_nodes[node_id].shard_leader_id = shard_leader_id

                        if node_id != shard_leader_id:
                            if idx in b_shard_indices:
                                # 如果是桥接分片，则设置为桥接分片类型
                                self.full_nodes[node_id].shard_type = 2
                            else:
                                # 如果是独立分片，则设置为独立分片类型
                                self.full_nodes[node_id].shard_type = 1
                            self.full_nodes[node_id].node_type = 3
                            self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                            self.params["Number_of_votes_of_ordinary_segmented_nodes"][f"{node_id}"] = 0
            if mode_type == 7:
                        # 应用 Louvain 方法来检测社区
                partition = community.best_partition(self.params["graph"], weight='weight')

                # 获取所有节点的处理延迟信息
                nodes_with_latency = [
                    (node_id, self.params['Node_processing_delay'][node_id])
                    for node_id in self.params['Node_processing_delay'].keys()
                ]

                # 根据处理延迟从小到大排序节点
                sorted_nodes = sorted(nodes_with_latency, key=lambda x: x[1])

                # 计算主委员会应有的节点数
                num_principal_committe_nodes = int(len(sorted_nodes) * self.params["principal_committee_size"])

                # 分配前 num_principal_committe_nodes 个节点作为主委员会成员
                self.principal_committee_node_ids = [node_id for node_id, _ in sorted_nodes[:num_principal_committe_nodes]]

                # 随机选择一个主委员会成员作为主委员会领导者
                principal_committee_leader = random.choice(self.principal_committee_node_ids)

                # 设置主委员会成员的类型和领导者信息
                for node_id, _ in sorted_nodes[:num_principal_committe_nodes]:
                    self.full_nodes[node_id].node_type = 1
                    self.full_nodes[node_id].pc_leader_id = principal_committee_leader
                    self.params["Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block"][f"{node_id}"] = 0

                # 根据社区检测结果分配分片
                shard_groups = {}
                for node_id, community_id in partition.items():
                    if community_id not in shard_groups:
                        shard_groups[community_id] = []
                    shard_groups[community_id].append(node_id)

                # 去除成为主委员会成员的节点
                for committee_node in self.principal_committee_node_ids:
                    for group in shard_groups.values():
                        if committee_node in group:
                            group.remove(committee_node)

                # # 确保分片数为self.params["num_shards"]
                # if len(shard_groups) < self.params["num_shards"]:
                #     # 如果社区数小于self.params["num_shards"]，拆分一些社区以达到self.params["num_shards"]个分片
                #     while len(shard_groups) < self.params["num_shards"]:
                #         largest_community = max(shard_groups, key=lambda k: len(shard_groups[k]))
                #         new_community = shard_groups[largest_community][:len(shard_groups[largest_community]) // 2]
                #         shard_groups[largest_community] = shard_groups[largest_community][len(shard_groups[largest_community]) // 2:]
                #         shard_groups[len(shard_groups)] = new_community
                # else:
                #     # 如果社区数大于self.params["num_shards"]，合并一些社区以达到self.params["num_shards"]个分片
                #     while len(shard_groups) > self.params["num_shards"]:
                #         smallest_community = min(shard_groups, key=lambda k: len(shard_groups[k]))
                #         largest_community = max(shard_groups, key=lambda k: len(shard_groups[k]))
                #         shard_groups[largest_community].extend(shard_groups.pop(smallest_community))

                # 将分片组信息转换为列表形式，方便后续处理。
                self.shard_nodes = [shards for shards in shard_groups.values()]
                # print("社区检测结果 后的分片组信息:", self.shard_nodes)
                # print("len(self.shard_nodes):", len(self.shard_nodes))
                # print("self.params[frequent_transactions_custom]", self.params["frequent_transactions_custom"])

            # 找出每一个节点对应的边权重最高的5个节点，并判断这些节点是否在self.params["frequent_transactions_custom"]中
                for shard in self.shard_nodes:
                    for node_id in shard:
                        # 获取与节点 node_id 相连的所有邻居节点及其边权重
                        neighbor_weights = [(neighbor, self.params["graph"][node_id][neighbor]['weight']) for neighbor in self.params["graph"].neighbors(node_id)]

                        # 按权重降序排序邻居节点
                        sorted_neighbors = sorted(neighbor_weights, key=lambda x: x[1], reverse=True)

                        # 取前5个权重最高的邻居节点
                        top_5_neighbors = sorted_neighbors[:5]

                        in_frequent_transactions_num = 0
                        in_same_shard_num = 0
                        # 判断这些节点是否在 self.params["frequent_transactions_custom"] 中
                        frequent_transactions_custom = set(self.params["frequent_transactions_custom"])
                        for neighbor, weight in top_5_neighbors:
                            in_frequent_transactions = neighbor in frequent_transactions_custom
                            in_same_shard = neighbor in shard
                            # print(f"Node: {node_id}, Neighbor: {neighbor}, Weight: {weight}, In frequent_transactions_custom: {in_frequent_transactions}, In same shard: {in_same_shard}")
                            if in_frequent_transactions:
                                in_frequent_transactions_num += 1
                            if in_same_shard:
                                in_same_shard_num += 1
                        print(f"Node: {node_id}, In frequent_transactions_custom num: {in_frequent_transactions_num}, In same shard num: {in_same_shard_num}")

                # -----------------------------------

                # -------------------------------------------
                # 计算每个分片的延迟
                shard_delays = {}
                for idx, shard in enumerate(self.shard_nodes):
                    shard_delay = sum([self.params['Node_processing_delay'][node_id] for node_id in shard])
                    shard_delays[idx] = shard_delay

                # 计算延迟最低的分片作为桥接分片
                num_b_shards = int(len(self.shard_nodes) * 0.3)  # 桥接分片的数量应为总分片数的30%

                # 按照延迟升序排序分片
                sorted_shards_by_delay = sorted(shard_delays.items(), key=lambda x: x[1])

                # 前 num_b_shards 个延迟最低的分片成为桥接分片
                b_shard_indices = [idx for idx, _ in sorted_shards_by_delay[:num_b_shards]]
                print("b_shard_indices:", b_shard_indices)
                print("sorted_shards_by_delay", sorted_shards_by_delay)

                # 计算所有独立分片
                all_independent_shard_indices = [idx for idx in shard_delays.keys() if idx not in b_shard_indices]

                # 按延迟从高到低排序所有独立分片
                sorted_all_independent_shards_by_delay = sorted(all_independent_shard_indices, key=lambda x: shard_delays[x], reverse=True)

                # 分配桥接分片处理的独立分片交易
                Bshard_with_Ishard = {}
                for b_shard_idx in b_shard_indices:
                    # 每个桥接分片处理两个独立分片的交易
                    assigned_shards = []
                    for _ in range(2):
                        if sorted_all_independent_shards_by_delay:
                            assigned_shard = sorted_all_independent_shards_by_delay.pop(0)
                            assigned_shards.append(assigned_shard)
                    Bshard_with_Ishard[b_shard_idx] = assigned_shards

                # 确保每个桥接分片至少分配到一个独立分片
                for b_shard_idx in b_shard_indices:
                    if not Bshard_with_Ishard[b_shard_idx]:
                        # 如果没有分配到独立分片，随机选择一个独立分片
                        available_independent_shards = [idx for idx in shard_delays.keys() if idx not in b_shard_indices]
                        if available_independent_shards:
                            Bshard_with_Ishard[b_shard_idx].append(random.choice(available_independent_shards))

                # 为桥接分片设置类型
                for b_shard_idx in b_shard_indices:
                    for node_id in self.shard_nodes[b_shard_idx]:
                        self.full_nodes[node_id].shard_type = 2  # 设定为桥接分片类型

                # 对于剩下的分片，设置为独立分片
                for idx, shard in enumerate(self.shard_nodes):
                    if idx not in b_shard_indices:
                        for node_id in shard:
                            self.full_nodes[node_id].shard_type = 1  # 设定为独立分片类型

                self.params["Bshard_with_Ishard"] = Bshard_with_Ishard

                print("Bshard_with_Ishard:", self.params["Bshard_with_Ishard"])

                # 在完成最终检查后，有了最终的分片结果再为每个分片选择分片领导者
                for idx, shard in enumerate(self.shard_nodes):
                    # 从当前分片中选择处理延迟最小的节点作为分片领导者
                    shard_leader_id = min(shard, key=lambda node_id: self.params['Node_processing_delay'][node_id])

                    # 设置分片领导者的信息
                    self.full_nodes[shard_leader_id].node_type = 2
                    self.params["Node_transaction_generation_num"][f"{shard_leader_id}"] = 0
                    self.params["Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes"][f"{shard_leader_id}"] = 0

                    # 设置分片成员的信息
                    for node_id in shard:
                        self.full_nodes[node_id].shard_id = idx
                        self.full_nodes[node_id].shard_leader_id = shard_leader_id

                        if node_id != shard_leader_id:
                            if idx in b_shard_indices:
                                # 如果是桥接分片，则设置为桥接分片类型
                                self.full_nodes[node_id].shard_type = 2
                            else:
                                # 如果是独立分片，则设置为独立分片类型
                                self.full_nodes[node_id].shard_type = 1
                            self.full_nodes[node_id].node_type = 3
                            self.params["Node_transaction_generation_num"][f"{node_id}"] = 0
                            self.params["Number_of_votes_of_ordinary_segmented_nodes"][f"{node_id}"] = 0



        # ----------------------------------------------------------------------------------------
        print("self.shard_nodes:", self.shard_nodes)
        self.params["num_shards"] = len(self.shard_nodes)


        self.params["epoch_generated_tx_count"][self.params["current_epoch"]] = 0
        self.params["epoch_generated_cross_shard_tx_count"][self.params["current_epoch"]] = 0
        self.params["epoch_generated_intra_shard_tx_count"][self.params["current_epoch"]] = 0

        self.params["epoch_processed_tx_count"][self.params["current_epoch"]] = 0
        self.params["epoch_processed_intra_shard_tx_count"][self.params["current_epoch"]] = 0
        self.params["epoch_processed_cross_shard_tx_count"][self.params["current_epoch"]] = 0

        self.params["epoch_generated_tx_count_TPS"][self.params["current_epoch"]] = 0
        self.params["epoch_processed_tx_count_TPS"][self.params["current_epoch"]] = 0

        self.params["epoch_shard_generated_tx_count"][self.params["current_epoch"]] = {}
        self.params["epoch_shard_generated_intra_shard_tx_count"][self.params["current_epoch"]] = {}
        self.params["epoch_shard_generated_cross_shard_tx_count"][self.params["current_epoch"]] = {}
        self.params["epoch_shard_processed_tx_count"][self.params["current_epoch"]] = {}
        self.params["epoch_shard_processed_intra_shard_tx_count"][self.params["current_epoch"]] = {}
        self.params["epoch_shard_processed_cross_shard_tx_count"][self.params["current_epoch"]] = {}
        for index in range(self.params["num_shards"]):
            self.params["epoch_shard_generated_tx_count"][self.params["current_epoch"]][index] = 0
            self.params["epoch_shard_generated_intra_shard_tx_count"][self.params["current_epoch"]][index] = 0
            self.params["epoch_shard_generated_cross_shard_tx_count"][self.params["current_epoch"]][index] = 0
            self.params["epoch_shard_processed_tx_count"][self.params["current_epoch"]][index] = 0
            self.params["epoch_shard_processed_intra_shard_tx_count"][self.params["current_epoch"]][index] = 0
            self.params["epoch_shard_processed_cross_shard_tx_count"][self.params["current_epoch"]][index] = 0

        if self.params["current_epoch"] == 0:
        #     遍历self.full_nodes，分配密钥
            for node_id, node in self.full_nodes.items():
                node.private_key, node.public_key = self.generate_key_pair()


        # 将配置好的节点信息存入参数字典中，以便后续使用。
        self.params["all_full_nodes"] = self.full_nodes
        self.params["shard_nodes"] = self.shard_nodes




    # 这段代码的目的是在一个分布式系统或区块链网络中建立网络拓扑结构，确保节点之间能够有效地通信。
    def establish_network_connections(self):
        """
        Establish network topology between the full nodes
        """
        """Degree of network graph. Degree >= n/2 guarantees a connected graph"""
        # degree = len(self.principal_committee_node_ids) // 2 + 1

        # # 判断当前epoch是不是第一次
        # if self.params["current_epoch"] == 0:

        ################## Connect the Principal Committee nodes ##################
        # keeping the degress as num nodes - 1 to make the pricinpal committee network fully connected
        degree = len(self.principal_committee_node_ids) - 1

        # neighbours info is a dictionary mapping nodes to its neighbours for constructing undirected graph
        # 主委员会节点之间的连接
        # 首先，代码确保主委员会内的节点是完全连接的，即每个节点都与其他所有节点建立连接。
        # 这是通过为每个节点创建一个邻居列表来实现的，该列表包含除自己之外的所有主委员会节点。
        # 这种完全连接的方式有利于主委员会内部的快速通信和共识达成。
        neighbours_info = {}

        for id in self.principal_committee_node_ids:
            possible_neighbours = self.principal_committee_node_ids.copy()
            possible_neighbours.remove(id)

            neighbours_info[id] = possible_neighbours

            """Generate a random sample of size degree without replacement from possible neighbours"""
            # NOTE - This is a generic code to create bidirectional links among neighbors when graph is not fully connected

            # neighbours_list = np.random.choice(
            #     possible_neighbours,
            #     size=degree,
            #     replace=False
            # )

            # if id not in neighbours_info.keys():
            #     neighbours_info[id] = set()

            # for neighbour_id in neighbours_list:
            #     if neighbour_id not in neighbours_info.keys():
            #         neighbours_info[neighbour_id] = set()

            #     neighbours_info[id].add(neighbour_id)
            #     neighbours_info[neighbour_id].add(id)

        for key, value in neighbours_info.items():
            self.full_nodes[key].add_network_parameters(self.full_nodes, list(value))

        ################## Connect the leaders of the shards with the Principal Committee ##################
        # 分片领导者与主委员会的连接
        # 分片领导者被连接到主委员会的部分成员，确保了分片与网络其余部分的通信路径。
        # 这种连接策略有助于在分片之间以及分片与主委员会之间传播信息。
        degree = len(self.principal_committee_node_ids) // 2 + 1
        for idx in range(len(self.shard_nodes)):
            curr_leader = self.get_shard_leader(idx)
            possible_neighbours = self.principal_committee_node_ids

            neighbours_list = np.random.choice(
                possible_neighbours, size=degree, replace=False
            )

            curr_leader.add_network_parameters(self.full_nodes, neighbours_list)

            # Add back connections to the principal committee neighbours
            # 为主委员会成员添加回向连接：最后，为每个被选为邻居的主委员会成员添加一个回向连接，指向当前的分片领导者。
            # 这是通过遍历 neighbours_list 并对每个ID执行 self.full_nodes[id].neighbours_ids.append(curr_leader.id) 实现的，
            # 确保主委员会成员也知道它们是哪个分片领导者的邻居。
            for id in neighbours_list:
                self.full_nodes[id].neighbours_ids.append(curr_leader.id)

        ################## Connect the shard nodes with each other and the leaders ##################
        # 初始化分片节点映射：对于网络中的每个分片，创建一个包含当前分片所有节点的映射（curr_shard_nodes），方便后续操作。
        for idx in range(len(self.shard_nodes)):
            curr_shard_nodes = {}
            for node_id in self.shard_nodes[idx]:
                curr_shard_nodes[node_id] = self.full_nodes[node_id]

            neighbours_info = {}
            # 计算连接度：对于分片内的每个节点，计算它应该连接的邻居数量，这个数量是分片内节点总数的一半加一（degree），以确保网络的稳健性。
            degree = len(self.shard_nodes[idx]) // 2 + 1

            # 随机选择邻居并建立连接：对于分片内的每个节点，从除自己外的节点中随机选择degree个节点作为邻居，然后将这些连接信息存储在neighbours_info中。

            for curr_node_id in self.shard_nodes[idx]:
                possible_neighbours = self.shard_nodes[idx].copy()
                possible_neighbours.remove(curr_node_id)

                # 确保 degree 不超过 possible_neighbours 的长度
                degree = min(degree, len(possible_neighbours))
                # 这一步骤通过np.random.choice函数实现，确保每个节点都能与足够多的邻居连接，以促进分片内的高效通信。
                neighbours_list = np.random.choice(
                    possible_neighbours, size=degree, replace=False
                )
                # 检查节点是否已有邻居信息：if curr_node_id not in neighbours_info.keys(): neighbours_info[curr_node_id] = set()
                # 这两行代码检查当前节点（curr_node_id）是否已在neighbours_info字典中有记录。
                # 如果没有，就为它创建一个空的集合。neighbours_info字典用于存储每个节点的邻居节点ID，使用集合是为了避免重复记录同一个邻居。。
                if curr_node_id not in neighbours_info.keys():
                    neighbours_info[curr_node_id] = set()

                # 为邻居节点做相同的检查：接下来的循环 for neighbour_id in neighbours_list:
                # 遍历由np.random.choice随机选出的邻居节点列表neighbours_list。
                # 对于列表中的每个邻居节点ID（neighbour_id），代码同样检查neighbours_info字典中是否已经有了对应的记录，
                #  如果没有，则同样为其创建一个空集合。
                for neighbour_id in neighbours_list:
                    if neighbour_id not in neighbours_info.keys():
                        neighbours_info[neighbour_id] = set()
                    # 建立双向邻居关系：在确认了当前节点和其邻居节点在neighbours_info字典中都有了对应的记录后，
                    # 代码通过neighbours_info[curr_node_id].add(neighbour_id)和neighbours_info[neighbour_id].add(curr_node_id)这两行，
                    # 分别为当前节点和其邻居节点添加对方的ID到各自的邻居集合中。这样做实现了节点间邻居关系的双向记录，即不仅当前节点记录了它的邻居，
                    # 邻居节点也记录了当前节点作为它的邻居，确保了网络连接的双向性。
                    neighbours_info[curr_node_id].add(neighbour_id)
                    neighbours_info[neighbour_id].add(curr_node_id)

                # self.full_nodes[curr_node_id].shard_leader = self.get_shard_leader(idx)
                # 这行代码为当前处理的节点（curr_node_id）指定了一个分片领导者。
                # self.get_shard_leader(idx)方法根据分片的索引idx返回该分片的领导者节点。
                # 这意味着分片内的所有节点都将知道自己的分片领导者是谁，这对于分片内的决策和跨分片通信都是重要的。
                self.full_nodes[curr_node_id].shard_leader = self.get_shard_leader(idx)

            # 初始化主委员会邻居列表：principal_committee_neigbours = [] 初始化一个空列表，
            # 用于存储主委员会成员的邻居信息。这个列表将用于存储分片领导者（通常被认为是主委员会成员）的邻居信息。
            principal_committee_neigbours = []
            # 遍历邻居信息：for key, value in neighbours_info.items():
            # 遍历neighbours_info字典，其中key是节点ID，value是该节点的邻居集合。
            for key, value in neighbours_info.items():
                # 如果节点是分片领导者（node_type == 2），则将其现有的邻居列表（self.full_nodes[key].neighbours_ids）
                # 赋值给principal_committee_neigbours，并使用update_neighbours方法更新领导者节点的邻居信息为value列表。
                if self.full_nodes[key].node_type == 2:
                    # If curr_node is a leader, append to the neighbors list
                    principal_committee_neigbours = self.full_nodes[key].neighbours_ids
                    self.full_nodes[key].update_neighbours(list(value))
                else:
                    # 对于非领导者节点，调用add_network_parameters方法，传入当前分片的节点映射curr_shard_nodes和邻居列表value，以更新节点的网络参数。
                    self.full_nodes[key].add_network_parameters(curr_shard_nodes, list(value))

            # Create a Spanning Tree for the broadcast for the shard nodes
            # 构建最小生成树：spanning_tree = SpanningTree(curr_shard_nodes) 创建一个SpanningTree实例，
            # 传入当前分片的节点映射curr_shard_nodes。然后通过spanning_tree.Kruskal_MST()调用克鲁斯卡尔算法，
            # 为分片内的节点构建一个最小生成树，优化分片内的广播效率。结果重新赋值给neighbours_info，包含了生成树中的邻居关系。
            spanning_tree = SpanningTree(curr_shard_nodes)
            neighbours_info = spanning_tree.Kruskal_MST()

            # 确保边双向：通过遍历neighbours_info，为每个邻居对添加反向连接，
            # 确保所有的边都是双向的。这是通过在每个邻居的邻居集合中添加当前节点ID来实现的，保证了信息可以在两个方向上流动。
            # Make edges bi-directional
            for id, neighbours in neighbours_info.items():
                for neighbour_id in list(neighbours):
                    neighbours_info[neighbour_id].add(id)

            # Update the neighbours
            # 更新节点的邻居信息：再次遍历neighbours_info，根据最小生成树的结果更新每个节点的邻居信息。
            # 如果节点是分片领导者，其邻居列表还需要加上之前保存的principal_committee_neigbours列表，
            # 以确保领导者与主委员会成员之间的连接。
            for key, value in neighbours_info.items():
                # print(f"{key} -- {self.full_nodes[key].neighbours_ids}")
                value = list(value)
                if self.full_nodes[key].node_type == 2:
                    value += list(principal_committee_neigbours)
                self.full_nodes[key].update_neighbours(value)

            # Assign next_hop to reach the leader
            # 指定到领导者的下一跳：assign_next_hop_to_leader(curr_shard_nodes, self.get_shard_leader(idx))
            # 为当前分片的每个节点指定到达分片领导者的下一跳节点。这对于实现分片内的有效路由非常重要，确保了分片内的消息可以高效地传递给领导者。

            assign_next_hop_to_leader(curr_shard_nodes, self.get_shard_leader(idx))
            # for id, node in curr_shard_nodes.items():
            #     print(f"{id} = {node.next_hop_id}")

        """
        Cross-shard Transactions -
            Connect shard leaders with each other
        """
        # 获取领导节点数量：
        num_leaders = len(self.shard_nodes)
        # 这里创建一个空列表 leaders_id_list，然后通过循环遍历所有的领导节点，
        # 调用 self.get_shard_leader(id) 方法获取每个领导节点的ID，并将其添加到 leaders_id_list 中。
        leaders_id_list = []
        for id in range(num_leaders):
            leaders_id_list.append(self.get_shard_leader(id).id)

        # neighbours_info 是一个字典，用于存储每个领导节点的邻居节点信息。
        # degree 计算出每个领导节点应该有多少个邻居，这里是总领导节点数的一半加一。
        neighbours_info = {}
        degree = num_leaders // 2 + 1
        # 为每个领导节点选择邻居：对于每个领导节点，创建一个可能的邻居列表 possible_neighbours，并从中移除当前节点 id，因为节点不能成为自己的邻居。
        for id in leaders_id_list:
            possible_neighbours = leaders_id_list.copy()
            possible_neighbours.remove(id)

            # 如果当前节点 id 不在 neighbours_info 中，则为其初始化一个空集合，用于存储邻居节点。
            if id not in neighbours_info.keys():
                neighbours_info[id] = set()

            # 使用 numpy 的 random.choice 方法从 possible_neighbours 中随机选择 degree 个邻居节点，
            # 并确保不重复选择（replace=False）。
            neighbours_list = np.random.choice(
                possible_neighbours,
                size=degree,
                replace=False
            )

            # 对于每个选择的邻居节点，首先确保其在 neighbours_info 中有一个空集合，
            # 然后将当前节点 id 和邻居节点 neighbour_id 互相添加到各自的邻居集合中。
            for neighbour_id in neighbours_list:
                if neighbour_id not in neighbours_info.keys():
                    neighbours_info[neighbour_id] = set()

                neighbours_info[id].add(neighbour_id)
                neighbours_info[neighbour_id].add(id)

        # 这里创建一个字典 leader_nodes，将每个领导节点的ID映射到其对应的完整节点对象。
        leader_nodes = {id: self.full_nodes[id] for id in leaders_id_list}

        # 最后，遍历每个领导节点，调用其 init_shard_leaders 方法来初始化领导节点的信息，
        # 并将其邻居节点ID添加到 neighbours_ids 列表中。
        for id in leaders_id_list:
            self.full_nodes[id].init_shard_leaders(leader_nodes)
            self.full_nodes[id].neighbours_ids += (list(neighbours_info[id]))

    def get_shard_leader(self, idx):
        """
        Return leader of the specified shard
        """
        return self.full_nodes[self.full_nodes[self.shard_nodes[idx][0]].shard_leader_id]
        # leader = [idx for idx in self.shard_nodes[idx] if self.full_nodes[idx].node_type == 2]
        # if len(leader_id) != 1:
        #     raise RuntimeError("More than 1 leader for the Shard - %d" %idx)
        
        # return self.full_nodes[leader[0]]


    def allow_transactions_generation(self):
        """
        Prompt each shard node to generate and broadcast the transactions
        """
        # 这段代码首先遍历所有分片（self.shard_nodes 是一个列表，
        # 其中的每个元素也是一个列表，包含该分片中所有节点的ID）。对于每个分片中的每个节点ID，执行以下操作。
        # print("range(len(self.shard_nodes)) :", range(len(self.shard_nodes)) )
        # print("self.shard_nodes :", self.shard_nodes )

        for idx in range(len(self.shard_nodes)):
            # print("111")
            # print("self.shard_nodes[idx]", len(self.shard_nodes[idx]))
            for node_id in self.shard_nodes[idx]:

                # 使用节点ID从 self.full_nodes（一个字典，将节点ID映射到节点对象）中获取当前节点对象。
                curr_node = self.full_nodes[node_id]

                # if curr_node.node_type == 2:
                #     # curr_node.env.process(curr_node.preprocess_transactions())
                #     curr_node.env.process(curr_node.preprocess_intra_shard_transactions())
                #     curr_node.env.process(curr_node.preprocess_cross_shard_transactions())
                #     continue

                # 对于每个节点，调用其 generate_transactions 方法来生成交易。这个方法可能是异步的，
                # 因为它被包装在 curr_node.env.process() 中，这表明它可能是在某种模拟环境或事件循环中执行。
                # curr_node.env.process(curr_node.generate_transactions(2))
                curr_node.env.process(curr_node.generate_transactions_batch_size4())
                # 如果当前节点的类型为2（可能表示某种特殊功能的节点），则除了生成交易之外，还会进行额外的处理：
                # preprocess_intra_shard_transactions：预处理同一个分片内的交易。
                # preprocess_cross_shard_transactions：预处理跨分片的交易。
                if curr_node.node_type == 2:
                    # curr_node.env.process(curr_node.preprocess_transactions())

                    curr_node.env.process(curr_node.preprocess_intra_shard_transactions())

                    curr_node.env.process(curr_node.preprocess_cross_shard_transactions())
                    

    def display_network_info(self):
        print("\n============  NETWORK INFORMATION  ============")
        # self.principal_committee_node_ids 是一个列表，包含主委员会节点的ID。
        # 通过 self.full_nodes 获取主委员会中第一个节点的领导者ID，并打印出来。
        print("Principal Committee Nodes -", self.principal_committee_node_ids)
        print(f"Leader = '{self.full_nodes[self.principal_committee_node_ids[0]].pc_leader_id}'")

        # 遍历每个主委员会节点，打印出其邻居节点的ID（neighbours_ids）。
        for id in self.principal_committee_node_ids:
            print(f"{id} has neighbors - {self.full_nodes[id].neighbours_ids}")
        print("\n")

        # 遍历每个分片（self.params["num_shards"] 表示分片的数量）。
        # 打印当前分片的编号（从1开始）和该分片中的节点列表（self.shard_nodes[i]）。
        # 通过 self.get_shard_leader(i) 获取当前分片的领导节点，并打印其ID。
        for i in range(self.params["num_shards"]):
            print("\t\t\t\tSHARD -", i+1)
            print("Nodes -", self.shard_nodes[i])  
            print(f"Leader - '{self.get_shard_leader(i).id}'\n")

            # 对于当前分片中的每个节点，获取其完整节点对象（curr_node）。
            # 打印该节点的ID、其邻居节点的ID和到领导节点的下一跳ID（next_hop_id）。
            for j in range(len(self.shard_nodes[i])):
                curr_node = self.full_nodes[self.shard_nodes[i][j]]
                print(f"{j+1}. {curr_node.id} has neighbours - {curr_node.neighbours_ids} and next hop to leader is '{curr_node.next_hop_id}'")
            print("\n")

    def display_epoch_info(self):

        start_time = self.start_time
        stop_time = self.stop_time
        params = self.params
        sim_time = stop_time - start_time


        params['epoch_generated_tx_count_TPS'][params['current_epoch']] = params['epoch_generated_tx_count'][params['current_epoch']]/params['simulation_time']
        params['epoch_processed_tx_count_TPS'][params['current_epoch']] = params['epoch_processed_tx_count'][params['current_epoch']]/params['simulation_time']
        # 计算模拟时间：计算模拟的实际运行时间。
        # 输出模拟详情：打印模拟的基本信息，如节点数、分片数、交易类型分布等。
        # 输出区块链信息（如果有）：如果模拟生成了区块链数据，打印区块链长度、交易数量等详细信息。
        # 计算和输出交易处理速度：计算并打印每秒处理的交易数（TPS）。
        print("\n\n============  SIMULATION DETAILS  ============")
        print("当前时期：", params["current_epoch"])
        print(f"\nNumber of nodes = {params['num_nodes']}")
        print(f"Number of shards = {params['num_shards']}")
        print(f"Fraction of cross-shard tx = {params['cross_shard_tx_percentage']}")
        print(f"Simulation Time = {sim_time} seconds")

        if 'chain' in params:
            count, cross_shard_tx_count, intra_shard_tx_count = 0, 0, 0
            for block in params['chain']:
                count += len(block.transactions_list)

                for tx in block.transactions_list:
                    intra_shard_tx_count += 1 - tx.cross_shard_status
                    cross_shard_tx_count += tx.cross_shard_status

            print(f"\nLength of Blockchain = {len(params['chain'])}")
            print(f"Total no of transactions included in Blockchain = {count}")
            print(f"Total no of intra-shard transactions included in Blockchain = {intra_shard_tx_count}")
            print(f"Total no of cross-shard transactions included in Blockchain = {cross_shard_tx_count}")

            time_tx_processing = params['simulation_time'] - params['tx_start_time']
            time_network_configuration = params['tx_start_time'] - params['network_config_start_time']

            print(f"\nTotal no of transactions processed = {params['processed_tx_count']}")
            print(f"Total no of intra-shard transactions processed = {params['processed_intra_shard_tx_count']}")
            print(f"Total no of cross-shard transactions processed = {params['processed_cross_shard_tx_count']}")

            print(f"\nTotal no of transactions generated = {params['generated_tx_count']}")
            print(f"Total no of intra-shard transactions generated = {params['generated_intra_shard_tx_count']}")
            print(f"Total no of cross-shard transactions generated = {params['generated_cross_shard_tx_count']}")

            print(f"\nepoch_generated_tx_count = {params['epoch_generated_tx_count']}")
            print(f"epoch_generated_intra_shard_tx_count = {params['epoch_generated_intra_shard_tx_count']}")
            print(f"epoch_generated_cross_shard_tx_count = {params['epoch_generated_cross_shard_tx_count']}")

            print(f"\nepoch_processed_tx_count = {params['epoch_processed_tx_count']}")
            print(f"epoch_processed_intra_shard_tx_count = {params['epoch_processed_intra_shard_tx_count']}")
            print(f"epoch_processed_cross_shard_tx_count = {params['epoch_processed_cross_shard_tx_count']}")

            print(f"\nepoch_shard_generated_tx_count = {params['epoch_shard_generated_tx_count']}")
            print(f"epoch_shard_generated_intra_shard_tx_count = {params['epoch_shard_generated_intra_shard_tx_count']}")
            print(f"epoch_shard_generated_cross_shard_tx_count = {params['epoch_shard_generated_cross_shard_tx_count']}")

            print(f"\nepoch_shard_processed_tx_count = {params['epoch_shard_processed_tx_count']}")
            print(f"epoch_shard_processed_intra_shard_tx_count = {params['epoch_shard_processed_intra_shard_tx_count']}")
            print(f"epoch_shard_processed_cross_shard_tx_count = {params['epoch_shard_processed_cross_shard_tx_count']}")

            print(f"\nProcessed TPS = {params['processed_tx_count']/params['simulation_time']}")
            print(f"\nAccepted TPS = {count/params['simulation_time']}")

            print(f"\nepoch_generated_tx_count_TPS = {params['epoch_generated_tx_count_TPS']}")
            print(f"\nepoch_processed_tx_count_TPS = {params['epoch_processed_tx_count_TPS']}")

            # print(f"\nNode_processing_delay = {params['Node_processing_delay']}")
            # print(f"\nNode_transaction_generation_num = {params['Node_transaction_generation_num']}")
            # print(f"\nNumber_of_votes_of_ordinary_segmented_nodes = {params['Number_of_votes_of_ordinary_segmented_nodes']}")
            # print(f"\nNumber_of_mini_Blocks_Generated_by_Segment_Leader_Nodes = {params['Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes']}")
            # print(f"\nNumber_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block = {params['Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block']}")



            print(f"\nsimulation_time = {self.env.now}")
            # print(f"\nNode_transaction_generation_num TPS")
            # for key, value in params['Node_transaction_generation_num'].items():
            #     print(f"\n{key}:{value/params['simulation_time']}")
            # print("------------------------------------------------------------------------------------")
            # print(f"\nNumber_of_votes_of_ordinary_segmented_nodes TPS")
            # for key, value in params['Number_of_votes_of_ordinary_segmented_nodes'].items():
            #     print(f"\n {key}:{value/params['simulation_time']}")
            # print("------------------------------------------------------------------------------------")
            # print(f"\nLatency of network configuration (in simpy units) = {time_network_configuration}")
        else:
            print("Simulation didn't execute for sufficiently long time")

    def get_Non_organizing_Committee_node_id(self):

        all_full_nodes = self.params["all_full_nodes"]

        # 获取所有符合条件的节点的 ID
        filtered_cross_shard_nodes = [
            node_id
            for node_id, node in all_full_nodes.items()
            if node.node_type == 2 or node.node_type == 3
        ]

        return  filtered_cross_shard_nodes

    def get_frequent_transactions_custom(self):
        # # 假设这是您提供的所有节点列表
        # nodes_custom = self.params["all_full_nodes"]
        #
        # # 使用相同的逻辑来为每个节点生成5个不同的交易节点
        # # 注意：由于节点数量较少（只有5个），我们只能从中随机选出4个不同的节点作为交易节点
        # frequent_transactions_custom = {}
        # for node in nodes_custom:
        #     # 从其他节点中随机选取k个作为频繁交易节点
        #     frequent_transactions_custom[node] = random.sample([n for n in nodes_custom if n != node], self.params["frequent_transactions_custom_num"])
        # self.params["frequent_transactions_custom"] = frequent_transactions_custom
        # # if "frequent_transactions_custom" in self.params:
        # #     print("频繁交易节点信息:")
        # #     print(self.params["frequent_transactions_custom"])
        # 获取所有节点列表
        nodes_custom = self.params["all_full_nodes"]

        # 计算每个节点的交易节点数
        num_nodes = self.params["num_nodes"]
        num_shards = self.params["num_shards"]
        num_transactions_per_node = int((num_nodes // num_shards - 1) / 2)

        # 初始化频繁交易节点字典
        frequent_transactions_custom = {node: [] for node in nodes_custom}

        # 为每个节点生成指定数量的交易节点
        for node in nodes_custom:
            # 从其他节点中随机选取指定数量的节点作为频繁交易节点
            other_nodes = [n for n in nodes_custom if n != node]
            frequent_transactions_custom[node] = random.sample(other_nodes, min(num_transactions_per_node, len(other_nodes)))

            # 确保交易节点关系是对称的
            for neighbor in frequent_transactions_custom[node]:
                if node not in frequent_transactions_custom[neighbor]:
                    frequent_transactions_custom[neighbor].append(node)

        # 更新参数
        self.params["frequent_transactions_custom"] = frequent_transactions_custom