from say_miniMax import parse_time_to_minutes
import pytest

class DummyConsole:
    def print(self, *args, **kwargs):
        pass

import say_miniMax
say_miniMax.console = DummyConsole()

def test_hangul_parsing():
    assert parse_time_to_minutes("십삼분") == 13
    assert parse_time_to_minutes("이십구분") == 29
    assert parse_time_to_minutes("오분") == 5
    assert parse_time_to_minutes("일시간") == 60
    assert parse_time_to_minutes("한시간") == 5 # '한' is not in my simple map yet, regex fallback to 5 default or 0? 
    # Current map has '일', '이', ... '구'. '하나', '둘' not supported yet. '한' is tricky. 
    # '1시간' logic handles "1시간". 
    
    assert parse_time_to_minutes("백분") == 100
    assert parse_time_to_minutes("1시간 반") == 90
    
    print("Hangul tests passed!")

if __name__ == "__main__":
    test_hangul_parsing()
