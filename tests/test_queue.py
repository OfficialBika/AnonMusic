import unittest

from anony.helpers._dataclass import Track
from anony.helpers._queue import Queue


class QueueTests(unittest.TestCase):
    def test_empty_queue_next_is_none(self):
        queue = Queue()
        self.assertIsNone(queue.get_next(-100))

    def test_get_next_removes_current_and_returns_next(self):
        queue = Queue()
        first = Track(id="abcdefghijk", title="first")
        second = Track(id="lmnopqrstuv", title="second")
        queue.add(-100, first)
        queue.add(-100, second)
        self.assertIs(queue.get_next(-100), second)
        self.assertIs(queue.get_current(-100), second)

    def test_force_add_keeps_item_at_front(self):
        queue = Queue()
        current = Track(id="abcdefghijk", title="current")
        urgent = Track(id="lmnopqrstuv", title="urgent")
        queue.add(-100, current)
        queue.force_add(-100, urgent)
        self.assertIs(queue.get_current(-100), urgent)


if __name__ == "__main__":
    unittest.main()
