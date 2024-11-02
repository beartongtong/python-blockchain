"""
python simulate.py <params.json> <netDump.pkl>
下面是代码的主要部分和功能的解释：

导入模块：
sys：用于处理命令行参数。
simpy：用于创建和管理模拟环境。
numpy：用于数学计算和统计。
json：用于读取JSON格式的参数文件。
pickle：用于序列化和反序列化Python对象。
自定义模块（如 network.block.Block, network.network.Network）：用于定义区块链中的区块和网络类。
simulate 函数：
创建一个区块链网络实例 (Network) 并返回。
网络初始化包括添加矿工和全节点 (addNodes) 和连接管道 (addPipes)。
加载参数：
从命令行第一个参数获取参数文件路径。
读取参数文件并解析为字典形式 (params)。
设置随机种子：
使用固定的随机种子 (7) 来确保每次运行的结果可复现。
初始化模拟环境：
创建 simpy 环境 (env)。
调用 simulate 函数初始化网络 (net)。
运行模拟直到指定的时间点 (env.run(until=params["simulationTime"]))。
输出统计数据：
输出参数信息（如节点数、模拟时间等）。
输出节点位置分布。
输出区块传播数据，包括平均、中位数、最小值和最大值。
计算最长链的长度、平均区块大小、无效区块数量、总交易数量等。
输出交易等待时间和奖励。
输出观察到的分支数量。
输出实际模拟时间和每秒处理的交易数 (TPS)。
保存网络状态：
代码注释掉了这部分，原本的功能是将网络中所有节点的状态序列化后保存到文件 (netDump.pkl)。
具体解释：
位置分布：显示每个位置的节点数量百分比。
区块传播时间：展示每个区块从创建到被全部节点接收的时间。
最长链：找出拥有最长链的节点，并计算该链上所有区块的平均大小。
交易统计：分析交易等待时间及奖励。
分支统计：记录分支的数量。
性能指标：包括实际模拟耗时与每秒处理的交易数 (TPS)。
该脚本可以用来研究不同参数设置下区块链网络的行为特征，例如区块传播效率、交易确认时间等。
"""
import sys
import simpy
import numpy as np
import json
import pickle as pkl
from network.block import Block
from network.network import Network
from time import time


def simulate(env, params):
    """Begin simulation"""
    net = Network("Blockchain", env, params)
    net.addNodes(params["numMiners"], params["numFullNodes"])
    net.addPipes(params["numMiners"], params["numFullNodes"])
    return net


"""Load parameters from params.json"""
paramsFile = sys.argv[1]
print("paramsFile", paramsFile)
with open(paramsFile, "r") as f:
    params = f.read()
params = json.loads(params)

np.random.seed(7)
start = time()
env = simpy.Environment()
net = simulate(env, params)
env.run(until=params["simulationTime"])
net.displayChains()
stop = time()

totalNodes = params["numFullNodes"] + params["numMiners"]
print("\n\n\t\t\t\t\t\tPARAMETERS")
print(f"Number of Full nodes = {params['numFullNodes']}")
print(f"Number of Miners = {params['numMiners']}")
print(f"Degree of nodes = {totalNodes//2 + 1}")
print(f"Simulation time = {params['simulationTime']} seconds")

print("\t\t\t\t\t\tSIMULATION DATA")
"""Location distribution"""
print("Location Distribution Data")
for key, value in net.data["locationDist"].items():
    print(f"{key} : {100*value/totalNodes}%")

"""Block Propagation"""
print("\nBlock Propagation Data")
blockPropData = []
for key, value in net.data["blockProp"].items():
    blockPropData.append(value[1] - value[0])
    print(f"{key} : {blockPropData[-1]} seconds")

print(f"Mean Block Propagation time = {np.mean(blockPropData)} seconds")
print(f"Median Block Propagation time = {np.median(blockPropData)} seconds")
print(f"Minimum Block Propagation time = {np.min(blockPropData)} seconds")
print(f"Maximum Block Propagation time = {np.max(blockPropData)} seconds")

longestChain = []
longestChainNode = net.nodes["M0"]

for node in net.nodes.values():
    if len(node.blockchain) > len(longestChain):
        longestChainNode = node
        longestChain = node.blockchain

numTxs = 0
for block in longestChain:
    numTxs += len(block.transactionList)
meanBlockSize = (numTxs * 250) / len(longestChain)

print(f"\nTotal number of Blocks = {len(longestChain)}")
print(f"Mean block size = {meanBlockSize} bytes")
print(f"Total number of Stale Blocks = {net.data['numStaleBlocks']}")
print(f"Total number of Transactions = {net.data['numTransactions']}")

txWaitTimes = []
txRewards = []

for block in longestChain:
    for transaction in block.transactionList:
        txRewards.append(transaction.reward)
        txWaitTimes.append(transaction.miningTime - transaction.creationTime)

print(f"\nNode with longest chain = {longestChainNode.identifier}")
print(
    f"Min waiting time = {np.min(txWaitTimes)} with reward = {txRewards[np.argmin(txWaitTimes)]}"
)
print(f"Median waiting time = {np.median(txWaitTimes)}")
print(
    f"Max waiting time = {np.max(txWaitTimes)} with reward = {txRewards[np.argmax(txWaitTimes)]}"
)

print(f"\nNumber of forks observed = {net.data['numForks']}")

print(f"\nSimulation Time = {stop-start} seconds")
print(f"\nTPS = {numTxs/(stop-start)} seconds")

toStore = net.nodes.copy()

# netDump = {}

# for node in net.nodes.values():
#     netDump[node.identifier] = {}
#     netDump[node.identifier]["neighbourList"] = node.neighbourList
#     netDump[node.identifier]["location"] = node.location
#     netDump[node.identifier]["data"] = node.data
#     netDump[node.identifier]["blockchain"] = node.blockchain

# with open(sys.argv[2], "wb") as f:
#     pkl.dump(netDump, f)
