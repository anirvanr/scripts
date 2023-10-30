#!/bin/bash

# Define your S3 bucket and folder paths
bucket="dyna-detailedcostreport"
folder="DynaCost/DynaCostReport"

# Read the user's input for the start month and year
read -p "Enter the start month (MM): " user_month
read -p "Enter the start year (YYYY): " user_year

# Validate the user's input for month and year
if ! [[ "$user_month" =~ ^[0-9]{2}$ && "$user_year" =~ ^[0-9]{4}$ ]]; then
  echo "Invalid input for month or year. Please use the MM and YYYY format."
  exit 1
fi

# Calculate the start and end dates using Python
startdate="${user_year}${user_month}01"
enddate=$(python -c "from datetime import datetime, timedelta; start = datetime.strptime('$startdate', '%Y%m%d'); end = (start + timedelta(days=32)).replace(day=1); print(end.strftime('%Y%m%d'))")

# Build the S3 object path
s3_path="s3://$bucket/$folder/$startdate-$enddate/"

# Get the manifest JSON file
aws s3 cp $s3_path"DynaCostReport-Manifest.json" .

# Parse the JSON to extract reportKeys
reportKeys=$(jq -r '.reportKeys[]' DynaCostReport-Manifest.json)

# Loop through the reportKeys and download the CSV.gz files
for reportKey in $reportKeys; do
  aws s3 cp s3://$bucket/$reportKey .
done

# Extract file 
gzip -d "DynaCostReport-00001.csv.gz"

# Delete the manifest file
rm "DynaCostReport-Manifest.json" 
