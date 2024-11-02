import os, sys, inspect
import json
import re
import csv
import glob
import pathlib

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from utils.color_print import ColorPrint

# 这个函数用于在处理日志文件时，根据提供的查询字符串（query）在特定行中查找信息。如果找到了匹配的信息，它将被添加到 row_data 列表中，该列表最终会被写入 CSV 文件。
def add_cell_entry(query, row_data, line):
    res = re.search(query, line)
    if res:
        row_data.append(line[res.end() : len(line)-1])

# summarize(dir)
# 这是脚本的核心函数，它接收一个目录路径作为输入，然后搜索该目录下的所有日志文件。对于每个文件，它使用 add_cell_entry 函数来提取信息，并将这些信息汇总到一个 CSV 文件中。
#
# 目录和文件处理：使用 pathlib 和 os 模块来创建汇总文件的存储目录，并构建输出文件的路径。
# 信息汇总：对每个日志文件，通过遍历预定义的查询列表来提取信息，然后将这些信息作为一行数据写入 CSV 文件。
def summarize(dir):
    log_files = glob.glob(dir+'/*')
    # queries = ['Number of nodes = ', 'Number of shards = ', 'Fraction of cross-shard tx = ', 'Total no of transactions included in Blockchain = ', \
    #             'Total no of intra-shard transactions included in Blockchain = ', 'Total no of cross-shard transactions included in Blockchain = ', \
    #             'Total no of transactions processed = ', 'Total no of intra-shard transactions processed = ', 'Total no of cross-shard transactions processed = ', \
    #             'Total no of transactions generated = ', 'Total no of intra-shard transactions generated = ', 'Total no of cross-shard transactions generated = ', \
    #             'Processed TPS = ', 'Accepted TPS = ']
    queries = ['Number of nodes = ', 'Number of shards = ',  \
               'Processed TPS = ', 'Accepted TPS = ']
    
    col_names = [name.rstrip(' = ') for name in queries]
    
    dir_name = f"logs_data/summary/{pathlib.PurePath(dir).parent.name}"
    if not os.path.exists(dir_name):
        ColorPrint.print_info(f"\n[Info]: Creating directory '{dir_name}' for storing summary of the simulation logs\n")
    pathlib.Path(dir_name).mkdir(parents=True, exist_ok=True)

    filename = f"{dir_name}/{os.path.basename(os.path.normpath(dir))}_summary.csv"
    writer = csv.writer(open(filename, 'w'))
    writer.writerow(col_names)

    for log_file in log_files:
        ColorPrint.print_info(f"[Info]: Summarizing {log_file} ...")
        row_data = []
        with open(log_file, 'r') as f:
            for line in f:
                for query in queries:
                    add_cell_entry(query, row_data, line)
            writer.writerow(row_data)

    ColorPrint.print_info(f"[Info]: Writing metadata in file '{filename}'\n")

# 主函数处理命令行输入，确保用户指定了包含日志文件的目录。然后，它调用 summarize 函数来执行汇总操作。
def main():
    if len(sys.argv) == 1:
        ColorPrint.print_fail(f"\n[Error]: log file not specified")
        exit(1)

    dir = sys.argv[1]
    summarize(dir)
    

if __name__=="__main__":
    main()