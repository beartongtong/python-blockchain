import simpy
import numpy as np

from playground.nodes.miner import Miner
from nodes.full_node import FullNode
from network.block import Block
from network.pipe import Pipe
from network.broadcast import broadcast
from factory.transaction import Transaction
from utils import get_transaction_delay
# from utils.helper import  get_transaction_delay

class Network:
    """docstring for Network
    self.name：网络的名称。
    self.env：模拟环境。
    self.params：模拟参数。
    self.locations：可能的位置列表。
    self.miners：存储所有矿工节点的字典。
    self.fullNodes：存储所有全节点的字典。
    self.nodes：存储所有节点（包括矿工和全节点）的字典。
    self.pipes：存储所有节点间通信管道的字典。
    self.data：存储各种统计数据的字典。
    self.data["blockProp"]：存储区块传播数据的字典。
    self.data["locationDist"]：存储位置分布数据的字典。
    self.data["numStaleBlocks"]：无效区块的数量。
    self.data["numTransactions"]：总交易数量。
    self.data["numForks"]：观察到的分支数量。
    """

    def __init__(self, name, env, params):
        self.name = name
        self.env = env
        self.params = params
        self.locations = params["locations"]
        self.miners = {}
        self.fullNodes = {}
        self.nodes = {}
        self.pipes = {}
        self.data = {}
        self.data["blockProp"] = {}
        self.data["locationDist"] = {}
        self.data["numStaleBlocks"] = 0
        self.data["numTransactions"] = 0
        self.data["numForks"] = 0

        """Initialize the location distribution data"""
        for loc in self.locations:
            self.data["locationDist"][loc] = 0

        self.env.process(self.addTransaction())

    def addTransaction(self):
        num = 0
        while True:
            delay = get_transaction_delay(
                self.params["transactionMu"], self.params["transactionSigma"]
            )
            yield self.env.timeout(delay)

            value = np.random.randint(self.params["txLow"], self.params["txHigh"])
            reward = value * self.params["rewardPercentage"]

            transaction = Transaction("T%d" % num, self.env.now, value, reward)
            self.data["numTransactions"] += 1
            if self.params["verbose"]:
                print(
                    "%7.4f" % self.env.now
                    + " : "
                    + "%s added with reward %.2f"
                    % (transaction.identifier, transaction.reward)
                )
            """Broadcast transactions to all neighbours"""
            transactionNeighbours = list(
                np.random.choice(list(self.nodes.keys()), size=len(self.nodes) // 2)
            )
            broadcast(
                self.env,
                transaction,
                "Transaction",
                "TempID",
                transactionNeighbours,
                self.params,
                nodes=self.nodes,
            )
            num += 1

    def addNodes(self, numMiners, numFullNodes):
        """Add Nodes to network
        初始化节点总数
        """
        numNodes = numFullNodes + numMiners
        """Degree of network graph. Degree >= n/2 guarantees a connected graph
        确定每个节点的连接度
        """
        degree = numNodes // 2 + 1

        """
           循环遍历所有节点，这个循环用于为每个节点生成邻居列表和位置。
        """
        for identifier in range(numNodes):
            """
            确定每个节点可能的邻居
            可能的邻居是 [0, 1, ... i-1, i+1, ... n]
            """
            possibleNeighbours = list(range(identifier)) + list(
                range(identifier + 1, numNodes)
            )
            """从可能的邻居列表中随机选择degree个节点作为当前节点的实际邻居，并且不重复选择。"""
            randNeighbour = np.random.choice(
                possibleNeighbours, size=degree, replace=False
            )

            """
            这里生成了一个包含邻居节点标识符的列表，对于小于numMiners的节点，它们是矿工节点，标记为"M"开头；对于大于等于numMiners的节点，它们是全节点，标记为"F"开头。
            """
            neighbourList = [
                "M%d" % x if x < numMiners else "F%d" % (x - numMiners)
                for x in randNeighbour
            ]

            """为当前节点随机选择一个位置，并更新locationDist字典来记录该位置上的节点数量。"""
            location = np.random.choice(self.locations, size=1)[0]
            self.data["locationDist"][location] += 1
            """如果当前节点是一个矿工节点，则创建一个Miner类的实例，并将其添加到self.miners字典中。
            如果当前节点是一个全节点，则创建一个FullNode类的实例，并将其添加到self.fullNodes字典中。
            """
            if identifier < numMiners:
                self.miners["M%d" % identifier] = Miner(
                    "M%d" % identifier,
                    self.env,
                    neighbourList,
                    self.pipes,
                    self.nodes,
                    location,
                    self.data,
                    self.params,
                )
                if bool(self.params["verbose"]):
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "%s added at location %s with neighbour list %s"
                        % ("M%d" % identifier, location, neighbourList)
                    )
            else:
                self.fullNodes["F%d" % (identifier - numMiners)] = FullNode(
                    "F%d" % (identifier - numMiners),
                    self.env,
                    neighbourList,
                    self.pipes,
                    self.nodes,
                    location,
                    self.data,
                    self.params,
                )
                if bool(self.params["verbose"]):
                    print(
                        "%7.4f" % self.env.now
                        + " : "
                        + "%s added at location %s with neighbour list %s"
                        % ("F%d" % identifier, location, neighbourList)
                    )
        self.nodes.update(self.miners)
        self.nodes.update(self.fullNodes)

    def addPipes(self, numMiners, numFullNodes):
        # 这段循环为每个矿工节点创建一个 Pipe 对象，并将其存储在 self.pipes 字典中。每个矿工节点的标识符都以 "M" 开头加上对应的编号。
        for identifier in range(numMiners):
            self.pipes["M%d" % identifier] = Pipe(
                self.env, "M%d" % identifier, self.nodes
            )
        # 这段循环为每个全节点创建一个 Pipe 对象，并将其存储在同一个 self.pipes 字典中。每个全节点的标识符都以 "F" 开头加上对应的编号。
        #         这里的 Pipe 类应当是一个已经定义好的类，它负责处理节点之间的通信。每个 Pipe 实例的创建都需要传递三个参数：
        #
        # self.env: 模拟环境的对象，可能是用来跟踪时间或者模拟中的其他状态。
        # name: 管道的名字，这里使用节点的标识符。
        # nodes: 包含所有节点的字典或列表，可能用来在管道中实现节点间的交互。
        # 总结来说，addPipes 方法的作用是在创建了所需的矿工节点和全节点后，为每一个这样的节点创建一个数据管道，以便于它们之间可以互相通信。这样就建立了一个初步的网络模型，其中节点能够通过这些管道发送和接收消息或数据。
        for identifier in range(numFullNodes):
            self.pipes["F%d" % identifier] = Pipe(
                self.env, "F%d" % identifier, self.nodes
            )


    def displayChains(self):
        print("\n--------------------All Miners--------------------\n")
        for node in self.nodes.values():
            node.displayChain()

