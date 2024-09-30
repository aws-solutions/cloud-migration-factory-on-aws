/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from "react";
import { ColumnLayout, Container, Header, SpaceBetween, Tabs } from "@cloudscape-design/components";

import Audit from "../components/ui_attributes/Audit";
import ItemTable from "./ItemTable";
import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import { ValueWithLabel } from "./ui_attributes/ValueWithLabel";
import {
  PipelineTemplateVisualEditorWrapper
} from "./UserPipelineTemplateVisualEditor.tsx";

type PipelineTemplateViewParams = {
  schema: Record<string, any>;
  handleTabChange: (arg0: string) => void;
  selectedTab: any;
  pipelineTemplate: {
    pipeline_template_name: string;
    pipeline_template_description: string;
  };
  pipelineTemplateTasks: any;
  pipelineTemplateTasksRefresh: any;
  dataAll: any;
  userEntityAccess: any;
};
const PipelineTemplateView = (props: PipelineTemplateViewParams) => {
  const [pipelineTasksWithScripts, setPipelineTasksWithScripts] = useState(resolveScripts());
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

  function resolveScripts() {
    return props.pipelineTemplateTasks.map((task: any) => {
      const task_script = props.dataAll.script.data.find((script: any) => {
        return task.task_id === script.package_uuid;
      });
      return {...task, 'script': task_script}
    });
  }

  useEffect(() => {
    setPipelineTasksWithScripts(resolveScripts())
  }, [props.pipelineTemplateTasks]);

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
                  <ValueWithLabel label="Pipeline Template Name">
                    {props.pipelineTemplate.pipeline_template_name}
                  </ValueWithLabel>
                  <ValueWithLabel label="Pipeline Template Description">
                    {props.pipelineTemplate.pipeline_template_description}
                  </ValueWithLabel>
                  <Audit item={props.pipelineTemplate} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
        {
          label: "Pipeline Template Tasks",
          id: "pipeline_template_tasks",
          content: (
            <ItemTable
              schema={props.schema.pipeline_template_task}
              schemaName={"pipeline_template_task"}
              schemaKeyAttribute={"pipeline_template_task_id"}
              items={props.pipelineTemplateTasks}
              dataAll={props.dataAll}
              isLoading={props.dataAll.pipeline_template_task.isLoading}
              errorLoading={props.dataAll.pipeline_template_task.error}
              handleRefreshClick={props.pipelineTemplateTasksRefresh}
              handleSelectionChange={() => {}}
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
                    schema={props.schema.pipeline_template}
                    schemas={props.schema}
                    item={props.pipelineTemplate}
                    dataAll={props.dataAll}
                  />
                  <Audit item={props.pipelineTemplate} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
        {
          label: "Visual Task Editor",
          id: "visual",
          content: (
            <PipelineTemplateVisualEditorWrapper
              schemas={props.schema}
              schemaName={"pipeline_template_task"}
              pipelineTemplate={{...props.pipelineTemplate, 'pipeline_template_tasks': pipelineTasksWithScripts}}
              userEntityAccess={props.userEntityAccess}
              handleRefresh={props.pipelineTemplateTasksRefresh}
            />
          ),
        },
      ]}
      // variant="container"
    />
  );
};

export default PipelineTemplateView;
