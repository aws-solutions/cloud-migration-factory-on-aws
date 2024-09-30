import { render, screen, waitFor, waitForElementToBeRemoved, within } from "@testing-library/react";
import * as XLSX from "xlsx";
import UserServerTable from "./UserTableServers";
import { MemoryRouter } from "react-router-dom";
import { defaultTestProps, mockNotificationContext, TEST_SESSION_STATE } from "../__tests__/TestUtils";
import { SessionContext } from "../contexts/SessionContext";
import { rest } from "msw";
import { server } from "../setupTests";
import { generateTestApps, generateTestServers } from "../__tests__/mocks/user_api";
import userEvent from "@testing-library/user-event";
import React from "react";
import { NotificationContext } from "../contexts/NotificationContext";

function renderUserServerTable(props = defaultTestProps) {
  return {
    ...mockNotificationContext,
    renderResult: render(
      <MemoryRouter initialEntries={["/servers"]}>
        <NotificationContext.Provider value={mockNotificationContext}>
          <SessionContext.Provider value={TEST_SESSION_STATE}>
            <div id="modal-root" />
            <UserServerTable {...props}></UserServerTable>
          </SessionContext.Provider>
        </NotificationContext.Provider>
      </MemoryRouter>
    ),
  };
}

test('it renders an empty table with "no servers" message', async () => {
  // WHEN
  renderUserServerTable();

  // THEN
  // page should render in loading state
  expect(screen.getByRole("heading", { name: "Servers (0)" })).toBeInTheDocument();
  expect(screen.getByText("Loading servers")).toBeInTheDocument();

  // after server response came in, it should render the table
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading servers/i));

  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];

  expect(await within(tbody).findByText("No servers")).toBeInTheDocument();
  expect(within(tbody).getByRole("button", { name: "Add server" })).toBeInTheDocument();
});

test("it renders a paginated table with 50 servers", async () => {
  // GIVEN
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(generateTestServers(50)));
    })
  );

  // WHEN
  renderUserServerTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading servers/i));

  // THEN
  expect(screen.getByRole("heading", { name: "Servers (50)" })).toBeInTheDocument();

  const table = screen.getByRole("table");
  const rows = within(table).getAllByRole("rowgroup")[1];

  // only 10 of the entries should be rendered, due to pagination
  expect(within(rows).getAllByText("linux")).toHaveLength(10);
});

test("click on refresh button refreshes the table", async () => {
  // GIVEN
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestServers(1)));
    }),
    // second request to same endpoint gives a different response
    rest.get("/user/server", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestServers(5)));
    })
  );

  renderUserServerTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading servers/i));
  expect(screen.getByRole("heading", { name: "Servers (1)" })).toBeInTheDocument();

  const refreshButton = screen.getByRole("button", { name: "Refresh" });

  // WHEN
  await userEvent.click(refreshButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Servers (5)" })).toBeInTheDocument();
});

test('click on add button opens "Add server" form', async () => {
  // GIVEN
  renderUserServerTable();

  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Add server" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Servers (0)" })).toBeInTheDocument();
});

test("submitting the add form saves a new server to API", async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(generateTestServers(2)));
    }),
    rest.post(`/user/server`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(201));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(2)));
    })
  );

  const { addNotification } = renderUserServerTable();
  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN we see the Add form with a disabled save button until we enter valid values into all fields
  expect(await screen.findByRole("button", { name: /Save/i })).not.toBeEnabled();
  expect(screen.getAllByText("You must specify a valid value.")[0]).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.type(screen.getByRole("textbox", { name: "server_name" }), "my-test-server");
  await userEvent.type(screen.getByRole("textbox", { name: "server_fqdn" }), "foo");

  await userEvent.click(screen.getByLabelText("Application"));
  await userEvent.click(await screen.findByText("Unit testing App 1"));

  await userEvent.click(
    screen.getByRole("button", { name: /migration strategy info r_type select migration strategy/i })
  );
  await userEvent.click(await screen.findByText("Retire"));

  await userEvent.click(screen.getByLabelText("Server OS Family"));
  await userEvent.click(await screen.findByText("windows"));

  await userEvent.type(screen.getByRole("textbox", { name: "server_environment" }), "Production");
  await userEvent.type(screen.getByRole("textbox", { name: "server_os_version" }), "Production");

  // THEN expect no more validation errors
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  await waitFor(() => expect(saveButton).toBeEnabled());
  expect(screen.queryByText("You must specify a valid value.")).not.toBeInTheDocument();

  // AND WHEN we hit 'save'
  await userEvent.click(saveButton);

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.server_name).toEqual("my-test-server");
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "my-test-server saved successfully.",
      dismissible: true,
      header: "Add server",
      type: "success",
    });
  });
}, 60000);

test('click on row enables "Edit" button and shows "Details" tab', async () => {
  // GIVEN
  const servers = generateTestServers(1);
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(servers));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(2)));
    })
  );

  const { addNotification } = renderUserServerTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeDisabled();

  const serverRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(serverRowCheckbox);

  // THEN
  expect(editButton).not.toBeDisabled();
  expect(screen.getByRole("heading", { name: "Details" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Application" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Application" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("tab", { name: "All attributes" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "All attributes" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit server" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  expect(saveButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(saveButton);

  // THEN
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "No updates to save.",
      dismissible: true,
      header: "Save server",
      type: "warning",
    });
  });
});

test("submitting the edit form saves the server to API", async () => {
  // GIVEN
  let captureRequest: any;
  const servers = generateTestServers(1);
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(servers));
    }),
    rest.put(`/user/server/${servers[0].server_id}`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(200));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(2)));
    })
  );

  renderUserServerTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const serverRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(serverRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit server" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  expect(saveButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(await screen.findByRole("button", { name: "Related details" }));

  // THEN
  const dialog = await screen.findByRole("dialog", { name: "Item detail" });
  expect(await within(dialog).findByText("Unit testing App 1")).toBeInTheDocument();

  // AND WHEN we edit some data and hit 'save'
  const serverNameInput = screen.getByRole("textbox", { name: "server_name" });
  await userEvent.type(serverNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.server_name).toEqual("unittest0-some-name");
  });
  await screen.findByRole("heading", { name: "Servers (1)" });
});

test("when update fails with server error, display notification", async () => {
  // GIVEN
  let captureRequest: any;
  const servers = generateTestServers(1);
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(servers));
    }),
    rest.put(`/user/server/${servers[0].server_id}`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(502));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(2)));
    })
  );

  const { addNotification } = renderUserServerTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const serverRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(serverRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit server" })).toBeInTheDocument();
  await screen.findByRole("button", { name: /Save/i });

  // AND WHEN we edit some data and hit 'save'
  const serverNameInput = screen.getByRole("textbox", { name: "server_name" });
  await userEvent.type(serverNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the failure message
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "Unknown error occurred.",
      dismissible: true,
      header: "Edit server",
      type: "error",
    });
  });
});

test('click on row enables "Delete" button, shows "Delete" modal', async () => {
  // GIVEN
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(generateTestServers(1)));
    })
  );

  renderUserServerTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const serverRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(serverRowCheckbox);

  // THEN
  expect(await screen.findByRole("heading", { name: "Servers (1 of 1)" })).toBeInTheDocument();
  expect(deleteButton).not.toBeDisabled();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(withinModal.getByRole("heading", { name: "Delete servers" })).toBeInTheDocument();
  expect(withinModal.getByText("Are you sure you wish to delete the 1 selected servers?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(withinModal.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Servers (1 of 1)" })).toBeInTheDocument();
});

test("confirming the deletion successfully deletes a server", async () => {
  // GIVEN
  const servers = generateTestServers(1);
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response.once(context.status(200), context.json(servers));
    }),
    rest.delete(`/user/server/:id`, (request, response, context) => {
      return response(context.status(204));
    })
  );

  const { addNotification } = renderUserServerTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const serverRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(serverRowCheckbox);
  await userEvent.click(deleteButton);
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    content: "unittest0 was deleted.",
    dismissible: true,
    header: "Server deleted successfully",
    type: "success",
  });
  expect(await screen.findByRole("heading", { name: "Servers (0)" })).toBeInTheDocument();
});

test("delete multiple servers", async () => {
  // GIVEN
  const servers = generateTestServers(2);
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response.once(context.status(200), context.json(servers));
    }),
    rest.delete(`/user/server/:id`, (request, response, context) => {
      return response(context.status(204));
    })
  );

  const { addNotification } = renderUserServerTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();
  await userEvent.click(deleteButton);

  const serverRowCheckBoxes = screen.getAllByRole("checkbox");

  // WHEN
  await userEvent.click(serverRowCheckBoxes[0]);

  // THEN
  expect(await screen.findByRole("heading", { name: "Servers (2 of 2)" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(await withinModal.findByText("Are you sure you wish to delete the 2 selected servers?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    dismissible: false,
    header: "Deleting selected servers...",
    loading: true,
    type: "success",
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "unittest0, unittest1 were deleted.",
      dismissible: true,
      header: "Servers deleted successfully",
      type: "success",
    });
  });
});

test("click on export downloads an xlsx file", async () => {
  // GIVEN
  jest.spyOn(XLSX.utils, "json_to_sheet");

  const testServers = generateTestServers(2);
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(testServers));
    })
  );
  renderUserServerTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading servers/i));

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

  const testServers = generateTestServers(2);
  server.use(
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(testServers));
    })
  );
  renderUserServerTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading servers/i));

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
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(generateTestServers(2)));
    })
  );

  renderUserServerTable({
    ...defaultTestProps,
    userEntityAccess: {
      ...defaultTestProps.userEntityAccess,
      server: {
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
