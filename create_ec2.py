#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import boto3


VPC_ID = "vpc-0e201942cd4c27ac2"
SECURITY_GROUP_ID = "sg-006b598e3c6681752"
REGION = "eu-central-1"
UBUNTU_RELEASE = "26.04"


def parse_args():
	parser = argparse.ArgumentParser(description="Create an Ubuntu EC2 instance from a local profile folder.")
	parser.add_argument("profile", help="Folder name containing config.json and init.sh, for example: gpu")
	parser.add_argument("--key-name", required=True, help="Existing EC2 SSH key pair name")
	return parser.parse_args()


def load_profile(profile_name):
	profile_path = Path(profile_name)
	config_path = profile_path / "config.json"
	init_path = profile_path / "init.sh"

	if not config_path.is_file():
		raise FileNotFoundError(f"Missing config file: {config_path}")
	if not init_path.is_file():
		raise FileNotFoundError(f"Missing init script: {init_path}")

	with config_path.open("r", encoding="utf-8") as config_file:
		config = json.load(config_file)

	try:
		instance_type = config["instance-type"]
		storage = int(config["storage"])
		architecture = config["architecture"]
	except KeyError as error:
		raise KeyError(f"Missing required config key: {error.args[0]}") from error

	init_script = init_path.read_text(encoding="utf-8")
	return instance_type, storage, architecture, init_script


def get_ubuntu_ami(ec2_client, ssm_client, architecture):
	parameter_name = f"/aws/service/canonical/ubuntu/server/{UBUNTU_RELEASE}/stable/current/{architecture}/hvm/ebs-gp3/ami-id"
	ami_id = ssm_client.get_parameter(Name=parameter_name)["Parameter"]["Value"]
	return ec2_client.describe_images(ImageIds=[ami_id])["Images"][0]


def choose_subnet(ec2_client):
	subnets = ec2_client.describe_subnets(
		Filters=[
			{"Name": "vpc-id", "Values": [VPC_ID]},
			{"Name": "state", "Values": ["available"]},
		]
	)["Subnets"]

	if not subnets:
		raise RuntimeError(f"No available subnet found in VPC {VPC_ID}.")

	return sorted(subnets, key=lambda subnet: subnet["SubnetId"])[0]["SubnetId"]


def build_user_data(init_script):
	return init_script


def create_instance(ec2_client, ssm_client, args):
	instance_type, storage, architecture, init_script = load_profile(args.profile)
	image = get_ubuntu_ami(ec2_client, ssm_client, architecture)
	subnet_id = choose_subnet(ec2_client)
	name = Path(args.profile).name

	request = {
		"ImageId": image["ImageId"],
		"InstanceType": instance_type,
		"KeyName": args.key_name,
		"MinCount": 1,
		"MaxCount": 1,
		"SubnetId": subnet_id,
		"SecurityGroupIds": [SECURITY_GROUP_ID],
		"UserData": build_user_data(init_script),
		"BlockDeviceMappings": [
			{
				"DeviceName": image["RootDeviceName"],
				"Ebs": {
					"VolumeSize": storage,
					"VolumeType": "gp3",
					"DeleteOnTermination": True,
				},
			}
		],
		"TagSpecifications": [
			{
				"ResourceType": "instance",
				"Tags": [
					{"Key": "Name", "Value": name},
					{"Key": "Profile", "Value": Path(args.profile).name},
				],
			}
		],
	}

	return ec2_client.run_instances(**request)["Instances"][0], image, subnet_id


def main():
	args = parse_args()
	ec2_client = boto3.client("ec2", region_name=REGION)
	ssm_client = boto3.client("ssm", region_name=REGION)
	instance, image, subnet_id = create_instance(ec2_client, ssm_client, args)

	print(f"Created instance: {instance['InstanceId']}")
	print(f"AMI: {image['ImageId']} ({image['Name']})")
	print(f"Subnet: {subnet_id}")
	print(f"State: {instance['State']['Name']}")


if __name__ == "__main__":
	main()
