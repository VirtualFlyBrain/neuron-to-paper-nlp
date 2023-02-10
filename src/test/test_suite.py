import unittest

loader = unittest.TestLoader()
suite = loader.discover(start_dir='./', pattern='*_test.py')
# tests that only can run locally (due to memory and time constraints) not on CI action
local_suite = loader.discover(start_dir='./', pattern='*_localtest.py')
alltests = unittest.TestSuite((suite, local_suite))

runner = unittest.TextTestRunner()
runner.run(alltests)
