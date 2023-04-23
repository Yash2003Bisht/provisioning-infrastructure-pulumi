import json

import pulumi
from pulumi_aws import s3

# pulumi automation framework
import pulumi.automation as auto


def create_pulumi_program(content: str):
    """
    Create the website and deploy it to amazon s3 bucket
    :param content: HTML content - HTML code pass by the user
    """
    # create a bucket and expose a website index document
    site_bicket = s3.Bucket(
        "s3-website-bucket", website=s3.BucketWebsiteArgs(index_document="index.html")
    )
    index_content = content

    # write our index.html into the site bucket
    s3.BucketObject(
        "index",
        bucket=site_bicket.id,
        content=index_content,
        key="index.html",
        content_type="text/html; charset=utf-8",
    )

    # set the access policy for the bucket so all objects are readable
    s3.BucketPolicy(
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


def ensure_plugins():
    work_space = auto.LocalWorkspace()
    work_space.install_plugin("aws", "v4.0.0")
