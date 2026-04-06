"""
性能对比测试脚本
对比优化前后的 select_stock.py 性能
"""
import subprocess
import time
import sys
from pathlib import Path


def run_benchmark(name, cmd, iterations=3):
    """运行性能测试"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    
    times = []
    for i in range(iterations):
        print(f"\n第 {i+1}/{iterations} 轮...")
        start = time.perf_counter()
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f"耗时: {elapsed:.3f}s")
        
        if result.returncode != 0:
            print(f"错误: {result.stderr}")
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\n{name} 结果:")
    print(f"  平均: {avg_time:.3f}s")
    print(f"  最快: {min_time:.3f}s")
    print(f"  最慢: {max_time:.3f}s")
    
    return avg_time


def main():
    data_dir = "./data"
    config = "./configs.json"
    
    # 检查目录是否存在
    if not Path(data_dir).exists():
        print(f"错误: 数据目录 {data_dir} 不存在")
        print("请先运行 fetch_kline.py 下载数据")
        sys.exit(1)
    
    print("="*60)
    print("Select Stock 性能对比测试")
    print("="*60)
    
    # 测试1: 首次运行（无缓存）
    print("\n【测试1】首次运行 - 并行加载（无缓存）")
    time_parallel = run_benchmark(
        "并行加载",
        f"python select_stock.py --data-dir {data_dir} --config {config} --no-cache --strategy-workers 4",
        iterations=1
    )
    
    # 测试2: 缓存运行
    print("\n【测试2】缓存运行 - 使用缓存")
    time_cached = run_benchmark(
        "缓存运行",
        f"python select_stock.py --data-dir {data_dir} --config {config} --strategy-workers 4",
        iterations=3
    )
    
    # 测试3: 单策略运行
    print("\n【测试3】单策略运行 - 只运行第一个策略")
    # 需要创建一个单策略配置文件
    time_single = run_benchmark(
        "单策略",
        f"python select_stock.py --data-dir {data_dir} --config {config} --strategy-workers 1",
        iterations=3
    )
    
    # 总结
    print("\n" + "="*60)
    print("性能对比总结")
    print("="*60)
    print(f"并行加载(无缓存): {time_parallel:.3f}s")
    print(f"缓存运行(平均):   {time_cached:.3f}s")
    print(f"单策略运行:       {time_single:.3f}s")
    
    if time_parallel > 0:
        speedup = time_parallel / time_cached
        print(f"\n缓存加速比: {speedup:.2f}x")
    
    print("\n建议:")
    print("- 首次运行使用并行加载")
    print("- 日常运行使用缓存模式")
    print("- 调试时使用单策略模式")


if __name__ == "__main__":
    main()
