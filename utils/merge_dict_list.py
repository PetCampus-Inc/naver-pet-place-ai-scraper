def merge_dict_lists_by_key(key, base_list, additional_list):
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
            result_dict[item[key]] |= item  # Python 3.9+ union 연산자 활용
        elif key in item:
            result_dict[item[key]] = item
            
    return list(result_dict.values())



if __name__ == "__main__":
    base_list = [
        {'id': 1, 'name': 'A'},
        {'id': 2, 'name': 'B'},
    ]
    new_list = [{'id': 1, 'data': 'C'}, {'id': 2, 'data': 'D'}]
    print(merge_dict_lists_by_key('id', base_list, new_list))