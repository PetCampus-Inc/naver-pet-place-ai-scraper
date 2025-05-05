import logging
import colorlog
from functools import lru_cache

_initialized = False

def setup_logging(level=logging.INFO):
    global _initialized
    if _initialized:
        return
        
    # 이미 핸들러가 있는지 확인하고 중복 방지
    root = logging.getLogger()
    if root.handlers:
        _initialized = True
        return
        
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '[%(asctime)s - %(log_color)s%(levelname)s%(reset)s] \033[90m(%(filename)s:%(lineno)d)\033[0m %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        style='%'
    ))
    
    root.setLevel(level)
    root.addHandler(handler)

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    logging.getLogger('selenium').setLevel(logging.WARNING)

    _initialized = True

@lru_cache(maxsize=32)
def get_logger(name=None):
    """로거 인스턴스를 반환하는 함수 (캐싱 적용)"""
    setup_logging()
    return logging.getLogger(name)