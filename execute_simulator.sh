#!/bin/sh

set -e

echo "\n[Shell]: Running script.py"
python script.py

echo "\n[Shell]: Creating necessary directories"
mkdir -p logs_data/interactive_plots logs_data/metadata logs_data/plots logs_data/summary

echo "[Shell]: Running log_summarizer.py\n"
DIR=$(ls -td ./simulation_logs/*/*| head -1)
python analyzer/log_summarizer.py $DIR

echo "[Shell]: Running visualizer.py\n"
SUMMARY_FILE=$(ls -t ./logs_data/summary/*/* | head -1)
python analyzer/visualizer.py $SUMMARY_FILE

#脚本流程
 #设置脚本在遇到错误时终止执行：
 #使用 set -e 命令，这意味着如果脚本中的任何命令失败（返回非零退出状态），脚本将立即终止执行。这有助于防止在发生错误时继续执行可能依赖于之前步骤的操作。
 #
 #执行预处理脚本：
 #首先执行一个名为 script.py 的 Python 脚本，可能用于准备数据、清理旧日志或进行其他预处理操作。
 #
 #创建必要的目录结构：
 #使用 mkdir -p 命令创建多个目录，这些目录用于存储交互式图表、元数据、普通图表和日志汇总文件。-p 参数确保如果目录已存在，则不会报错，并且可以一次性创建多级目录。
 #
 #运行日志汇总脚本：
 #
 #首先，使用 ls -td ./simulation_logs/*/*| head -1 命令找到最新的模拟日志目录。这个命令列出 simulation_logs 目录下所有子目录，按时间排序，然后选择最新的一个。
 #然后，执行 analyzer/log_summarizer.py 脚本，将最新的日志目录作为参数传递。这个脚本负责汇总日志信息，可能生成 CSV 文件。
 #运行可视化脚本：
 #
 #使用 ls -t ./logs_data/summary/*/* | head -1 命令找到最新生成的汇总文件。这个命令按时间排序 logs_data/summary 目录下的所有文件，并选择最新的一个。
 #执行 analyzer/visualizer.py 脚本，将最新的汇总文件作为参数传递。这个脚本根据汇总文件生成可视化图表。