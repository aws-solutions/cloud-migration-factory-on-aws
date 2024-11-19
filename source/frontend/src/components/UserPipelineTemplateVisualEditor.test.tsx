import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { PipelineTemplateVisualEditorWrapper } from "./UserPipelineTemplateVisualEditor";
import { PipelineTemplate, PipelineTemplateTask, Task } from "../models/Pipeline";
import {
  addPipelineTemplateTasksToPipelineTemplates,
  generateTestPipelineTemplates,
  generateTestPipelineTemplateTasksWithSuccessors,
  generateTestTasks,
} from "../__tests__/mocks/user_api.ts";
import { defaultSchemas } from "../../test_data/default_schema.ts";
import { mockNotificationContext } from "../__tests__/TestUtils.ts";

import { NotificationContext } from "../contexts/NotificationContext";

describe("PipelineTemplateVisualEditorWrapper", () => {
  const mockUserEntityAccess = {
    canEdit: true,
    canDelete: false,
    // Add other properties as needed
  };
  const mockHandleRefresh = jest.fn();
  const pipelineTemplates: PipelineTemplate[] = generateTestPipelineTemplates(1);
  const tasks: Task[] = generateTestTasks(3);
  const pipelineTemplatesAndTasks: PipelineTemplateTask[] = generateTestPipelineTemplateTasksWithSuccessors(
    pipelineTemplates,
    tasks
  );
  const pipelineTemplateUnderTest: PipelineTemplate = addPipelineTemplateTasksToPipelineTemplates(
    pipelineTemplates,
    pipelineTemplatesAndTasks
  )[0];

  // Mock data for testing
  const defaultProps = {
    schemaName: "pipeline_template_task",
    schemas: defaultSchemas,
    userEntityAccess: { mockUserEntityAccess },
    handleRefresh: mockHandleRefresh,
    pipelineTemplate: pipelineTemplateUnderTest,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderComponent = (props = {}) => {
    return render(
      <NotificationContext.Provider value={mockNotificationContext}>
        <PipelineTemplateVisualEditorWrapper {...defaultProps} {...props} />
      </NotificationContext.Provider>
    );
  };

  it("renders the visual editor when pipeline template is provided", () => {
    renderComponent();
    expect(screen.getByRole("heading", { name: pipelineTemplateUnderTest.pipeline_template_name })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /toggle layout direction/i })).toBeInTheDocument();
  });

  it("handles add task button click", async () => {
    // GIVEN
    renderComponent();
    const addButton = screen.getByRole("button", { name: "Add" });

    // WHEN
    fireEvent.click(addButton);

    // THEN
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toBeInTheDocument();
    screen.logTestingPlaygroundURL(dialog);
    expect(within(dialog).getByRole("heading", { name: "Add pipeline Template Task" })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /save/i })).toBeInTheDocument();
  });

  it("handles direction change", () => {
    renderComponent();
    const directionButton = screen.getByRole("button", { name: /toggle layout direction/i });
    fireEvent.click(directionButton);
    // Add assertions to check if the direction has changed
  });
});
