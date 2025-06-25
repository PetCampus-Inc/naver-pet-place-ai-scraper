from typing import List

def merge_dict_lists(key, base_list, additional_list) -> List[dict]:
    """
    키를 기준으로 두 딕셔너리 리스트를 병합하는 함수
    
    Args:
        key: 병합 기준이 되는 키
        base_list: 기본 딕셔너리 리스트
        additional_list: 추가할 딕셔너리 리스트
        
    Returns:
        list: 병합된 딕셔너리 리스트
    """
    # 딕셔너리 컴프리헨션으로 기본 리스트의 딕셔너리들 저장
    result_dict = {item[key]: item for item in base_list if key in item}
    
    # 딕셔너리 메소드 활용해 추가 리스트 병합
    for item in additional_list:
        if key in item and item[key] in result_dict:
            result_dict[item[key]] |= item
        elif key in item:
            result_dict[item[key]] = item
            
    return list(result_dict.values())

def pick_fields(dict, keys):
    """
    딕셔너리에서 특정 키들만 선택하여 새로운 딕셔너리를 반환하는 함수

    Args:
        `dict`: 타겟 딕셔너리
        `keys`: 선택할 키들

    Returns:
        `dict`: 선택된 키들만 포함하는 새로운 딕셔너리
    """
    return {k: dict[k] for k in keys if k in dict}

def omit_fields(dict, keys):
    """
    딕셔너리에서 특정 키들을 제외하고 새로운 딕셔너리를 반환하는 함수

    Args:
        `dict`: 타겟 딕셔너리
        `keys`: 제외할 키들

    Returns:
    """
    return {k: dict[k] for k in dict if k not in keys}