import React, { useMemo } from 'react';
import {
  Container,
  FormField,
  Header,
  SpaceBetween,
  Textarea,
  Toggle,
} from "@cloudscape-design/components";
import GroupsAttribute from './GroupsAttribute';

type TaskLevelEmailSettingsAttributeProps = {
  item: any;
  handleUserInput: (updates: any[]) => void;
  dataAll: any;
};

const taskLevelValidationError = 'You must specify either email recipients or email groups when override defaults is enabled';

export const TaskLevelEmailSettingsAttribute = ({
  item,
  handleUserInput,
  dataAll,
}: TaskLevelEmailSettingsAttributeProps) => {
  // Memoize filtered tasks to prevent unnecessary recalculations
  const tasks = useMemo(() =>
    dataAll.pipeline_template_task?.data.filter(
      (task: any) => task.pipeline_template_id === item.pipeline_template_id
    ) || [],
    [dataAll.pipeline_template_task?.data, item.pipeline_template_id]
  );

  const validateRecipients = (taskRecipients: any): string | null => {
    if (!taskRecipients.enabled || !taskRecipients.override_defaults) {
      return null;
    }

    const hasUsers = taskRecipients.email_users?.length > 0;
    const hasGroups = taskRecipients.email_groups?.length > 0;

    if (!hasUsers && !hasGroups) {
      return taskLevelValidationError;
    }

    return null;
  };

  const handleRecipientChange = (taskId: string, field: string, value: any) => {
    const updatedRecipients = [...(item.task_level_email_settings || [])];
    const existingIndex = updatedRecipients.findIndex(r => r.task_id === taskId);

    let updatedRecipient;
    if (existingIndex >= 0) {
      updatedRecipient = {
        ...updatedRecipients[existingIndex],
        [field]: value
      };
      updatedRecipients[existingIndex] = updatedRecipient;
    } else {
      const taskInfo = tasks.find((t: any) =>
        `${item.pipeline_name}:${t.pipeline_template_task_name}` === taskId
      );

      updatedRecipient = {
        task_id: taskId,
        task_name: taskInfo?.pipeline_template_task_name || '',
        email_users: field === 'email_users' ? value : [],
        email_groups: field === 'email_groups' ? value : [],
        email_body: field === 'email_body' ? value : '',
        enabled: field === 'enabled' ? value : false,
        override_defaults: field === 'override_defaults' ? value : false
      };
      updatedRecipients.push(updatedRecipient);
    }

    const validationError = validateRecipients(updatedRecipient);

    handleUserInput([{
      field: "task_level_email_settings",
      value: updatedRecipients,
      validationError
    }]);
  };

  const handleEnableAllTasks = (enabled: boolean) => {
    const updatedRecipients = tasks.map((task: any) => {
      const taskId = `${item.pipeline_name}:${task.pipeline_template_task_name}`;
      const existingRecipient = item.task_level_email_settings?.find(
        (r: any) => r.task_id === taskId
      );

      return {
        ...(existingRecipient || {
          task_id: taskId,
          task_name: task.pipeline_template_task_name,
          email_users: [],
          email_groups: [],
          email_body: '',
          override_defaults: false
        }),
        enabled
      };
    });

    // Validate all recipients
    const validationErrors = updatedRecipients.map(validateRecipients);
    const hasErrors = validationErrors.some((error: any) => error !== null);

    handleUserInput([{
      field: "task_level_email_settings",
      value: updatedRecipients,
      validationError: hasErrors ? 'Some tasks have incomplete email configurations' : null
    }]);
  };

  const validateEmailBody = (value: string): string | null => {
    if (value.length > 140) {
      return 'Email body must not exceed 140 characters';
    }
    return null;
  };

  // Calculate if all tasks have notifications enabled
  const allTasksEnabled = useMemo(() => {
    if (!tasks.length || !item.task_level_email_settings?.length) {
      return false;
    }

    return tasks.every((task: any) => {
      const taskId = `${item.pipeline_name}:${task.pipeline_template_task_name}`;
      const recipient = item.task_level_email_settings?.find(
        (r: any) => r.task_id === taskId
      );
      return recipient?.enabled;
    });
  }, [tasks, item.task_level_email_settings]);

  return (
    <Container
      header={
        <Header
          variant="h2"
          actions={
            <Toggle
              onChange={({ detail }) => handleEnableAllTasks(detail.checked)}
              checked={allTasksEnabled}
              data-testid="enable-all-task-notifications"
            >
              Enable All Task Notifications
            </Toggle>
          }
        >
          Task Level Email Notification Settings
        </Header>
      }
    >
      <SpaceBetween size="l">
        {tasks.map((task: any) => {
          const combinedTaskId = `${item.pipeline_name}:${task.pipeline_template_task_name}`;
          const taskRecipients = item.task_level_email_settings?.find(
            (r: any) => r.task_id === combinedTaskId
          ) || {
            task_id: combinedTaskId,
            task_name: task.pipeline_template_task_name,
            email_users: [],
            email_groups: [],
            email_body: '',
            enabled: false,
            override_defaults: false
          };

          const emailBodyError = validateEmailBody(taskRecipients.email_body || '');
          const hasUsers = taskRecipients.email_users?.length > 0;
          const hasGroups = taskRecipients.email_groups?.length > 0;
          const showValidationError = taskRecipients.enabled &&
            taskRecipients.override_defaults &&
            !hasUsers &&
            !hasGroups;
          const recipientsError = showValidationError ?
            taskLevelValidationError :
            undefined;

          return (
            <Container
              key={combinedTaskId}
              header={
                <Header
                  variant="h3"
                  actions={
                    <SpaceBetween direction="horizontal" size="xs">
                      <Toggle
                        onChange={({ detail }) => handleRecipientChange(
                          combinedTaskId,
                          'enabled',
                          detail.checked
                        )}
                        checked={taskRecipients.enabled}
                        data-testid={`enable-notifications-${combinedTaskId}`}
                      >
                        Enable email notifications
                      </Toggle>
                      {taskRecipients.enabled && (
                        <Toggle
                          onChange={({ detail }) => handleRecipientChange(
                            combinedTaskId,
                            'override_defaults',
                            detail.checked
                          )}
                          checked={taskRecipients.override_defaults}
                          data-testid={`override-defaults-${combinedTaskId}`}
                        >
                          Override defaults
                        </Toggle>
                      )}
                    </SpaceBetween>
                  }
                >
                  {task.pipeline_template_task_name || `Task ${task.task_id}`}
                </Header>
              }
            >
              {taskRecipients.enabled && taskRecipients.override_defaults && (
                <SpaceBetween size="l">
                  <FormField
                    errorText={recipientsError}
                  >
                    <GroupsAttribute
                      attribute={{
                        name: task.pipeline_template_task_name + 'users',
                        description: 'Email Recipients',
                        type: 'users',
                        listMultiSelect: true,
                        listValueAPI: '/admin/users'
                      }}
                      value={taskRecipients.email_users}
                      isReadonly={false}
                      returnErrorMessage={() => null}
                      handleUserInput={(attribute: any, value: any) => handleRecipientChange(
                        combinedTaskId,
                        'email_users',
                        value
                      )}
                      displayHelpInfoLink={() => undefined}
                      data-testid={`users-value-${combinedTaskId}`}
                    />
                  </FormField>
                  <FormField
                    errorText={recipientsError}
                  >
                    <GroupsAttribute
                      attribute={{
                        name: task.pipeline_template_task_name + 'groups',
                        description: 'Email Groups',
                        type: 'groups',
                        listMultiSelect: true,
                        listValueAPI: '/admin/groups'
                      }}
                      value={taskRecipients.email_groups}
                      isReadonly={false}
                      returnErrorMessage={() => null}
                      handleUserInput={(attribute: any, value: any) => handleRecipientChange(
                        combinedTaskId,
                        'email_groups',
                        value
                      )}
                      displayHelpInfoLink={() => undefined}
                      data-testid={`groups-value-${combinedTaskId}`}
                    />
                  </FormField>
                  <FormField
                    label="Email Body"
                    errorText={emailBodyError}
                  >
                    <Textarea
                      value={taskRecipients.email_body || ''}
                      onChange={({ detail }) => handleRecipientChange(
                        combinedTaskId,
                        'email_body',
                        detail.value
                      )}
                      placeholder="Enter email body text. Maximum 140 characters"
                      rows={3}
                      data-testid={`email-body-${combinedTaskId}`}
                    />
                  </FormField>
                </SpaceBetween>
              )}
            </Container>
          );
        })}
      </SpaceBetween>
    </Container>
  );
};
