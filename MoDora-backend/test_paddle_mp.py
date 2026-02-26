import paddle
import multiprocessing as mp
import os

def check_worker():
    print(f"Worker PID: {os.getpid()}")
    try:
        import paddle
        paddle.utils.run_check()
        print("Worker: Paddle check passed")
    except Exception as e:
        print(f"Worker: Paddle check failed: {e}")

if __name__ == "__main__":
    print(f"Main PID: {os.getpid()}")
    mp.set_start_method('spawn', force=True)
    
    # Initialize paddle in main process
    paddle.utils.run_check()
    print("Main: Paddle check passed")
    
    p = mp.Process(target=check_worker)
    p.start()
    p.join()
