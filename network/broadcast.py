from network.packet import Packet

def broadcast(env, object, object_type, source, neighbour_list, nodes, params):
    """
    Broadcast the object from the source to destination
    """
    if neighbour_list:
        if object_type == "Tx":
            # 如果 object_type 是 "Tx"（交易），根据交易是否跨片（通过 object.cross_shard_status 判断）来设定交易类型（tx_type）。
            # 然后，对于每个邻居，使用 env.process 启动一个进程来处理交易（添加到交易池）。如果启用了详细输出（params["verbose"]），则打印相关信息。
            tx_type = 'intra-shard' if object.cross_shard_status == 0 else 'cross-shard'
            # Broadcast a transaction to all neighbours
            # 递归和并发处理：函数使用 env.process 来处理交易，这意味着每个交易的处理都是并发进行的。对于其他广播类型，使用 env.all_of 等待所有广播事件完成。
            # for neighbour in neighbour_list:
            #     env.process(
            #         nodes[neighbour].transaction_pool.put_transaction_dict(object, nodes[source].location, tx_type)
            #     )
            if params["chain_mode_type"] == 0:
                for neighbour in neighbour_list:
                    env.process(
                        nodes[neighbour].transaction_pool.put_transaction(object, nodes[source].location, tx_type)
                    )

            if params["chain_mode_type"] == 1:
                for neighbour in neighbour_list:
                    env.process(
                        nodes[neighbour].transaction_pool.put_transaction_dict(object, nodes[source].location, tx_type)
                    )
                # events = []
                # for neighbour in neighbour_list:
                #     source_location = nodes[neighbour].location
                #     packeted_object = Packet(source, object, neighbour)
                #     store = nodes[neighbour].pipes
                #     events.append(store.put_data(packeted_object, source_location))
                #
                # if params["verbose"]:
                #     debug_info = "Mini-block-voting-list" if isinstance(object, list) else object.id
                #     print(
                #         "%7.4f" % env.now
                #         + " : "
                #         + "Node %s propagated %s %s to its neighbours %s" % (source, object_type, debug_info, neighbour_list)
                #     )


            if params["verbose"]:
                print(
                    "%7.4f" % env.now
                    + " : "
                    + "%s added to tx-pool of %s"
                    % (object.id, neighbour_list)
                )

        else:
            # Broadcast Block to the network
            # OR Broadcast Tx-block to the shard nodes
            # OR Broadcast Mini-block to the Principal Committee members
            # OR Intra-committee broadcast Mini-block between the Principal Committee members
            # 如果对象不是交易，则可能是区块或其他需要广播的数据结构。为每个邻居创建一个 Packet 对象，并将其放入相应的 pipes 存储中。
            # 如果启用了详细输出，打印广播的详细信息。最后，使用 env.all_of 返回一个事件列表，这些事件在所有的广播完成后都会触发。
            events = []
            for neighbour in neighbour_list:
                source_location = nodes[neighbour].location
                packeted_object = Packet(source, object, neighbour)
                store = nodes[neighbour].pipes
                events.append(store.put_data(packeted_object, source_location))

            if params["verbose"]:
                debug_info = "Mini-block-voting-list" if isinstance(object, list) else object.id
                print(
                    "%7.4f" % env.now
                    + " : "
                    + "Node %s propagated %s %s to its neighbours %s" % (source, object_type, debug_info, neighbour_list)
                )
            #    env.all_of(events)的作用是等待所有广播操作完成。如果广播的是多个迷你块（Mini-block-voting-list），
            #    那么events列表会包含多个事件，每个事件代表一个迷你块被发送到了一个邻居节点。通过env.all_of(events)，
            #    我们可以确保所有的迷你块都被正确地广播给了邻居节点。
            return env.all_of(events)
