Make sure you have Python ___3.11.3___ installed on your system before using pip to install packages. 
If you don't have Python installed, you can download it from the official Python website (https://www.python.org/downloads/). 
Once Python is installed, you can use pip to manage your Python packages.

Install Pandas:
Pandas is a powerful data manipulation and analysis library. You can install it using the following command: `pip install pandas`

Install UUID:
The uuid module is part of Python's standard library, so you don't need to install it separately.

Install OS:
The os module is also part of Python's standard library, so there is no need to install it separately.

1. `s3_report_download.sh` script is created to streamline the process of fetching AWS cost report data stored in an Amazon S3 bucket. It initiates a user prompt for specifying the start month and year, computes the corresponding date range, and subsequently retrieves the "DynaCostReport-00001.csv" file from the S3 bucket.

2. `split.py` script takes a dataset in CSV format and performs various data processing tasks. It filters, groups, and organizes the data, then saves the results as Excel files.

3. `print_total.py` script scans the current directory for Excel files (files with a .xlsx extension), calculates the total sum of values in the 'lineItem/UnblendedCost' column across all the Excel files. Finally, it prints the total unblended cost obtained by summing these values.
