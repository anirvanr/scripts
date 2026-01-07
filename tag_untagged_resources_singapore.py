#!/usr/bin/env python3
import boto3
import json

REGION = "ap-southeast-1"
TAG_KEY = "map-migrated"
TAG_VALUE = "migYY56Z04RPH"

# ANSI colors for terminal output
COLOR_KEY = "\033[94m"      # Blue
COLOR_SUCCESS = "\033[92m"  # Green
COLOR_FAIL = "\033[91m"     # Red
COLOR_SKIP = "\033[93m"     # Yellow
COLOR_RESET = "\033[0m"

# Load untagged resources from previous script
with open("untagged_resources.json") as f:
    untagged_resources = json.load(f)

successfully_tagged = []
failed_to_tag = []
skipped_resources = []


def tag_resource(resource):
    identifier = resource["Identifier"]
    service = resource["Service"]
    res_type = resource["Type"]

    try:
        # EC2 Network Interface
        if service == "ec2" and res_type == "network-interface":
            client = boto3.client("ec2", region_name=REGION)
            client.create_tags(
                Resources=[identifier],
                Tags=[{"Key": TAG_KEY, "Value": TAG_VALUE}]
            )

        # EC2 Volume
        elif service == "ec2" and res_type == "volume":
            client = boto3.client("ec2", region_name=REGION)
            client.create_tags(
                Resources=[identifier],
                Tags=[{"Key": TAG_KEY, "Value": TAG_VALUE}]
            )

        # S3 Bucket
        elif service == "s3" and res_type == "bucket":
            client = boto3.client("s3")
            client.put_bucket_tagging(
                Bucket=identifier,
                Tagging={"TagSet": [{"Key": TAG_KEY, "Value": TAG_VALUE}]}
            )

        # RDS Snapshots (DB + Cluster)
        elif service == "rds" and res_type in ["db-snapshot", "db-cluster-snapshot"]:
            client = boto3.client("rds", region_name=REGION)

            # Build ARN if missing
            resource_arn = resource.get("ResourceARN")
            if not resource_arn:
                account_id = boto3.client("sts").get_caller_identity()["Account"]
                if res_type == "db-snapshot":
                    resource_arn = f"arn:aws:rds:{REGION}:{account_id}:snapshot:{identifier}"
                else:  # db-cluster-snapshot
                    resource_arn = f"arn:aws:rds:{REGION}:{account_id}:cluster-snapshot:{identifier}"

            client.add_tags_to_resource(
                ResourceName=resource_arn,
                Tags=[{"Key": TAG_KEY, "Value": TAG_VALUE}]
            )
            print(f"{COLOR_SUCCESS}✅ Tagged RDS snapshot {identifier} ({resource_arn}) successfully.{COLOR_RESET}")
            successfully_tagged.append(f"{identifier} ({resource_arn})")
            return  # Exit early since we already logged

        # EventBridge rules
        elif service == "events" and res_type == "rule":
            # Skip AWS-managed rules
            if resource.get("ManagedBy"):
                print(f"{COLOR_SKIP}⚠️ Skipping managed rule {identifier}{COLOR_RESET}")
                skipped_resources.append(identifier)
                return
            client = boto3.client("events", region_name=REGION)
            client.tag_resource(
                ResourceARN=resource["ResourceARN"],  # Must use ARN
                Tags=[{"Key": TAG_KEY, "Value": TAG_VALUE}]
            )

        # All other resources via Tagging API
        else:
            client = boto3.client("resourcegroupstaggingapi", region_name=REGION)
            client.tag_resources(
                ResourceARNList=[identifier],
                Tags={TAG_KEY: TAG_VALUE}
            )

        print(f"{COLOR_SUCCESS}✅ Tagged {identifier} successfully.{COLOR_RESET}")
        successfully_tagged.append(identifier)

    except Exception as e:
        print(f"{COLOR_FAIL}❌ Failed to tag {identifier}: {e}{COLOR_RESET}")
        failed_to_tag.append(identifier)


if __name__ == "__main__":
    for resource in untagged_resources:
        tag_resource(resource)

    # Summary
    print("\n" + "="*50)
    print(f"{COLOR_KEY}Total resources processed:{COLOR_RESET} {len(untagged_resources)}")
    print(f"{COLOR_KEY}✅ Successfully tagged:{COLOR_RESET} {COLOR_SUCCESS}{len(successfully_tagged)}{COLOR_RESET}")
    print(f"{COLOR_KEY}⚠️ Skipped (managed/AWS rules):{COLOR_RESET} {COLOR_SKIP}{len(skipped_resources)}{COLOR_RESET}")
    print(f"{COLOR_KEY}❌ Failed to tag:{COLOR_RESET} {COLOR_FAIL}{len(failed_to_tag)}{COLOR_RESET}")

    if skipped_resources:
        print(f"\n{COLOR_KEY}Skipped resources:{COLOR_RESET}")
        for r in skipped_resources:
            print(f" - {COLOR_SKIP}{r}{COLOR_RESET}")

    if failed_to_tag:
        print(f"\n{COLOR_KEY}Resources failed to tag:{COLOR_RESET}")
        for r in failed_to_tag:
            print(f" - {COLOR_FAIL}{r}{COLOR_RESET}")

    print("="*50)
    print(f"{COLOR_KEY}Tagging process completed.{COLOR_RESET}")
