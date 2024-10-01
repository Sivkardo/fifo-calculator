import utils
import pandas as pd
import time
import argparse
import os
import sys

def graceful_exit(message: str):
    """
    Exits the program with a message.

    Args:
        message (str): message to be printed
    """

    print(message)
    sys.exit(1)

def validate_transaction_data(transaction: pd.DataFrame, sheet: str):
    """Validates given transaction by checking for specific cases.
        It checks for empty values, negative values and incorrect formating.
    Args:
        transaction (Pandas): transaction tuple
        sheet (str): sheet name

    """

    order = transaction[utils.ORDER]
    note = transaction[utils.NOTE]
    date = transaction[utils.DATE]
    transaction_type = transaction[utils.TRANS_TYPE]
    input_amount = transaction[utils.INPUT_AMOUNT]
    input_currency = transaction[utils.INPUT_CURR]
    output_amount = transaction[utils.OUTPUT_AMOUNT]
    output_currency = transaction[utils.OUTPUT_CURR]

    # TODO (avoid so many ifs?)
    # Checks for missing values
    if pd.isna(date):
        graceful_exit("DATE is missing in transaction order {}, sheet {}".format(order, sheet))
    if pd.isna(transaction_type):
        graceful_exit("TRANSACTION TYPE is missing in transaction order {}, sheet {}".format(order, sheet))
    if pd.isna(input_currency):
        graceful_exit("INPUT CURRENCY is missing in transaction order {}, sheet {}".format(order, sheet))
    if pd.isna(input_amount):
        graceful_exit("INPUT AMOUNT is missing in transaction order {}, sheet {}".format(order, sheet))
    if pd.isna(output_currency):
        graceful_exit("OUTPUT CURRENCY is missing in transaction order {}, sheet {}".format(order, sheet))
    if pd.isna(output_amount):
        graceful_exit("OUTPUT AMOUNT is missing in transaction order {}, sheet {}".format(order, sheet))
    if pd.isna(note):
        graceful_exit("NOTE is missing in transaction order {}, sheet {}".format(order, sheet))

    # Check if input and output amounts are numeric values
    try:
        pd.to_numeric(input_amount)
    except:
        graceful_exit("INPUT CURRENCY is not a numeric value in transaction order {}, sheet {}".format(order, sheet))
    try:
        pd.to_numeric(output_amount)
    except:
        graceful_exit("OUTPUT CURRENCY is not a numeric value in transaction order {}, sheet {}".format(order, sheet))

    # Checks for negative values
    if input_amount < 0:
        graceful_exit("INPUT AMOUNT is negative in transaction {}, sheet {}".format(order, sheet))
    if output_amount < 0:
        graceful_exit("OUTPUT AMOUNT is negative in transaction {}, sheet {}".format(order, sheet))

    # Check if date is in correct format, override default exception for readability
    try:
        pd.to_datetime(date)
    except:
        graceful_exit("Incorrect format of DATE in transaction order {}, sheet {}".format(order, sheet))


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

    for transaction in balances.itertuples():
        validate_transaction_data(transaction=transaction, sheet=sheet)

    # Format the date from excel file to 'YYYY-MM-DD'
    balances['Date'] = pd.to_datetime(balances['Date'])
    balances['Date'] = balances['Date'].dt.strftime('%Y-%m-%d')

    # Map the fiat currency to a proper ISO 4217 format
    currency_mapping = {
        'EURO (fiat)': 'EUR',
        'USD (fiat)': 'USD',
    }

    balances['Input Currency'] = balances['Input Currency'].replace(currency_mapping)
    balances['Output Currency'] = balances['Output Currency'].replace(currency_mapping)

    data = []
    for transaction in balances.itertuples():

        order = transaction[utils.ORDER]
        note = transaction[utils.NOTE]
        date = transaction[utils.DATE]
        input_amount = transaction[utils.INPUT_AMOUNT]
        input_currency = transaction[utils.INPUT_CURR]
        output_amount = transaction[utils.OUTPUT_AMOUNT]
        output_currency = transaction[utils.OUTPUT_CURR]

        # Check if dates are in ascending order
        if order == 1:
            previous_date = date
            previous_order = order
        else:
            if previous_date > date:
                graceful_exit("DATE in transaction {} is smaller than in transaction {}, sheet {}!".format(order, previous_order, sheet))
            previous_date = date
            previous_order = order
            
        

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
            
        csv_row = (date, note, 
                   input_amount, input_currency,
                   output_amount, output_currency)
        
        data.append(csv_row)
        
    pd.DataFrame(data).to_csv("{}.csv".format(filename), index=False, header=True)


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

    parser.add_argument('-g', '--generate', action="store_true", help='Generates csv from excel file (used as input to fifoator app).')
    parser.add_argument('-u', '--unspent', help="Calculates unspent tokens received from interest (takes FIFO output as input file)")

    parser.add_argument('-c', '--concatenate', action="store_true", help='Concatenates multiple csv files into a single file. Used if user has multiple CSV files which he wants to concatenate.')
    parser.add_argument('-s', '--sheet', nargs='+', help="Single or multiple sheet names. Make sure the order of sheets corresponds to header row index number.")
    parser.add_argument('-r', '--row', nargs='+', help='Row index or indices of transaction header in excel file. Make sure the order of indices corresponds to sheet name.')

    parser.add_argument('-e', '--excel', help='Path to excel file.')
    parser.add_argument('-v', '--csv', nargs='+', help='Path(s) to csv file(s).')
    parser.add_argument('-o', '--output', help='Name of output CSV file.')
    parser.add_argument('-t', '--temporary', help="Keep temporary files (CSV files that are concatenated into the final file).")

    args = parser.parse_args()


    # If user didn't provide an output name, assign the current timestamp to output name
    if args.output:
        out_name = args.output
    else:
        out_name = time.strftime("%Y%m%d-%H%M%S")
    
            
    # User only wants to generate CSV file from excel file
    if args.generate:

        # Check if excel file is provided, generate CSV files from provided excel file
        if args.excel:

            # Check if needed arguments are provided (SHEET + ROW) and their length is equal
            if not args.sheet:
                graceful_exit("No sheet names were provided!")
            
            if not args.row:
                graceful_exit("No index of header row was provided!")
            
            if len(args.sheet) != len(args.row):
                graceful_exit("Number of sheets and indices should be equal: {} != {}".format(len(args.sheet), len(args.row)))
            
            # Generate needed CSV files
            files = []
            for sheet, index, file_num in zip(args.sheet, args.row, range(len(args.sheet))):
                filename = out_name + str(file_num)
                generate_transaction_csv(excel_path=args.excel, sheet=sheet, header_row_index=int(index), filename=filename)
                files.append(filename + ".csv")

            
            # Concatenate CSV files into a single file
            concatenate_csv(csv_paths=files, filename=out_name)
            if not args.temporary:
                for file in files:
                    os.remove(file)

        else:
            graceful_exit("Missing excel file path!")

    # User only wants to concatenate provided CSV files
    elif args.concatenate:
        if not args.csv:
            graceful_exit("Missing CSV file paths!")
        
        # Concatenate CSV files into a single file
        concatenate_csv(csv_paths=args.csv, filename=out_name)

    elif args.unspent:
        calculate_unspent_interest(args.unspent)


if __name__ == "__main__":
    main()



