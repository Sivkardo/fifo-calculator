import os

# Path to excel file with balance and transaction data
BALANCES_PATH = os.path.abspath('data/balances.xlsx')

# URL of Fifoator
FIFOATOR_URL = 'https://fifoator.com/'

# Browser
USER_BROWSER = "firefox"

# Seconds waiting for page to load
PAGE_LOAD_TIME = 1

# Seconds waiting for FIFO output to download
DOWNLOAD_WAIT_TIME = 0.2

# Download folder path
BROWSER_DOWNLOADS_PATH = os.path.abspath(os.environ["Download"])

# Interest transaction types
INTEREST_TRANS_TYPE = ("Interest", "Staking Rewards")

# Interest key word
INTEREST = "INTEREST"

# Column indices in excel file (first column = 1)
ORDER = 1
DATE = 2
TRANS_TYPE = 3
INPUT_CURR = 4
INPUT_AMOUNT = 5
OUTPUT_CURR = 6
OUTPUT_AMOUNT = 7
NOTE = 8
