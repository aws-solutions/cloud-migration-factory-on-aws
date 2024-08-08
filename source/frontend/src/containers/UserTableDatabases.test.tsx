import { defaultTestProps, mockNotificationContext, TEST_SESSION_STATE } from "../__tests__/TestUtils";
import { render, screen, waitFor, waitForElementToBeRemoved, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionContext } from "../contexts/SessionContext";
import React from "react";
import UserDatabaseTable from "./UserTableDatabases";
import { server } from "../setupTests";
import { rest } from "msw";
import { generateTestApps, generateTestDatabases } from "../__tests__/mocks/user_api";
import userEvent from "@testing-library/user-event";
import * as XLSX from "xlsx";
import { NotificationContext } from "../contexts/NotificationContext";

function renderUserDatabasesTable(props = defaultTestProps) {
  return {
    ...mockNotificationContext,
    renderResult: render(
      <MemoryRouter initialEntries={["/databases"]}>
        <NotificationContext.Provider value={mockNotificationContext}>
          <SessionContext.Provider value={TEST_SESSION_STATE}>
            <div id="modal-root" />
            <UserDatabaseTable {...props}></UserDatabaseTable>
          </SessionContext.Provider>
        </NotificationContext.Provider>
      </MemoryRouter>
    ),
  };
}

test('it renders an empty table with "no databases" message', async () => {
  // WHEN
  renderUserDatabasesTable();

  // THEN
  // page should render in loading state
  expect(screen.getByRole("heading", { name: "Databases (0)" })).toBeInTheDocument();
  expect(screen.getByText("Loading databases")).toBeInTheDocument();

  // after server response came in, it should render the table
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading databases/i));

  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];

  expect(await within(tbody).findByText("No databases")).toBeInTheDocument();
  expect(within(tbody).getByRole("button", { name: "Add database" })).toBeInTheDocument();
});

test("it renders a paginated table with 50 databases", async () => {
  // GIVEN
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(generateTestDatabases(50)));
    })
  );

  // WHEN
  renderUserDatabasesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading databases/i));

  // THEN
  expect(screen.getByRole("heading", { name: "Databases (50)" })).toBeInTheDocument();

  const table = screen.getByRole("table");
  const rows = within(table).getAllByRole("rowgroup")[1];

  // only 10 of the entries should be rendered, due to pagination
  expect(within(rows).getAllByText("mysql")).toHaveLength(10);
});

test("click on refresh button refreshes the table", async () => {
  // GIVEN
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestDatabases(1)));
    }),
    // second request to same endpoint gives a different response
    rest.get("/user/database", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestDatabases(5)));
    })
  );

  renderUserDatabasesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading databases/i));
  expect(screen.getByRole("heading", { name: "Databases (1)" })).toBeInTheDocument();

  const refreshButton = screen.getByRole("button", { name: "Refresh" });

  // WHEN
  await userEvent.click(refreshButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Databases (5)" })).toBeInTheDocument();
});

test('click on add button opens "Add database" form', async () => {
  // GIVEN
  renderUserDatabasesTable();

  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Add database" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Databases (0)" })).toBeInTheDocument();
});

test("submitting the add form saves a new database to API", async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(generateTestDatabases(2)));
    }),
    rest.post(`/user/database`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(201));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(2)));
    })
  );

  renderUserDatabasesTable();
  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN we see the Add form with a disabled save button until we enter valid values into all fields
  expect(await screen.findByRole("button", { name: /Save/i })).not.toBeEnabled();
  expect(screen.getAllByText("You must specify a valid value.")[0]).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.type(screen.getByRole("textbox", { name: "Database Name" }), "my-test-database");

  await userEvent.click(screen.getByLabelText("Application"));
  await userEvent.click(await screen.findByText("Unit testing App 1"));

  await userEvent.click(screen.getByLabelText("Database Type"));
  await userEvent.click(await screen.findByText("db2"));

  // THEN expect no more validation errors
  expect(screen.queryByText("You must specify a valid value.")).not.toBeInTheDocument();

  // AND WHEN we hit 'save'
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.database_name).toEqual("my-test-database");
  });
  await screen.findByRole("heading", { name: "Databases (2)" });
});

test('click on row enables "Edit" button and shows "Details" tab', async () => {
  // GIVEN
  const databases = generateTestDatabases(1);
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(databases));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(2)));
    })
  );

  const { addNotification } = renderUserDatabasesTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeDisabled();

  const databaseRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(databaseRowCheckbox);

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
  expect(await screen.findByRole("heading", { name: "Edit database" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  expect(saveButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(saveButton);

  // THEN
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "No updates to save.",
      dismissible: true,
      header: "Save database",
      type: "warning",
    });
  });
});

test("submitting the edit form saves the database to API", async () => {
  // GIVEN
  let captureRequest: any;
  const databases = generateTestDatabases(1);
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(databases));
    }),
    rest.put(`/user/database/${databases[0].database_id}`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(200));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(2)));
    })
  );

  renderUserDatabasesTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const databaseRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(databaseRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit database" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  await waitFor(() => expect(saveButton).toBeEnabled());

  // AND WHEN
  await userEvent.click(await screen.findByRole("button", { name: "Related details" }));

  // THEN
  const dialog = await screen.findByRole("dialog");
  expect(await within(dialog).findByRole("heading", { name: "Item detail" })).toBeInTheDocument();
  expect(await within(dialog).findByText("Unit testing App 1")).toBeInTheDocument();

  // AND WHEN we edit some data and hit 'save'
  const databaseNameInput = screen.getByRole("textbox", { name: "Database Name" });
  await userEvent.type(databaseNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.database_name).toEqual("unittest0-some-name");
  });
  await screen.findByRole("heading", { name: "Databases (1)" });
});

test("when update fails with server error, display notification", async () => {
  // GIVEN
  let captureRequest: any;
  const databases = generateTestDatabases(1);
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(databases));
    }),
    rest.put(`/user/database/${databases[0].database_id}`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(502));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(2)));
    })
  );

  const { addNotification } = renderUserDatabasesTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const databaseRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(databaseRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit database" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });

  // AND WHEN we edit some data and hit 'save'
  const databaseNameInput = screen.getByRole("textbox", { name: "Database Name" });
  await userEvent.type(databaseNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the failure message
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "Unknown error occurred.",
      dismissible: true,
      header: "Edit database",
      type: "error",
    });
  });
});

test('click on row enables "Delete" button, shows "Delete" modal', async () => {
  // GIVEN
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(generateTestDatabases(1)));
    })
  );

  renderUserDatabasesTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const databaseRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(databaseRowCheckbox);

  // THEN
  expect(await screen.findByRole("heading", { name: "Databases (1 of 1)" })).toBeInTheDocument();
  expect(deleteButton).not.toBeDisabled();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(withinModal.getByRole("heading", { name: "Delete databases" })).toBeInTheDocument();
  expect(withinModal.getByText("Are you sure you wish to delete the 1 selected databases?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(withinModal.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Databases (1 of 1)" })).toBeInTheDocument();
});

test("confirming the deletion successfully deletes a database", async () => {
  // GIVEN
  const databases = generateTestDatabases(1);
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response.once(context.status(200), context.json(databases));
    }),
    rest.delete(`/user/database/:id`, (request, response, context) => {
      return response(context.status(204));
    })
  );

  const { addNotification } = renderUserDatabasesTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const databaseRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(databaseRowCheckbox);
  await userEvent.click(deleteButton);
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    content: "unittest0 was deleted.",
    dismissible: true,
    header: "database deleted successfully",
    type: "success",
  });
  expect(await screen.findByRole("heading", { name: "Databases (0)" })).toBeInTheDocument();
});

test("delete multiple databases", async () => {
  // GIVEN
  const databases = generateTestDatabases(2);
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response.once(context.status(200), context.json(databases));
    }),
    rest.delete(`/user/database/:id`, (request, response, context) => {
      return response(context.status(204));
    })
  );

  const { addNotification } = renderUserDatabasesTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();
  await userEvent.click(deleteButton);

  const databaseRowCheckBoxes = screen.getAllByRole("checkbox");

  // WHEN
  await userEvent.click(databaseRowCheckBoxes[0]);

  // THEN
  expect(await screen.findByRole("heading", { name: "Databases (2 of 2)" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(await withinModal.findByText("Are you sure you wish to delete the 2 selected databases?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    dismissible: false,
    header: "Deleting selected databases...",
    loading: true,
    type: "success",
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "unittest0, unittest1 were deleted.",
      dismissible: true,
      header: "database deleted successfully",
      type: "success",
    });
  });
});

test("click on export downloads an xlsx file", async () => {
  // GIVEN
  jest.spyOn(XLSX, "writeFile").mockImplementation(() => {});
  jest.spyOn(XLSX.utils, "json_to_sheet");

  const testDatabases = generateTestDatabases(2);
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(testDatabases));
    })
  );
  renderUserDatabasesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading databases/i));

  const exportButton = screen.getByRole("button", { name: "Download" });

  // WHEN
  await userEvent.click(exportButton);

  // THEN
  expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(1);
  expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
});

test("selecting a row and click on export downloads an xlsx file", async () => {
  // GIVEN
  jest.spyOn(XLSX, "writeFile").mockImplementation(() => {});
  jest.spyOn(XLSX.utils, "json_to_sheet");

  const testDatabases = generateTestDatabases(2);
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(testDatabases));
    })
  );
  renderUserDatabasesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading databases/i));

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
  server.use(
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(generateTestDatabases(2)));
    })
  );

  renderUserDatabasesTable({
    ...defaultTestProps,
    userEntityAccess: {
      ...defaultTestProps.userEntityAccess,
      database: {
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
