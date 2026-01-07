#!/usr/bin/env python3
import boto3
import pandas as pd
from datetime import datetime
from openpyxl.styles import PatternFill, Font, Border, Side
from openpyxl.utils import get_column_letter
import botocore.exceptions
import sys
import getpass

# --- Initialize session and account info ---
try:
    session = boto3.Session()
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]
except botocore.exceptions.ClientError as e:
    print(f"❌ AWS authentication failed: {e}")
    sys.exit(1)

# --- Timestamped filename ---
timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
file_name = f"aws_report_{account_id}_{timestamp}.xlsx"

# --- Styles ---
header_fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
header_font = Font(bold=True)
thin_border = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)

def style_sheet(ws):
    # Header
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    # Borders
    for row in ws.iter_rows():
        for cell in row:
            cell.border = thin_border
    # Adjust column width
    for col in ws.columns:
        max_length = max((len(str(cell.value)) if cell.value else 0) for cell in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

# ------------------------
# 1️⃣ IAM Users
# ------------------------
iam = session.client("iam")
iam_data = []
for user in iam.list_users()["Users"]:
    username = user["UserName"]
    attached_policies = [p["PolicyName"] for p in iam.list_attached_user_policies(UserName=username).get("AttachedPolicies", [])]
    inline_policies = iam.list_user_policies(UserName=username).get("PolicyNames", [])
    all_policies = attached_policies + inline_policies
    iam_data.append({"User": username, "Roles/Policies": ", ".join(all_policies) if all_policies else "None"})
df_iam = pd.DataFrame(iam_data)

# ------------------------
# 2️⃣ Lambda Functions
# ------------------------
lambda_client = session.client("lambda")
lambda_data = []
paginator = lambda_client.get_paginator("list_functions")
for page in paginator.paginate():
    for fn in page["Functions"]:
        lambda_data.append({
            "Function Name": fn["FunctionName"],
            "Purpose": fn.get("Description", "No description")
        })
df_lambda = pd.DataFrame(lambda_data)

# ------------------------
# 3️⃣ Route53 (Resolver Rules + Hosted Zones)
# ------------------------
route53 = session.client("route53")
route53resolver = session.client("route53resolver")

# Resolver rules
resolver_data = []
resolver_rules = route53resolver.list_resolver_rules()["ResolverRules"]
resolver_rule_assocs = route53resolver.list_resolver_rule_associations()["ResolverRuleAssociations"]
resolver_endpoints = route53resolver.list_resolver_endpoints()["ResolverEndpoints"]

for rule in resolver_rules:
    rule_id = rule["Id"]
    rule_type = rule.get("RuleType", "")
    domain = rule.get("DomainName", "")
    vpcs = [assoc['VPCId'] for assoc in resolver_rule_assocs if assoc['ResolverRuleId'] == rule_id]
    target_ips = []
    if rule_type == "FORWARD":
        for ep in resolver_endpoints:
            if ep["Direction"]=="OUTBOUND" and 'IpAddresses' in ep:
                for ip_info in ep["IpAddresses"]:
                    target_ips.append(ip_info.get("Ip", ""))
    resolver_data.append({
        "Rule Name": rule.get("Name", ""),
        "Rule ID": rule_id,
        "Rule Type": rule_type,
        "Domain Name": domain,
        "Target IPs": ",".join(target_ips),
        "VPC Associations": ",".join(vpcs),
        "Purpose": ""
    })
df_resolver = pd.DataFrame(resolver_data)

# Hosted zones
hosted_data = []
hosted_zones = route53.list_hosted_zones()["HostedZones"]
for zone in hosted_zones:
    zone_id = zone["Id"].split("/")[-1]
    zone_name = zone["Name"]
    zone_type = "Private" if zone["Config"]["PrivateZone"] else "Public"
    records = route53.list_resource_record_sets(HostedZoneId=zone_id)["ResourceRecordSets"]
    for record in records:
        value = ""
        if "ResourceRecords" in record:
            value = ",".join([r["Value"] for r in record["ResourceRecords"]])
        elif "AliasTarget" in record:
            value = record['AliasTarget'].get("DNSName","")
        hosted_data.append({
            "Hosted Zone Name": zone_name,
            "Hosted Zone Type": zone_type,
            "Record Name": record.get("Name", ""),
            "Record Type": record.get("Type", ""),
            "Record Value": value,
            "Purpose": ""
        })
df_hosted = pd.DataFrame(hosted_data)

# ------------------------
# 4️⃣ Load Balancers (ALB/NLB + Classic)
# ------------------------
elbv2_client = session.client("elbv2")
elb_client = session.client("elb")
lb_data = []

for lb in elbv2_client.describe_load_balancers()["LoadBalancers"]:
    listeners = elbv2_client.describe_listeners(LoadBalancerArn=lb["LoadBalancerArn"])["Listeners"]
    listener_str = ", ".join([f"{l['Protocol']}:{l['Port']}" for l in listeners])
    tgs = elbv2_client.describe_target_groups(LoadBalancerArn=lb["LoadBalancerArn"])["TargetGroups"]
    tg_str = ", ".join([f"{tg['TargetGroupName']} ({tg['Protocol']}:{tg['Port']})" for tg in tgs])
    lb_data.append({
        "Name": lb["LoadBalancerName"],
        "Type": lb["Type"],
        "DNS Name": lb["DNSName"],
        "Scheme": lb["Scheme"],
        "VPC": lb["VpcId"],
        "Subnets": ", ".join([az["SubnetId"] for az in lb["AvailabilityZones"]]),
        "Security Groups": ", ".join(lb.get("SecurityGroups", [])),
        "Listeners": listener_str,
        "Target Groups": tg_str
    })

for lb in elb_client.describe_load_balancers()["LoadBalancerDescriptions"]:
    listeners_info = [f"{lst['Listener']['Protocol']}:{lst['Listener']['LoadBalancerPort']}" for lst in lb['ListenerDescriptions']]
    lb_data.append({
        "Name": lb["LoadBalancerName"],
        "Type": "classic",
        "DNS Name": lb["DNSName"],
        "Scheme": lb["Scheme"],
        "VPC": lb.get("VPCId", ""),
        "Subnets": ", ".join(lb["Subnets"]),
        "Security Groups": ", ".join(lb.get("SecurityGroups", [])),
        "Listeners": ", ".join(listeners_info),
        "Target Groups": ""
    })
df_lb = pd.DataFrame(lb_data)

# ------------------------
# 5️⃣ ACM Certificates (Singapore)
# ------------------------
acm_client = session.client("acm", region_name="ap-southeast-1")
cert_data = []
paginator = acm_client.get_paginator("list_certificates")
for page in paginator.paginate(CertificateStatuses=['ISSUED','EXPIRED','INACTIVE','PENDING_VALIDATION']):
    for cert in page['CertificateSummaryList']:
        details = acm_client.describe_certificate(CertificateArn=cert["CertificateArn"])["Certificate"]
        cert_data.append({
            "Domain Name": details.get("DomainName", ""),
            "Type": details.get("Type", ""),
            "Status": details.get("Status", ""),
            "In Use?": "Yes" if details.get("InUseBy") else "No",
            "Expiry Date": details.get("NotAfter").strftime("%Y-%m-%d %H:%M:%S") if details.get("NotAfter") else "",
            "Region": "ap-southeast-1"
        })
df_acm = pd.DataFrame(cert_data)

# ------------------------
# 6️⃣ Network Inventory (Singapore)
# ------------------------
region = "ap-southeast-1"
ec2 = session.client("ec2", region_name=region)
network_data = {
    "VPCs": [], "Subnets": [], "RouteTables": [], "InternetGateways": [], "NATGateways": [],
    "SecurityGroups": [], "NetworkACLs": [], "VPCPeering": [], "VPNConnections": [],
    "TransitGateways": [], "VPCEndpoints": [], "ElasticIPs": []
}

# --- Fetch VPCs ---
for v in ec2.describe_vpcs()["Vpcs"]:
    network_data["VPCs"].append({
        "Region": region,
        "VPC ID": v["VpcId"],
        "CIDR": v["CidrBlock"],
        "Default": v.get("IsDefault", False),
        "Name": next((t['Value'] for t in v.get("Tags", []) if t["Key"]=="Name"), "")
    })

# --- Fetch Subnets ---
for s in ec2.describe_subnets()["Subnets"]:
    network_data["Subnets"].append({
        "Region": region,
        "Subnet ID": s["SubnetId"],
        "VPC ID": s["VpcId"],
        "CIDR": s["CidrBlock"],
        "AZ": s["AvailabilityZone"],
        "Public": s.get("MapPublicIpOnLaunch", False),
        "Name": next((t['Value'] for t in s.get("Tags", []) if t["Key"]=="Name"), "")
    })

# --- Route Tables ---
for rt in ec2.describe_route_tables()["RouteTables"]:
    network_data["RouteTables"].append({
        "Region": region,
        "RouteTable ID": rt["RouteTableId"],
        "VPC ID": rt["VpcId"],
        "Associations": ", ".join([a.get('SubnetId','Main') for a in rt.get("Associations", [])])
    })

# --- Internet Gateways ---
for igw in ec2.describe_internet_gateways()["InternetGateways"]:
    network_data["InternetGateways"].append({
        "Region": region,
        "IGW ID": igw["InternetGatewayId"],
        "Attached VPCs": ", ".join([a["VpcId"] for a in igw.get("Attachments", [])]),
        "Name": next((t['Value'] for t in igw.get("Tags", []) if t["Key"]=="Name"), "")
    })

# --- NAT Gateways ---
for nat in ec2.describe_nat_gateways()["NatGateways"]:
    network_data["NATGateways"].append({
        "Region": region,
        "NAT ID": nat["NatGatewayId"],
        "Subnet ID": nat["SubnetId"],
        "VPC ID": nat["VpcId"],
        "State": nat["State"],
        "Elastic IP": nat["NatGatewayAddresses"][0]["PublicIp"] if nat.get("NatGatewayAddresses") else ""
    })

# --- Security Groups ---
for sg in ec2.describe_security_groups()["SecurityGroups"]:
    network_data["SecurityGroups"].append({
        "Region": region,
        "SG ID": sg["GroupId"],
        "VPC ID": sg.get("VpcId",""),
        "Name": sg.get("GroupName",""),
        "Description": sg.get("Description","")
    })

# --- Network ACLs ---
for acl in ec2.describe_network_acls()["NetworkAcls"]:
    network_data["NetworkACLs"].append({
        "Region": region,
        "NACL ID": acl["NetworkAclId"],
        "VPC ID": acl["VpcId"],
        "IsDefault": acl.get("IsDefault", False)
    })

# --- VPC Peering ---
for p in ec2.describe_vpc_peering_connections()["VpcPeeringConnections"]:
    network_data["VPCPeering"].append({
        "Region": region,
        "Peering ID": p["VpcPeeringConnectionId"],
        "Requester VPC": p["RequesterVpcInfo"]["VpcId"],
        "Accepter VPC": p["AccepterVpcInfo"]["VpcId"],
        "Status": p["Status"]["Code"]
    })

# --- VPN Connections ---
for vpn in ec2.describe_vpn_connections()["VpnConnections"]:
    network_data["VPNConnections"].append({
        "Region": region,
        "VPN ID": vpn["VpnConnectionId"],
        "VGW ID": vpn["VpnGatewayId"],
        "Customer Gateway": vpn["CustomerGatewayId"],
        "State": vpn["State"]
    })

# --- Transit Gateways ---
for tg in ec2.describe_transit_gateways()["TransitGateways"]:
    network_data["TransitGateways"].append({
        "Region": region,
        "TGW ID": tg["TransitGatewayId"],
        "Name": next((t['Value'] for t in tg.get("Tags", []) if t["Key"]=="Name"), ""),
        "State": tg["State"]
    })

# --- VPC Endpoints ---
for ep in ec2.describe_vpc_endpoints()["VpcEndpoints"]:
    network_data["VPCEndpoints"].append({
        "Region": region,
        "Endpoint ID": ep["VpcEndpointId"],
        "Service Name": ep["ServiceName"],
        "Type": ep["VpcEndpointType"],
        "VPC ID": ep["VpcId"],
        "Subnet IDs": ", ".join(ep.get("SubnetIds", []))
    })

# --- Elastic IPs ---
for eip in ec2.describe_addresses()["Addresses"]:
    network_data["ElasticIPs"].append({
        "Region": region,
        "Allocation ID": eip.get("AllocationId",""),
        "Public IP": eip.get("PublicIp",""),
        "Instance ID": eip.get("InstanceId","")
    })

# ------------------------
# 0️⃣ Summary Sheet
# ------------------------
summary_data = [{
    "Total IAM Users": len(df_iam),
    "Total Lambda Functions": len(df_lambda),
    "Total VPCs": len(network_data["VPCs"]),
    "Total Subnets": len(network_data["Subnets"]),
    "Total Security Groups": len(network_data["SecurityGroups"]),
    "Total Load Balancers": len(df_lb),
    "Total ACM Certificates": len(df_acm),
    "Notes / Comments": "Some resources may not be captured if permissions missing"
}]
df_summary = pd.DataFrame(summary_data)

# ------------------------
# Write all sheets to Excel
# ------------------------
with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
    # Summary first
    df_summary.to_excel(writer, index=False, sheet_name="Summary")
    
    # Other sheets
    df_iam.to_excel(writer, index=False, sheet_name="IAM Users")
    df_lambda.to_excel(writer, index=False, sheet_name="Lambda Functions")
    df_resolver.to_excel(writer, index=False, sheet_name="Route53 Resolver")
    df_hosted.to_excel(writer, index=False, sheet_name="Route53 Hosted Zones")
    df_lb.to_excel(writer, index=False, sheet_name="Load Balancers")
    df_acm.to_excel(writer, index=False, sheet_name="ACM Certificates")
    for sheet_name, data in network_data.items():
        if data:
            pd.DataFrame(data).to_excel(writer, index=False, sheet_name=sheet_name)
    
    # Apply styling
    for ws in writer.sheets.values():
        style_sheet(ws)

print(f"✅ Complete AWS inventory report saved as '{file_name}' (Generated by IAM user: {getpass.getuser()})")
