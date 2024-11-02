import json
import os
import sys
import subprocess
import time

num_nodes = [100]
num_shards = [i for i in range(3, 60)]
# tx_block_capacity = [5, 8, 10, 15, 20]

cs_tx_fraction = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] # 跨分片交易比例

dir_suffix = time.strftime('%Y-%m-%d/%H-%M')
# 这段代码主要用于执行一系列的网络模拟，通过改变网络参数（节点数、分片数和跨分片交易比例）来探索这些参数对网络性能的影响。以下是代码的详细解释：
#
# 定义参数范围：定义了节点数、分片数和跨分片交易比例的取值范围。节点数是固定的（100），分片数从3到60，跨分片交易比例从0.0到1.0。
#
# 设置日志目录：根据当前时间生成日志文件的目录。
#
# 参数组合遍历：对每个参数组合进行模拟。在每次模拟前，读取默认的模拟参数，修改特定的参数值，然后保存回文件。
#
# 执行模拟：使用 subprocess.Popen 执行模拟脚本 simulate.py，并等待其完成。如果模拟过程中发生错误，程序将退出并输出错误信息。
#
# 注意事项
# 错误处理：当模拟脚本返回非零的退出码时，程序会退出并输出错误信息。但是，这种错误处理方式可能不足以捕获所有可能的错误，例如读写文件失败或 JSON 解析错误。
# 文件操作：在修改和保存模拟参数前，先删除原文件，然后再创建新文件。这可能导致在写入过程中发生错误时丢失原文件。一个更安全的做法是先写入一个临时文件，然后再替换原文件。
# 并行性：这个脚本是串行执行每个模拟的，即在一个模拟完成之前，不会开始下一个模拟。如果模拟的计算量很大，可以考虑使用并行化技术来提高效率。
# 这个脚本为进行大规模的网络模拟提供了一个基本的框架，可以根据具体的需求进行调整和扩展，以适应不同的模拟场景和目标。
for node_cnt in num_nodes:
    for shard_cnt in num_shards:
        # num_nodes 和 num_shards 是两个列表，分别包含不同的节点数量和分片数量。
        # 对于每一对节点数 (node_cnt) 和分片数 (shard_cnt)，检查分片数是否等于节点数的 65% 除以 3 的整数部分。如果等于，跳出内层循环，不再对当前节点数进行更多分片数的模拟。
        if shard_cnt == int(0.65 * node_cnt / 3):
            break

        # 遍历跨分片交易比例
        # cs_tx_fraction 是一个列表，包含不同的跨分片交易比例。
        for cs_tx_ratio in cs_tx_fraction:
            # 读取 params.json 配置文件。
            # 修改配置文件中的节点数 (num_nodes)、分片数 (num_shards)、详细输出设置 (verbose) 和跨分片交易比例 (cross_shard_tx_percentage)。如果节点数大于 15，设置 verbose 为 0（不输出详细信息），否则为 1。
            filename = 'config/params.json'
            with open(filename, 'r') as f:
                data = json.load(f)
                data['num_nodes'] = node_cnt
                data['num_shards'] = shard_cnt
                data['verbose'] = 0 if node_cnt > 15 else 1
                data['cross_shard_tx_percentage'] = cs_tx_ratio

            # 保存修改后的配置文件
            # 删除原配置文件，然后重新写入修改后的数据。
            os.remove(filename)
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)

            # 执行模拟脚本
            # 构建命令行命令，调用 simulate.py 脚本，传递 dir_suffix 参数（这个参数在代码中未定义，可能是用于指定输出目录或文件名的前缀或后缀）。
            # 使用 subprocess.Popen 执行命令，并等待其完成。
            cmd = ['python', 'simulate.py', dir_suffix]
            proc = subprocess.Popen(cmd)
            proc.wait()

            # 检查执行结果
            # 使用 communicate() 方法获取进程的标准输出和错误输出。
            # 检查进程返回码，如果不为 0（表示发生错误），则输出错误信息并退出程序。
            (stdout, stderr) = proc.communicate()
            if proc.returncode != 0:
                sys.exit("\n\x1b[1;31m[script.py]: Aw, Snap! An error has occurred")