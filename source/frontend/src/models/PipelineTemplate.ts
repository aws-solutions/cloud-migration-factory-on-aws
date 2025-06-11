/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export type PipelineTemplate = {
    pipeline_template_id: string;
    deletion_protection: boolean;
    pipeline_template_description: string;
    pipeline_template_name: string;
    version: string;
    _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
