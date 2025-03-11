import React from "react";
import {fireEvent, render, screen, waitFor, waitForElementToBeRemoved, within} from "@testing-library/react";
import { PipelineTemplateVisualEditorWrapper } from "./UserPipelineTemplateVisualEditor";
import { PipelineTemplate, PipelineTemplateTask, Task } from "../models/Pipeline";
import {
  addPipelineTemplateTasksToPipelineTemplates,
  generateTestPipelineTemplates,
  generateTestPipelineTemplateTasksWithSuccessors,
  generateTestTasks,
} from "../__tests__/mocks/user_api.ts";
import { defaultSchemas } from "../../test_data/default_schema.ts";
import { mockNotificationContext } from "../__tests__/TestUtils";
import userEvent from "@testing-library/user-event";
import { NotificationContext } from "../contexts/NotificationContext";
import '@testing-library/jest-dom';
import {Position} from "@xyflow/react";
import {server} from "../setupTests.ts";
import {rest} from "msw";

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
  const twoTasks: Task[] = generateTestTasks(2);
  const twoPipelineTemplatesAndTasks: PipelineTemplateTask[] = generateTestPipelineTemplateTasksWithSuccessors(
    pipelineTemplates,
    twoTasks
  );

  const pipelineTemplateUnderTest: PipelineTemplate = addPipelineTemplateTasksToPipelineTemplates(
    pipelineTemplates,
    pipelineTemplatesAndTasks
  )[0];

  const pipelineTemplateUnderTestTwo: PipelineTemplate = addPipelineTemplateTasksToPipelineTemplates(
    pipelineTemplates,
    twoPipelineTemplatesAndTasks
  )[0];

  // Mock data for testing
  const defaultProps = {
    schemaName: "pipeline_template_task",
    schemas: defaultSchemas,
    userEntityAccess: { mockUserEntityAccess },
    handleRefresh: mockHandleRefresh,
    pipelineTemplate: pipelineTemplateUnderTest,
  };

  const defaultPropsTwo = {
    schemaName: "pipeline_template_task",
    schemas: defaultSchemas,
    userEntityAccess: { mockUserEntityAccess },
    handleRefresh: mockHandleRefresh,
    pipelineTemplate: pipelineTemplateUnderTestTwo,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderComponent = (props = {}) => {
    return {
      ...mockNotificationContext,
      renderResult: render(
        <NotificationContext.Provider value={mockNotificationContext}>
          <PipelineTemplateVisualEditorWrapper {...defaultProps} {...props} />
        </NotificationContext.Provider>
      ),
    };
  };

  /**
   * Helper function to get the custom nodes rendered in the visual editor
   * @returns {HTMLElement[]} - Array of custom nodes
   */
  const getAllNodes = (): HTMLElement[] => {
    const container = screen.getByTestId('rf__wrapper');
    return within(container).getAllByTestId(/^rf__node-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
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

  it("handles direction change", async () => {
    // GIVEN
    const { addNotification, renderResult } = renderComponent();
    const user = userEvent.setup();
    // @ts-ignore
    const nodeId = pipelineTemplateUnderTest.pipeline_template_tasks[0].pipeline_template_task_id;
    const directionButton = screen.getByRole("button", { name: /toggle layout direction/i });

    // WHEN find the target and source handles
    const targetHandleTB = document.querySelector(`[data-nodeid="${nodeId}"][data-id$="-target"]`);
    const sourceHandleTB = document.querySelector(`[data-nodeid="${nodeId}"][data-id$="-source"]`);

    // THEN Assert that handles are found and have Top and Bottom values
    expect(targetHandleTB).not.toBeNull();
    expect(sourceHandleTB).not.toBeNull();
    // Assert target handle position
    expect(targetHandleTB).toHaveAttribute('data-handlepos', Position.Top);
    expect(sourceHandleTB).toHaveAttribute('data-handlepos', Position.Bottom);

    //WHEN the user clicks the toggle direction button
    await user.click(directionButton);
    screen.logTestingPlaygroundURL();
    const targetHandleLR = document.querySelector(`[data-nodeid="${nodeId}"][data-id$="-target"]`);
    const sourceHandleLR = document.querySelector(`[data-nodeid="${nodeId}"][data-id$="-source"]`);

    // THEN expect the React flow direction to be changed
    expect(targetHandleLR).not.toBeNull();
    expect(sourceHandleLR).not.toBeNull();
    // Assert target handle position
    expect(targetHandleLR).toHaveAttribute('data-handlepos', Position.Left);
    expect(sourceHandleLR).toHaveAttribute('data-handlepos', Position.Right);
  });

  it("handles edit task button click and cancels the change", async () => {
    // GIVEN
    renderComponent();
    const editButton = screen.getByRole("button", { name: "Edit" });
    expect(editButton).toBeDisabled();
    const user = userEvent.setup();

    // WHEN the pipeline_template has a pipeline_template_task
    // @ts-ignore
    const nodeId = "rf__node-" + pipelineTemplateUnderTest.pipeline_template_tasks[0].pipeline_template_task_id;
    const node = await screen.findByTestId(nodeId);

    // THEN expect the node to be in the visual editor document with the correct class and attributes
    expect(node).not.toBeNull();
    expect(node).toBeInTheDocument();
    expect(node).toHaveClass('react-flow__node', 'react-flow__node-task', 'nopan', 'selectable', 'draggable');
    expect(node).toHaveAttribute('role', 'button');
    expect(node.ownerDocument).toBe(document);
    expect(document.body.contains(node)).toBe(true);

    // WHEN the user selects the node
    fireEvent.click(node);

    // THEN expect the edit button to be enabled
    expect(editButton).toBeEnabled();

    //AND WHEN the user clicks the edit button
    await user.click(editButton)
    // THEN expect a dialog box pops up
    await screen.findByRole("dialog");
    const popupDialog = screen.getByRole("dialog");
    expect(within(popupDialog).getByRole("heading", { name: "Edit pipeline Template Task" })).toBeInTheDocument();
    expect(within(popupDialog).getByRole("button", { name: /save/i })).toBeInTheDocument();
    expect(within(popupDialog).getByRole("button", { name: /cancel/i })).toBeInTheDocument();

    // WHEN clicking the cancel button
    const cancelButton = within(popupDialog).getByRole("button", { name: /cancel/i });
    fireEvent.click(cancelButton);

    // THEN expect the pop-up dialog disappear and node be in the document
    expect(popupDialog).not.toBeInTheDocument();
    expect(node).toBeInTheDocument();
  });

  it("handles delete task button click and cancel delete", async () => {
    // GIVEN
    renderComponent();
    const deleteButton = screen.getByRole("button", { name: "Delete" });
    const user = userEvent.setup();

    // THEN expect the delete button to be disabled initially
    expect(deleteButton).toBeDisabled();

    // WHEN the pipeline_template has a pipeline_template_task
    // @ts-ignore
    const nodeId = "rf__node-" + pipelineTemplateUnderTest.pipeline_template_tasks[0].pipeline_template_task_id;
    const node = await screen.findByTestId(nodeId);

    // THEN expect the node to be in the visual editor document with the correct class and attributes
    expect(node).not.toBeNull();
    expect(node).toBeInTheDocument();
    expect(node).toHaveClass('react-flow__node', 'react-flow__node-task', 'nopan', 'selectable', 'draggable');
    expect(node).toHaveAttribute('role', 'button');
    expect(node.ownerDocument).toBe(document);
    expect(document.body.contains(node)).toBe(true);

    // WHEN the user selects the node
    // Note: user.click(node) cannot be used here, because the node is hidden/not-user-interactable
    fireEvent.click(node);

    // THEN expect the delete button to be enabled
    expect(deleteButton).toBeEnabled();

    //AND WHEN the user clicks the delete button
    await user.click(deleteButton)

    // THEN expect a confirmation dialog to appear
    // @ts-ignore
    const task_name = pipelineTemplateUnderTest.pipeline_template_tasks[0].pipeline_template_task_name;
    const dialog = within(await screen.findByRole("dialog"));
    expect(await dialog.findByText(/Are you sure you wish to delete the task.*\?/)).toBeInTheDocument();

    // WHEN the user cancels the deletion by clicking on the Cancel button
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    // THEN expect the task be in the document
    expect(node).toBeInTheDocument();
  });

  it("handles delete task button click and confirm delete", async () => {
    // GIVEN
    const { addNotification, renderResult } = renderComponent();
    const deleteButton = screen.getByRole("button", { name: "Delete" });
    const user = userEvent.setup();

    server.use(
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response.once(context.status(200), context.json(pipelineTemplateUnderTest));
      }),
      // second request to same endpoint gives a different response
      rest.get("/user/pipeline_template_task", (request, response, context) => {
        return response.once(context.status(200), context.json(pipelineTemplateUnderTest));
      }),
      // second request to same endpoint gives a different response
      rest.delete(`/user/pipeline_template_task/:id`, (request, response, context) => {
        return response(context.status(204));
      }),
      // second request to same endpoint gives a different response
      rest.get("/user/pipeline_template_task", (request, response, context) => {
        return response.once(context.status(200), context.json(pipelineTemplateUnderTestTwo));
      })
    );


    // THEN expect the delete button to be disabled initially and 3 pipeline_template_tasks are listed
    expect(deleteButton).toBeDisabled();
    let nodeCount = getAllNodes().length;
    expect(nodeCount).toBe(3);

    // WHEN the pipeline_template has a pipeline_template_task
    // @ts-ignore
    const nodeId = "rf__node-" + pipelineTemplateUnderTest.pipeline_template_tasks[0].pipeline_template_task_id;
    const node = await screen.findByTestId(nodeId);

    // THEN expect the node to be in the visual editor document with the correct class and attributes
    expect(node).not.toBeNull();
    expect(node).toBeInTheDocument();
    expect(node).toHaveClass('react-flow__node', 'react-flow__node-task', 'nopan', 'selectable', 'draggable');
    expect(node).toHaveAttribute('role', 'button');

    // WHEN the user selects the node
    // Note: user.click(node) cannot be used here, because the node is hidden/not-user-interactable
    fireEvent.click(node);

    // THEN expect the delete button to be enabled
    expect(deleteButton).toBeEnabled();

    //AND WHEN the user clicks the delete button
    await user.click(deleteButton)

    // THEN expect a confirmation dialog to appear
    // @ts-ignore
    const dialog = within(await screen.findByRole("dialog"));
    expect(await dialog.findByText(/Are you sure you wish to delete the task.*\?/)).toBeInTheDocument();

    // WHEN the user cancels the deletion by clicking on the Cancel button
    await user.click(screen.getByRole("button", { name: "Ok" }));

    // wait for the screen to update
    await screen.findByRole("heading", { name: pipelineTemplateUnderTest.pipeline_template_name });
    // THEN render a pipeline_template with two pipeline_template_tasks
    // @ts-ignore
    renderResult.rerender(
      <NotificationContext.Provider value={mockNotificationContext}>
        <PipelineTemplateVisualEditorWrapper {...defaultPropsTwo} />
      </NotificationContext.Provider>
    );
    // THEN expect the third task be deleted
    nodeCount = getAllNodes().length;
    expect(nodeCount).toBe(2);
  });

  it("handles edit task button click and saves the change", async () => {
    // GIVEN
    const { addNotification } = renderComponent();
    const editButton = screen.getByRole("button", { name: "Edit" });
    expect(editButton).toBeDisabled();
    const user = userEvent.setup();

    // WHEN the pipeline_template has a pipeline_template_task
    // @ts-ignore
    const nodeId = "rf__node-" + pipelineTemplateUnderTest.pipeline_template_tasks[0].pipeline_template_task_id;
    // @ts-ignore
    const node = await screen.findByTestId(nodeId);

    // THEN expect the node to be in the visual editor document with the correct class and attributes
    expect(node).not.toBeNull();
    expect(node).toBeInTheDocument();
    expect(node).toHaveClass('react-flow__node', 'react-flow__node-task', 'nopan', 'selectable', 'draggable');
    expect(node).toHaveAttribute('role', 'button');
    expect(node.ownerDocument).toBe(document);
    expect(document.body.contains(node)).toBe(true);

    // WHEN the user selects the node
    fireEvent.click(node);

    // THEN expect the edit button to be enabled
    expect(editButton).toBeEnabled();

    //AND WHEN the user clicks the edit button
    await user.click(editButton);

    // THEN expect a dialog box pops up
    await screen.findByRole("dialog");
    const popupDialog = screen.getByRole("dialog");
    expect(within(popupDialog).getByRole("heading", { name: "Edit pipeline Template Task" })).toBeInTheDocument();
    expect(within(popupDialog).getByRole("button", { name: /save/i })).toBeInTheDocument();
    expect(within(popupDialog).getByRole("button", { name: /cancel/i })).toBeInTheDocument();

    //const templateTaskName = within(node).getByText(nodeName);
    //console.log(templateTaskName);
    //screen.logTestingPlaygroundURL(templateTaskName)
    //const inputElement = within(templateTaskName).getByRole('textbox');
    const inputElement = within(popupDialog).getByRole('textbox', { name: /task_sequence_number/i });
    // expect inputElement to be defined and not null
    expect(inputElement).not.toBeNull();
    expect(inputElement).toBeDefined();

    // @ts-ignore
    await user.type(inputElement, '-some-edit');
    const saveButton = within(popupDialog).getByRole("button", { name: /save/i });
    await user.click(saveButton);

    // WHEN the user selects to edit the node
    fireEvent.click(node);
    await user.click(editButton);

    // THEN expect a dialog box pops up
    const dialog= await screen.findByRole("dialog");
    const input = within(popupDialog).getByRole('textbox', { name: /task_sequence_number/i });
    expect(input).toHaveValue("-some-edit");
  });

});
