class Transaction:
    """
    This class models a transaction
    """

    def __init__(self, id, creation_time, value, reward, state, cross_shard_status):
        self.id = id
        self.creation_time = creation_time
        self.miningTime = 0
        self.value = value
        self.reward = reward
        self.state = {}
        self.cross_shard_status = cross_shard_status    # 0 - Intra-shard;  1 - Cross-shard
        self.receiver = None
        self.originate_shard = None
        self.target_shard = None
    def display(self):
        print(self.id)
    
    def set_receiver(self, receiver_node_id):
        self.receiver = receiver_node_id

    def set_originate_shard(self, originate_shard):
        self.originate_shard = originate_shard

    def set_target_shard(self, target_shard):
        self.target_shard = target_shard