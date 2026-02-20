/* eslint-disable @typescript-eslint/no-explicit-any */
import { wpmTestProps, mockNotificationContext, TEST_SESSION_STATE } from "../__tests__/TestUtils";
import { render, screen, waitFor, waitForElementToBeRemoved, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionContext } from "../contexts/SessionContext";
import UserTableWaves from "./UserTableWaves";
import { server } from "../setupTests";
import { rest } from "msw";
import {
  generateTestApps,
  generateTestDatabases,
  generateTestMoveGroups,
  generateTestWaves,
  generateTestWpmJobs,
  generateTestAppsWithWaveIds,
} from "../__tests__/mocks/user_api";
import userEvent from "@testing-library/user-event";
import * as XLSX from "xlsx";
import { NotificationContext } from "../contexts/NotificationContext";
import { ToolsContext } from "../contexts/ToolsContext";
import AuthenticatedRoutes from "../AuthenticatedRoutes";
import { Wave } from "../models";

function renderUserWavesTable(props = wpmTestProps) {
  return {
    ...mockNotificationContext,
    renderResult: render(
      <MemoryRouter initialEntries={["/waves"]}>
        <NotificationContext.Provider value={mockNotificationContext}>
          <SessionContext.Provider value={TEST_SESSION_STATE}>
            <div id="modal-root" />
            <UserTableWaves {...props}></UserTableWaves>
          </SessionContext.Provider>
        </NotificationContext.Provider>
      </MemoryRouter>
    ),
  };
}

function setupApiCallsForLoad(...waves: Wave[][]) {
  let mainGetCallCount = 0;
  server.use(
    rest.get("/user/wave", (request, response, context) => {
      const index = Math.min(mainGetCallCount++, waves.length - 1);
      return response(context.status(200), context.json(waves[index]));
    }),
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(generateTestDatabases(2)));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(2)));
    }),
    rest.get("/user/move_group", (request, response, context) => {
      return response(context.status(200), context.json(generateTestMoveGroups(2)));
    }),
    rest.get("/user/wpm_job", (request, response, context) => {
      return response(context.status(200), context.json(generateTestWpmJobs(1)));
    })
  );
}

function setupApiCallsForSave(operation: "post" | "put" | "delete", newItemForPost?: Wave) {
  const saveRequestBodies: any[] = [];
  const manageEntityRequestBodies: any[] = [];

  if (operation === "post") {
    server.use(
      rest.post(`/user/wave`, async (request, response, context) => {
        request.json().then((body) => saveRequestBodies.push(body));
        return response(context.status(200), context.json({ newItems: [newItemForPost] }));
      })
    );
  } else if (operation === "put") {
    server.use(
      rest.put(`/user/wave/:id`, async (request, response, context) => {
        request.json().then((body) => saveRequestBodies.push(body));
        return response(context.status(200));
      })
    );
  }

  server.use(
    rest.post("/manage-entities", (request, response, context) => {
      request.json().then((body) => manageEntityRequestBodies.push(body));
      return response(context.status(200), context.json({}));
    })
  );

  return {
    saveRequestBodies,
    manageEntityRequestBodies,
  };
}

test('it renders an empty table with "no waves" message', async () => {
  // WHEN
  setupApiCallsForLoad([]);
  renderUserWavesTable();

  // THEN
  // page should render in loading state
  expect(screen.getByRole("heading", { name: "Waves (0)" })).toBeInTheDocument();
  expect(screen.getByText("Loading Waves")).toBeInTheDocument();

  // after server response came in, it should render the table
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading waves/i));

  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];

  expect(await within(tbody).findByText("No Waves")).toBeInTheDocument();
  expect(within(tbody).getByRole("button", { name: "Add Wave" })).toBeInTheDocument();
});

test("it updates the help tools panel", async () => {
  // GIVEN
  setupApiCallsForLoad([]);
  const { renderResult } = renderUserWavesTable();

  const mockToolsContext = {
    setHelpPanelContent: jest.fn(),
    setHelpPanelContentFromSchema: jest.fn(),
    setToolsOpen: jest.fn(),
    toolsState: {
      toolsOpen: false,
      helpPanelContent: undefined,
    },
  };

  // WHEN re-rendering with different props
  renderResult.rerender(
    <MemoryRouter initialEntries={["/waves"]}>
      <NotificationContext.Provider value={mockNotificationContext}>
        <ToolsContext.Provider value={mockToolsContext}>
          <UserTableWaves {...wpmTestProps}></UserTableWaves>
        </ToolsContext.Provider>
      </NotificationContext.Provider>
    </MemoryRouter>
  );

  // THEN
  expect(mockToolsContext.setHelpPanelContentFromSchema).toHaveBeenCalledWith(wpmTestProps.schemas, "wave");
});

test("it renders a paginated table with 50 waves", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestWaves(50));

  // WHEN
  renderUserWavesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading waves/i));

  // THEN
  expect(screen.getByRole("heading", { name: "Waves (50)" })).toBeInTheDocument();

  const table = screen.getByRole("table");
  const rows = within(table).getAllByRole("rowgroup")[1];

  // only 10 of the entries should be rendered, due to pagination
  expect(within(rows).getAllByText("foo@example.com")).toHaveLength(10);
});

test("click on refresh button refreshes the table", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestWaves(1), generateTestWaves(5));

  renderUserWavesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading waves/i));
  expect(screen.getByRole("heading", { name: "Waves (1)" })).toBeInTheDocument();

  const refreshButton = screen.getByRole("button", { name: "Refresh" });

  // WHEN
  await userEvent.click(refreshButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Waves (5)" })).toBeInTheDocument();
});

test('click on add button opens "Add wave" form', async () => {
  // GIVEN
  setupApiCallsForLoad([]);
  renderUserWavesTable();

  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Add wave" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Waves (0)" })).toBeInTheDocument();
});

test("submitting the add form saves a new wave to API", async () => {
  // GIVEN
  const [wave0, wave1] = generateTestWaves(2);
  setupApiCallsForLoad([wave0], [wave0, wave1]);
  const { saveRequestBodies, manageEntityRequestBodies } = setupApiCallsForSave("post", wave1);

  renderUserWavesTable();
  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN we see the Add form with a disabled save button until we enter valid values into all fields
  expect(await screen.findByRole("button", { name: /Save/i })).not.toBeEnabled();
  expect(screen.getAllByText("You must specify a valid value.")[0]).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.type(screen.getByRole("textbox", { name: "wave_name" }), "my-test-wave");

  await userEvent.click(screen.getByLabelText("Wave Status"));
  await userEvent.click(await screen.findByText("Not started"));

  // THEN expect no more validation errors
  expect(screen.queryByText("You must specify a valid value.")).not.toBeInTheDocument();

  // AND WHEN we hit 'save'
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(saveRequestBodies).toEqual([{ wave_name: "my-test-wave", wave_status: "Not started" }]);
    expect(manageEntityRequestBodies).toEqual([]);
  });
  await screen.findByRole("heading", { name: "Waves (2)" });
});

test('click on row enables "Edit" button and shows "Details" tab', async () => {
  // GIVEN
  const waves = generateTestWaves(1);
  setupApiCallsForLoad(waves);
  const { saveRequestBodies, manageEntityRequestBodies } = setupApiCallsForSave("put");

  const { addNotification } = renderUserWavesTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeDisabled();

  const waveRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(waveRowCheckbox);

  // THEN
  expect(editButton).not.toBeDisabled();
  expect(screen.getByRole("heading", { name: "Details" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("tab", { name: "All attributes" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "All attributes" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit wave" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  expect(saveButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(saveButton);

  // THEN
  await waitFor(() => {
    expect(saveRequestBodies).toEqual([]);
    expect(manageEntityRequestBodies).toEqual([]);

    expect(addNotification).toHaveBeenCalledWith({
      content: "No updates to save.",
      dismissible: true,
      header: "Edit wave",
      type: "warning",
    });
  });
});

test("submitting the edit form saves the wave to API", async () => {
  // GIVEN
  const waves = generateTestWaves(1);
  setupApiCallsForLoad(waves);
  const { saveRequestBodies, manageEntityRequestBodies } = setupApiCallsForSave("put");

  renderUserWavesTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const waveRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(waveRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit wave" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  expect(saveButton).toBeEnabled();

  // AND WHEN we edit some data and hit 'save'
  const waveNameInput = screen.getByRole("textbox", { name: "wave_name" });
  await userEvent.type(waveNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(saveRequestBodies).toEqual([{ wave_name: "Unit testing Wave 0-some-name" }]);
    expect(manageEntityRequestBodies).toEqual([]);
  });
  await screen.findByRole("heading", { name: "Waves (1)" });
});

test("when update fails with server error, display notification", async () => {
  // GIVEN
  const waves = generateTestWaves(1);
  setupApiCallsForLoad(waves);
  server.use(
    rest.put(`/user/wave/${waves[0].wave_id}`, async (request, response, context) => {
      request.json().then(() => {});
      return response(context.status(502));
    })
  );

  const { addNotification } = renderUserWavesTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const waveRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(waveRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit wave" })).toBeInTheDocument();
  await screen.findByRole("button", { name: /Save/i });

  // AND WHEN we edit some data and hit 'save'
  const waveNameInput = screen.getByRole("textbox", { name: "wave_name" });
  await userEvent.type(waveNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the failure message
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "Unknown error occurred.",
      dismissible: true,
      header: "Edit wave",
      type: "error",
    });
  });
});

test("when update fails with 200 success response, parse error", async () => {
  // GIVEN
  const waves = generateTestWaves(1);
  setupApiCallsForLoad(waves);
  server.use(
    rest.put(`/user/wave/${waves[0].wave_id}`, async (request, response, context) => {
      return response(
        context.status(200),
        context.json({
          errors: {
            // TODO get a real example of the error payload
            validation_errors: [
              {
                prop1: ["message"],
              },
            ],
            existing_name: ["prop2"],
            unprocessed_items: {
              baz: { error_detail: "baz" },
            },
          },
        })
      );
    })
  );

  const { addNotification } = renderUserWavesTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const waveRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(waveRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit wave" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });

  // AND WHEN we edit some data and hit 'save'
  const waveNameInput = screen.getByRole("textbox", { name: "wave_name" });
  await userEvent.type(waveNameInput, "-some-name");
  await userEvent.click(saveButton);

  // THEN verify the failure message
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "prop1 : message" + "," + "prop2 already exists.",
      dismissible: true,
      header: "Edit wave",
      type: "error",
    });
  });
});

test('click on row enables "Delete" button, shows "Delete" modal', async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestWaves(1));

  renderUserWavesTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const waveRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(waveRowCheckbox);

  // THEN
  expect(await screen.findByRole("heading", { name: "Waves (1 of 1)" })).toBeInTheDocument();
  expect(deleteButton).not.toBeDisabled();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const deleteModal = await screen.findByRole("dialog", { name: "Delete waves" });
  expect(within(deleteModal).getByText("Are you sure you wish to delete the 1 selected wave?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(within(deleteModal).getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Waves (1 of 1)" })).toBeInTheDocument();
});

test("confirming the deletion successfully deletes a wave", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestWaves(1), []);
  const { saveRequestBodies, manageEntityRequestBodies } = setupApiCallsForSave("delete");

  const { addNotification } = renderUserWavesTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const waveRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(waveRowCheckbox);
  await userEvent.click(deleteButton);
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(saveRequestBodies).toEqual([]);
  expect(manageEntityRequestBodies).toEqual([{ entity_ids: ["0"], entity_type: "wave", operation: "cleanup" }]);

  expect(addNotification).toHaveBeenCalledWith({
    header: "Deleting selected wave...",
    dismissible: false,
    loading: true,
  });
  expect(addNotification).toHaveBeenCalledWith({
    content: "Unit testing Wave 0 was deleted.",
    dismissible: true,
    header: "Delete wave",
    type: "success",
  });
  expect(await screen.findByRole("heading", { name: "Waves (0)" })).toBeInTheDocument();
});

test("delete multiple waves", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestWaves(2), []);
  const { saveRequestBodies, manageEntityRequestBodies } = setupApiCallsForSave("delete");

  const { addNotification } = renderUserWavesTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();
  await userEvent.click(deleteButton);

  const waveRowCheckBoxes = screen.getAllByRole("checkbox");

  // WHEN
  await userEvent.click(waveRowCheckBoxes[0]);

  // THEN
  expect(await screen.findByRole("heading", { name: "Waves (2 of 2)" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(await withinModal.findByText("Are you sure you wish to delete the 2 selected waves?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(saveRequestBodies).toEqual([]);
  expect(manageEntityRequestBodies).toEqual([{ entity_ids: ["0", "1"], entity_type: "wave", operation: "cleanup" }]);

  expect(addNotification).toHaveBeenCalledWith({
    header: "Deleting selected waves...",
    dismissible: false,
    loading: true,
  });
  expect(addNotification).toHaveBeenCalledWith({
    content: "Unit testing Wave 0, Unit testing Wave 1 were deleted.",
    dismissible: true,
    header: "Delete waves",
    type: "success",
  });
  expect(await screen.findByRole("heading", { name: "Waves (0)" })).toBeInTheDocument();
});

test("click on export downloads an xlsx file", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestWaves(2));
  jest.spyOn(XLSX.utils, "json_to_sheet");

  renderUserWavesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading waves/i));

  const exportButton = screen.getByRole("button", { name: "Download" });

  // WHEN
  await userEvent.click(exportButton);

  // THEN
  expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(1);
  expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
});

test("selecting a row and click on export downloads an xlsx file", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestWaves(2));
  jest.spyOn(XLSX.utils, "json_to_sheet");

  renderUserWavesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading waves/i));

  await userEvent.click(screen.getAllByRole("row")[1]);
  const exportButton = screen.getByRole("button", { name: "Download" });

  // WHEN
  await userEvent.click(exportButton);

  // THEN
  expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(1);
  expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
});

test("buttons are disabled based on user permissions", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestWaves(2));

  renderUserWavesTable({
    ...wpmTestProps,
    userEntityAccess: {
      ...wpmTestProps.userEntityAccess,
      wave: {
        delete: false,
        create: false,
        update: false,
        read: true,
        attributes: [],
      },
    },
  });

  // WHEN
  await userEvent.click(screen.getByRole("checkbox"));

  // THEN
  expect(screen.getByRole("button", { name: "Add" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Edit" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
});

test("Run Automation", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestWaves(1));

  renderUserWavesTable();
  const actionsButton = screen.getByRole("button", { name: "Actions" });
  expect(actionsButton).toBeDisabled();

  const waveRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(waveRowCheckbox);

  // THEN
  expect(actionsButton).not.toBeDisabled();

  // AND WHEN
  await userEvent.click(actionsButton);
  await userEvent.click(await screen.findByRole("menuitem", { name: "Run Automation" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Run Automation" })).toBeInTheDocument();

  // TODO fill out the form and submit - what entity data do we need to add to the schema in order to have values for the dropwdowns?
});

test("MGN server migration", async () => {
  // GIVEN
  let captureRequest: any;
  const waves = generateTestWaves(1);
  setupApiCallsForLoad(waves);

  const applications = generateTestAppsWithWaveIds(2, { waveId: waves[0].wave_id });
  server.use(
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(applications));
    }),
    rest.post("/mgn", (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(201));
    })
  );

  renderUserWavesTable();
  const actionsButton = screen.getByRole("button", { name: "Actions" });

  // WHEN selecting a wave and navigating through the action menu
  await userEvent.click(screen.getByRole("checkbox"));
  await userEvent.click(actionsButton);
  await userEvent.click(await screen.findByRole("menuitem", { name: "Rehost" }));
  await userEvent.click(await screen.findByRole("menuitem", { name: "MGN" }));

  // THEN MGN server migration form should open with wave preselected
  expect(await screen.findByRole("heading", { name: "MGN server migration" })).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: /wave unit testing wave 0/i })).toBeInTheDocument();

  // WHEN
  await userEvent.click(screen.getByLabelText("Action"));
  await userEvent.click(await screen.findByText("Validate Launch Template"));

  await userEvent.click(screen.getByLabelText("Applications"));
  await userEvent.click(await screen.findByText(applications[0].app_name));

  // THEN
  const submitBtn = await screen.findByRole("button", { name: "Submit" });
  expect(submitBtn).toBeEnabled();

  // WHEN
  await userEvent.click(submitBtn);

  // THEN
  await waitFor(() => {
    expect(captureRequest.action).toEqual("Validate Launch Template");
  });
});

test("it deep links to Add form", async () => {
  // GIVEN
  const addWaveRoute = "/waves/add";
  setupApiCallsForLoad([]);

  // WHEN
  render(
    <MemoryRouter initialEntries={[addWaveRoute]}>
      <NotificationContext.Provider value={mockNotificationContext}>
        <SessionContext.Provider value={TEST_SESSION_STATE}>
          <div id="modal-root" />
          <AuthenticatedRoutes childProps={wpmTestProps}></AuthenticatedRoutes>
        </SessionContext.Provider>
      </NotificationContext.Provider>
    </MemoryRouter>
  );

  // THEN
  expect(await screen.findByRole("heading", { name: "Add wave" })).toBeInTheDocument();
});

test("it deep links to Edit form", async () => {
  // GIVEN
  const waves = generateTestWaves(1);
  setupApiCallsForLoad(waves);

  const editWaveRoute = `/waves/edit/${waves[0].wave_id}`;

  // WHEN
  render(
    <MemoryRouter initialEntries={[editWaveRoute]}>
      <NotificationContext.Provider value={mockNotificationContext}>
        <SessionContext.Provider value={TEST_SESSION_STATE}>
          <div id="modal-root" />
          <AuthenticatedRoutes childProps={wpmTestProps}></AuthenticatedRoutes>
        </SessionContext.Provider>
      </NotificationContext.Provider>
    </MemoryRouter>
  );

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit wave" })).toBeInTheDocument();
});
