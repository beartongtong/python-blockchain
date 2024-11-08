import os, sys, inspect
import json
import re
import csv
from prettytable import PrettyTable

import networkx as nx
from pyvis.network import Network
import matplotlib.pyplot as plt

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from utils.color_print import ColorPrint

# 主要功能和流程
# 动态路径设置：通过 inspect 和 os 模块动态设置路径，以便可以从父目录导入模块。
# 参数和文件处理：使用正则表达式和命令行参数处理，提取日志文件名的特定部分。
# 网络图创建：通过解析日志文件，构建网络图并以静态和交互式形式保存。
# 交易块分析：解析日志文件中的交易块信息，提取和整理相关数据，最后以 CSV 和文本格式保存。
# 主函数：处理命令行输入的日志文件，调用创建网络图和分析交易块的函数。

# 提取命令行参数中指定的日志文件名的一部分，用于后续文件命名。
def get_file_suffix():
    idx = [m.start() for m in re.finditer(r"_", sys.argv[1])]
    return sys.argv[1][idx[2] + 1 : idx[4]]

# 从给定的字符串中提取节点信息，用于网络图的节点和边的构建。
def extract_nodes(line):
    nodes = []
    start_idx = 0

    while True:
        idx1 = int(line.find("'", start_idx))
        if idx1 == -1:
            return nodes

        idx2 = int(line.find("'", idx1 + 1))
        nodes.append(line[idx1 + 1 : idx2])

        start_idx = idx2 + 1

# 解析日志文件，构建网络图，并保存为静态（PNG）和交互式（HTML）格式。这个函数首先解析日志文件中的网络结构信息，然后使用 networkx 和 pyvis 库来创建和保存图。
#
# 静态图：使用 matplotlib 和 networkx 绘制并保存。
# 交互式图：使用 pyvis 库从 networkx 图创建交互式网络图，并保存为 HTML 文件。
def create_graph(log_file, verbose=False):
    ct = 0

    network_info = {}
    network_info['principal_committee'] = {}
    pc_flag = 0
    leaders = []

    with open(log_file, 'r') as f:
        for line in f:
            if 'Principal Committee Nodes' in line:
                pc_flag = 1
                nodes = extract_nodes(line)
                network_info['principal_committee']['Leader'] = extract_nodes(next(f))
                leaders.append(network_info['principal_committee']['Leader'][0])
                for node in nodes:
                    network_info['principal_committee'][node] = extract_nodes(next(f))
            
            elif 'SHARD' in line:
                num_shard = re.findall(r'\d+', line)[0]
                shard_name = 'Shard_' + num_shard
                network_info[shard_name] = {}

                shard_nodes = extract_nodes(next(f))
                network_info[shard_name]['Leader'] = extract_nodes(next(f))
                leaders.append(network_info[shard_name]['Leader'][0])

                next(f)     # Read a whitespace line
                for node in shard_nodes:
                    duplicate_free_nodes = set(extract_nodes(next(f)))
                    network_info[shard_name][node] = list(duplicate_free_nodes.difference(["-1"]))

    if verbose:   
        print(
            json.dumps(
                network_info,
                indent=4,
                separators=(',', ': ')
            )
        )
            
    G = nx.Graph()
    total_nodes, principal_committee_nodes = [], []
    for key, val in network_info.items():
        if key == 'principal_committee':
            principal_committee_nodes = val.keys()
        total_nodes += val.keys()
    
    total_nodes = list(set(total_nodes).difference(["Leader"]))
    for node in total_nodes:
        c = 'blue' if node in leaders else 'green'
        if node in principal_committee_nodes:
            if node in leaders:
                c = 'orange'
            else:
                c = 'yellow'
        G.add_node(node, color=c)

    for key, val in network_info.items():
        for id, neighbours in val.items():
            if id != 'Leader':
                for node in neighbours:
                    G.add_edge(id, node)
    
    nx.draw(G, with_labels = True)

    filename = "network_graph_" + get_file_suffix()
    ColorPrint.print_info(f"\nSaving static graph in file 'logs_data/plots/{filename}.png'")
    plt.savefig(f"logs_data/plots/{filename}.png")

    vis_net = Network(height='750px', width='100%')
    vis_net.from_nx(G)
    # vis_net.show_buttons(filter_=['physics'])
    ColorPrint.print_info(f"\n[Info]: Saving interactive graph in file 'logs_data/interactive_plots/{filename}.html'")
    vis_net.save_graph(f"logs_data/interactive_plots/{filename}.html")

# 解析日志文件中的交易块信息，包括交易块的 ID、时间戳、发送者和接收者。信息被整理为 CSV 和文本格式，并保存到指定目录。
def analyse_tx_blocks(log_file):
    relevant_lines = []
    ids = set()
    keywords = ['propagated', 'received', 'voted']

    with open(log_file, 'r') as f:
        for line in f:
            res = re.search('TB_FN[0-9]+_[0-9]+', line)
            if res:
                relevant_lines.append(line)
                ids.add(line[res.start() : res.end()])
    
    filename = "metadata_" + get_file_suffix()
    col_names = ['Tx-Block ID', 'Timestamp', 'Sender', 'Receiver']

    ColorPrint.print_info(f"[Info]: Preparing csv file 'logs_data/metadata/{filename}.csv'")
    writer = csv.writer(open(f"logs_data/metadata/{filename}.csv", 'w'))
    writer.writerow(col_names)
    pt = PrettyTable()
    pt.field_names = col_names

    for id in ids:
        writer.writerow([id, '', '', ''])
        pt.add_row([id, '', '', ''])
        for line in relevant_lines:
            if id in line:
                timestamp = line[0 : line.find(':') - 1]
                # print(timestamp)
                receiver, sender = None, None
                if keywords[0] in line:
                    receiver = extract_nodes(line)
                    sender = line[line.find('Node') + 4 : line.find('propagated') - 1]
                elif keywords[1] in line:
                    receiver = line[line.find('Node') + 4 : line.find('received') - 1]
                    sender = "[voted block]" if line.find('from') == -1 else line[line.find('from') + 4 : line.find('\n')]
                else:
                    continue

                writer.writerow(['', timestamp, sender, receiver])
                pt.add_row(['', timestamp, sender, receiver])

    ColorPrint.print_info(f"[Info]: Writing metadata in file 'logs_data/metadata/{filename}.txt'\n")
    with open(f"logs_data/metadata/{filename}.txt", "w") as text_file:
        text_file.write(pt.get_string())


def main():
    if len(sys.argv) == 1:
        ColorPrint.print_fail(f"\n[Error]: log file not specified")
        exit(1)
        
    log_file = sys.argv[1]
    create_graph(log_file)
    analyse_tx_blocks(log_file)
    

if __name__=="__main__":
    main()