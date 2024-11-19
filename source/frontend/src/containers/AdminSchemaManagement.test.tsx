/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {render, screen, waitFor, within} from "@testing-library/react";
import React from "react";

import {defaultTestProps, mockNotificationContext} from "../__tests__/TestUtils";
import AdminSchemaMgmt from "./AdminSchemaMgmt";
import {NotificationContext} from "../contexts/NotificationContext";
import userEvent from "@testing-library/user-event";
import {server} from "../setupTests";
import {rest} from "msw";

const renderAdminSchemaManagementComponent = () => {
  return {
    addNotification: mockNotificationContext.addNotification,
    renderResult: render(
      <NotificationContext.Provider value={mockNotificationContext}>
        <AdminSchemaMgmt {...defaultTestProps} />
      </NotificationContext.Provider>
    ),
  };
};

test("Schema management screen loads and displays tabs.", () => {
  renderAdminSchemaManagementComponent();
  expect(screen.getByRole("tab", { name: "Database" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Wave" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Application" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Server" })).toBeInTheDocument();

  expect(screen.getByRole("tab", { name: "Attributes" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Info Panel" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Schema Settings" })).toBeInTheDocument();
});

test("loads Attributes table with the attributes of database schema", async () => {
  // GIVEN
  renderAdminSchemaManagementComponent();

  // WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Database" }));
  await userEvent.click(screen.getByRole("tab", { name: "Attributes" }));

  // THEN show the attributes according to the loaded schema
  expect(screen.getByRole("heading", { name: "Attributes (5)" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: /database_id/i })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: /app_id/i })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: /database_name/i })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: /database_type/i })).toBeInTheDocument();
});

test('click on add button opens "Add attribute" form', async () => {
  // GIVEN
  renderAdminSchemaManagementComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Database" }));
  await userEvent.click(screen.getByRole("tab", { name: "Attributes" }));

  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(screen.getByRole("heading", { name: "Amend attribute" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN the dialog should be closed
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("submitting the add form saves a new attribute to API", async () => {
  // GIVEN
  server.use(
    rest.put(`/admin/schema/database`, async (request, response, context) => {
      return response(context.status(200));
    })
  );
  const { addNotification } = renderAdminSchemaManagementComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Database" }));
  await userEvent.click(screen.getByRole("tab", { name: "Attributes" }));

  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN
  const dialog = screen.getByRole("dialog", { name: "Amend attribute" });
  expect(dialog).toBeInTheDocument();

  // AND WHEN we populate the required fields
  await userEvent.type(within(dialog).getByRole("textbox", { name: "Programmatic name" }), "my-name");
  await userEvent.type(within(dialog).getByRole("textbox", { name: "Display name" }), "My fancy name");

  await userEvent.click(within(dialog).getByRole("button", { name: /type/i }));
  await userEvent.click(await within(dialog).findByText("textarea"));

  await userEvent.click(within(dialog).getByRole("button", { name: /Save/i }));

  // THEN
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Add attribute",
      content: "my-name added successfully.",
    });
  });
});

test("submitting the edit form saves a new attribute to API", async () => {
  // GIVEN
  server.use(
    rest.put(`/admin/schema/database`, async (request, response, context) => {
      return response(context.status(200));
    })
  );
  const { addNotification } = renderAdminSchemaManagementComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Database" }));
  await userEvent.click(screen.getByRole("tab", { name: "Attributes" }));

  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeDisabled();

  // WHEN
  await userEvent.click(screen.getByRole("cell", { name: "Database Name" }));

  // THEN
  expect(editButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(editButton);

  // THEN
  const dialog = screen.getByRole("dialog", { name: "Amend attribute" });
  expect(dialog).toBeInTheDocument();

  // AND WHEN we change the display name
  await userEvent.type(within(dialog).getByRole("textbox", { name: "Display name" }), "Something");

  await userEvent.click(within(dialog).getByRole("button", { name: /Save/i }));

  // THEN
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Update attribute",
      content: "database_name updated successfully.",
    });
  });
});

test('click on non-system attribute row enables "Delete" button, shows "Delete" modal', async () => {
  // GIVEN
  server.use(
    rest.put(`/admin/schema/database`, async (request, response, context) => {
      return response(context.status(200));
    })
  );

  const { addNotification } = renderAdminSchemaManagementComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Database" }));
  await userEvent.click(screen.getByRole("tab", { name: "Attributes" }));

  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  // WHEN clicking on an attribute that is not `system: true`
  await userEvent.click(screen.getByRole("cell", { name: "Foo" }));

  // THEN
  expect(deleteButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const dialog = screen.getByRole("dialog", { name: "Delete attribute" });
  expect(dialog).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(within(dialog).getByRole("button", { name: /Ok/i }));

  // THEN
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Attribute deleted successfully",
      content: "foo was deleted.",
    });
  });
});

test("editing the info panel", async () => {
  // GIVEN
  let capturedRequest: any;
  server.use(
    rest.put(`/admin/schema/database`, async (request, response, context) => {
      request.json().then((json) => (capturedRequest = json));
      return response(context.status(200));
    })
  );
  const { addNotification } = renderAdminSchemaManagementComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Database" }));
  await userEvent.click(screen.getByRole("tab", { name: "Info Panel" }));

  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeEnabled();

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(screen.getByRole("heading", { name: "Info panel guidance" })).toBeInTheDocument();

  // AND WHEN we fill out all fields
  await userEvent.type(screen.getByRole("textbox", { name: /Help title/i }), "This is a heading");
  await userEvent.type(screen.getByRole("textbox", { name: /Help content/i }), "This is a test");

  await userEvent.click(screen.getByRole("button", { name: /Add new URL/i }));

  await userEvent.type(screen.getByRole("combobox", { name: /help links label/i }), "This is a link");
  await userEvent.type(screen.getByRole("combobox", { name: /help links url - optional/i }), "https://example.com");

  await userEvent.click(screen.getByRole("button", { name: /Save/i }));

  // THEN
  await waitFor(() => {
    expect(capturedRequest).toEqual({
      event: "PUT",
      update_schema: {
        schema_name: "database",
        help_content: {
          header: "This is a heading",
          content_html: "This is a test",
          content_links: [
            {
              key: "This is a link",
              value: "https://example.com",
              existing: false,
            },
          ],
        },
      },
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Update schema help",
      content: "Schema updated successfully.",
    });
  });
});

test("cancelling the edit of the info panel", async () => {
  // GIVEN
  renderAdminSchemaManagementComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Database" }));
  await userEvent.click(screen.getByRole("tab", { name: "Info Panel" }));

  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeEnabled();

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(screen.getByRole("heading", { name: "Info panel guidance" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN
  const dialog = await screen.findByRole("dialog", { name: "Cancel schema update" });
  expect(dialog).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(within(dialog).getByRole("button", { name: /Ok/i }));

  // THEN
  expect(screen.queryByRole("textbox", { name: /Help title/i })).not.toBeInTheDocument();
});

test("editing the schema settings", async () => {
  // GIVEN
  let capturedRequest: any;
  server.use(
    rest.put(`/admin/schema/database`, async (request, response, context) => {
      request.json().then((json) => (capturedRequest = json));
      return response(context.status(200));
    })
  );
  const { addNotification } = renderAdminSchemaManagementComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Database" }));
  await userEvent.click(screen.getByRole("tab", { name: "Schema Settings" }));

  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeEnabled();

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("textbox", { name: /Schema friendly name/i })).toBeInTheDocument();

  // AND WHEN
  await userEvent.type(screen.getByRole("textbox", { name: /Schema friendly name/i }), "New Friendly Name");

  await userEvent.click(screen.getByRole("button", { name: /Save/i }));

  // THEN
  await waitFor(() => {
    expect(capturedRequest).toEqual({
      event: "PUT",
      update_schema: {
        schema_name: "database",
        friendly_name: "New Friendly Name",
      },
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Update schema settings",
      content: "Schema updated successfully.",
    });
  });
});

test("cancelling the edit of the schema settings", async () => {
  // GIVEN
  renderAdminSchemaManagementComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Database" }));
  await userEvent.click(screen.getByRole("tab", { name: "Schema Settings" }));

  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeEnabled();

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("textbox", { name: /Schema friendly name/i })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN
  const dialog = await screen.findByRole("dialog", { name: "Cancel schema update" });
  expect(dialog).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(within(dialog).getByRole("button", { name: /Ok/i }));

  // THEN
  expect(screen.queryByRole("textbox", { name: /Schema friendly name/i })).not.toBeInTheDocument();
});
