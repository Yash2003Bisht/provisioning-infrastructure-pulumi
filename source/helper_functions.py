import json
import os
from pathlib import Path

import pulumi
import pulumi_aws as aws
# pulumi automation framework
import pulumi.automation as auto

from source import logger, redis_instance


def ensure_plugins():
    """
    Install plugins
    """
    work_space = auto.LocalWorkspace()
    work_space.install_plugin("aws", "v4.0.0")


def store_in_redis(key: str, data: list):
    """
    Store data in redis
    :param key: 
    :param data: 
    """
    redis_instance.set(key, json.dumps(data))


def get_from_redis(key: str, search: bool = False):
    """
    Get data from redis
    :param key: 
    :param search: 
    """
    if search:
        if not redis_instance.get(key):
            return False
        return True
    return json.loads(redis_instance.get(key))


def create_pulumi_program_s3(content: str):
    """
    Create the website and deploy it to amazon s3 bucket
    :param content: HTML content - HTML code pass by the user
    """
    # create a bucket and expose a website index document
    site_bicket = aws.s3.Bucket(
        "s3-website-bucket", website=aws.s3.BucketWebsiteArgs(index_document="index.html")
    )
    index_content = content

    # write our index.html into the site bucket
    aws.s3.BucketObject(
        "index",
        bucket=site_bicket.id,
        content=index_content,
        key="index.html",
        content_type="text/html; charset=utf-8",
    )

    # set the access policy for the bucket so all objects are readable
    aws.s3.BucketPolicy(
        "bucket-policy",
        bucket=site_bicket.id,
        policy=site_bicket.id.apply(
            lambda id: json.dumps({
                "Version": "2012-10-17",
                "Statement": {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    # policy refers to bucket explicitly
                    "Resource": [f"arn:aws:s3:::{id}/*"]
                }
            })
        )
    )

    # export the website url
    pulumi.export("website_url", site_bicket.website_endpoint)
    pulumi.export("website_content", index_content)


def create_pulumi_program_vms(keydata: str, instance_type: str):
    """
    Create the virtual machines and deploy it to amazon ec2 instance
    :param keydata: 
    :param instance_type: 
    """
    # choose the latest minimal amzn2 linux AMI
    # TODO: make this something the user can choose
    ami = aws.ec2.get_ami(most_recent=True,
                          owners=["amazon"],
                          filters=[aws.GetAmiFilterArgs(name="name", values=["*amzn2-ami-minimal-hvm*"])])
    
    group = aws.ec2.SecurityGroup("web-secgrp",
                                  description="Enable SSH access",
                                  ingress=[aws.ec2.SecurityGroupIngressArgs(
                                    protocol="tcp",
                                    from_port=22,
                                    to_port=22,
                                    cidr_blocks=["0.0.0.0/0"]
                                  )])
    
    public_key = keydata
    if public_key is None or public_key == "":
        home = str(Path.home())
        # generate public key using ssh-keygen
        with open(os.path.join(home, ".ssh/id_rsa.pub"), "r") as file:
            public_key = file.read()
    
    public_key = public_key.strip()
    logger.info(f"Public Key: '{public_key}'")

    keypair = aws.ec2.KeyPair("dlami-keypair", public_key=public_key)
    server = aws.ec2.Instance("dlami-server",
                              instance_type=instance_type,
                              vpc_security_group_ids=[group.id],
                              key_name=keypair.id,
                              ami=ami.id)

    pulumi.export("instance_type", server.instance_type)
    pulumi.export("public_key", keypair.public_key)
    pulumi.export("public_ip", server.public_ip)
    pulumi.export("public_dns", server.public_dns)
