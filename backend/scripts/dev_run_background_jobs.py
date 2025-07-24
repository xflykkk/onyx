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
            break


def start_flower_delayed(cmd_flower, delay_seconds=40):
    """Start Flower after a delay"""
    print(f"等待 {delay_seconds} 秒后启动 Flower...")
    time.sleep(delay_seconds)
    
    # Set environment variable for unauthenticated API access
    import os
    env = os.environ.copy()
    env['FLOWER_UNAUTHENTICATED_API'] = 'true'
    
    flower_process = subprocess.Popen(
        cmd_flower, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
    )
    print("🌸 Flower 已启动，访问 http://localhost:5001")
    
    # Monitor the process
    monitor_process("FLOWER", flower_process)


def run_jobs() -> None:
    # command setup
    cmd_worker_primary = [
        "celery",
        "-A",
        "onyx.background.celery.versioned_apps.primary",
        "worker",
        "--pool=threads",
        "--concurrency=6",
        "--prefetch-multiplier=1",
        "--loglevel=INFO",
        "--hostname=primary@%n",
        "-Q",
        "celery",
    ]

    cmd_worker_light = [
        "celery",
        "-A",
        "onyx.background.celery.versioned_apps.light",
        "worker",
        "--pool=threads",
        "--concurrency=16",
        "--prefetch-multiplier=8",
        "--loglevel=INFO",
        "--hostname=light@%n",
        "-Q",
        "vespa_metadata_sync,connector_deletion,doc_permissions_upsert,checkpoint_cleanup",
    ]

    cmd_worker_heavy = [
        "celery",
        "-A",
        "onyx.background.celery.versioned_apps.heavy",
        "worker",
        "--pool=threads",
        "--concurrency=6",
        "--prefetch-multiplier=1",
        "--loglevel=INFO",
        "--hostname=heavy@%n",
        "-Q",
        "connector_pruning,connector_doc_permissions_sync,connector_external_group_sync,csv_generation",
    ]

    cmd_worker_indexing = [
        "celery",
        "-A",
        "onyx.background.celery.versioned_apps.indexing",
        "worker",
        "--pool=threads",
        "--concurrency=6",
        "--prefetch-multiplier=2",
        "--loglevel=INFO",
        "--hostname=indexing@%n",
        "--queues=connector_indexing",
    ]

    cmd_worker_user_files_indexing = [
        "celery",
        "-A",
        "onyx.background.celery.versioned_apps.indexing",
        "worker",
        "--pool=threads",
        "--concurrency=3",
        "--prefetch-multiplier=1",
        "--loglevel=INFO",
        "--hostname=user_files_indexing@%n",
        "--queues=user_files_indexing",
    ]

    cmd_worker_monitoring = [
        "celery",
        "-A",
        "onyx.background.celery.versioned_apps.monitoring",
        "worker",
        "--pool=solo",
        "--concurrency=1",
        "--prefetch-multiplier=1",
        "--loglevel=INFO",
        "--hostname=monitoring@%n",
        "--queues=monitoring"
    ]


    cmd_worker_kg_processing = [
        "celery",
        "-A",
        "onyx.background.celery.versioned_apps.kg_processing",
        "worker",
        "--pool=threads",
        "--concurrency=4",
        "--prefetch-multiplier=1",
        "--loglevel=INFO",
        "--hostname=kg_processing@%n",
        "--queues=kg_processing",
    ]

    cmd_beat = [
        "celery",
        "-A",
        "onyx.background.celery.versioned_apps.beat",
        "beat",
        "--loglevel=INFO",
    ]

    cmd_flower = [
        "celery",
        "--broker=redis://localhost:6379/15",
        "-A", "onyx.background.celery.versioned_apps.primary",
        "flower",
        "--address=0.0.0.0",
        "--port=5001"
    ]

    # spawn processes
    worker_primary_process = subprocess.Popen(
        cmd_worker_primary, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    worker_light_process = subprocess.Popen(
        cmd_worker_light, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    worker_heavy_process = subprocess.Popen(
        cmd_worker_heavy, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    worker_indexing_process = subprocess.Popen(
        cmd_worker_indexing, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    worker_user_files_indexing_process = subprocess.Popen(
        cmd_worker_user_files_indexing,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    worker_monitoring_process = subprocess.Popen(
        cmd_worker_monitoring,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    

    worker_kg_processing_process = subprocess.Popen(
        cmd_worker_kg_processing,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    beat_process = subprocess.Popen(
        cmd_beat, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    # monitor threads
    worker_primary_thread = threading.Thread(
        target=monitor_process, args=("PRIMARY", worker_primary_process)
    )
    worker_light_thread = threading.Thread(
        target=monitor_process, args=("LIGHT", worker_light_process)
    )
    worker_heavy_thread = threading.Thread(
        target=monitor_process, args=("HEAVY", worker_heavy_process)
    )
    worker_indexing_thread = threading.Thread(
        target=monitor_process, args=("INDEX", worker_indexing_process)
    )
    worker_user_files_indexing_thread = threading.Thread(
        target=monitor_process,
        args=("USER_FILES_INDEX", worker_user_files_indexing_process),
    )
    worker_monitoring_thread = threading.Thread(
        target=monitor_process, args=("MONITORING", worker_monitoring_process)
    )
    worker_kg_processing_thread = threading.Thread(
        target=monitor_process, args=("KG_PROCESSING", worker_kg_processing_process)
    )
    beat_thread = threading.Thread(target=monitor_process, args=("BEAT", beat_process))
    flower_thread = threading.Thread(target=start_flower_delayed, args=(cmd_flower, 40))

    worker_primary_thread.start()
    worker_light_thread.start()
    worker_heavy_thread.start()
    worker_indexing_thread.start()
    worker_user_files_indexing_thread.start()
    worker_monitoring_thread.start()
    worker_kg_processing_thread.start()
    beat_thread.start()
    flower_thread.start()
    

    worker_primary_thread.join()
    worker_light_thread.join()
    worker_heavy_thread.join()
    worker_indexing_thread.join()
    worker_user_files_indexing_thread.join()
    worker_monitoring_thread.join()
    worker_kg_processing_thread.join()
    beat_thread.join()
    flower_thread.join()
    


if __name__ == "__main__":
    run_jobs()


   
