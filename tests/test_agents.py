from agents.memory_manager import MemoryManager


def test_memory_manager_add():
    mm = MemoryManager(max_items=2)
    mm.add("user", "hello")
    mm.add("assistant", "world")
    mm.add("system", "overflow")
    hist = mm.get_history()
    assert len(hist) == 2
