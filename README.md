# FIFO Calculator

## Requirements
 * Run `pip install -r requirements.txt` to download needed packages 

## Arguments
 * `-g`, `--generate`: Generates CSV file from provided excel file (generated file is formatted for FIFO app input).
 * `-c`, `--concatenate`: Concatenates multiple csv files into a single file. Used if user has multiple CSV files which he wants to concatenate.
 * `-s`, `--sheet`: Single or multiple sheet names from provided excel file. Make sure the order of sheets corresponds to header row index number.
 * `-i`, `--index`: Row index or indices of transaction header in excel file. Make sure the order of indices corresponds to sheet names.
 * `-e`, `--excel`: Path to excel file.
 * `-v`, `--csv`: Path(s) to csv file(s). Make sure the order in which the files are provided is chronological.
 * `-o`, `--output`: Name of output CSV file. If the output name is not provided, a timestamp will be used instead.
 * `-t`, `--temporary`: Keep temporary files (CSV files that are concatenated into the final file).
 * `-u`, `--unspent`: Calculates unspent tokens received from interest (takes FIFO output as input file).
## Usage
 * Run the program by running the `main.py` script with arbitrary arguments.
 * The program has 3 main usages:
    * generating CSV files from provided excel file: `-g` argument
    * concatenating CSV files: `-c` argument (can also be used with `-g`)
    * calculating unspent tokens received from interest: `-u` argument
## Examples
 * `python main.py -g -e data.xlsx -s 1998 1999 -r 152 50 -c`
 * In the above line, with `-g` we tell the program we only want to generate a CSV file(s) from provided excel file.
 The program will generate 3 CSV files in this instance, one for each sheet and finally a concatenated file because the flag `-c` was used. <br/><br/>
 * `python main.py -c -v file1.csv file2.csv file3.csv -o joined`
 * In the above line, since only the `-c` argument is given, the program will concatenate the given files `-v file1.csv file2.csv file3.csv` and create
 output file `joined.csv`.