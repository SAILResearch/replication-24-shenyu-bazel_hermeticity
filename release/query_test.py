import unittest
import release.query as release_query


class TestingQueryMethods(unittest.TestCase):

    def test_release_dates(self):
        release_dates = release_query.package_release_dates("libstdc++6")
        print(release_dates)
        #TODO add assertions




if __name__ == '__main__':
    unittest.main()
