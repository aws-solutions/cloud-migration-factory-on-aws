/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { mockNotificationContext, TEST_SESSION_STATE, wpmTestProps } from "../__tests__/TestUtils";
import { render, screen, waitFor, waitForElementToBeRemoved, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionContext } from "../contexts/SessionContext";
import { server } from "../setupTests";
import { rest } from "msw";
import {
  generateTestApps,
  generateTestDatabases,
  generateTestMoveGroups,
  generateTestServers,
  generateTestWaves,
  generateTestWpmJobs,
} from "../__tests__/mocks/user_api";
import userEvent from "@testing-library/user-event";
import * as XLSX from "xlsx";
import UserTableApps from "./UserTableApps";
import { NotificationContext } from "../contexts/NotificationContext";
import AuthenticatedRoutes from "../AuthenticatedRoutes";
import { Application } from "../models";

function renderUserApplicationsTable(props = wpmTestProps) {
  return {
    ...mockNotificationContext,
    renderResult: render(
      <MemoryRouter initialEntries={["/applications"]}>
        <NotificationContext.Provider value={mockNotificationContext}>
          <SessionContext.Provider value={TEST_SESSION_STATE}>
            <div id="modal-root" />
            <UserTableApps {...props}></UserTableApps>
          </SessionContext.Provider>
        </NotificationContext.Provider>
      </MemoryRouter>
    ),
  };
}

function setupApiCallsForLoad(...apps: Application[][]) {
  let counter = 0;
  server.use(
    rest.get("/user/app", (request, response, context) => {
      const index = Math.min(counter++, apps.length - 1);
      return response(context.status(200), context.json(apps[index]));
    }),
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(generateTestDatabases(10)));
    }),
    rest.get("/user/servers", (request, response, context) => {
      return response(context.status(200), context.json(generateTestServers(10)));
    }),
    rest.get("/user/move_group", (request, response, context) => {
      return response(context.status(200), context.json(generateTestMoveGroups(1)));
    }),
    rest.get("/user/wave", (request, response, context) => {
      return response(context.status(200), context.json(generateTestWaves(2)));
    }),
    rest.get("/user/wpm_job", (request, response, context) => {
      return response(context.status(200), context.json(generateTestWpmJobs(1)));
    })
  );
}

test('it renders an empty table with "no applications" message', async () => {
  // GIVEN
  setupApiCallsForLoad([]);

  // WHEN
  renderUserApplicationsTable();

  // THEN
  // page should render in loading state
  expect(screen.getByRole("heading", { name: "Applications (0)" })).toBeInTheDocument();
  expect(screen.getByText("Loading Applications")).toBeInTheDocument();

  // after server response came in, it should render the table
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading applications/i));

  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];

  expect(await within(tbody).findByText("No Applications")).toBeInTheDocument();
  expect(within(tbody).getByRole("button", { name: "Add Application" })).toBeInTheDocument();
});

test("it renders a paginated table with 50 applications", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestApps(50));

  // WHEN
  renderUserApplicationsTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading applications/i));

  // THEN
  expect(screen.getByRole("heading", { name: "Applications (50)" })).toBeInTheDocument();

  const table = screen.getByRole("table");
  const rows = within(table).getAllByRole("rowgroup")[1];

  // only 10 of the entries should be rendered, due to pagination
  expect(within(rows).getAllByText(/Unit testing App (0-9)*/)).toHaveLength(10);
});

test("click on refresh button refreshes the table", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestApps(1), generateTestApps(5));

  renderUserApplicationsTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading applications/i));
  expect(screen.getByRole("heading", { name: "Applications (1)" })).toBeInTheDocument();

  const refreshButton = screen.getByRole("button", { name: "Refresh" });

  // WHEN
  await userEvent.click(refreshButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Applications (5)" })).toBeInTheDocument();
});

test('click on add button opens "Add application" form', async () => {
  // GIVEN
  setupApiCallsForLoad([]);
  renderUserApplicationsTable();

  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Add application" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Applications (0)" })).toBeInTheDocument();
});

test("submitting the add form saves a new application to API", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestApps(1), generateTestApps(2));

  let captureRequest: any;
  server.use(
    rest.post(`/user/app`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(201));
    })
  );

  renderUserApplicationsTable();
  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN we see the Add form with a disabled save button until we enter valid values into all fields
  expect(await screen.findByRole("button", { name: /Save/i })).not.toBeEnabled();
  expect(screen.getAllByText("You must specify a valid value.")[0]).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.type(screen.getByRole("textbox", { name: "app_name" }), "my-test-application");

  await userEvent.click(screen.getByRole("button", { name: /select aws account id/i }));
  await userEvent.click(await screen.findByText("123456789012")); // see default_schema.ts

  await userEvent.click(screen.getByLabelText("AWS Region"));
  await userEvent.click(await screen.findByText("us-east-1"));

  // THEN expect no more validation errors
  expect(screen.queryByText("You must specify a valid value.")).not.toBeInTheDocument();

  // AND WHEN we hit 'save'
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.app_name).toEqual("my-test-application");
  });
  await screen.findByRole("heading", { name: "Applications (2)" });
});

test('click on row enables "Edit" button and shows "Details" tab', async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestApps(1));

  const { addNotification } = renderUserApplicationsTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeDisabled();

  const applicationRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(applicationRowCheckbox);

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
  expect(await screen.findByRole("heading", { name: "Edit application" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  await waitFor(() => expect(saveButton).toBeEnabled());

  // AND WHEN
  await userEvent.click(saveButton);

  // THEN
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "No updates to save.",
      dismissible: true,
      header: "Save application",
      type: "warning",
    });
  });
});

test("submitting the edit form saves the application to API", async () => {
  // GIVEN
  const applications = generateTestApps(1);
  setupApiCallsForLoad(applications);

  let captureRequest: any;
  server.use(
    rest.put(`/user/app/${applications[0].app_id}`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(200));
    })
  );

  renderUserApplicationsTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const applicationRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(applicationRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit application" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  await waitFor(() => expect(saveButton).toBeEnabled());

  expect(await screen.findByText("Unit testing Wave 1")).toBeInTheDocument();

  // AND WHEN we edit some data and hit 'save'
  const applicationNameInput = screen.getByRole("textbox", { name: "app_name" });
  await userEvent.type(applicationNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.app_name).toEqual("Unit testing App 0-some-name");
  });
  await screen.findByRole("heading", { name: "Applications (1)" });
});

test("when update fails with server error, display notification", async () => {
  // GIVEN
  const applications = generateTestApps(1);
  setupApiCallsForLoad(applications);

  server.use(
    rest.put(`/user/app/${applications[0].app_id}`, async (request, response, context) => {
      return response(context.status(502));
    })
  );

  const { addNotification } = renderUserApplicationsTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const applicationRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(applicationRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit application" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  await waitFor(() => expect(saveButton).toBeEnabled());

  // AND WHEN we edit some data and hit 'save'
  const applicationNameInput = screen.getByRole("textbox", { name: "app_name" });
  await userEvent.type(applicationNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the failure message
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "Unknown error occurred.",
      dismissible: true,
      header: "Edit application",
      type: "error",
    });
  });
});

test('click on row enables "Delete" button, shows "Delete" modal', async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestApps(1));

  renderUserApplicationsTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const applicationRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(applicationRowCheckbox);

  // THEN
  expect(await screen.findByRole("heading", { name: "Applications (1 of 1)" })).toBeInTheDocument();
  expect(deleteButton).not.toBeDisabled();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(withinModal.getByRole("heading", { name: "Delete applications" })).toBeInTheDocument();
  expect(withinModal.getByText("Are you sure you wish to delete the 1 selected application?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(withinModal.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Applications (1 of 1)" })).toBeInTheDocument();
});

test("confirming the deletion successfully deletes a application", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestApps(1), []);

  const deleteAppRequestBodies: any[] = [];
  server.use(
    rest.post(`/manage-entities`, (request, response, context) => {
      request.json().then((body) => deleteAppRequestBodies.push(body));
      return response(context.status(204));
    })
  );

  const { addNotification } = renderUserApplicationsTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const applicationRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(applicationRowCheckbox);
  await userEvent.click(deleteButton);
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(deleteAppRequestBodies).toEqual([{ entity_ids: ["0"], entity_type: "app", operation: "cleanup" }]);
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "Unit testing App 0 was deleted.",
      dismissible: true,
      header: "Delete application",
      type: "success",
    });
  });
  expect(await screen.findByRole("heading", { name: "Applications (0)" })).toBeInTheDocument();
});

test("delete multiple applications", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestApps(2));
  const deleteAppRequestBodies: any[] = [];
  server.use(
    rest.post(`/manage-entities`, (request, response, context) => {
      request.json().then((body) => deleteAppRequestBodies.push(body));
      return response(context.status(204));
    })
  );

  const { addNotification } = renderUserApplicationsTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();
  await userEvent.click(deleteButton);

  const applicationRowCheckBoxes = screen.getAllByRole("checkbox");

  // WHEN
  await userEvent.click(applicationRowCheckBoxes[0]);

  // THEN
  expect(await screen.findByRole("heading", { name: "Applications (2 of 2)" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(
    await withinModal.findByText("Are you sure you wish to delete the 2 selected applications?")
  ).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(deleteAppRequestBodies).toEqual([
    {
      entity_ids: ["0", "1"],
      entity_type: "app",
      operation: "cleanup",
    },
  ]);

  expect(addNotification).toHaveBeenCalledWith({
    dismissible: false,
    header: "Deleting applications...",
    loading: true,
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "Unit testing App 0, Unit testing App 1 were deleted.",
      dismissible: true,
      header: "Delete applications",
      type: "success",
    });
  });
});

test("click on export downloads an xlsx file", async () => {
  // GIVEN
  jest.spyOn(XLSX.utils, "json_to_sheet");

  const testApplications = generateTestApps(2);
  setupApiCallsForLoad(testApplications);

  renderUserApplicationsTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading applications/i));

  const exportButton = screen.getByRole("button", { name: "Download" });

  // WHEN
  await userEvent.click(exportButton);

  // THEN
  expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(1);
  expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
});

test("selecting a row and click on export downloads an xlsx file", async () => {
  // GIVEN
  jest.spyOn(XLSX.utils, "json_to_sheet");

  const testApplications = generateTestApps(2);
  setupApiCallsForLoad(testApplications);

  renderUserApplicationsTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading applications/i));

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
  setupApiCallsForLoad(generateTestApps(2));

  renderUserApplicationsTable({
    ...wpmTestProps,
    userEntityAccess: {
      ...wpmTestProps.userEntityAccess,
      application: {
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

test("it deep links to Add form", async () => {
  // GIVEN
  const addAppRoute = "/apps/add";
  setupApiCallsForLoad([]);

  // WHEN
  render(
    <MemoryRouter initialEntries={[addAppRoute]}>
      <NotificationContext.Provider value={mockNotificationContext}>
        <SessionContext.Provider value={TEST_SESSION_STATE}>
          <div id="modal-root" />
          <AuthenticatedRoutes childProps={wpmTestProps}></AuthenticatedRoutes>
        </SessionContext.Provider>
      </NotificationContext.Provider>
    </MemoryRouter>
  );

  // THEN
  expect(await screen.findByRole("heading", { name: "Add application" })).toBeInTheDocument();
});

test("it deep links to Edit form", async () => {
  // GIVEN
  const applications = generateTestApps(1);
  setupApiCallsForLoad(applications);

  const editAppRoute = `/apps/edit/${applications[0].app_id}`;

  // WHEN
  render(
    <MemoryRouter initialEntries={[editAppRoute]}>
      <NotificationContext.Provider value={mockNotificationContext}>
        <SessionContext.Provider value={TEST_SESSION_STATE}>
          <div id="modal-root" />
          <AuthenticatedRoutes childProps={wpmTestProps}></AuthenticatedRoutes>
        </SessionContext.Provider>
      </NotificationContext.Provider>
    </MemoryRouter>
  );

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit application" })).toBeInTheDocument();
});
