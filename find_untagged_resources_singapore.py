#!/usr/bin/env python3
import boto3
import json

REGION = "ap-southeast-1"
TAG_KEY = "map-migrated"
TAG_VALUE = "migYY56Z04RPH"

# ANSI colors for terminal output
COLOR_KEY = "\033[94m"     # Blue
COLOR_VALUE = "\033[92m"   # Green
COLOR_RESET = "\033[0m"

# Load Tag Editor supported resource types (exclude CloudFormation stacks and KMS keys)
with open("tag_editor_supported.json") as f:
    RESOURCE_TYPES = json.load(f)


def list_untagged_resources(region):
    client = boto3.client("resourcegroupstaggingapi", region_name=region)
    paginator = client.get_paginator("get_resources")
    untagged_resources = []

    for resource_type in RESOURCE_TYPES:
        if resource_type in ["ec2:network-interface", "ec2:volume", "rds:snapshot", "rds:cluster-snapshot"]:
            # Skip special cases handled separately
            continue

        try:
            for page in paginator.paginate(ResourceTypeFilters=[resource_type]):
                for resource in page.get("ResourceTagMappingList", []):
                    tags = {t["Key"]: t["Value"] for t in resource.get("Tags", [])}
                    if tags.get(TAG_KEY) != TAG_VALUE:
                        untagged_resources.append({
                            "Identifier": resource["ResourceARN"],
                            "Service": resource_type.split(":")[0],
                            "Type": resource_type.split(":")[1],
                            "Region": region,
                            "Tags": tags
                        })
        except client.exceptions.InvalidParameterException:
            continue
        except Exception as e:
            print(f"Error scanning {resource_type}: {e}")
            continue

    return untagged_resources


def list_untagged_eventbridge_rules(region):
    client = boto3.client("events", region_name=region)
    untagged_rules = []

    paginator = client.get_paginator("list_rules")
    for page in paginator.paginate():
        for rule in page.get("Rules", []):
            arn = rule["Arn"]
            tags_response = client.list_tags_for_resource(ResourceARN=arn)
            tags = {t["Key"]: t["Value"] for t in tags_response.get("Tags", [])}
            if tags.get(TAG_KEY) != TAG_VALUE:
                untagged_rules.append({
                    "Identifier": rule["Name"],
                    "Service": "events",
                    "Type": "rule",
                    "Region": region,
                    "Tags": tags
                })

    return untagged_rules


def list_untagged_network_interfaces(region):
    client = boto3.client("ec2", region_name=region)
    untagged_enis = []

    paginator = client.get_paginator("describe_network_interfaces")
    for page in paginator.paginate():
        for eni in page["NetworkInterfaces"]:
            tags = {t["Key"]: t["Value"] for t in eni.get("TagSet", [])}
            if tags.get(TAG_KEY) != TAG_VALUE:
                untagged_enis.append({
                    "Identifier": eni["NetworkInterfaceId"],
                    "Service": "ec2",
                    "Type": "network-interface",
                    "Region": region,
                    "Tags": tags
                })

    return untagged_enis


def list_untagged_ebs_volumes(region):
    client = boto3.client("ec2", region_name=region)
    untagged_volumes = []

    paginator = client.get_paginator("describe_volumes")
    for page in paginator.paginate():
        for volume in page["Volumes"]:
            tags = {t["Key"]: t["Value"] for t in volume.get("Tags", [])}
            if tags.get(TAG_KEY) != TAG_VALUE:
                untagged_volumes.append({
                    "Identifier": volume["VolumeId"],
                    "Service": "ec2",
                    "Type": "volume",
                    "Region": region,
                    "Tags": tags
                })

    return untagged_volumes


def list_untagged_rds_snapshots(region):
    client = boto3.client("rds", region_name=region)
    untagged_snapshots = []

    # DB Snapshots
    paginator = client.get_paginator("describe_db_snapshots")
    for page in paginator.paginate():
        for snapshot in page["DBSnapshots"]:
            arn = snapshot["DBSnapshotArn"]
            try:
                tags_response = client.list_tags_for_resource(ResourceName=arn)
                tags = {t["Key"]: t["Value"] for t in tags_response.get("TagList", [])}
            except Exception as e:
                print(f"Error fetching tags for RDS snapshot {arn}: {e}")
                tags = {}

            if tags.get(TAG_KEY) != TAG_VALUE:
                untagged_snapshots.append({
                    "Identifier": snapshot["DBSnapshotIdentifier"],
                    "Service": "rds",
                    "Type": "db-snapshot",
                    "Region": region,
                    "Tags": tags
                })

    # Cluster Snapshots (Aurora, etc.)
    paginator = client.get_paginator("describe_db_cluster_snapshots")
    for page in paginator.paginate():
        for snapshot in page["DBClusterSnapshots"]:
            arn = snapshot["DBClusterSnapshotArn"]
            try:
                tags_response = client.list_tags_for_resource(ResourceName=arn)
                tags = {t["Key"]: t["Value"] for t in tags_response.get("TagList", [])}
            except Exception as e:
                print(f"Error fetching tags for RDS cluster snapshot {arn}: {e}")
                tags = {}

            if tags.get(TAG_KEY) != TAG_VALUE:
                untagged_snapshots.append({
                    "Identifier": snapshot["DBClusterSnapshotIdentifier"],
                    "Service": "rds",
                    "Type": "db-cluster-snapshot",
                    "Region": region,
                    "Tags": tags
                })

    return untagged_snapshots


def list_untagged_s3_buckets():
    client = boto3.client("s3")
    untagged_buckets = []

    response = client.list_buckets()
    for bucket in response["Buckets"]:
        tags = {}
        try:
            tagset = client.get_bucket_tagging(Bucket=bucket["Name"]).get("TagSet", [])
            tags = {t["Key"]: t["Value"] for t in tagset}
        except client.exceptions.ClientError:
            # No tags on bucket
            pass

        if tags.get(TAG_KEY) != TAG_VALUE:
            untagged_buckets.append({
                "Identifier": bucket["Name"],
                "Service": "s3",
                "Type": "bucket",
                "Region": "global",
                "Tags": tags
            })

    return untagged_buckets


def print_colored_resources(resources):
    for res in resources:
        for key, value in res.items():
            if isinstance(value, dict):
                print(f"{COLOR_KEY}{key}:{COLOR_RESET}")
                for k, v in value.items():
                    print(f"  {COLOR_KEY}{k}:{COLOR_RESET} {COLOR_VALUE}{v}{COLOR_RESET}")
            else:
                print(f"{COLOR_KEY}{key}:{COLOR_RESET} {COLOR_VALUE}{value}{COLOR_RESET}")
        print("-" * 50)


if __name__ == "__main__":
    resources = list_untagged_resources(REGION)
    rules = list_untagged_eventbridge_rules(REGION)
    enis = list_untagged_network_interfaces(REGION)
    volumes = list_untagged_ebs_volumes(REGION)
    rds_snapshots = list_untagged_rds_snapshots(REGION)
    buckets = list_untagged_s3_buckets()

    all_untagged = resources + rules + enis + volumes + rds_snapshots + buckets

    # Print to console with colors
    print_colored_resources(all_untagged)

    # Save to JSON file
    with open("untagged_resources.json", "w") as f:
        json.dump(all_untagged, f, indent=2)

    print(f"{COLOR_KEY}Total untagged resources:{COLOR_RESET} {COLOR_VALUE}{len(all_untagged)}{COLOR_RESET}")
    print("Saved output to untagged_resources.json")
