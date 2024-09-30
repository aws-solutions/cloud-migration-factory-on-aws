/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useEffect, useState } from "react";
import { ColumnLayout, Container, Header, SpaceBetween, SplitPanel, Tabs } from "@cloudscape-design/components";

import UserApiClient from "../api_clients/userApiClient";
import Audit from "../components/ui_attributes/Audit";
import ItemTable from "./ItemTable";
import TaskExecutionView from "../components/TaskExecutionView";
import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import { ValueWithLabel } from "./ui_attributes/ValueWithLabel";
import { parsePUTResponseErrors } from "../resources/recordFunctions";
import { NotificationContext } from "../contexts/NotificationContext";
import { SplitPanelContext } from "../contexts/SplitPanelContext";
import { EntitySchema } from "../models/EntitySchema";
import {PipelineVisualManagerWrapper} from "./UserPipelineVisualManager.tsx";
import {TaskExecution} from "../models/Pipeline.ts";

export const ViewTaskExecution = (props: {
  schema: Record<string, EntitySchema>;
  taskExecution: any;
  dataAll: any;
}) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState("inputs");

  return (
    <SplitPanel header={props.taskExecution.task_execution_name} hidePreferencesButton>
      <TaskExecutionView
        schema={props.schema}
        taskExecution={props.taskExecution}
        handleTabChange={setViewerCurrentTab}
        dataAll={props.dataAll}
        selectedTab={viewerCurrentTab}
      />
    </SplitPanel>
  );
};

type PipelineViewParams = {
  schema: Record<string, any>;
  handleTabChange: (arg0: string) => void;
  selectedTab: any;
  pipeline: {
    pipeline_name: string;
    pipeline_id: string;
  };
  taskExecutions: any;
  dataAll: any;
  taskExecutionsRefresh: any;
  tasksRefresh: any;
  userEntityAccess: any;
};

type PipelineViewerContent = {
    pipeline_name: string;
    pipeline_id: string;
    pipeline_tasks: TaskExecution[]
}

const PipelineView = (props: PipelineViewParams) => {
  const { addNotification, deleteNotification } = useContext(NotificationContext);
  const { setContent, setSplitPanelOpen } = useContext(SplitPanelContext);
  const [ pipelineVisualContent, setPipelineVisualContent ] = useState<PipelineViewerContent>();
  const apiUser = new UserApiClient();

  const [selectedTaskExecutions, setSelectedTaskExecutions] = useState<Array<any>>([]);

  const allowStatusUpdateToSkip = ["Failed"];
  const allowStatusUpdateToInProgress = ["Not Started"];
  const allowStatusUpdateToRetry = ["Failed", "Complete", "Skip"];
  const allowStatusUpdateToComplete = ["Pending Approval"]

  useEffect(() => {
    // Set split panel content to undefined so it doesn't show on pipeline change
    return function cleanup() {
      setContent(undefined);
    };
  }, []);

  useEffect(() => {
    if (selectedTaskExecutions[0] && props.pipeline.pipeline_id !== selectedTaskExecutions[0].pipeline_id) {
      setContent(undefined);
      setSelectedTaskExecutions([]);
    }
  }, [props.pipeline]);

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

  const handleAction = async (event: CustomEvent) => {
    switch (event.detail.id) {
      case 'view_inputs':
        setSplitPanelOpen(true);
        break;
      case 'update_status_skip':
      case 'update_status_retry':
      case 'update_status_complete':
      case 'update_status_in-progress':
        await handleTaskExecutionStatusChange(event.detail.id);
        break;
    }
  };

  async function handleTaskExecutionStatusChange(action: 'update_status_skip' | 'update_status_retry' | 'update_status_complete' | 'update_status_in-progress') {
    const schemaName = "task_execution";
    const humanReadableSchemaName = schemaName.split("_").join(" ");
    const selectedItem = selectedTaskExecutions[0];
    const statusMap = {
      'update_status_skip': "Skip",
      'update_status_retry': "Retry",
      'update_status_complete': "Complete",
      'update_status_in-progress': "In Progress"
    }

    if (!statusMap[action]) {
      addNotification({
        type: "error",
        dismissible: true,
        header: "Update " + humanReadableSchemaName,
        content: "Invalid status change.",
      });
    }

    const loadingNotificationId = addNotification({
      type: "success",
      loading: true,
      dismissible: true,
      content: `Updating ${selectedItem.task_execution_name} to ${statusMap[action]}.`,
    });

    try {
      await apiUser.putItem(
        selectedItem.task_execution_id,
        {
          task_execution_status: statusMap[action],
        },
        schemaName
      );

      addNotification({
        type: "success",
        dismissible: true,
        header: "Update " + humanReadableSchemaName,
        content: selectedItem.task_execution_name + " updated successfully.",
      });

      props.taskExecutionsRefresh();
    } catch (e: any) {
      let errorsReturned = e.message;
      if (e.response?.data?.errors) {
        const errorResponse = e.response.data.errors;
        console.debug("PUT " + humanReadableSchemaName + " errors");
        console.debug(errorResponse);
        errorsReturned = parsePUTResponseErrors(errorResponse).join(",");
      }

      addNotification({
        type: "error",
        dismissible: true,
        header: "Update " + humanReadableSchemaName,
        content: errorsReturned,
      });
    } finally {
      deleteNotification(loadingNotificationId);
    }
  }

  function handleTaskExecutionSelectionChange(selection: Array<any>) {
    if (selection){
      setSelectedTaskExecutions(selection);
      setContent(
        <ViewTaskExecution
          schema={props.schema}
          taskExecution={selection[0]}
          dataAll={props.dataAll}
        />
      );
    }
  }

  function shouldDisableTaskExecutionStatusChange(action: string) {
    if (selectedTaskExecutions.length === 0 || selectedTaskExecutions.length > 1) {
      return true;
    }

    switch (action) {
      case 'update_status_skip':
        return !allowStatusUpdateToSkip.includes(selectedTaskExecutions[0].task_execution_status);
      case 'update_status_retry':
        return !allowStatusUpdateToRetry.includes(selectedTaskExecutions[0].task_execution_status);
      case 'update_status_in-progress':
        return !allowStatusUpdateToInProgress.includes(selectedTaskExecutions[0].task_execution_status);
      case 'update_status_complete':
        return !allowStatusUpdateToComplete.includes(selectedTaskExecutions[0].task_execution_status);
      default:
        return true;
    }
  }

  function resolveScripts() {
    return props.taskExecutions.map((task: any) => {
      const task_script = props.dataAll.script.data.find((script: any) => {
        return task.task_id === script.package_uuid;
      });
      return {...task, 'script': task_script}
    });
  }

  useEffect(() => {
    setPipelineVisualContent({...props.pipeline, 'pipeline_tasks': resolveScripts()})
  }, [props.pipeline, props.taskExecutions]);

  return (
    <Tabs
      activeTabId={selectedTab()}
      onChange={({ detail }) => handleOnTabChange(detail.activeTabId)}
      tabs={[
        {
          label: "Details",
          id: "details",
          content: (
            <Container header={<Header variant="h2">Details</Header>}>
              <ColumnLayout columns={2} variant="text-grid">
                <SpaceBetween size="l">
                  <ValueWithLabel label="Pipeline Name">{props.pipeline.pipeline_name}</ValueWithLabel>
                  <Audit item={props.pipeline} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
        {
          label: "Manage",
          id: "visual",
          content: (
            <PipelineVisualManagerWrapper
              schemas={props.schema.pipeline}
              schemaName={"pipeline"}
              templateData={pipelineVisualContent}
              handleRefreshTasks={props.taskExecutionsRefresh}
            />
          ),
        },
        {
          label: "Tasks",
          id: "task_executions",
          content: (
            <ItemTable
              schema={props.schema.task_execution}
              schemaName={"task_execution"}
              schemaKeyAttribute={"task_execution_id"}
              items={props.taskExecutions}
              dataAll={props.dataAll}
              isLoading={props.dataAll.task_execution.isLoading}
              errorLoading={props.dataAll.task_execution.error}
              handleSelectionChange={handleTaskExecutionSelectionChange}
              selectedItems={selectedTaskExecutions}
              // for now disable multi select, but can easily add batch calling later
              selectionType="single"
              actionsButtonDisabled={!props.taskExecutions || props.taskExecutions.length === 0}
              handleAction={handleAction}
              handleRefreshClick={props.taskExecutionsRefresh}
              actionItems={[
                {
                  id: "view_inputs",
                  text: "View Inputs & Logs",
                },
                {
                  id: "update_status",
                  text: "Update Status",
                  items: [
                    {
                      id: "update_status_skip",
                      text: "Skip",
                      disabled: shouldDisableTaskExecutionStatusChange('update_status_skip'),
                    },
                    {
                      id: "update_status_retry",
                      text: "Retry",
                      disabled: shouldDisableTaskExecutionStatusChange('update_status_retry'),
                    },
                    {
                      id: "update_status_complete",
                      text: "Complete",
                      disabled: shouldDisableTaskExecutionStatusChange('update_status_complete'),
                    },
                    {
                      id: "update_status_in-progress",
                      text: "In Progress",
                      disabled: shouldDisableTaskExecutionStatusChange('pdate_status_in-progress'),
                    },
                  ],
                },
              ]}
            />
          ),
        },
        {
          label: "All attributes",
          id: "attributes",
          content: (
            <Container header={<Header variant="h2">All attributes</Header>}>
              <ColumnLayout columns={2} variant="text-grid">
                <SpaceBetween size="l">
                  <AllViewerAttributes
                    schema={props.schema.pipeline}
                    schemas={props.schema}
                    item={props.pipeline}
                    dataAll={props.dataAll}
                  />
                  <Audit item={props.pipeline} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
      ]}
      // variant="container"
    />
  );
};

export default PipelineView;
