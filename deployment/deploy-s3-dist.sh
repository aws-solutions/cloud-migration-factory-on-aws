#!/bin/bash
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#

#
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#
# This script should be run from the repo's deployment directory
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name solution-name version-code
#
# Parameters:
#  - source-bucket-base-name: Name for the S3 bucket location where the template will source the Lambda
#    code from. The template will append '-[region_name]' to this bucket name.
#    For example: ./build-s3-dist.sh solutions my-solution v1.0.0
#    The template will then expect the source code to be located in the solutions-[region_name] bucket
#
#  - solution-name: name of the solution for consistency
#
#  - version-code: version of the package

ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)
REGION=$(aws configure get region)
BASE_BUCKET_NAME=cmf-deployment-$ACCOUNT_ID
TEMPLATE_BUCKET_NAME=$BASE_BUCKET_NAME-reference
ASSET_BUCKET_NAME=$BASE_BUCKET_NAME-$REGION

SOLUTION_NAME=cloud-migration-factory-on-aws
VERSION=custom001

# Build the distributable using build-s3-dist.sh
cd /Users/emmawitt/cloud-migration-factory-on-aws/deployment
./build-s3-dist.sh $BASE_BUCKET_NAME $SOLUTION_NAME $VERSION

# Deployment: Deploy the distributable to an Amazon S3 bucket in your account
aws s3 ls s3://$ASSET_BUCKET_NAME 
aws s3 cp global-s3-assets/  s3://$TEMPLATE_BUCKET_NAME/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control
aws s3 cp regional-s3-assets/  s3://$ASSET_BUCKET_NAME/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control

# Update stack
aws cloudformation update-stack \
    --stack-name cmf-solution-stack-TEST \
    --template-url https://cmf-deployment-537124965680-reference.s3.eu-central-1.amazonaws.com/cloud-migration-factory-on-aws/custom001/aws-cloud-migration-factory-solution.template