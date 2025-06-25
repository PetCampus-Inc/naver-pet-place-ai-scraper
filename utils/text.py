import re


def text_to_sentence(text: str) -> list[str]:
    """
    텍스트의 구두점을 기준하여 문장으로 분리합니다. 공백+단어+구두점 패턴이 있는 경우만 분리합니다.

    Example:
        `text` - "안녕하세요. 장성남입니다."\n
        `result` - ["안녕하세요.", "장성남입니다."]
    """

    # 공백이 없으면 문장이 아니므로 그대로 반환
    if ' ' not in text: return [text]
    
    # 문장 패턴(단어+공백+단어+구두점)이 있는지 확인
    has_sentence_pattern = bool(re.search(r'\S+\s+\S+[.!?]', text))
    if not has_sentence_pattern: return [text]
    
    # 문장 분리
    sentences = []
    current_position = 0
    
    pattern = r'([.!?])(?:\s+|\Z)'
    
    for match in re.finditer(pattern, text):
        end_pos = match.end(1)  # 구두점 위치
        
        # 구두점 전까지의 텍스트 + 구두점
        sentence = text[current_position:end_pos].strip()
        
        # '가.나.다.라'와 같은 패턴 확인 (공백 없이 구두점으로만 연결된 단어인 경우)
        if ' ' in sentence:  # 공백이 있으면 일반 문장으로 간주
            sentences.append(sentence)
            current_position = end_pos
    
    # 남은 부분 처리
    if current_position < len(text):
        remaining = text[current_position:].strip()
        if remaining:
            sentences.append(remaining)
    
    return sentences

def remove_duplicate_texts(texts: list[str]) -> list[str]:
    """텍스트 리스트에서 중복된 내용을 제거합니다."""
    results = []
    processed = set()
    
    for text in texts:
        norm_text = re.sub(r'\s+', '', text.lower())

        # 빈 문자열은 대상에서 제외
        if not norm_text: continue

        # 이미 처리했거나 다른 텍스트에 완전히 포함되는 경우 제외
        is_contained_in_others = False
        
        for other in texts:
            if text == other: continue  # 자기 자신은 비교 대상에서 제외
                
            other_norm = re.sub(r'\s+', '', other.lower())
            
            # 현재 텍스트가 다른 텍스트에 포함되어 있는지 검사
            if norm_text != other_norm and norm_text in other_norm:
                is_contained_in_others = True
                break
                
        # 다른 텍스트에 포함되어 있지 않고, 아직 처리하지 않은 경우에만 추가
        if not is_contained_in_others and norm_text not in processed:
            results.append(text)
            processed.add(norm_text)
    
    return results