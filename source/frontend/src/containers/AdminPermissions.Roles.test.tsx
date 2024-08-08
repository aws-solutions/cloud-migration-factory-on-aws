/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import "@testing-library/jest-dom";
import AdminPermissions from "./AdminPermissions";
import userEvent from "@testing-library/user-event";
import { defaultTestProps, mockNotificationContext } from "../__tests__/TestUtils";
import { server } from "../setupTests";
import { rest } from "msw";

import roles from "../../test_data/default_roles.json";
import { NotificationContext } from "../contexts/NotificationContext";
import { generateTestPolicies } from "../__tests__/mocks/admin_api";

const renderAdminPermissionsComponent = () => {
  return {
    ...mockNotificationContext,
    renderResult: render(
      <NotificationContext.Provider value={mockNotificationContext}>
        <AdminPermissions {...defaultTestProps} />
        <div id="modal-root" />
      </NotificationContext.Provider>
    ),
  };
};

test('click on add button opens "Add role" form', async () => {
  // GIVEN
  renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Roles" }));

  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Add role" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Roles (0)" })).toBeInTheDocument();
});

test('submitting the "Add role" form saves a new role to API', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.post(`/admin/role`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(201));
    }),
    rest.get("/admin/policy", (request, response, context) => {
      return response(context.status(200), context.json(generateTestPolicies(2)));
    }),
    rest.get("/login/groups", (request, response, context) => {
      return response(context.status(200), context.json(["admin", "readonly"]));
    })
  );

  renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Roles" }));

  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Add role" })).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.type(screen.getByRole("textbox", { name: "Role Name" }), "my-test-role");

  await userEvent.click(screen.getByLabelText("Attached Policies"));
  await userEvent.click(await screen.findByText("ReadOnly-1"));

  await userEvent.click(screen.getByLabelText("Groups"));
  await userEvent.click(await screen.findByText("readonly"));

  await userEvent.click(screen.getByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected request
  await waitFor(() => {
    expect(captureRequest.role_name).toEqual("my-test-role");
  });
  expect(await screen.findByRole("heading", { name: "Roles (0)" })).toBeInTheDocument();
});

test("click on a row enables `edit` button and shows details", async () => {
  // GIVEN
  server.use(
    rest.get("/admin/role", (request, response, context) => {
      return response(context.status(200), context.json(roles));
    })
  );
  renderAdminPermissionsComponent();
  const roleName = roles[0].role_name;

  await userEvent.click(screen.getByRole("tab", { name: "Roles" }));
  const firstRoleRow = screen.getByRole("row", { name: roleName });

  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeDisabled();

  // WHEN
  await userEvent.click(firstRoleRow);

  // THEN
  expect(editButton).toBeEnabled();
  expect(screen.getByRole("tab", { name: "Details" })).toBeInTheDocument();

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit role" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Roles (1 of 2)" })).toBeInTheDocument();
});

test('submitting the "Edit role" form saves the updated role to API', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.get("/admin/role", (request, response, context) => {
      return response(context.status(200), context.json(roles));
    }),
    rest.put(`/admin/role/:id`, async (request, response, context) => {
      request.json().then((body) => {
        return (captureRequest = body);
      });
      return response(context.status(201));
    }),
    rest.get("/admin/policy", (request, response, context) => {
      return response(context.status(200), context.json(generateTestPolicies(2)));
    }),
    rest.get("/login/groups", (request, response, context) => {
      return response(context.status(200), context.json(["admin", "readonly"]));
    })
  );

  renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole("tab", { name: "Roles" }));

  const roleName = roles[0].role_name;
  const firstRoleRow = screen.getByRole("row", { name: roleName });

  const editButton = screen.getByRole("button", { name: "Edit" });
  await userEvent.click(firstRoleRow);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit role" })).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.type(screen.getByRole("textbox", { name: "Role Name" }), "updated-role");

  await userEvent.click(screen.getByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected request
  await waitFor(() => {
    expect(captureRequest.role_name).toEqual(roleName + "updated-role");
  });
  expect(await screen.findByRole("heading", { name: `Roles (${roles.length})` })).toBeInTheDocument();
});

test("click on `delete` shows the Delete modal", async () => {
  // GIVEN
  server.use(
    rest.get("/admin/role", (request, response, context) => {
      return response(context.status(200), context.json(roles));
    })
  );
  renderAdminPermissionsComponent();
  const roleName = roles[0].role_name;

  await userEvent.click(screen.getByRole("tab", { name: "Roles" }));
  const firstRoleRow = screen.getByRole("row", { name: roleName });
  await userEvent.click(firstRoleRow);

  // WHEN
  await userEvent.click(screen.getByRole("button", { name: "Delete" }));

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  // TODO why 'policy' and not 'role'? is this a bug?
  expect(withinModal.getByRole("heading", { name: "Delete policy" })).toBeInTheDocument();
  expect(withinModal.getByText("Are you sure you wish to delete the selected policy?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(withinModal.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Roles (1 of 2)" })).toBeInTheDocument();
});

test("confirming the deletion successfully deletes a role", async () => {
  // GIVEN
  server.use(
    rest.get("/admin/role", (request, response, context) => {
      return response(context.status(200), context.json(roles));
    }),
    rest.delete(`/admin/role/:id`, (request, response, context) => {
      return response(context.status(204));
    })
  );

  const { addNotification } = renderAdminPermissionsComponent();
  const roleName = roles[0].role_name;

  await userEvent.click(screen.getByRole("tab", { name: "Roles" }));
  const firstRoleRow = screen.getByRole("row", { name: roleName });
  await userEvent.click(firstRoleRow);
  await userEvent.click(screen.getByRole("button", { name: "Delete" }));

  const withinModal = within(await screen.findByRole("dialog"));

  // AND WHEN
  await userEvent.click(withinModal.getByRole("button", { name: /Ok/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Roles (2)" })).toBeInTheDocument();

  expect(addNotification).toHaveBeenCalledWith({
    content: `${roleName} was deleted.`,
    dismissible: true,
    header: "Group deleted successfully",
    type: "success",
  });
});
