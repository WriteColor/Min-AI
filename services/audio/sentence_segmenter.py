"""services/audio/sentence_segmenter.py — Streaming sentence segmenter for TTS"""

class SentenceSegmenter:
    def __init__(self, min_segment_length: int = 3, target_length: int = 50):
        self._buffer = ""
        self._min_length = min_segment_length
        self._target_length = target_length

    def process(self, chunk: str) -> list[str]:
        self._buffer += chunk
        segments = []
        
        i = 0
        while i < len(self._buffer):
            c = self._buffer[i]
            
            # 1. Major sentence end characters: . ! ? \n
            if c in ".!?\n":
                # Check for floating numbers (e.g. 3.14) -> don't split
                if c == '.' and i > 0 and i < len(self._buffer) - 1 and self._buffer[i-1].isdigit() and self._buffer[i+1].isdigit():
                    i += 1
                    continue
                
                # Found major sentence boundary
                end_idx = i + 1
                # Consume trailing whitespace
                while end_idx < len(self._buffer) and self._buffer[end_idx] in " \t\r":
                    end_idx += 1
                
                segment = self._buffer[:end_idx].strip()
                if len(segment) >= self._min_length:
                    segments.append(segment)
                
                self._buffer = self._buffer[end_idx:]
                i = 0
                continue
            
            # 2. Minor punctuation (comma, semicolon, colon) only when segment is long enough
            if c in ",;:" and i >= self._target_length:
                end_idx = i + 1
                while end_idx < len(self._buffer) and self._buffer[end_idx] in " \t\r":
                    end_idx += 1
                
                segment = self._buffer[:end_idx].strip()
                if len(segment) >= self._min_length:
                    segments.append(segment)
                
                self._buffer = self._buffer[end_idx:]
                i = 0
                continue
                
            i += 1
            
        return segments

    def flush(self) -> list[str]:
        if not self._buffer:
            return []
        text = self._buffer.strip()
        self._buffer = ""
        if len(text) >= self._min_length:
            return [text]
        return []

    def reset(self):
        self._buffer = ""

    @property
    def pending(self) -> str:
        return self._buffer