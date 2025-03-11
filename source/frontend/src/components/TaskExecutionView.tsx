/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { Container, Header, Textarea, Tabs } from "@cloudscape-design/components";

type TaskExecutionViewParams = {
  schema: Record<string, any>;
  handleTabChange: (arg0: string) => void;
  selectedTab: any;
  taskExecution: any;
  dataAll: any;
};
const TaskExecutionView = (props: TaskExecutionViewParams) => {
  function handleOnTabChange(activeTabId: string) {
    if (props.handleTabChange) {
      props.handleTabChange(activeTabId);
    }
  }

  function selectedTab() {
    if (props.selectedTab) {
      return props.selectedTab;
    } else {
      return null;
    }
  }

  return (
    <Tabs
      activeTabId={selectedTab()}
      onChange={({ detail }) => handleOnTabChange(detail.activeTabId)}
      tabs={[
        {
          label: "Log",
          id: "log",
          content: (
            <Container header={<Header variant="h2">Log</Header>}>
              <Textarea value={props.taskExecution.output} rows={12} readOnly />
            </Container>
          ),
        },
        {
          label: "Inputs",
          id: "inputs",
          content: (
            <Container header={<Header variant="h2">Task Execution Inputs</Header>}>
              <pre>
                <code>{JSON.stringify(props.taskExecution.task_execution_inputs, null, " ")}</code>
              </pre>
            </Container>
          ),
        },
      ]}
      // variant="container"
    />
  );
};

export default TaskExecutionView;
