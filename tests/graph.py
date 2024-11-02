import networkx as nx

def build_transaction_graph(transactions):
    """
    根据交易记录构建一个加权图，其中边的权重代表节点之间的交易次数。

    参数:
    transactions (list of tuples): 交易记录列表，每个交易是一个元组 (source, target)，代表一次交易从 source 发起到 target。

    返回:
    G (networkx.Graph): 加权图
    """
    G = nx.Graph()  # 创建一个无向图

    # 遍历所有的交易记录，构建图
    for source, target in transactions:
        if G.has_edge(source, target):
            # 如果边已经存在，则增加权重（即交易次数）
            G[source][target]['weight'] += 1
        else:
            # 否则，创建一条新的边，并设置权重为 1
            G.add_edge(source, target, weight=1)

    return G

# 示例交易数据
transactions = [
    ('FN0', 'FN1'),
    ('FN0', 'FN2'),
    ('FN1', 'FN3'),
    ('FN1', 'FN2'),
    ('FN1', 'FN2'),
    ('FN2', 'FN3'),
    ('FN3', 'FN4'),
    ('FN4', 'FN0'),
    # 更多交易记录...
]

# 构建交易图
G = build_transaction_graph(transactions)

# 输出图中的边和权重
print("Edges and weights:")
for u, v, data in G.edges(data=True):
    print(f"({u}, {v}): {data['weight']}")

# 可视化图
import matplotlib.pyplot as plt
pos = nx.spring_layout(G)  # 位置布局
labels = nx.get_edge_attributes(G, 'weight')  # 获取边的权重标签
nx.draw(G, pos, with_labels=True, font_weight='bold')
nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
plt.show()