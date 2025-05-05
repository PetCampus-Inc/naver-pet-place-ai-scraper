import pandas as pd
import time
from typing import List, Dict, Any
from lib.logger import get_logger


log = get_logger()

def dict_list_to_excel(dict_list: List[Dict[str, Any]], name: str, chunk_size: int = 1000):
    """딕셔너리 리스트를 엑셀 파일로 저장하는 함수"""

    try:
        name = f"{name}_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # 결과가 많을 경우 메모리 효율을 위해 청크 단위로 처리
        if len(dict_list) > chunk_size:
            writer = pd.ExcelWriter(name, engine='xlsxwriter')
            
            # 청크 단위로 나누어 데이터프레임 생성 및 저장
            for i in range(0, len(dict_list), chunk_size):
                chunk = dict_list[i:i+chunk_size]
                chunk_df = pd.DataFrame(chunk)
                
                # 첫 번째 청크면 헤더 포함, 아니면 헤더 제외
                chunk_df.to_excel(
                    writer, 
                    sheet_name='데이터', 
                    index=False,
                    startrow=(0 if i == 0 else writer.sheets['데이터'].max_row),
                    header=(i == 0)
                )
            
            writer.close()
        else:
            # 결과가 적을 경우 간단히 저장
            df = pd.DataFrame(dict_list)
            df.to_excel(name, index=False)
        
        log.info(f"엑셀 파일이 생성되었습니다: {name}")
    except Exception as e:
        log.error(f"결과 저장 중 오류 발생: {e}")
        # 에러 발생 시 CSV로 백업 저장 시도
        try:
            backup_file = f"backup_{name}_{time.strftime('%Y%m%d_%H%M%S')}.csv"
            pd.DataFrame(dict_list).to_csv(backup_file, index=False)
            log.info(f"백업 CSV 파일이 생성되었습니다: {backup_file}")
        except Exception as backup_error:
            log.error(f"백업 저장 중 오류 발생: {backup_error}")
    
    