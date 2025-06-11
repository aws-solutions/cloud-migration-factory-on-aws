/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { rest } from "msw";
import { v4 } from "uuid";
import { Pipeline, PipelineTemplate, PipelineTemplateTask, Task, TaskExecution } from "../../models/Pipeline.ts";

export const mock_tools_api = [
  rest.get("/pipelines/templates", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
];

export function generateTestTasks(count: number): Array<Task> {
  const taskTypes = ["TypeA", "TypeB", "TypeC"];
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    task_id: v4(),
    task_name: `unittest_task${number}`,
    task_description: `Description for unittest_task${number}`,
    task_type: taskTypes[number % taskTypes.length],
    lambda_function_name_suffix: `lambda_suffix_${number}`,
    ssm_script_name: `script_name_${number}`,
    ssm_script_version: `v${number + 1}`,
    task_arguments: {},
    _history: {
      createdBy: {
        userRef: v4(),
        email: "foo@example.com",
      },
      createdTimestamp: new Date().toISOString(),
    },
  }));
}

export function generateTestPipelineTemplates(count: number): Array<PipelineTemplate> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    pipeline_template_id: v4(),
    pipeline_template_name: `unittest_pipeline_template${number}`,
    pipeline_template_description: `Description for unittest_pipeline_template${number}`,
    _history: {
      createdBy: {
        userRef: v4(),
        email: "foo@example.com",
      },
      createdTimestamp: new Date().toISOString(),
    },
  }));
}

export function generateSystemOwnedTestPipelineTemplates(count: number): Array<PipelineTemplate> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    pipeline_template_id: v4(),
    pipeline_template_name: `unittest_pipeline_template${number}`,
    pipeline_template_description: `Description for unittest_pipeline_template${number}`,
    _history: {
      createdBy: {
        userRef: v4(),
        email: "[system]",
      },
      createdTimestamp: new Date().toISOString(),
    },
  }));
}

export function generateTestPipelineTemplateTasks(
  pipelineTemplates: Array<PipelineTemplate>,
  tasks: Array<Task>
): Array<PipelineTemplateTask> {
  return pipelineTemplates.flatMap((template, index) =>
    tasks.map((task, taskIndex) => ({
      pipeline_template_task_id: v4(),
      pipeline_template_id: template.pipeline_template_id,
      task_id: task.task_id,
      task_successors: [],
      pipeline_template_task_name: `template_task_${index}_${taskIndex}`,
      _history: {
        createdBy: {
          userRef: v4(),
          email: "foo@example.com",
        },
        createdTimestamp: new Date().toISOString(),
      },
    }))
  );
}

export function generateTestPipelines(
  count: number,
  data?: { status: string },
  pipelineTemplate?: PipelineTemplate,
  tasks?: Array<Task>
): Array<Pipeline> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    pipeline_id: `${number}`,
    pipeline_name: `unittest_pipeline${number}`,
    pipeline_status: data?.status ?? "Created",
    pipeline_template_id: pipelineTemplate?.pipeline_template_id ?? v4(),
    task_arguments: tasks ? tasks.map((task) => ({ ...task })) : [],
    _history: {
      createdBy: {
        userRef: v4(),
        email: "foo@example.com",
      },
      createdTimestamp: new Date().toISOString(),
    },
  }));
}

export function generateTestTaskExecutions(pipeline: Pipeline, tasks: Array<Task>): Array<TaskExecution> {
  return tasks.map((task, index) => ({
    task_execution_id: v4(),
    task_execution_name: `unittest_task_execution${index}`,
    pipeline_id: pipeline.pipeline_id,
    task_successors: [],
    task_id: task.task_id,
    task_type: task.task_type,
    task_description: task.task_description,
    task_execution_status: index === 0 ? "In Progress" : "Not Started",
    outputLastMessage: `Last message for unittest_task_execution${index}`,
    output: `Output for unittest_task_execution${index}`,
    task_execution_inputs: {
      sizing_preference: "Maximum utilization",
      ec2_instance_family_exclusions: ["T2"],
      aws_region: "us-east-1",
      home_region: "eu-central-1",
      aws_accountid: "123456789012",
      r_type: "Retire",
    },
    _history: {
      createdBy: {
        userRef: v4(),
        email: "foo@example.com",
      },
      createdTimestamp: new Date().toISOString(),
    },
  }));
}
  // generate the POST response object with an array with the given number of pipeline_template records
  export function generateTestPostPipelineTemplatesResponse(count: number, data?: { pipelineTemplate: PipelineTemplate }): object {
    const numbers = Array.from({ length: count }, (_, index) => index);
    let response = numbers.map((number) => ({
      pipeline_template_id: `${number}`,
      pipeline_template_name: `unittest_pipeline_template${number}`,
      pipeline_template_description: `Description for unittest_pipeline_template${number}`,
      version: `0`,
      _history: {
        createdBy: {
          userRef: v4(),
          email: "foo@example.com",
        },
        createdTimestamp: new Date().toISOString(),
      },
    }))
    return {"newItems": response};
}
