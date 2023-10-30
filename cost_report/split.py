import pandas as pd
import uuid
import os

# Load the original CSV file
data = pd.read_csv('DynaCostReport-00001.csv', low_memory=False)

# Filter rows where 'product/servicename' is blank and keep only specific columns
file1 = data.loc[data['product/servicename'].isna(), ['product/ProductName', 'lineItem/UnblendedCost']]

# Replace 'product/ProductName' with 'Tax' if it doesn't contain 'Amazon Registrar'
file1['product/ProductName'] = file1['product/ProductName'].apply(lambda x: 'Tax' if 'Amazon Registrar' not in x else x)

# Aggregate 'lineItem/UnblendedCost' for duplicates in 'product/ProductName'
aggregated_df = file1.groupby('product/ProductName')['lineItem/UnblendedCost'].sum().reset_index()

# Add a new column 'product/region' with the value 'global' as the second column
aggregated_df.insert(1, 'product/region', 'global')

# Save the result to 'tax_registrar.xlsx'
output_file = 'tax_registrar.xlsx'
aggregated_df.to_excel(output_file, index=False)


# Keep specified columns and filter product/servicename containing Amazon Elastic Compute Cloud
file2 = data[data['product/servicename'].str.contains('Amazon Elastic Compute Cloud', na=False)]

selected_columns = [
    'product/servicename', 'product/region', 'lineItem/ProductCode',
    'lineItem/ResourceId', 'lineItem/UnblendedCost', 'lineItem/LineItemDescription',
    'product/location', 'resourceTags/user:Environment', 'resourceTags/user:KubernetesCluster',
    'resourceTags/user:Name', 'resourceTags/user:Project', 'resourceTags/user:Role',
    'lineItem/Operation', 'product/group', 'product/usagetype', 'product/productFamily'
]

file2 = file2[selected_columns]

# Save the selected data to an Excel file named 'ec2.xlsx'
file2.to_excel('ec2.xlsx', index=False)

# Filter rows where lineItem/Operation is "NatGateway," group by 'product/location,' and sum 'lineItem/UnblendedCost'
ec2 = pd.read_excel('ec2.xlsx')
nat_gateway = ec2[ec2['lineItem/Operation'] == 'NatGateway']
nat_gateway_grouped = nat_gateway.groupby('product/location')['lineItem/UnblendedCost'].sum().reset_index()
nat_gateway_grouped.rename(columns={'lineItem/Operation': 'product/group'}, inplace=True)
nat_gateway_grouped.sort_values('product/location', inplace=True)
nat_gateway_grouped.to_excel('nat_gateway_ec2.xlsx', index=False)

# Replace "ElasticIP:Address" with "Elastic IP Address" in the 'product/group' column and perform further operations
ec2['product/group'] = ec2['product/group'].str.replace('ElasticIP:Address', 'Elastic IP Address')

# Keep the required columns and rearrange the column order
ec2_eip = ec2[['product/group', 'product/location', 'lineItem/UnblendedCost']]
ec2_eip = ec2_eip[ec2_eip['product/group'] == 'Elastic IP Address']
eip_grouped = ec2_eip.groupby('product/location')['lineItem/UnblendedCost'].sum().reset_index()
eip_grouped.sort_values('product/location', inplace=True)
eip_grouped.to_excel('eip_ec2.xlsx', index=False)

# Keep columns, filter rows, and perform aggregation
ec2_ebs = ec2[['lineItem/UnblendedCost', 'product/location', 'product/usagetype']]
ec2_ebs_filtered = ec2_ebs.dropna(subset=['product/usagetype'])
ec2_ebs = ec2_ebs[ec2_ebs['product/usagetype'].str.contains('EBS')]
ec2_ebs.drop(columns=['product/usagetype'], inplace=True)
ec2_ebs['product/group'] = 'EBS Volume'
ebs_grouped = ec2_ebs.groupby('product/location')['lineItem/UnblendedCost'].sum().reset_index()
ebs_grouped.to_excel('ebs_ec2.xlsx', index=False)

# Drop specified rows from the 'ec2' DataFrame
ec2.drop(ec2[ec2['lineItem/Operation'] == 'NatGateway'].index, inplace=True)
ec2.drop(ec2[ec2['product/group'] == 'Elastic IP Address'].index, inplace=True)
ec2.dropna(subset=['product/usagetype'], inplace=True)
ec2.drop(ec2[ec2['product/usagetype'].str.contains('EBS')].index, inplace=True)

# Save the cleaned 'ec2' DataFrame to 'ec2_new.xlsx' and delete 'ec2.xlsx'
ec2.to_excel('ec2_new.xlsx', index=False)

if os.path.exists('ec2.xlsx'):
    os.remove('ec2.xlsx')

# File 3: Keep specified columns, filter product/servicename, aggregate lineItem/UnblendedCost, and sort data by product/region
file3 = data[data['product/servicename'].str.contains('.+') & ~data['product/servicename'].str.contains('Amazon Elastic Compute Cloud', na=False)]
file3 = file3[['lineItem/UnblendedCost', 'product/servicename', 'product/region']]
file3 = file3.groupby(['product/servicename', 'product/region'])['lineItem/UnblendedCost'].sum().reset_index()
file3 = file3.sort_values(by='product/region')
file3.rename(columns={'product/servicename': 'product/group'}, inplace=True)
file3.to_excel('services.xlsx', index=False)

# Add 'product/group' column to 'nat_gateway_ec2.xlsx'
nat_gateway_ec2 = pd.read_excel('nat_gateway_ec2.xlsx')
nat_gateway_ec2.insert(0, 'product/group', 'Nat Gateway')
nat_gateway_ec2.to_excel('nat_gateway_ec2.xlsx', index=False)

# Add 'product/group' column to 'ebs_ec2.xlsx'
ebs_ec2 = pd.read_excel('ebs_ec2.xlsx')
ebs_ec2.insert(0, 'product/group', 'EBS Volume')
ebs_ec2.to_excel('ebs_ec2.xlsx', index=False)

# Add 'product/group' column to 'eip_ec2.xlsx'
eip_ec2 = pd.read_excel('eip_ec2.xlsx')
eip_ec2.insert(0, 'product/group', 'Elastic IP Address')
eip_ec2.to_excel('eip_ec2.xlsx', index=False)

# Load the 'services.xlsx' file
services = pd.read_excel('services.xlsx')

# Define the region mapping
region_mapping = {
    "ap-south-1": "Asia Pacific (Mumbai)",
    "eu-north-1": "Europe (Stockholm)",
    "eu-west-3": "Europe (Paris)",
    "eu-west-2": "Europe (London)",
    "eu-west-1": "Europe (Ireland)",
    "ap-northeast-3": "Asia Pacific (Osaka)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ca-central-1": "Canada (Central)",
    "sa-east-1": "South America (Sao Paulo)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "eu-central-1": "Europe (Frankfurt)",
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "global": "Global"
}

# Replace the 'product/region' values with the region mapping
services['product/location'] = services['product/region'].map(region_mapping)

# Drop the original 'product/region' column
services.drop(columns=['product/region'], inplace=True)

# Save the modified DataFrame to 'services.xlsx'
services.to_excel('services.xlsx', index=False)

# Load the input Excel file
input_file = "ec2_new.xlsx"
df = pd.read_excel(input_file)

# Map region codes to human-readable names
df['product/region'] = df['product/region'].map(region_mapping)

# Filter rows based on different conditions and aggregate lineItem/UnblendedCost
# Part 1: "ElasticIP:AdditionalAddress"
part1_df = df[df['product/group'].str.contains('ElasticIP:AdditionalAddress', case=False, na=False)]
part1_df = part1_df.groupby(['product/group', 'product/region'])['lineItem/UnblendedCost'].sum().reset_index()
part1_df.rename(columns={'product/group': 'product/group', 'lineItem/UnblendedCost': 'lineItem/UnblendedCost'}, inplace=True)
part1_df.to_excel("AdditionalAddress.xlsx", index=False)

# Part 2: "T3CPUCredits"
part2_df = df[df['lineItem/Operation'].str.contains("T3CPUCredits")]
part2_df = part2_df.groupby(['product/region', 'lineItem/Operation'])['lineItem/UnblendedCost'].sum().reset_index()
part2_df.rename(columns={'lineItem/Operation': 'product/group'}, inplace=True)
part2_df = part2_df[['product/group', 'product/region', 'lineItem/UnblendedCost']]
part2_df.to_excel("T3CPUCredits.xlsx", index=False)

# List of files to merge
file_list = ['eip_ec2.xlsx', 'ebs_ec2.xlsx', 'nat_gateway_ec2.xlsx', 'services.xlsx', 'AdditionalAddress.xlsx', 'T3CPUCredits.xlsx']

# Initialize an empty DataFrame for merging
merged_data = pd.DataFrame()

for file in file_list:
    if os.path.exists(file):
        data_to_merge = pd.read_excel(file)
        # Rename the 'product/location' column to 'product/region'
        data_to_merge.rename(columns={'product/location': 'product/region'}, inplace=True)
        merged_data = pd.concat([merged_data, data_to_merge], ignore_index=True)
        os.remove(file)

# Save the merged data to 'others.xlsx'
merged_data.to_excel('others.xlsx', index=False)

# Read the data from the Excel file
data = pd.read_excel('others.xlsx')

# Sort the data by the 'product/region' column
sorted_data = data.sort_values(by='product/region')

# Filter and keep only the rows where 'lineItem/UnblendedCost' is not equal to "0"
filtered_data = sorted_data[sorted_data['lineItem/UnblendedCost'] != 0]

# Save the filtered and sorted data back to 'others.xlsx' without the index
filtered_data.to_excel('others.xlsx', index=False)


# Load the input Excel file
input_file = "ec2_new.xlsx"
df = pd.read_excel(input_file)

# Filter rows to exclude "AssociateAddressVPC" and "T3CPUCredits" in "lineItem/Operation"
filtered_df = df[~df['lineItem/Operation'].isin(["AssociateAddressVPC", "T3CPUCredits"])]

# Save the filtered result to a new Excel file
output_file = "ec2_instance.xlsx"
filtered_df.to_excel(output_file, index=False)

# Delete the original file if it exists
if os.path.exists(input_file):
    os.remove(input_file)

# EC2

input_file = "ec2_instance.xlsx"
df = pd.read_excel(input_file)

# Select the columns to copy
selected_columns = df[[
    'lineItem/ProductCode',
    'lineItem/ResourceId',
    'lineItem/UnblendedCost',
    'lineItem/LineItemDescription',
    'product/location',
    'resourceTags/user:Environment',
    'resourceTags/user:KubernetesCluster',
    'resourceTags/user:Name',
    'resourceTags/user:Project',
    'resourceTags/user:Role'
]]

# Filter and keep only rows where "lineItem/ProductCode" is equal to "AmazonEC2"
filtered_df = selected_columns[selected_columns['lineItem/ProductCode'] == 'AmazonEC2']


# Filter and keep only rows where "lineItem/LineItemDescription" contains "Instance Hour"
filtered_df = filtered_df[filtered_df['lineItem/LineItemDescription'].str.contains('Instance Hour')]


def create_resource_tag(row):
    environment = str(row['resourceTags/user:Environment']).lower() if not pd.isna(row['resourceTags/user:Environment']) else ''
    kubernetes_cluster = str(row['resourceTags/user:KubernetesCluster']).lower() if not pd.isna(row['resourceTags/user:KubernetesCluster']) else ''
    name = str(row['resourceTags/user:Name']).lower() if not pd.isna(row['resourceTags/user:Name']) else ''
    project = str(row['resourceTags/user:Project']).lower() if not pd.isna(row['resourceTags/user:Project']) else ''
    role = str(row['resourceTags/user:Role']).lower() if not pd.isna(row['resourceTags/user:Role']) else ''
    
    resource_tag = environment + kubernetes_cluster + name + project + role
    return resource_tag

def assign_project(row):
    resource_tag = create_resource_tag(row)
    
    if "vznl" in resource_tag or "v3vznl" in resource_tag:
        return "VFZiggo"
    elif "vfde" in resource_tag or "v3vfde" in resource_tag:
        return "VFGermany"
    elif "delta" in resource_tag:
        return "Caiway-Delta Fiber"
    elif "dclab" in resource_tag or "infra" in resource_tag:
        return "Infra"
    elif "slave" in resource_tag or "jenkins-all-in-one" in resource_tag:
        return "Jenkins Slave"
    elif "retail" in resource_tag:
        return "BM Retail Commerce"
    elif "attmx" in resource_tag:
        return "AT&T MX"
    else:
        return "Unidentified"


# Create the "Project" column by applying the function
filtered_df['project/Name'] = filtered_df.apply(assign_project, axis=1)

# Delete the specified columns while keeping "resourceTags/user:Name"
columns_to_delete = [
    'resourceTags/user:Environment',
    'resourceTags/user:KubernetesCluster',
    'resourceTags/user:Project',
    'resourceTags/user:Role'
]
filtered_df = filtered_df.drop(columns=columns_to_delete)

# Remove "per On Demand" and "Instance Hour" from "lineItem/LineItemDescription"
filtered_df['lineItem/LineItemDescription'] = filtered_df['lineItem/LineItemDescription'].str.replace('per On Demand', '').str.replace('Instance Hour', '')

# Split the remaining text by spaces into three columns
filtered_df[['instance/Hour', 'instance/Os', 'instance/Type']] = filtered_df['lineItem/LineItemDescription'].str.split(n=2, expand=True)

# Drop the "lineItem/LineItemDescription" column
filtered_df = filtered_df.drop(columns=['lineItem/LineItemDescription'])

# Group by 'lineItem/ResourceId' and aggregate 'lineItem/UnblendedCost' by sum
filtered_df['lineItem/UnblendedCost'] = filtered_df.groupby('lineItem/ResourceId')['lineItem/UnblendedCost'].transform('sum')

# Drop duplicate rows based on 'lineItem/ResourceId'
filtered_df = filtered_df.drop_duplicates(subset=['lineItem/ResourceId'])

# Sort the data by 'product/location' column
filtered_df = filtered_df.sort_values(by='product/location')

# Generate random intermediate file names
def generate_random_filename(prefix, extension):
    return f"{prefix}_{uuid.uuid4().hex}.{extension}"

# Define a function to delete intermediate files
def delete_intermediate_files(files):
    for file in files:
        if os.path.isfile(file):
            os.remove(file)

# Create random intermediate file names
intermediate_files = [
    generate_random_filename("tmp", "xlsx"),
    generate_random_filename("tmp", "xlsx"),
    generate_random_filename("tmp", "xlsx"),
    generate_random_filename("tmp", "xlsx"),
    generate_random_filename("tmp", "xlsx"),
    generate_random_filename("tmp", "xlsx"),
    generate_random_filename("tmp", "xlsx"),
]

# Save the modified data to an intermediate Excel file
filtered_df.to_excel(intermediate_files[0], index=False)

# Load the Excel file
input_file = intermediate_files[0]
df = pd.read_excel(input_file)

# Split the DataFrame into two based on "resourceTags/user:Name" column
df_empty_name = df[df["resourceTags/user:Name"].isna()]
df_non_empty_name = df[df["resourceTags/user:Name"].notna()]

# Save the DataFrames to separate Excel files
output_file_empty_name = intermediate_files[1]
df_empty_name.to_excel(output_file_empty_name, index=False)

output_file_non_empty_name = intermediate_files[2]
df_non_empty_name.to_excel(output_file_non_empty_name, index=False)

# Load the "non_empty_name_ec2.xlsx" file
input_file = intermediate_files[2]
df = pd.read_excel(input_file)

# Find duplicates in the "resourceTags/user:Name" column
duplicates = df[df.duplicated(subset=["resourceTags/user:Name"], keep=False)]

# Create a DataFrame without duplicates
df_no_duplicates = df[~df.duplicated(subset=["resourceTags/user:Name"], keep=False)]

# Save the duplicates to a new Excel file
output_file_duplicates = intermediate_files[3]
duplicates.to_excel(output_file_duplicates, index=False)

# Save the DataFrame without duplicates to a new Excel file
output_file_no_duplicates = intermediate_files[4]
df_no_duplicates.to_excel(output_file_no_duplicates, index=False)

# Load the duplicates file
duplicates_file = intermediate_files[3]
duplicates_df = pd.read_excel(duplicates_file)

# Make the "lineItem/ResourceId" column empty
duplicates_df["lineItem/ResourceId"] = ""

# Save the modified DataFrame to a new file
output_file = intermediate_files[5]
duplicates_df.to_excel(output_file, index=False)

# Load the duplicates_empty_resource_id file
input_file = intermediate_files[5]
df = pd.read_excel(input_file)

# Find duplicates in the "resourceTags/user:Name" column
duplicates = df[df.duplicated(subset=["resourceTags/user:Name"], keep=False)]

# Create a dictionary to store the sum of "lineItem/UnblendedCost" values for each "resourceTags/user:Name"
cost_sum = {}
for index, row in duplicates.iterrows():
    name = row["resourceTags/user:Name"]
    cost = row["lineItem/UnblendedCost"]
    if name in cost_sum:
        cost_sum[name] += cost
    else:
        cost_sum[name] = cost

# Update the DataFrame with the sum of "lineItem/UnblendedCost" for duplicates
for index, row in df.iterrows():
    name = row["resourceTags/user:Name"]
    if name in cost_sum:
        df.at[index, "lineItem/UnblendedCost"] = cost_sum[name]

# Remove duplicates from the DataFrame
df_no_duplicates = df.drop_duplicates(subset=["resourceTags/user:Name"])

# Save the DataFrame without duplicates to a new file
output_file = intermediate_files[6]
df_no_duplicates.to_excel(output_file, index=False)

# Load the three Excel files
file1 = intermediate_files[1]
file2 = intermediate_files[4]
file3 = intermediate_files[6]

df1 = pd.read_excel(file1)
df2 = pd.read_excel(file2)
df3 = pd.read_excel(file3)

# Concatenate the DataFrames vertically
total_df = pd.concat([df1, df2, df3], ignore_index=True)

# Save the merged DataFrame to a new Excel file and sort by "product/location"
output_file = "ec2.xlsx"
total_df = total_df.sort_values(by='product/location')  # Sort by 'product/location'
total_df.to_excel(output_file, index=False)

# Delete intermediate Excel files
delete_intermediate_files(intermediate_files)

if os.path.exists('ec2_instance.xlsx'):
    os.remove('ec2_instance.xlsx')
