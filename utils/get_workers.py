import os
import multiprocessing


def get_optimal_workers(min_workers: int = 3, max_workers: int = 5) -> int:
    """최적의 스레드 수를 계산하는 함수"""
    
    # CPU 코어 수 확인
    cpu_count = os.cpu_count() or multiprocessing.cpu_count()
    
    # I/O 바운드 작업, 코어 수의 2배 (최소 min_workers개, 최대 max_workers개)
    return min(max(min_workers, int(cpu_count * 2)), max_workers)