/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export type PipelineTemplateTask = {
    pipeline_template_task_id: string;
    pipeline_template_id: string;
    pipeline_template_task_name: string;
    task_id: string;
    task_sequence_number: string;
    _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
