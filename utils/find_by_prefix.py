def find_by_prefix(data: dict, prefix: str) -> dict:
    """딕셔너리에서 접두사로 시작하는 첫 번째 키의 값을 반환"""
    return next((v for k, v in data.items() if k.startswith(prefix)), None)

def find_by_prefix_all(data: dict, prefix: str) -> list[dict]:
    """딕셔너리에서 접두사로 시작하는 모든 키의 값을 반환"""
    return [v for k, v in data.items() if k.startswith(prefix)]