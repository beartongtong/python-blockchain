import os, sys, inspect
import pandas as pd
import matplotlib.pyplot as plt
import pathlib

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from utils.color_print import ColorPrint

# 这是一个私有函数，用于生成特定条件下的性能图表。它接受多个参数，包括：
#
# df：包含性能数据的 pandas DataFrame。
# base_list, param_list, cond_list：用于迭代的参数列表，分别代表基础参数、变化参数和条件参数的值。
# base_col, param_col, cond_col, tps_col：DataFrame 中对应的列名，分别代表基础参数、变化参数、条件参数和性能指标（TPS）。
# plt_title, plt_name：每个图表的标题和文件名。
# 函数内部，它迭代每个参数组合，根据参数值筛选数据，然后使用 matplotlib 绘制并保存图表。
def __visualize(df, base_list, param_list, cond_list, base_col, param_col, cond_col, tps_col, plt_title, plt_name):
    # plt.figure()
    
    for n in base_list:
        for m in cond_list:
            # if not (abs(m) <= 1e-4 or abs(m - 0.7) <= 1e-4):
            #     continue
            
            rows = df.loc[(df[base_col] == n) & (df[cond_col] == m)]
            rows = rows.sort_values(param_col)
            x = rows[param_col]
            y = rows[tps_col]
            
            plt.xlabel(param_col)
            plt.ylabel(tps_col)
            plt.title(f'{plt_title} for {base_col} = {n}')
            plt.plot(x, y, marker="o")

            # plt.grid()
            plt.savefig(f"{plt_name}_{base_col}={n}_{cond_col}={m}.png")
            plt.figure()

            ColorPrint.print_info(f"[Info]: Saving plot for {plt_title} for {base_col} = {n} and {cond_col}={m}")
        
        plt.legend(cond_list, loc='best', title=cond_col)
        # plt.legend([0.0, 0.7], loc='best', title=cond_col)
        plt.grid(axis='y')
        # plt.savefig(f"{plt_name}_{base_col}={n}.png")
        # plt.show()
    
# 这个函数是可视化操作的入口点，它读取 CSV 文件，提取唯一的参数值，然后调用 __visualize 函数生成图表。它还负责创建存储图表的目录。
def visualize(filename, dir_name):
    df = pd.read_csv(filename)
    num_nodes = sorted(df['Number of nodes'].unique())
    cross_shard_tx_ratio = sorted(df['Fraction of cross-shard tx'].unique())
    num_shards = sorted(df['Number of shards'].unique())

    plt_name = f"{dir_name}/shardsVsTPS"
    __visualize(df, num_nodes, num_shards, cross_shard_tx_ratio, 'Number of nodes', 'Number of shards', \
            'Fraction of cross-shard tx', 'Processed TPS', 'Processed TPS vs Number of Shards', plt_name)

    plt_name = f"{dir_name}/txRatioVsTPS"
    __visualize(df, num_nodes, cross_shard_tx_ratio, num_shards, 'Number of nodes', 'Fraction of cross-shard tx', \
            'Number of shards', 'Processed TPS', 'fraction of cross-shard tx vs TPS', plt_name)
        
# 主函数处理命令行输入，确保用户指定了 CSV 文件。然后，它调用 visualize 函数来执行可视化操作。
def main():
    if len(sys.argv) == 1:
        ColorPrint.print_fail(f"\n[Error]: log file not specified")
        exit(1)

    filename = sys.argv[1]
    parent_dir_name = f"logs_data/plots/{pathlib.PurePath(filename).parent.name}"
    exact_filename = pathlib.PurePath(filename).name
    dir_name = f"{parent_dir_name}/{exact_filename[:exact_filename.find('_')]}"
    
    if not os.path.exists(dir_name):
        ColorPrint.print_info(f"[Info]: Creating directory '{dir_name}' for storing plots")
    pathlib.Path(dir_name).mkdir(parents=True, exist_ok=True)
    
    visualize(filename, dir_name)
    print("\n")


if __name__=="__main__":
    main()