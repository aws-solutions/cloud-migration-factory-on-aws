/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {render, screen, within} from '@testing-library/react';
import React from "react";
import '@testing-library/jest-dom'
import AdminPermissions from "./AdminPermissions";
import userEvent from "@testing-library/user-event";
import {defaultTestProps, mockNotificationContext} from "../__tests__/TestUtils";
import {server} from "../setupTests";
import {rest} from "msw";

import users from "../../test_data/default_users.json";
import {NotificationContext} from '../contexts/NotificationContext';

const renderAdminPermissionsComponent = () => {
  return {
    ...mockNotificationContext,
    renderResult: render(
      <NotificationContext.Provider value={mockNotificationContext}>
        <AdminPermissions
          {...defaultTestProps}
        />
        <div id='modal-root'/>
      </NotificationContext.Provider>
    )
  };
}

test('click on add button opens "Add user to group" form', async () => {
  // GIVEN
  server.use(
    rest.get('/admin/users', (request, response, context) => {
      return response(
        context.status(200),
        context.json(users)
      );
    }),
  );
  renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole('tab', {name: 'Users'}));

  const userEmail = users[0].email;
  const firstUserCell = screen.getByRole('cell', {name: userEmail});
  await userEvent.click(firstUserCell);

  const actionsMenu = screen.getByRole('button', {name: "Actions"});

  // WHEN
  await userEvent.click(actionsMenu);

  // THEN
  const addToGroupBtn = await screen.findByRole('menuitem', {name: "Add users to group"});
  expect(addToGroupBtn).toBeInTheDocument();
  const removeFromGroupBtn = await screen.findByRole('menuitem', {name: "Remove users to group"}); // sic!
  expect(removeFromGroupBtn).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(addToGroupBtn);

  // THEN
  const addUserToGroupModal = await screen.findByRole('dialog');
  expect(await within(addUserToGroupModal).findByRole('heading', {name: "Select groups to add"})).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole('button', {name: "Cancel"}));

  // THEN
  expect(addUserToGroupModal).not.toBeInTheDocument();
});

test('submitting "Add user to group" form saves user with new group', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.get('/admin/users', (request, response, context) => {
      return response(
        context.status(200),
        context.json(users)
      );
    }),
    rest.get('/login/groups', (request, response, context) => {
      return response(
        context.status(200),
        context.json(["admin", "readonly"])
      );
    }),
    rest.put(`/admin/users`, async (request, response, context) => {
      request.json().then(body => {
        return captureRequest = body;
      });
      return response(
        context.status(200),
      );
    }),
  );

  renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole('tab', {name: 'Users'}));

  const userEmail = users[0].email;
  const firstUserCell = screen.getByRole('cell', {name: userEmail});
  await userEvent.click(firstUserCell);

  const actionsMenu = screen.getByRole('button', {name: "Actions"});

  // WHEN
  await userEvent.click(actionsMenu);
  await userEvent.click(await screen.findByRole('menuitem', {name: "Add users to group"}));

  // THEN
  const addUserToGroupModal = await screen.findByRole('dialog');
  expect(await within(addUserToGroupModal).findByRole('heading', {name: "Select groups to add"})).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.click(within(addUserToGroupModal).getByRole('button', {name: /group selection/i}));
  await userEvent.click(await screen.findByText('readonly'));

  await userEvent.click(screen.getByRole('button', {name: /update/i}));

  // THEN
  expect(addUserToGroupModal).not.toBeInTheDocument();
  expect(captureRequest.users[0].addGroups).toEqual(["readonly"]);
});

test('submitting "Remove user from group" form saves user without selected group', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.get('/admin/users', (request, response, context) => {
      return response(
        context.status(200),
        context.json(users)
      );
    }),
    rest.get('/login/groups', (request, response, context) => {
      return response(
        context.status(200),
        context.json(["admin", "readonly"])
      );
    }),
    rest.put(`/admin/users`, async (request, response, context) => {
      request.json().then(body => {
        return captureRequest = body;
      });
      return response(
        context.status(200),
      );
    }),
  );

  renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole('tab', {name: 'Users'}));

  const userEmail = users[0].email;
  const firstUserCell = screen.getByRole('cell', {name: userEmail});
  await userEvent.click(firstUserCell);

  const actionsMenu = screen.getByRole('button', {name: "Actions"});

  // WHEN
  await userEvent.click(actionsMenu);
  const removeGroupButton = await screen.findByRole('menuitem', {name: "Remove users to group"}); // sic!
  await userEvent.click(removeGroupButton);

  // THEN
  const removeUserFromGroupModal = await screen.findByRole('dialog');
  expect(await within(removeUserFromGroupModal).findByRole('heading', {name: "Select groups to remove"})).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.click(within(removeUserFromGroupModal).getByRole('button', {name: /group selection/i}));
  await userEvent.click(await screen.findByText('readonly'));

  await userEvent.click(screen.getByRole('button', {name: /update/i}));

  // THEN
  expect(removeUserFromGroupModal).not.toBeInTheDocument();
  expect(captureRequest.users[0].removeGroups).toEqual(["readonly"]);
});

test('shows notification on server error', async () => {
  // GIVEN
  server.use(
    rest.get('/admin/users', (request, response, context) => {
      return response(
        context.status(200),
        context.json(users)
      );
    }),
    rest.get('/login/groups', (request, response, context) => {
      return response(
        context.status(200),
        context.json(["admin", "readonly"])
      );
    }),
    rest.put(`/admin/users`, async (request, response, context) => {
      return response(
        context.status(500), // simulate error
        context.body("Some server error")
      );
    }),
  );

  const {addNotification} = renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole('tab', {name: 'Users'}));

  const userEmail = users[0].email;
  const firstUserCell = screen.getByRole('cell', {name: userEmail});
  await userEvent.click(firstUserCell);

  const actionsMenu = screen.getByRole('button', {name: "Actions"});

  // WHEN
  await userEvent.click(actionsMenu);
  const removeGroupButton = await screen.findByRole('menuitem', {name: "Remove users to group"}); // sic!
  await userEvent.click(removeGroupButton);

  // THEN
  const removeUserFromGroupModal = await screen.findByRole('dialog');
  expect(await within(removeUserFromGroupModal).findByRole('heading', {name: "Select groups to remove"})).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.click(within(removeUserFromGroupModal).getByRole('button', {name: /group selection/i}));
  await userEvent.click(await screen.findByText('readonly'));

  await userEvent.click(screen.getByRole('button', {name: /update/i}));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    id: undefined,
    type: 'error',
    dismissible: true,
    header: "Update users",
    content: "Remove from group failed: Some server error"
  })
});
