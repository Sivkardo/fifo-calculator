import utils
import pandas as pd
import time
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options


def generate_transaction_csv(filename):
    balance_sheets = []
    for sheet, header_index in zip(utils.SHEETS, utils.SHEET_TRANSACTION_START):
        balances = pd.read_excel(
            io=utils.BALANCES_PATH,
            sheet_name=sheet,
            skiprows=header_index - 1
        )

        # Remove all empty rows
        empty_row_index = balances['Date'].isna().idxmax()
        balances = balances.iloc[:empty_row_index]

        balance_sheets.append(balances)

    balances = pd.concat(balance_sheets)

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

        input_amount = transaction[utils.INPUT_AMOUNT]
        input_currency = transaction[utils.INPUT_CURR]
        output_amount = transaction[utils.OUTPUT_AMOUNT]
        output_currency = transaction[utils.OUTPUT_CURR]

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
            
        csv_row = (transaction[utils.DATE], transaction[utils.NOTE], 
                   input_amount, input_currency,
                   output_amount, output_currency)
        
        data.append(csv_row)
        
    pd.DataFrame(data).to_csv("{}.csv".format(filename), index=False, header=False)


def generate_fifo_output(path):

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
    file_input.send_keys(path)
    print("File uploaded...")

    # Wait for the processed file to download before closing browser
    time.sleep(utils.DOWNLOAD_WAIT_TIME)

    print("Quitting driver...")
    driver.quit()


def calculate_income_and_expenses(path):

    fifo_output = pd.read_csv(path)
    fifo_output['profit'] = pd.to_numeric(fifo_output['profit'])

    income = fifo_output['profit'].dropna()[fifo_output['profit'] > 0].sum()
    expenses = fifo_output['profit'].dropna()[fifo_output['profit'] < 0].sum()

    print("Prihod: ", income)
    print("Rashod: ", expenses)


def main():

    generate_csv = input("Generate csv from excel? (y/n): ")

    if generate_csv in ('y', 'Y'):
        filename = time.strftime("%Y%m%d-%H%M%S")
        generate_transaction_csv(filename)

        file_path = os.path.abspath(filename + ".csv")
        generate_fifo_output(path=file_path)

        fifo_output_path = utils.BROWSER_DOWNLOADS_PATH + os.sep + filename + "-FIFO.csv" 
        time.sleep(0.5)
        calculate_income_and_expenses(path=fifo_output_path)

    else:
        file_path = os.path.abspath(input("Please enter path to csv file: \n"))
        generate_fifo_output(path=file_path)
        
        filename = file_path.split(os.sep)[-1].split(".")[0]

        fifo_output_path = utils.BROWSER_DOWNLOADS_PATH + os.sep + filename + "-FIFO.csv" 
        time.sleep(0.5)
        calculate_income_and_expenses(path=fifo_output_path)


if __name__ == "__main__":
    main()



