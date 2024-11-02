import numpy as np
import json
from queue import Queue


def is_voting_complete(tx_block):
    for tx_id, tx_status in tx_block.votes_status.items():
        for _, node_vote in tx_status.items():
            if node_vote == -1:
                return False
    return True


def is_voting_complete_for_cross_shard_block(cross_shard_block, shard_id):
    for _, tx_status in cross_shard_block.shard_votes_status[shard_id].items():
        for _, node_vote in tx_status.items():
            if node_vote == -1:
                return False
    return True


def is_vote_casted(tx_block, node_id):

    random_tx = list(tx_block.votes_status.values())[0]
    return random_tx[node_id] != -1

# def is_vote_casted(tx_block, node_id):
#     for tx_status in tx_block.votes_status.values():
#         if tx_status[node_id] == -1:
#             return False
#     return True

def is_vote_casted_for_cross_shard_block(cross_shard_block, shard_id, node_id):

    random_tx = list(cross_shard_block.shard_votes_status[shard_id].values())[0]
    return random_tx[node_id] != -1


def received_cross_shard_block_for_first_time(cross_shard_block, shard_id):
    # flag = 1
    # for tx_id, tx_status in cross_shard_block.shard_votes_status[shard_id].items():
    #     for _, node_vote in tx_status.items():
    #         flag = flag and (node_vote == -1)
    # return flag
    # print(f"Debug: {shard_id}\n{json.dumps(cross_shard_block.shard_votes_status, indent=4)}")
    # print(f"Res = {shard_id not in cross_shard_block.shard_votes_status.keys()}")
    return shard_id not in cross_shard_block.shard_votes_status.keys()

# 目的是从给定的节点集合中筛选出属于特定分片（shard）并且具有特定类型的邻居节点。
# 具体来说，这个函数会返回一个列表，该列表包含了属于指定分片并且节点类型为 3 或 2 的邻居节点的 ID。
def get_shard_neighbours(nodes, neighbours_ids, shard_id):
    shard_neigbours = []
    for id in neighbours_ids:
        if nodes[id].shard_id == shard_id and (nodes[id].node_type == 3 or nodes[id].node_type == 2):
            shard_neigbours.append(id)
    return shard_neigbours


def get_shard_nodes(nodes, neighbours_ids, shard_id):
    shard_neigbours = []
    for id in neighbours_ids:
        if nodes[id].shard_id == shard_id:
            shard_neigbours.append(id)
    return shard_neigbours


def get_principal_committee_neigbours(nodes, neighbours_list):
    principal_committee_neigbours = []
    for id in neighbours_list:
        if nodes[id].node_type == 1:
            principal_committee_neigbours.append(id)
    return principal_committee_neigbours


def get_block_delay(mu, sigma):
    delay = mu + sigma * np.random.randn()
    if delay < 0:
        return get_block_delay(mu, sigma)
    return delay


def get_transaction_delay(mu, sigma):
    delay = mu + sigma * np.random.randn()
    if delay < 0:
        return get_transaction_delay(mu, sigma)
    return delay

def get_deal_delay(mu, sigma):
    delay = mu + sigma * np.random.randn()
    if delay < 0:
        return get_deal_delay(mu, sigma)
    return delay

def get_transmission_delay(source, destination):
    with open("config/params.json", "r") as f:
        params = f.read()
    params = json.loads(params)
    mu = params["delay"][source][destination]["mu"]
    sigma = params["delay"][source][destination]["sigma"]
    delay = mu + sigma * np.random.randn()
    if delay < 0:
        return get_transmission_delay(source, destination)
    return delay


def can_generate_block(mini_block_consensus_pool, size_principal_committee, num_shards):
    """
    Check whether the principal committee node can generate block
    """
    # To-do: Handle case when 1 shard produces mutliple mini-blocks while other shard has produced only 1 mini-block
    # 待办事项:处理一个分片产生多个小块而另一个分片只产生一个小块的情况
    if len(mini_block_consensus_pool) < num_shards:
        return False
    else:
        for key, val in mini_block_consensus_pool.items():
            if len(val["votes"]) != size_principal_committee:
                return False
            
            for node_id, vote in val["votes"].items():
                if vote == -1:
                    return False
        return True        


def has_received_mini_block(mini_block_consensus_pool, block_id):
    """
    Check whether the principal committee node is receiving mini-block for the first time
    """
    return block_id in mini_block_consensus_pool


def assign_next_hop_to_leader(nodes, leader):
    """
    Perform BFS to assign next_hop to all the shard nodes
    """
    q = Queue(maxsize = len(nodes))
    q.put(leader.id)
    used = {node_id: False for node_id in nodes}
    used[leader.id] = True

    while not q.empty():
        curr_node = nodes[q.get()]
        for neighbour_id in curr_node.neighbours_ids:
            if neighbour_id not in nodes:               # neighbour is a principal committee node
                continue
            if not used[neighbour_id]:
                used[neighbour_id] = True
                q.put(neighbour_id)
                nodes[neighbour_id].next_hop_id = curr_node.id


def filter_transactions(tx_block, tx_block_type, cutoff_vote_percentage):
    """
    Returns the filtered transactions from the tx_block based on the votes
    """
    filtered_transactions = []
    tx_mapping = {}
    for tx in tx_block.transactions_list:
        tx_mapping[tx.id] = tx

    if tx_block_type == 'intra_shard_tx_block':
        for tx_id, votes_info in tx_block.votes_status.items():
            affirmative_votes_count = 0
            for node_id, vote in votes_info.items():
                affirmative_votes_count += 1 if vote else 0
            
            affirmative_votes_ratio = affirmative_votes_count / len(votes_info.keys())
            if affirmative_votes_ratio > cutoff_vote_percentage:
                filtered_transactions.append(tx_mapping[tx_id])
    else:
        shard_votes = {}

        for shard_id, shard_info in tx_block.shard_votes_status.items():

            for tx_id, votes_info in shard_info.items():
                affirmative_votes_count = 0
                flag = False
                for node_id, vote in votes_info.items():
                    affirmative_votes_count += 1 if vote else 0
                    flag = (vote == 2 or vote == -1)
                    if flag:
                        break
                    # else:
                    #     print("这是一个有效的投票")
                    #     print("shard_id", shard_id)
                    #     print("shard_info", shard_info)
                    #     print("node_id", node_id)
                    #     print("vote", vote)
                if not flag:
                    affirmative_votes_ratio = affirmative_votes_count / len(votes_info.keys())
                    if tx_id not in shard_votes:
                        shard_votes[tx_id] = {}
                    shard_votes[tx_id][shard_id] = affirmative_votes_ratio > cutoff_vote_percentage
                    # if shard_votes[tx_id][shard_id]:
                    #         print("这是一个有效的投票")
                    #         print("shard_id", shard_id)
                    #         print("shard_info", shard_info)
                    #         print("node_id", node_id)
                    #         print("vote", vote)
                    # print("打印shard_votes", shard_votes)
                    # print("打印shard_votes[tx_id][shard_id]", shard_votes[tx_id][shard_id])
        for tx_id, votes_info in shard_votes.items():
            # print("打印tx_id", tx_id)

            for node_id, vote in votes_info.items():
                # print("打印votes_info", votes_info)
                # print("打印vote", vote)
                if not vote:        # Accept the tx only when all shards vote True
                    continue
            filtered_transactions.append(tx_mapping[tx_id])


        for tx_id, votes_info in shard_votes.items():
            all_shards_agree = True  # 引入标志变量，假设所有分片都同意
            for shard_id, vote_passed in votes_info.items():
                if not vote_passed:  # 如果有任何一个分片不同意
                    all_shards_agree = False  # 更新标志变量
                    break  # 跳出循环，无需检查其他分片

            if all_shards_agree:  # 只有当所有分片都同意时
                filtered_transactions.append(tx_mapping[tx_id])  # 添加交易到结果列表

    return filtered_transactions

def deal_transaction(current_load, load_capacity):
    return current_load < load_capacity

def get_load_capacity_delay(mu, sigma):
    # load_capacity = mu + sigma * np.random.randn()
    load_capacity = int(round(mu + sigma * np.random.randn()))
    if load_capacity < 1:
        return 1
    return int(round(load_capacity))


