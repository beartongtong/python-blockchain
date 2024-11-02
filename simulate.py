import os, sys
import simpy
import numpy as np
import json
import pathlib
import time

from network.network import Network
from utils.color_print import ColorPrint

# 这个函数 execute_simulation 是用来执行网络模拟的。下面是具体的步骤：
# 首先，它创建一个 Network 对象，这个对象可能是用来模拟一个网络环境。Network 的构造函数接收三个参数：一个名字 name，一个 simpy 环境对象 env，以及一个包含模拟参数的字典 params。
# 然后，它调用 Network 对象的 execute_sybil_resistance_mechanism 方法。这个方法的具体实现在这段代码中并没有给出，但从名字来看，它可能是用来执行某种防止 Sybil 攻击的机制。
# 接着，它执行一个循环，循环次数由参数字典 params 中的 num_epochs 决定。在每次循环中，它调用 Network 对象的 run_epoch 方法，可能是让网络经过一个模拟周期。
# 最后，它运行 simpy 环境，直到模拟时间结束。模拟时间由参数字典 params 中的 simulation_time 决定。
# 这个函数的主要作用应该是设置和执行网络模拟。具体的网络行为（如何防止 Sybil 攻击，一个周期是什么，等等）应该是在 Network 类中定义的。
def execute_simulation(name, env, params):


    # 初始化网络
    network_obj = Network(name, params)

    for idx in range(params["num_epochs"]):
        params["current_epoch"] = idx
        #
        # params["epoch_generated_tx_count"][idx] = 0
        # params["epoch_generated_cross_shard_tx_count"][idx] = 0
        # params["epoch_generated_intra_shard_tx_count"][idx] = 0
        #
        # params["epoch_processed_tx_count"][idx] = 0
        # params["epoch_processed_intra_shard_tx_count"][idx] = 0
        # params["epoch_processed_cross_shard_tx_count"][idx] = 0
        #
        # params["epoch_generated_tx_count_TPS"][idx] = 0
        # params["epoch_processed_tx_count_TPS"][idx] = 0
        #
        # params["epoch_shard_generated_tx_count"][idx] = {}
        # params["epoch_shard_generated_intra_shard_tx_count"][idx] = {}
        # params["epoch_shard_generated_cross_shard_tx_count"][idx] = {}
        # params["epoch_shard_processed_tx_count"][idx] = {}
        # params["epoch_shard_processed_intra_shard_tx_count"][idx] = {}
        # params["epoch_shard_processed_cross_shard_tx_count"][idx] = {}
        # for index in range(params["num_shards"]):
        #     params["epoch_shard_generated_tx_count"][idx][index] = 0
        #     params["epoch_shard_generated_intra_shard_tx_count"][idx][index] = 0
        #     params["epoch_shard_generated_cross_shard_tx_count"][idx][index] = 0
        #     params["epoch_shard_processed_tx_count"][idx][index] = 0
        #     params["epoch_shard_processed_intra_shard_tx_count"][idx][index] = 0
        #     params["epoch_shard_processed_cross_shard_tx_count"][idx][index] = 0

        # 创建新的环境
        new_env = simpy.Environment()
        network_obj.env = new_env
        if params["num_epochs"] > 0 :

            # 更新所有节点的环境属性
            for node_id, node in network_obj.full_nodes.items():
                node.env = new_env
                node.node_type = 0
                # 负载能力
                node.load_capacity = params["load_capacity"]
                # 当前负载
                node.current_load = 0

                node.shard_id = -1
                node.shard_leader_id = -1
                node.curr_shard_nodes = {}
                node.neighbours_ids = []
                node.blockchain = []
                node.shard_leaders = {}

                # Handled by only principal committee
                node.mini_block_consensus_pool = {}
                node.processed_mini_blocks = []
                node.processed_tx_blocks = []
                node.current_tx_blocks = []

                # Experimental
                node.pc_leader_id = -1
                node.mini_blocks_vote_pool = []
                node.next_hop_id = -1




        # for node_id, node in network_obj.participating_nodes.items():
        #     node.env = new_env
        if idx == 0:
            # 选举full node
            network_obj.add_participating_nodes(params["num_nodes"])
            network_obj.execute_sybil_resistance_mechanism()




        # print("当前时期", idx)

        network_obj.run_epoch()

    """
    To-Do:  Decide where it should be put.
            Putting it before prev loop doesn't generate transactions.
    """
    # env.run(until=params["simulation_time"])

# 这个 load_parameters 函数的主要目的是从一个 JSON 文件中加载参数。以下是这个函数的详细步骤：
#
# 首先，它设置默认的参数文件路径为 "config/params.json"。
#
# 然后，它检查命令行参数的数量。如果参数数量大于 2，那么它会将第一个命令行参数（sys.argv[1]）作为参数文件的路径。这里的命令行参数是指在运行 Python 脚本时传递给脚本的参数，例如 python script.py arg1 arg2。在这个例子中，arg1 就是 sys.argv[1]，arg2 是 sys.argv[2]。
#
# 接着，它打开参数文件，并将文件内容读取到一个字符串 params 中。
#
# 最后，它使用 json.loads 函数将字符串 params 转换为一个 Python 对象（通常是一个字典或列表），并返回这个对象。
#
# 这个函数的主要作用是加载模拟的参数。这些参数可能包括网络的大小、模拟的时间、Sybil 攻击的概率等等。通过从文件中加载参数，可以使得模拟更加灵活，不需要修改代码就可以改变模拟的设置。
def load_parameters():
    params_file = "config/params.json"
    if len(sys.argv) > 2:
        params_file = sys.argv[1]

    with open(params_file, "r") as f:
        params = f.read()
    params = json.loads(params)

    return params


def main():
    # 初始化和参数加载
    # 设置随机种子：为了确保模拟的可重复性，使用 np.random.seed(7) 设置了一个固定的随机种子。
    # 加载参数：通过调用 load_parameters() 函数从 JSON 文件中加载模拟参数。
    np.random.seed(7)
    params = load_parameters()

    # 1. 重定向标准输出
    # 这行代码保存了原始的标准输出（通常是控制台）。这样做是为了在日志记录完成后能够恢复标准输出。
    orig_stdout = sys.stdout

    # 2. 生成日志文件夹名称
    # dir_suffix 用于存储日志文件的子文件夹名称。如果在命令行参数中提供了参数，则使用该参数作为子文件夹名称；如果没有提供，则使用当前日期和时间作为子文件夹名称。
    # dir_name 是完整的日志文件夹路径，基于一个固定的父文件夹 simulation_logs。
    dir_suffix = sys.argv[1] if len(sys.argv) > 1 else time.strftime('%Y-%m-%d/%H-%M')
    dir_name = f"simulation_logs/{dir_suffix}"

    # 3. 创建日志文件夹
    # 首先检查目标文件夹是否存在，如果不存在，则打印信息提示正在创建文件夹。
    # 使用 pathlib.Path.mkdir 方法创建文件夹，parents=True 参数确保创建所有必需的父文件夹，exist_ok=True 参数允许文件夹已存在而不抛出异常。
    if not os.path.exists(dir_name):
        ColorPrint.print_info(f"\n[Info]: Creating directory '{dir_name}' for storing the simulation logs")
    pathlib.Path(dir_name).mkdir(parents=True, exist_ok=True)
    # file_name = f"{dir_name}/simulation_results_txLimit{params['tx_block_capacity']}_n{params['num_nodes']}_sh{params['num_shards']}_sim{params['simulation_time']}.log"

    # 4. 创建日志文件
    # file_name 根据各种模拟参数构建日志文件的完整路径和名称。
    # 打开这个文件用于写入（'w' 模式），并将文件对象赋值给 f。
    # 打印信息提示日志将被写入到这个文件。
    # 将 sys.stdout 重定向到这个文件，这意味着接下来所有的打印输出都会被写入到 file_name 指定的文件中。
    file_name = f"{dir_name}/simulation_results_cstx{params['cross_shard_tx_percentage']}_n{params['num_nodes']}_sh{params['num_shards']}_sim{params['simulation_time']}.log"
    f = open(file_name, 'w')
    ColorPrint.print_info(f"\n[Info]: Writing simulation logs to the file '{file_name}'")
    sys.stdout = f

    # 5. 初始化模拟参数
    # 这些行初始化了各种模拟相关的计数器，包括生成的交易总数、处理的交易总数、跨分片和内分片的生成和处理交易数。这些参数可能用于在模拟过程中跟踪和报告状态。
    params["generated_tx_count"], params["processed_tx_count"] = 0, 0
    params["generated_cross_shard_tx_count"], params["generated_intra_shard_tx_count"] = 0, 0
    params["processed_cross_shard_tx_count"], params["processed_intra_shard_tx_count"] = 0, 0

    # SimPy 环境：初始化一个 SimPy 模拟环境。
    # 执行模拟：调用 execute_simulation 函数来执行网络模拟。这个函数应该定义了网络的具体行为，如节点交互、交易处理等。

    start_time = time.time()
    # 这行代码创建了一个 simpy 模拟环境的实例。simpy 是一个用于离散事件模拟的Python库，非常适合于模拟如网络通信、物流、资源共享等系统。Environment 类是 simpy 中用于定义和运行模拟的核心组件。
    env = simpy.Environment()
    # 这行代码调用了一个名为 execute_simulation 的函数，该函数负责在提供的 simpy 环境中执行具体的模拟逻辑。函数接收三个参数：
    # "Test Network"：这可能是一个字符串参数，用于标识或描述正在执行的模拟，例如模拟的名称或场景。
    # env：前面创建的 simpy 环境实例，它将被用于此次模拟。
    # params：一个字典，包含了模拟所需的各种参数，这些参数可能会影响模拟的行为和结果。
    execute_simulation("Test Network", env, params)

    stop_time = time.time()
    #
    # sim_time = stop_time - start_time
    #
    # # 计算模拟时间：计算模拟的实际运行时间。
    # # 输出模拟详情：打印模拟的基本信息，如节点数、分片数、交易类型分布等。
    # # 输出区块链信息（如果有）：如果模拟生成了区块链数据，打印区块链长度、交易数量等详细信息。
    # # 计算和输出交易处理速度：计算并打印每秒处理的交易数（TPS）。
    # print("Edges and weights:")
    # for u, v, data in params["graph"].edges(data=True):
    #     print(f"({u}, {v}): {data['weight']}")
    # print("\n\n============  SIMULATION DETAILS  ============")
    # print(f"\nNumber of nodes = {params['num_nodes']}")
    # print(f"Number of shards = {params['num_shards']}")
    # print(f"Fraction of cross-shard tx = {params['cross_shard_tx_percentage']}")
    # print(f"Simulation Time = {sim_time} seconds")
    #
    # if 'chain' in params:
    #     count, cross_shard_tx_count, intra_shard_tx_count = 0, 0, 0
    #     for block in params['chain']:
    #         count += len(block.transactions_list)
    #
    #         for tx in block.transactions_list:
    #             intra_shard_tx_count += 1 - tx.cross_shard_status
    #             cross_shard_tx_count += tx.cross_shard_status
    #
    #     print(f"\nLength of Blockchain = {len(params['chain'])}")
    #     print(f"Total no of transactions included in Blockchain = {count}")
    #     print(f"Total no of intra-shard transactions included in Blockchain = {intra_shard_tx_count}")
    #     print(f"Total no of cross-shard transactions included in Blockchain = {cross_shard_tx_count}")
    #
    #     time_tx_processing = params['simulation_time'] - params['tx_start_time']
    #     time_network_configuration = params['tx_start_time'] - params['network_config_start_time']
    #
    #     print(f"\nTotal no of transactions processed = {params['processed_tx_count']}")
    #     print(f"Total no of intra-shard transactions processed = {params['processed_intra_shard_tx_count']}")
    #     print(f"Total no of cross-shard transactions processed = {params['processed_cross_shard_tx_count']}")
    #
    #     print(f"\nTotal no of transactions generated = {params['generated_tx_count']}")
    #     print(f"Total no of intra-shard transactions generated = {params['generated_intra_shard_tx_count']}")
    #     print(f"Total no of cross-shard transactions generated = {params['generated_cross_shard_tx_count']}")
    #
    #     print(f"\nProcessed TPS = {params['processed_tx_count']/params['simulation_time']}")
    #     print(f"\nAccepted TPS = {count/params['simulation_time']}")
    #
    #     print(f"\nNode_processing_delay = {params['Node_processing_delay']}")
    #     print(f"\nNode_transaction_generation_num = {params['Node_transaction_generation_num']}")
    #     print(f"\nNumber_of_votes_of_ordinary_segmented_nodes = {params['Number_of_votes_of_ordinary_segmented_nodes']}")
    #     print(f"\nNumber_of_mini_Blocks_Generated_by_Segment_Leader_Nodes = {params['Number_of_mini_Blocks_Generated_by_Segment_Leader_Nodes']}")
    #     print(f"\nNumber_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block = {params['Number_of_votes_of_non_leader_nodes_of_the_Organizing_Committee_on_mini_block']}")
    #
    #     print(f"\nNode_transaction_generation_num TPS")
    #     for key, value in params['Node_transaction_generation_num'].items():
    #         print(f"\n{key}:{value/params['simulation_time']}")
    #     print("------------------------------------------------------------------------------------")
    #     print(f"\nNumber_of_votes_of_ordinary_segmented_nodes TPS")
    #     for key, value in params['Number_of_votes_of_ordinary_segmented_nodes'].items():
    #         print(f"\n {key}:{value/params['simulation_time']}")
    #     print("------------------------------------------------------------------------------------")
    #     # print(f"\nLatency of network configuration (in simpy units) = {time_network_configuration}")
    # else:
    #     print("Simulation didn't execute for sufficiently long time")

    sys.stdout = orig_stdout
    f.close()

def simple_process(env):
    while True:
        print("开始事件，当前时间:", env.now)
        # 暂停 0.1 秒
        yield env.timeout(10)
        print("事件完成，当前时间:", env.now)

def setup_and_start_simulation():
    # 创建一个模拟环境
    env = simpy.Environment()

    # 启动一个简单的进程
    env.process(simple_process(env))

    # 开始模拟
    env.run(until=50)  # 模拟 5 秒钟

if __name__=="__main__":
    main()
    # setup_and_start_simulation()
