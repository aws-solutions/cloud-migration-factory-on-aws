/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import "@testing-library/jest-dom";
import AdminPermissions from "./AdminPermissions";
import userEvent from "@testing-library/user-event";
import { defaultTestProps, mockNotificationContext } from "../__tests__/TestUtils";
import { server } from "../setupTests";
import { rest } from "msw";

import roles from "../../test_data/default_roles.json";
import policies from "../../test_data/default_policies.json";
import users from "../../test_data/default_users.json";
import { NotificationContext } from "../contexts/NotificationContext";

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

test("Admin permissions screen loads and displays tabs.", () => {
  renderAdminPermissionsComponent();
  expect(screen.getByRole("tab", { name: "Roles" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Policies" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Groups" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Users" })).toBeInTheDocument();
});

test("Switch to Roles tab and select first role to show details.", async () => {
  // GIVEN
  server.use(
    rest.get("/admin/role", (request, response, context) => {
      return response(context.status(200), context.json(roles));
    })
  );
  renderAdminPermissionsComponent();
  const roleName = roles[0].role_name;

  // WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Roles" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Roles (2)" })).toBeInTheDocument();
  const firstRoleRow = screen.getByRole("row", { name: roleName });
  expect(firstRoleRow).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();

  // AND WHEN
  await userEvent.click(firstRoleRow);

  // THEN
  expect(screen.getByRole("heading", { name: "Roles (1 of 2)" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Details" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: roleName })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete" })).toBeEnabled();
});

test("Switch to Groups tab.", async () => {
  // GIVEN
  // caution, for groups the AdminPermissionsHook calls the loginApi instead of the AdminAPI, and the response has a different structure then in testdata/default_groups.json
  // not sure if that is on purpose
  const groups = ["admin", "readonly"];
  server.use(
    rest.get("/login/groups", (request, response, context) => {
      return response(context.status(200), context.json(groups));
    })
  );
  renderAdminPermissionsComponent();
  const groupName = groups[0];

  // WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Groups" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Groups (2)" })).toBeInTheDocument();
  const firstGroupRow = screen.getByRole("row", { name: groupName });
  expect(firstGroupRow).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();

  // AND WHEN
  await userEvent.click(firstGroupRow);

  // THEN
  expect(screen.getByRole("heading", { name: "Groups (1 of 2)" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete" })).toBeEnabled();
});

test("Switch to Policies tab and select first policy to show details.", async () => {
  // GIVEN
  server.use(
    rest.get("/admin/policy", (request, response, context) => {
      return response(context.status(200), context.json(policies));
    })
  );

  renderAdminPermissionsComponent();
  const policyName = policies[0].policy_name;

  // WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Policies" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Policies (2)" })).toBeInTheDocument();
  const firstPolicyRow = screen.getByRole("row", { name: policyName });
  expect(firstPolicyRow).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Edit" })).toBeDisabled();

  // AND WHEN
  await userEvent.click(firstPolicyRow);

  // THEN
  expect(screen.getByRole("heading", { name: "Policies (1 of 2)" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Details" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: policyName })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete" })).toBeEnabled();
});

test("Switch to Users tab.", async () => {
  // GIVEN
  server.use(
    rest.get("/admin/users", (request, response, context) => {
      return response(context.status(200), context.json(users));
    })
  );

  renderAdminPermissionsComponent();
  const userEmail = users[0].email;

  // WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Users" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Users (1)" })).toBeInTheDocument();
  const firstUserRow = screen.getByRole("cell", { name: userEmail });
  expect(firstUserRow).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(firstUserRow);

  // THEN
  expect(screen.getByRole("heading", { name: "Users (1 of 1)" })).toBeInTheDocument();
});
