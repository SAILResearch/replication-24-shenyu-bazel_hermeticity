import logging

import cirunner.installed_tools
import release.process
from data_process.process import process_data
import externalmanaged.search
from visualization import visualize

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p')

    data_path = "data/"

    # release.process.process_packages(data_path)
    # cirunner.installed_tools.process_installed_tools(data_path)
    # externalmanaged.search.identify_package_for_projects(data_path)
    # process_data(data_path)
    visualize.visualize(data_path)
