import utils
import pandas as pd
import time
import argparse
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options


def generate_transaction_csv(excel_path: str, sheet: str, header_row_index: int, filename: str):
    """
    Generates a CSV file from provided excel file.

    Args:
        excel_path (str): path to excel file
        sheet (str): sheet name
        header_row_index (int): row number of transaction header
        filename (str): output CSV filename
    """

    balances = pd.read_excel(
            io=excel_path,
            sheet_name=sheet,
            skiprows=header_row_index - 1
        )
    
    empty_row_index = balances['Date'].isna().idxmax()
    balances = balances.iloc[:empty_row_index]

    # Format the date from excel file to 'YYYY-MM-DD'
    balances['Date'] = pd.to_datetime(balances['Date'])
    balances['Date'] = balances['Date'].dt.strftime('%Y-%m-%d')

    # Map the fiat currency to a proper ISO 4217 format
    currency_mapping = {
        'EURO (fiat)': 'EUR',
    }

    balances['Input Currency'] = balances['Input Currency'].replace(currency_mapping)
    balances['Output Currency'] = balances['Output Currency'].replace(currency_mapping)

    data = []
    for transaction in balances.itertuples():

        # (???)
        #if transaction[utils.TRANS_TYPE] == "Lock":
        #   continue

        note = transaction[utils.NOTE]
        input_amount = transaction[utils.INPUT_AMOUNT]
        input_currency = transaction[utils.INPUT_CURR]
        output_amount = transaction[utils.OUTPUT_AMOUNT]
        output_currency = transaction[utils.OUTPUT_CURR]

        if transaction[utils.TRANS_TYPE] in utils.INTEREST_TRANS_TYPE:
            note += (" - " + utils.INTEREST)
        if input_currency == output_currency:
            input_amount = input_amount - output_amount
            output_amount = 0
            output_currency = "EUR"

        if input_currency == "EMPTY":
            input_amount = 0
            input_currency = "EUR"

        if output_currency == "EMPTY":
            output_amount = 0
            output_currency = "EUR"
            
        csv_row = (transaction[utils.DATE], note, 
                   input_amount, input_currency,
                   output_amount, output_currency)
        
        data.append(csv_row)
        
    pd.DataFrame(data).to_csv("{}.csv".format(filename), index=False, header=True)



def generate_fifo_output(csv_path: str):
    """
    Generates FIFO output using provided CSV.
    The function calls the FIFO app and uploads the provided CSV file.
    FIFO app automatically downloads the file to the default downloads directory.

    Args:
        path (str): path to CSV file
    """

    if utils.USER_BROWSER == "safari":
        # headless mode not available for safari ¯\_(ツ)_/¯
        driver = webdriver.Safari()
    elif utils.USER_BROWSER == "firefox":
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        driver = webdriver.Firefox(options=firefox_options)

    driver.get(utils.FIFOATOR_URL)

    # Wait for the page to fully load
    time.sleep(utils.PAGE_LOAD_TIME)

    # Accept the "terms of service"
    checkbox = driver.find_element(By.ID, 'terms')
    checkbox.click()

    file_input = driver.find_element(By.ID, 'file')
    file_input.send_keys(csv_path)

    # Wait for the processed file to download before closing browser
    time.sleep(utils.DOWNLOAD_WAIT_TIME)

    driver.quit()


def calculate_income_and_expenses(path: str):
    """
    Calculates income and expenses using FIFO app output file.

    Args:
        path (str): path to FIFO app output
    """

    fifo_output = pd.read_csv(path)
    fifo_output['profit'] = pd.to_numeric(fifo_output['profit'])

    income = fifo_output['profit'].dropna()[fifo_output['profit'] > 0].sum()
    expenses = fifo_output['profit'].dropna()[fifo_output['profit'] < 0].sum()

    print("Prihod: ", income)
    print("Rashod: ", expenses)

def calculate_unspent_interest(path: str):
    """
    Calculates unspent interest.

    Args:
        path (str): path to FIFO app output
    """

    interest = {}

    csv = pd.read_csv(path)
    for _, row in csv.iterrows():
        date = row['datum']
        in_currency = row["početna valuta"]
        in_amount = row["početni iznos"]
        out_currency = row['završna valuta']
        out_amount = row['završni iznos']

        acquire_date = row['datum nabave']

        if utils.INTEREST in row['opis']:
            if date not in interest:
                interest[date] = {}
            if out_currency not in interest[date]:
                interest[date][out_currency] = 0 
            interest[date][out_currency] += out_amount

        if acquire_date in interest and in_currency in interest[acquire_date]:
            # Do not count locking tokens
            if in_amount == out_amount:
                continue
            #print(str(acquire_date) + str(in_currency) + ", " + str(in_amount))

            # Tokens from other transactions are being spent
            if interest[acquire_date][in_currency] - in_amount < 0:
                continue
            interest[acquire_date][in_currency] -= in_amount

    unspent_interest = {}
    for date, v in interest.items():
        for token, value in v.items():
            if token not in unspent_interest:
                unspent_interest[token] = value
            else:
                unspent_interest[token] += value
   
    print("Unspent tokens earned from interest:")
    for token, value in unspent_interest.items():
            print("  " + token + ": " + str(value))

        


def concatenate_csv(csv_paths: list, filename: str):
    """
        Concatenates all CSV files in given order.

    Args:
        csv_paths (list): paths to CSV files
    """

    data = []
    for path in csv_paths:
        path = os.path.abspath(path)
        csv = pd.read_csv(path)
        data.append(csv)

    data = pd.concat(data, axis=0, ignore_index=True)
    pd.DataFrame(data).to_csv("{}.csv".format(filename), index=False, header=True)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--fifo', action="store_true", help="Generates FIFO output and calculates income and expenses.")
    parser.add_argument('-g', '--generate', action="store_true", help='Generates csv from excel file (used as input to fifoator app).')

    parser.add_argument('-c', '--concatenate', action="store_true", help='Concatenates multiple csv files into a single file.')
    parser.add_argument('-s', '--sheet', nargs='+', help="Single or multiple sheet names. Make sure the order of sheets corresponds to header row index number.")
    parser.add_argument('-r', '--row', nargs='+', help='Row index or indices of transaction header in excel file. Make sure the order of indices corresponds to sheet name.')

    parser.add_argument('-e', '--excel', help='Path to excel file.')
    parser.add_argument('-v', '--csv', nargs='+', help='Path(s) to csv file(s).')
    parser.add_argument('-o', '--output', help='Name of output CSV file.')

    args = parser.parse_args()


    # If user didn't provide an output name, assign the current timestamp to output name
    if args.output:
        out_name = args.output
    else:
        out_name = time.strftime("%Y%m%d-%H%M%S")
    

    # User wants FIFO output, including income and expense data
    if args.fifo:

        # Check if excel file is provided, generate CSV files from provided excel file
        if args.excel:

            # Check if needed arguments are provided (SHEET + ROW) and their length is equal
            if not args.sheet:
                raise Exception("No sheet names were provided!")
            
            if not args.row:
                raise Exception("Index of header row wasn't provided!")
            
            if len(args.sheet) != len(args.row):
                raise Exception("Number of sheets and indices should be equal: {} != {}".format(len(args.sheet), len(args.row)))
            
            # Generate needed CSV files
            files = []
            for sheet, index, file_num in zip(args.sheet, args.row, range(len(args.sheet))):
                filename = out_name + str(file_num)
                generate_transaction_csv(excel_path=args.excel, sheet=sheet, header_row_index=int(index), filename=filename)
                files.append(filename + ".csv")

        # Check if instead of an excel file, a CSV file is provided
        elif args.csv:
            files = args.csv

        # Concatenate CSV files into a single file that will be fed into FIFO app
        concatenate_csv(csv_paths=files, filename=out_name)

        # Generate FIFO output
        file_path = os.path.abspath(out_name + ".csv")
        generate_fifo_output(file_path)

        # Calculate income and expenses
        fifo_output_path = utils.BROWSER_DOWNLOADS_PATH + os.sep + out_name + "-FIFO.csv" 
        calculate_income_and_expenses(path=fifo_output_path)
        calculate_unspent_interest(path=fifo_output_path)
            

    # User only wants to generate CSV file from excel file
    elif args.generate:

        # Check if excel file is provided, generate CSV files from provided excel file
        if args.excel:

            # Check if needed arguments are provided (SHEET + ROW) and their length is equal
            if not args.sheet:
                raise Exception("No sheet names were provided!")
            
            if not args.row:
                raise Exception("Index of header row wasn't provided!")
            
            if len(args.sheet) != len(args.row):
                raise Exception("Number of sheets and indices should be equal: {} != {}".format(len(args.sheet), len(args.row)))
            
            # Generate needed CSV files
            files = []
            for sheet, index, file_num in zip(args.sheet, args.row, range(len(args.sheet))):
                filename = out_name + str(file_num)
                generate_transaction_csv(excel_path=args.excel, sheet=sheet, header_row_index=int(index), filename=filename)
                files.append(filename + ".csv")

            if args.concatenate:
                # Concatenate CSV files into a single file
                concatenate_csv(csv_paths=files, filename=out_name)

        else:
            raise Exception("Missing excel file path!")

    # User only wants to concatenate provided CSV files
    elif args.concatenate:
        if not args.csv:
            raise Exception("Missing CSV file paths!")
        
        # Concatenate CSV files into a single file
        concatenate_csv(csv_paths=args.csv, filename=out_name)


if __name__ == "__main__":
    #main()
    calculate_unspent_interest("test.csv")



