import { defaultTestProps, mockNotificationContext, TEST_SESSION_STATE } from "../__tests__/TestUtils";
import { render, screen, waitFor, waitForElementToBeRemoved, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionContext } from "../contexts/SessionContext";
import React from "react";
import UserPipelineTable from "./UserTablePipelines";
import { server } from "../setupTests";
import { rest } from "msw";
import {
  generateTestPipelines,
  generateTestPipelineTemplates,
  generateTestPipelineTemplateTasks,
  generateTestTaskExecutions,
  generateTestTasks,
} from "../__tests__/mocks/user_api";
import userEvent from "@testing-library/user-event";
import { NotificationContext } from "../contexts/NotificationContext";
import { SplitPanelContext } from "../contexts/SplitPanelContext.tsx";

function renderUserPipelinesTable(props = defaultTestProps) {
  const mockSplitPanelContext = {
    setContent: jest.fn(),
    setContentFromSchema: jest.fn(),
    setSplitPanelOpen: jest.fn(),
    splitPanelState: {
      splitPanelOpen: false,
    },
  };

  return {
    ...mockNotificationContext,
    ...mockSplitPanelContext,
    renderResult: render(
      <MemoryRouter initialEntries={["/pipelines"]}>
        <NotificationContext.Provider value={mockNotificationContext}>
          <SplitPanelContext.Provider value={mockSplitPanelContext}>
            <SessionContext.Provider value={TEST_SESSION_STATE}>
              <div id="modal-root" />
              <UserPipelineTable {...props}></UserPipelineTable>
            </SessionContext.Provider>
          </SplitPanelContext.Provider>
        </NotificationContext.Provider>
      </MemoryRouter>
    ),
  };
}

test('it renders an empty table with "no pipelines" message', async () => {
  // WHEN
  renderUserPipelinesTable();

  // THEN
  // page should render in loading state
  expect(screen.getByRole("heading", { name: "Pipelines (0)" })).toBeInTheDocument();
  expect(screen.getByText("Loading pipelines")).toBeInTheDocument();

  // after server response came in, it should render the table
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipelines/i));

  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];

  expect(await within(tbody).findByText("No pipelines")).toBeInTheDocument();
  expect(within(tbody).getByRole("button", { name: "Add pipeline" })).toBeInTheDocument();
});

test("it renders a paginated table with 50 pipelines", async () => {
  // GIVEN
  server.use(
    rest.get("/user/pipeline", (request, response, context) => {
      return response(context.status(200), context.json(generateTestPipelines(50)));
    })
  );

  // WHEN
  renderUserPipelinesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipelines/i));

  // THEN
  expect(screen.getByRole("heading", { name: "Pipelines (50)" })).toBeInTheDocument();

  const table = screen.getByRole("table");
  const rows = within(table).getAllByRole("rowgroup")[1];

  // only 10 of the entries should be rendered, due to pagination
  // expected pipeline names are unittest_pipeline0, unittest_pipeline1, ...
  expect(within(rows).getAllByText(/unittest_pipeline\d+/)).toHaveLength(10);
});

test("click on refresh button refreshes the table", async () => {
  // GIVEN
  server.use(
    rest.get("/user/pipeline", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestPipelines(1)));
    }),
    // second request to same endpoint gives a different response
    rest.get("/user/pipeline", (request, response, context) => {
      return response.once(
        context.status(200),
        context.json(
          generateTestPipelines(5, {
            status: "In Progress",
          })
        )
      );
    })
  );

  renderUserPipelinesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipelines/i));
  expect(screen.getByRole("heading", { name: "Pipelines (1)" })).toBeInTheDocument();

  const refreshButton = screen.getByRole("button", { name: "Refresh" });

  // WHEN
  await userEvent.click(refreshButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipelines (5)" })).toBeInTheDocument();

  const table = screen.getByRole("table");
  const rows = within(table).getAllByRole("rowgroup")[1];
  expect(within(rows).getAllByText("In Progress")).toHaveLength(5);
});

// test('click on add button opens "Add pipeline" form', async () => {
//   // GIVEN
//   renderUserPipelinesTable();

//   const addButton = screen.getByRole('button', {name: "Add"});

//   // WHEN
//   await userEvent.click(addButton);

//   // THEN
//   expect(await screen.findByRole('heading', {name: "Add pipeline"})).toBeInTheDocument();

//   // AND WHEN
//   await userEvent.click(screen.getByRole('button', {name: /Cancel/i}));

//   // THEN
//   expect(await screen.findByRole('heading', {name: 'Pipelines (0)'})).toBeInTheDocument();
// });

// test('submitting the add form saves a new pipeline to API', async () => {
//   // GIVEN
//   let captureRequest: any;
//   server.use(
//     rest.get('/user/pipeline', (request, response, context) => {
//       return response(
//         context.status(200),
//         context.json(generateTestPipelines(2))
//       );
//     }),
//     rest.post(`/user/pipeline`, async (request, response, context) => {
//       request.json().then(body => captureRequest = body);
//       return response(
//         context.status(201),
//       );
//     }),
//     rest.get('/user/app', (request, response, context) => {
//       return response(
//         context.status(200),
//         context.json(generateTestApps(2))
//       );
//     }),
//   );

//   renderUserPipelinesTable();
//   const addButton = screen.getByRole('button', {name: "Add"});

//   // WHEN
//   await userEvent.click(addButton);

//   // THEN we see the Add form with a disabled save button until we enter valid values into all fields
//   expect(await screen.findByRole('button', {name: /Save/i})).not.toBeEnabled();
//   expect(screen.getAllByText('You must specify a valid value.')[0]).toBeInTheDocument();

//   // AND WHEN we populate all fields
//   await userEvent.type(screen.getByRole('textbox', {name: 'Pipeline Name'}), 'my-test-pipeline');

//   await userEvent.click(screen.getByLabelText('Application'));
//   await userEvent.click(await screen.findByText('Unit testing App 1'));

//   await userEvent.click(screen.getByLabelText('Pipeline Type'));
//   await userEvent.click(await screen.findByText('db2'));

//   // THEN expect no more validation errors
//   expect(screen.queryByText('You must specify a valid value.')).not.toBeInTheDocument()

//   // AND WHEN we hit 'save'
//   await userEvent.click(await screen.findByRole('button', {name: /Save/i}));

//   // THEN verify the API has received the expected update request
//   await waitFor(() => {
//     expect(captureRequest.pipeline_name).toEqual('my-test-pipeline');
//   })
//   await screen.findByRole('heading', {name: 'Pipelines (2)'});
// });

test('"Tasks" tab shows task status and task level logs', async () => {
  // GIVEN
  const pipelineTemplates = generateTestPipelineTemplates(2);
  const tasks = generateTestTasks(3);
  const pipelineTemplateTasks = generateTestPipelineTemplateTasks(pipelineTemplates, tasks);
  const pipelines = generateTestPipelines(1, { status: "In Progress" }, pipelineTemplates[0], tasks);
  const taskExecutions = generateTestTaskExecutions(pipelines[0], tasks);

  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(pipelineTemplates));
    }),
    rest.get("/user/task", (request, response, context) => {
      return response(context.status(200), context.json(tasks));
    }),
    rest.get("/user/pipeline_template_task", (request, response, context) => {
      return response(context.status(200), context.json(pipelineTemplateTasks));
    }),
    rest.get("/user/pipeline", (request, response, context) => {
      return response(context.status(200), context.json(pipelines));
    }),
    rest.get("/user/task_execution", (request, response, context) => {
      return response(context.status(200), context.json(taskExecutions));
    })
  );

  const { setSplitPanelOpen, setContent, setContentFromSchema } = renderUserPipelinesTable();
  const pipelineRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(pipelineRowCheckbox);

  // THEN
  expect(screen.getByRole("heading", { name: "Details" })).toBeInTheDocument();
  // AND WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Tasks" }));

  // THEN
  const detailsView = screen.getByTestId("pipeline-details-view");
  expect(await within(detailsView).findByRole("heading", { name: "Task Executions (3)" })).toBeInTheDocument();

  const table = within(detailsView).getByRole("table");
  const rows = within(table).getAllByRole("rowgroup")[1];
  expect(within(rows).getAllByText("In Progress")).toHaveLength(1);
  expect(within(rows).getAllByText("Not Started")).toHaveLength(2);

  // AND WHEN
  await userEvent.click(within(rows).getAllByRole("radio")[0]);
  await userEvent.click(within(detailsView).getByRole("button", { name: "Actions" }));
  await userEvent.click(within(detailsView).getByRole("menuitem", { name: "View Inputs & Logs" }));

  screen.logTestingPlaygroundURL(detailsView);
  // THEN
  expect(setSplitPanelOpen).toHaveBeenCalledTimes(1);

  // setContent is called with the react component <ViewTaskExecution>, which is hard to exactly verify here.
  // we're verifying that setContent is called with some component that has received the pipeline and task data,
  // and rely on separate unit tests for ViewTaskExecution
  expect(setContent).toHaveBeenCalledWith(
    expect.objectContaining({
      props: expect.objectContaining({
        dataAll: expect.objectContaining({
          pipeline: expect.objectContaining({
            data: expect.arrayContaining([
              expect.objectContaining({
                pipeline_name: "unittest_pipeline0",
                task_arguments: expect.arrayContaining([
                  expect.objectContaining({
                    task_name: "unittest_task0",
                  }),
                  expect.objectContaining({
                    task_name: "unittest_task1",
                  }),
                  expect.objectContaining({
                    task_name: "unittest_task2",
                  }),
                ]),
              }),
            ]),
          }),
        }),
      }),
    })
  );

  // AND WHEN
});

test('click on row enables "Delete" button, shows "Delete" modal', async () => {
  // GIVEN
  server.use(
    rest.get("/user/pipeline", (request, response, context) => {
      return response(context.status(200), context.json(generateTestPipelines(1)));
    })
  );

  renderUserPipelinesTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const pipelineRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(pipelineRowCheckbox);

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipelines (1 of 1)" })).toBeInTheDocument();
  await waitFor(() => {
    expect(deleteButton).not.toBeDisabled();
  });

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(withinModal.getByRole("heading", { name: "Delete pipelines" })).toBeInTheDocument();
  expect(withinModal.getByText("Are you sure you wish to delete the 1 selected pipelines?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(withinModal.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipelines (1 of 1)" })).toBeInTheDocument();
});

test("confirming the deletion successfully deletes a pipeline", async () => {
  // GIVEN
  const pipelines = generateTestPipelines(1);
  server.use(
    rest.get("/user/pipeline", (request, response, context) => {
      return response.once(context.status(200), context.json(pipelines));
    }),
    rest.delete(`/user/pipeline/:id`, (request, response, context) => {
      return response(context.status(204));
    })
  );

  const { addNotification } = renderUserPipelinesTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const pipelineRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(pipelineRowCheckbox);
  await userEvent.click(deleteButton);
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    content: "unittest_pipeline0 was deleted.",
    dismissible: true,
    header: "pipeline deleted successfully",
    type: "success",
  });
  expect(await screen.findByRole("heading", { name: "Pipelines (0)" })).toBeInTheDocument();
});

test("delete multiple pipelines", async () => {
  // GIVEN
  const pipelines = generateTestPipelines(2);
  server.use(
    rest.get("/user/pipeline", (request, response, context) => {
      return response.once(context.status(200), context.json(pipelines));
    }),
    rest.delete(`/user/pipeline/:id`, (request, response, context) => {
      return response(context.status(204));
    })
  );

  const { addNotification } = renderUserPipelinesTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();
  await userEvent.click(deleteButton);

  const pipelineRowCheckBoxes = screen.getAllByRole("checkbox");

  // WHEN
  await userEvent.click(pipelineRowCheckBoxes[0]);

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipelines (2 of 2)" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(await withinModal.findByText("Are you sure you wish to delete the 2 selected pipelines?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    dismissible: false,
    header: "Deleting selected pipelines...",
    loading: true,
    type: "success",
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "unittest_pipeline0, unittest_pipeline1 were deleted.",
      dismissible: true,
      header: "pipeline deleted successfully",
      type: "success",
    });
  });
});

test("Pipeline manage screen displays", async () => {
  // GIVEN
  const pipelines = generateTestPipelines(1);
  server.use(
    rest.get("/user/pipeline", (request, response, context) => {
      return response.once(context.status(200), context.json(pipelines));
    }),
    rest.delete(`/user/pipeline/:id`, (request, response, context) => {
      return response(context.status(204));
    })
  );

  renderUserPipelinesTable();

  const pipelineRowCheckBoxes = screen.getAllByRole("checkbox");

  // WHEN
  await userEvent.click(pipelineRowCheckBoxes[0]);

  // THEN
  expect(screen.getByRole("heading", { name: "Details" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Manage" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "unittest_pipeline0" })).toBeInTheDocument();
});

// test('click on export downloads an xlsx file', async () => {
//   // GIVEN
//   jest.spyOn(XLSX, 'writeFile').mockImplementation(() => {
//   });
//   jest.spyOn(XLSX.utils, 'json_to_sheet');

//   const testPipelines = generateTestPipelines(2);
//   server.use(
//     rest.get('/user/pipeline', (request, response, context) => {
//       return response(
//         context.status(200),
//         context.json(testPipelines)
//       );
//     })
//   );
//   renderUserPipelinesTable();
//   await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipelines/i));

//   const exportButton = screen.getByRole('button', {name: "Download"});

//   // WHEN
//   await userEvent.click(exportButton);

//   // THEN
//   expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(1);
//   expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
// });

// test('selecting a row and click on export downloads an xlsx file', async () => {
//   // GIVEN
//   jest.spyOn(XLSX, 'writeFile').mockImplementation(() => {
//   });
//   jest.spyOn(XLSX.utils, 'json_to_sheet');

//   const testPipelines = generateTestPipelines(2);
//   server.use(
//     rest.get('/user/pipeline', (request, response, context) => {
//       return response(
//         context.status(200),
//         context.json(testPipelines)
//       );
//     })
//   );
//   renderUserPipelinesTable();
//   await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipelines/i));

//   await userEvent.click(screen.getAllByRole('row')[1]);
//   const exportButton = screen.getByRole('button', {name: "Download"});

//   // WHEN
//   await userEvent.click(exportButton);

//   // THEN
//   expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(1);
//   expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
// });

// test('buttons are disabled based on user permissions', async () => {
//   // GIVEN
//   server.use(
//     rest.get('/user/pipeline', (request, response, context) => {
//       return response(
//         context.status(200),
//         context.json(generateTestPipelines(2))
//       );
//     })
//   );

//   renderUserPipelinesTable({
//     ...defaultTestProps,
//     userEntityAccess: {
//       ...defaultTestProps.userEntityAccess,
//       pipeline: {
//         delete: false,
//         create: false,
//         update: false,
//         read: true,
//         attributes: []
//       },
//     }
//   });

//   // WHEN
//   await userEvent.click(screen.getByRole('checkbox'));

//   // THEN
//   expect(screen.getByRole('button', {name: "Add"})).toBeDisabled();
//   expect(screen.getByRole('button', {name: "Edit"})).toBeDisabled();
//   expect(screen.getByRole('button', {name: "Delete"})).toBeDisabled();
// });
