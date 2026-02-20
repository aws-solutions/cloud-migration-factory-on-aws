/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen, waitFor, waitForElementToBeRemoved, within } from "@testing-library/react";
import * as XLSX from "xlsx";
import UserServerTable from "./UserTableServers";
import { MemoryRouter } from "react-router-dom";
import { mockNotificationContext, TEST_SESSION_STATE, wpmTestProps } from "../__tests__/TestUtils";
import { SessionContext } from "../contexts/SessionContext";
import { rest } from "msw";
import { server } from "../setupTests";
import {
  generateTestApps,
  generateTestMoveGroups,
  generateTestServers,
  generateTestWaves,
  generateTestWpmJobs,
} from "../__tests__/mocks/user_api";
import userEvent from "@testing-library/user-event";
import { NotificationContext } from "../contexts/NotificationContext";
import { Server } from "../models";

function renderUserServerTable(props = wpmTestProps) {
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

function setupApiCallsForLoad(...svrs: Server[][]) {
  let getDatabaseCall = 0;
  server.use(
    rest.get("/user/server", (request, response, context) => {
      const index = Math.min(getDatabaseCall++, svrs.length - 1);
      return response(context.status(200), context.json(svrs[index]));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(2)));
    }),
    rest.get("/user/move_group", (request, response, context) => {
      return response(context.status(200), context.json(generateTestMoveGroups(1)));
    }),
    rest.get("/user/wave", (request, response, context) => {
      return response(context.status(200), context.json(generateTestWaves(1)));
    }),
    rest.get("/user/wpm_job", (request, response, context) => {
      return response(context.status(200), context.json(generateTestWpmJobs(1)));
    })
  );
}

function setupApiCallsForSave(operation: "post" | "put" | "delete", createSvrItem?: Server) {
  const saveSvrRequestBodies: any[] = [];
  const manageEntityRequestBodies: any[] = [];
  const saveAppRequestBodies: any[] = [];

  if (operation === "post") {
    server.use(
      rest.post(`/user/server`, async (request, response, context) => {
        request.json().then((body) => saveSvrRequestBodies.push(body));
        return response(context.status(200), context.json({ newItems: [createSvrItem] }));
      })
    );
  } else if (operation === "put") {
    server.use(
      rest.put(`/user/server/:id`, async (request, response, context) => {
        request.json().then((body) => saveSvrRequestBodies.push(body));
        return response(context.status(200));
      })
    );
  }

  server.use(
    rest.put(`/user/app/:id`, (request, response, context) => {
      request.json().then((body) => saveAppRequestBodies.push(body));
      return response(context.status(200), context.json({}));
    }),
    rest.post("/manage-entities", (request, response, context) => {
      request.json().then((body) => manageEntityRequestBodies.push(body));
      return response(context.status(200), context.json({}));
    })
  );

  return {
    saveSvrRequestBodies,
    manageEntityRequestBodies,
    saveAppRequestBodies,
  };
}

test('it renders an empty table with "no servers" message', async () => {
  // WHEN
  renderUserServerTable();

  // THEN
  // page should render in loading state
  expect(screen.getByRole("heading", { name: "Servers (0)" })).toBeInTheDocument();
  expect(screen.getByText("Loading Servers")).toBeInTheDocument();

  // after server response came in, it should render the table
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading servers/i));

  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];

  expect(await within(tbody).findByText("No Servers")).toBeInTheDocument();
  expect(within(tbody).getByRole("button", { name: "Add Server" })).toBeInTheDocument();
});

test("it renders a paginated table with 50 servers", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestServers(50));

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
  setupApiCallsForLoad(generateTestServers(1), generateTestServers(5));

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
  const [svr0, svr1] = generateTestServers(2);
  setupApiCallsForLoad([svr0], [svr0, svr1]);
  const { saveSvrRequestBodies, saveAppRequestBodies, manageEntityRequestBodies } = setupApiCallsForSave("post", svr1);

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

  await userEvent.click(screen.getByText("Select Related Applications"));
  await userEvent.click(await screen.findByText("Unit testing App 1"));

  await userEvent.click(
    screen.getByRole("button", { name: /migration strategy info r_type select migration strategy/i })
  );
  await userEvent.click(await screen.findByText("Retire"));

  await userEvent.click(screen.getByLabelText("Server OS Family"));
  await userEvent.click(await screen.findByText("windows"));

  await userEvent.type(screen.getByRole("textbox", { name: "server_environment" }), "Production");
  await userEvent.type(screen.getByRole("textbox", { name: "server_os_version" }), "Production");

  await userEvent.click(screen.getByRole("button", { name: /select aws account id/i }));
  await userEvent.click(await screen.findByText("123456789012")); // see default_schema.ts

  await userEvent.click(screen.getByLabelText("AWS Region"));
  await userEvent.click(await screen.findByText("us-east-1"));

  // TODO: Set Move Group ID, but it is blocked by WPM-666

  // THEN expect no more validation errors
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  await waitFor(() => expect(saveButton).toBeEnabled());
  expect(screen.queryByText("You must specify a valid value.")).not.toBeInTheDocument();

  // AND WHEN we hit 'save'
  await userEvent.click(saveButton);

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(saveSvrRequestBodies).toEqual([
      {
        app_ids: ["1"],
        r_type: "Retire",
        server_environment: "Production",
        server_fqdn: "foo",
        server_name: "my-test-server",
        server_os_family: "windows",
        server_os_version: "Production",
        aws_accountid: "123456789012",
        aws_region: "us-east-1",
      },
    ]);
  });
  await waitFor(() => {
    expect(saveAppRequestBodies).toEqual([{ server_ids: ["1"] }]);
  });
  await waitFor(() => {
    expect(manageEntityRequestBodies).toEqual([
      {
        // TODO: Set Move Group ID, but it is blocked by WPM-666
        // destination_entity_id: "1",
        destination_entity_type: "move_group",
        operation: "move",
        source_entity_type: "move_group",
        target_entities: [
          {
            entity_id: "1",
            entity_type: "server",
          },
        ],
      },
    ]);
  });

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "my-test-server added successfully.",
      dismissible: true,
      header: "Add server",
      type: "success",
    });
  });
});

test('click on row enables "Edit" button and shows "Details" tab', async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestServers(1));

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
      header: "Edit server",
      type: "warning",
    });
  });
});

test("submitting the edit form saves the server to API", async () => {
  // GIVEN
  const servers = generateTestServers(1, { appId: "0" });

  setupApiCallsForLoad(servers);
  const { saveSvrRequestBodies, saveAppRequestBodies, manageEntityRequestBodies } = setupApiCallsForSave("put");

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

  expect(await screen.findByText("Unit testing App 0")).toBeInTheDocument();

  // AND WHEN we edit some data and hit 'save'
  const serverNameInput = screen.getByRole("textbox", { name: "server_name" });
  await userEvent.type(serverNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(saveSvrRequestBodies).toEqual([{ server_name: "unittest0-some-name" }]);
    expect(saveAppRequestBodies).toEqual([]);
    expect(manageEntityRequestBodies).toEqual([]);
  });
  await screen.findByRole("heading", { name: "Servers (1)" });
});

test("when update fails with server error, display notification", async () => {
  // GIVEN
  const servers = generateTestServers(1);
  setupApiCallsForLoad(servers);

  server.use(
    rest.put(`/user/server/${servers[0].server_id}`, async (request, response, context) => {
      request.json().then(() => {});
      return response(context.status(502));
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
  setupApiCallsForLoad(generateTestServers(1));

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
  setupApiCallsForLoad(generateTestServers(1), []);
  const { saveAppRequestBodies, saveSvrRequestBodies, manageEntityRequestBodies } = setupApiCallsForSave("delete");

  const { addNotification } = renderUserServerTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const serverRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(serverRowCheckbox);
  await userEvent.click(deleteButton);
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(saveAppRequestBodies).toEqual([]);
  expect(saveSvrRequestBodies).toEqual([]);
  expect(manageEntityRequestBodies).toEqual([{ entity_ids: ["0"], entity_type: "server", operation: "cleanup" }]);

  expect(addNotification).toHaveBeenCalledWith({
    content: "unittest0 was deleted.",
    dismissible: true,
    header: "Delete server",
    type: "success",
  });
  expect(await screen.findByRole("heading", { name: "Servers (0)" })).toBeInTheDocument();
});

test("delete multiple servers", async () => {
  // GIVEN
  setupApiCallsForLoad(generateTestServers(2), []);
  const { saveAppRequestBodies, saveSvrRequestBodies, manageEntityRequestBodies } = setupApiCallsForSave("delete");

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
  expect(saveAppRequestBodies).toEqual([]);
  expect(saveSvrRequestBodies).toEqual([]);
  expect(manageEntityRequestBodies).toEqual([{ entity_ids: ["0", "1"], entity_type: "server", operation: "cleanup" }]);

  expect(addNotification).toHaveBeenCalledWith({
    dismissible: false,
    header: "Deleting selected servers...",
    loading: true,
  });

  await waitFor(
    () => {
      expect(addNotification).toHaveBeenCalledWith({
        content: "unittest0, unittest1 were deleted.",
        dismissible: true,
        header: "Delete servers",
        type: "success",
      });
    },
    { timeout: 10_000 }
  );
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
    ...wpmTestProps,
    userEntityAccess: {
      ...wpmTestProps.userEntityAccess,
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
