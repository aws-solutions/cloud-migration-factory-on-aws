import React from "react";
import { Container, Header, Textarea, Tabs, ColumnLayout, SpaceBetween, Box } from "@cloudscape-design/components";

type TaskExecutionViewParams = {
  schema: Record<string, any>;
  handleTabChange: (arg0: string) => void;
  selectedTab: any;
  taskExecution: any;
  dataAll: any;
  pipelineMetadata: any;
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

  // Helper function to render email lists
  const renderEmailList = (emails: any[]) => {
    if (!emails || emails.length === 0) return null;
    return emails.map((item: any) => item.email || item.group_name).join(', ');
  };

  // Find the task level email settings for this task
  const taskEmailSettings = props.pipelineMetadata?.task_level_email_settings?.find(
    (recipient: any) => recipient.task_name === props.taskExecution.task_execution_name
  );

  console.log(`CHILD PIPELINE METADATA: ${JSON.stringify(props.pipelineMetadata)}`);

  const emailNotificationContent = (
    <Container header={<Header variant="h2">Email Notification Settings</Header>}>
      <ColumnLayout columns={2} variant="text-grid">
        <SpaceBetween size="l">
          {props.pipelineMetadata?.pipeline_default_email_recipients?.length > 0 && (
            <div>
              <Box variant="awsui-key-label">Default Email Recipients</Box>
              <div>{renderEmailList(props.pipelineMetadata.pipeline_default_email_recipients)}</div>
            </div>
          )}
          {props.pipelineMetadata?.pipeline_default_email_groups?.length > 0 && (
            <div>
              <Box variant="awsui-key-label">Default Email Groups</Box>
              <div>{renderEmailList(props.pipelineMetadata.pipeline_default_email_groups)}</div>
            </div>
          )}
          {taskEmailSettings && (
            <>
              <div>
                <Box variant="awsui-key-label">Email Notifications Enabled</Box>
                <div>{taskEmailSettings.enabled ? 'Yes' : 'No'}</div>
              </div>
              <div>
                <Box variant="awsui-key-label">Override Defaults</Box>
                <div>{taskEmailSettings.override_defaults ? 'Yes' : 'No'}</div>
              </div>
            </>
          )}
        </SpaceBetween>
        <SpaceBetween size="l">
          {taskEmailSettings?.email_users?.length > 0 && (
            <div>
              <Box variant="awsui-key-label">Task Email Recipients</Box>
              <div>{renderEmailList(taskEmailSettings.email_users)}</div>
            </div>
          )}
          {taskEmailSettings?.email_groups?.length > 0 && (
            <div>
              <Box variant="awsui-key-label">Task Email Groups</Box>
              <div>{renderEmailList(taskEmailSettings.email_groups)}</div>
            </div>
          )}
          {taskEmailSettings?.email_body && (
            <div>
              <Box variant="awsui-key-label">Email Body</Box>
              <div>{taskEmailSettings.email_body}</div>
            </div>
          )}
        </SpaceBetween>
      </ColumnLayout>
    </Container>
  );

  return (
    <Tabs
      activeTabId={selectedTab()}
      onChange={({ detail }) => handleOnTabChange(detail.activeTabId)}
      tabs={[
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
          label: "Email Notification Settings",
          id: "email",
          content: emailNotificationContent
        }
      ]}
    />
  );
};

export default TaskExecutionView;
