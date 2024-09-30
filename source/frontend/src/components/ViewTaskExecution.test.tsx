/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import React from "react";
import { ViewTaskExecution } from "./PipelineView.tsx";
import { render, screen } from "@testing-library/react";
import { defaultSchemas } from "../../test_data/default_schema.ts";
import {
  generateTestPipelines,
  generateTestPipelineTemplates,
  generateTestTaskExecutions,
  generateTestTasks,
} from "../__tests__/mocks/user_api.ts";
import { AppLayout } from "@cloudscape-design/components";
import userEvent from "@testing-library/user-event";

describe("ViewTaskExecution component", () => {
  const pipelineTemplates = generateTestPipelineTemplates(2);
  const tasks = generateTestTasks(3);
  const pipelines = generateTestPipelines(1, { status: "In Progress" }, pipelineTemplates[0], tasks);
  const taskExecutions = generateTestTaskExecutions(pipelines[0], tasks);
  const taskExecutionUnderTest = taskExecutions[0];

  it("should render the task execution inputs", async () => {
    // GIVEN

    // WHEN
    render(
      // component under test contains a SplitPanel which can only be rendered inside an AppLayout
      <AppLayout
        splitPanelOpen={true}
        onSplitPanelToggle={jest.fn}
        splitPanel={
          <ViewTaskExecution
            schema={defaultSchemas}
            taskExecution={taskExecutionUnderTest}
            dataAll={{}}
          />
        }
      ></AppLayout>
    );

    // THEN
    expect(await screen.findByRole("heading", { name: "Task Execution Inputs" })).toBeInTheDocument();
    expect(
      screen.getByText(
        /\{ "sizing_preference": "maximum utilization", "ec2_instance_family_exclusions": \[ "t2" ], "aws_region": "us-east-1", "home_region": "eu-central-1", "aws_accountid": "123456789012", "r_type": "retire" }/i
      )
    ).toBeInTheDocument();
  });

  it("should render the task execution logs", async () => {
    // GIVEN
    render(
      // component under test contains a SplitPanel which can only be rendered inside an AppLayout
      <AppLayout
        splitPanelOpen={true}
        onSplitPanelToggle={jest.fn}
        splitPanel={
          <ViewTaskExecution
            schema={defaultSchemas}
            taskExecution={taskExecutionUnderTest}
            dataAll={{}}
          />
        }
      ></AppLayout>
    );
    const tab = screen.getByRole("tab", { name: "Log" });

    // WHEN
    await userEvent.click(tab);

    // THEN
    const logHeading = await screen.findByRole("heading", { name: "Log" });
    expect(logHeading).toBeInTheDocument();
    expect(screen.getByText(/Output for unittest_task_execution0/i)).toBeInTheDocument();
  });
});
