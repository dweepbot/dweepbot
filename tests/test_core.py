import unittest
from dweepbot.core import main

class TestDweepBot(unittest.TestCase):
    def test_main(self):
        self.assertIsNone(main())

if __name__ == '__main__':
    unittest.main()