from say_miniMax import parse_time_to_minutes
import pytest

# Dummy console for testing if needed, though we just imported the function
class DummyConsole:
    def print(self, *args, **kwargs):
        pass

import say_miniMax
say_miniMax.console = DummyConsole()

def test_parse_time():
    assert parse_time_to_minutes("10분") == 10
    assert parse_time_to_minutes("13분") == 13
    assert parse_time_to_minutes("1시간 반") == 90
    assert parse_time_to_minutes("1시간반") == 90
    assert parse_time_to_minutes("1시간 30분") == 90
    assert parse_time_to_minutes("29분") == 29
    assert parse_time_to_minutes("120분") == 120
    # assert parse_time_to_minutes("반분") == 5 # Removed ambiguous test case
    
    assert parse_time_to_minutes("30초") == 0.5
    
    print("All tests passed!")

if __name__ == "__main__":
    test_parse_time()
