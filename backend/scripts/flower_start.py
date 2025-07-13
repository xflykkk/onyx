import subprocess
import threading
import time

def monitor_process(process_name: str, process: subprocess.Popen) -> None:
    assert process.stdout is not None

    while True:
        output = process.stdout.readline()

        if output:
            print(f"{process_name}: {output.strip()}")

        if process.poll() is not None:
            print(f"{process_name}: Process ended with code {process.returncode}")
            break

def start_flower():
    print("🌸 启动 Flower 监控界面...")
    
    cmd_flower = [
        "celery",
        "--broker=redis://localhost:6379/15",
        "-A", "onyx.background.celery.versioned_apps.primary",
        "flower",
        "--address=0.0.0.0",
        "--port=5001"
    ]
    
    print(f"执行命令: {' '.join(cmd_flower)}")
    
    # 启动 Flower
    flower_process = subprocess.Popen(
        cmd_flower, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True
    )
    
    flower_thread = threading.Thread(
        target=monitor_process, 
        args=("FLOWER", flower_process)
    )
    flower_thread.daemon = True
    flower_thread.start()
    
    print("🌸 Flower 已启动，访问 http://localhost:5001")
    print("🛑 按 Ctrl+C 停止")
    
    try:
        # 等待进程结束
        flower_thread.join()
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号，正在关闭 Flower...")
        flower_process.terminate()
        time.sleep(2)
        
        if flower_process.poll() is None:
            print("强制杀死 Flower...")
            flower_process.kill()
        
        print("✅ Flower 已停止")

if __name__ == "__main__":
    start_flower()