/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { rest } from "msw";
import { v4 } from "uuid";
import { Server } from "../../models/Server";
import { Database } from "../../models/Database";
import { Application } from "../../models/Application";
import { Wave } from "../../models/Wave";
import { Pipeline, PipelineTemplate, PipelineTemplateTask, Task, TaskExecution } from "../../models/Pipeline.ts";

export const mock_user_api = [
  rest.get("/user/server", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/user/database", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/user/pipeline", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/user/pipeline_template", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/user/pipeline_template_task", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/user/task", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/user/task_execution", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
];

// generate an array with the given number of server records
export function generateTestServers(count: number, data?: { appId: string }): Array<Server> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    server_os_family: "linux",
    app_id: data?.appId ?? `1`,
    server_name: `unittest${number}`,
    server_id: `${number}`,
    server_fqdn: `unittest${number}.testdomain.local`,
    _history: {
      createdBy: {
        userRef: v4(),
        email: "foo@example.com",
      },
      createdTimestamp: new Date().toISOString(),
    },
    r_type: "Rehost",
    server_os_version: "redhat",
  }));
}

export function generateTestApps(count: number, data?: { waveId: string }): Array<Application> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    aws_region: "us-east-2",
    app_id: `${number}`,
    _history: {
      createdBy: {
        userRef: "47237551-331e-44a8-a00b-67c739ce9676",
        email: "foo@example.com",
      },
      lastModifiedTimestamp: "2023-09-19T19:02:30.593821",
      lastModifiedBy: {
        userRef: "47237551-331e-44a8-a00b-67c739ce9676",
        email: "foo@example.com",
      },
      createdTimestamp: "2023-09-15T21:58:59.182564",
    },
    app_name: `Unit testing App ${number}`,
    wave_id: data?.waveId ?? "1",
    aws_accountid: "123456789012",
  }));
}

export function generateTestWaves(count: number, data?: { waveStatus: string }): Array<Wave> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    wave_id: `${number}`,
    wave_name: `Unit testing Wave ${number}`,
    wave_status: data?.waveStatus ?? undefined,
    _history: {
      createdBy: {
        userRef: "47237551-331e-44a8-a00b-67c739ce9676",
        email: "foo@example.com",
      },
      lastModifiedTimestamp: "2023-09-19T19:02:30.593821",
      lastModifiedBy: {
        userRef: "47237551-331e-44a8-a00b-67c739ce9676",
        email: "foo@example.com",
      },
      createdTimestamp: "2023-09-15T21:58:59.182564",
    },
  }));
}

export function generateTestDatabases(count: number, data?: { appId: string }): Array<Database> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    app_id: data?.appId ?? "1",
    database_type: "mysql",
    database_id: `${number}`,
    database_name: `unittest${number}`,
    _history: {
      createdBy: {
        userRef: v4(),
        email: "foo@example.com",
      },
      createdTimestamp: new Date().toISOString(),
    },
  }));
}

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
    deletion_protection: true,
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

export function generateTestDeleteProtectedPipelineTemplates(count: number): Array<PipelineTemplate> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    pipeline_template_id: v4(),
    pipeline_template_name: `unittest_pipeline_template${number}`,
    pipeline_template_description: `Description for unittest_pipeline_template${number}`,
    deletion_protection: true,
    version: `0`,
    _history: {
      createdBy: {
        userRef: v4(),
        email: "foo@example.com",
      },
      createdTimestamp: new Date().toISOString(),
    },
  }));
}

export function generateTestPipelineTemplateTasksWithSuccessors(
  pipelineTemplates: Array<PipelineTemplate>,
  tasks: Array<Task>
): PipelineTemplateTask[] {
  const pipelineTemplateTasks: Array<PipelineTemplateTask> = pipelineTemplates.flatMap((template, index) =>
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
  return addSuccessorsToPipelineTemplateTasks(pipelineTemplateTasks);
}

export function addPipelineTemplateTasksToPipelineTemplates(
  pipelineTemplates: Array<PipelineTemplate>,
  pipelineTemplateTasks: Array<PipelineTemplateTask>
): PipelineTemplate[] {
  // for each PipelineTemplate add the PipelineTemplateTask array, which share the same pipeline_template_id
  return pipelineTemplates.map((template) => {
    const tasksForTemplate = pipelineTemplateTasks.filter(
      (task) => task.pipeline_template_id === template.pipeline_template_id
    );
    return {
      ...template,
      pipeline_template_tasks: tasksForTemplate,
    };
  });
}

/* for each pipeline+template_task except the last task, add a successor value to be the pipeline_template_task_id
 * of the next item
 * @param PipelineTemplateTask []
 * @returns PipelineTemplateTask [] with successors added
 * @example
 * const tasks = [
 *   { pipeline_template_task_id: 1, task_successors: [2] },
 *   { pipeline_template_task_id: 2, task_successors: [3] },
 *   { pipeline_template_task_id: 3, task_successors: [] | null | undefined },
 * ];
 */
function addSuccessorsToPipelineTemplateTasks(pTTasks: PipelineTemplateTask[]): PipelineTemplateTask[] {
  if (pTTasks.length <= 1) {
    return pTTasks; // No changes needed if there's only one or no tasks
  }

  return pTTasks.map((pTTask, index) => {
    if (index < pTTasks.length - 1) {
      const nextTaskId = pTTasks[index + 1].pipeline_template_task_id;
      return {
        ...pTTask,
        task_successors: [
          ...(pTTask.task_successors ?? []),
          nextTaskId
        ]
      };
    }
    return pTTask;
  });
}
