/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {render, screen, waitFor, within} from '@testing-library/react';
import React from "react";
import '@testing-library/jest-dom'
import AdminPermissions from "./AdminPermissions";
import userEvent from "@testing-library/user-event";
import {defaultTestProps, mockNotificationContext} from "../__tests__/TestUtils";
import {server} from "../setupTests";
import {rest} from "msw";

import groups from "../../test_data/default_groups.json";
import {NotificationContext} from '../contexts/NotificationContext';
import {generateTestPolicies} from "../__tests__/mocks/admin_api";

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

test('click on add button opens "Add group" form', async () => {
  // GIVEN
  renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole('tab', {name: 'Groups'}));

  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Add group"})).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole('button', {name: /Cancel/i}));

  // THEN
  expect(await screen.findByRole('heading', {name: 'Groups (0)'})).toBeInTheDocument();
});

test('submitting the "Add group" form saves a new group to API', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.post(`/admin/groups`, async (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(201),
      );
    }),
    rest.get('/admin/policy', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestPolicies(2))
      );
    }),
    rest.get('/login/groups', (request, response, context) => {
      return response(
        context.status(200),
        context.json(["admin", "readonly"])
      );
    })
  );

  const {addNotification} = renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole('tab', {name: 'Groups'}));

  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN
  const dialog = await screen.findByRole('dialog');
  expect(await within(dialog).findByRole('heading', {name: "Add group"})).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.type(within(dialog).getByRole('textbox', {name: 'Group Name'}), 'my-test-group');

  await userEvent.click(within(dialog).getByRole('button', {name: /Add/i}));


  // THEN verify the API has received the expected request
  expect(addNotification).toHaveBeenCalledWith({
    "content": `Adding new group: my-test-group`,
    "dismissible": false,
    "loading": true,
    "header": "Add group",
    "type": "success"
  });

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      "content": `New group added: my-test-group`,
      "dismissible": true,
      "header": "Add group",
      "type": "success"
    });
  });

  expect(captureRequest.groups[0].group_name).toEqual('my-test-group');
});

test('click on `delete` shows the Delete modal', async () => {
  // GIVEN
  server.use(
    rest.get('/login/groups', (request, response, context) => {
      return response(
        context.status(200),
        context.json(["admin", "readonly"])
      );
    }),
  );
  renderAdminPermissionsComponent();
  const groupName = groups[0].group_name;

  await userEvent.click(screen.getByRole('tab', {name: 'Groups'}));
  const firstgroupRow = screen.getByRole('row', {name: groupName});
  await userEvent.click(firstgroupRow);

  // WHEN
  await userEvent.click(screen.getByRole('button', {name: "Delete"}));

  // THEN
  const withinModal = within(await screen.findByRole('dialog'));
  expect(withinModal.getByRole('heading', {name: "Delete group"})).toBeInTheDocument();
  expect(withinModal.getByText('Are you sure you wish to delete the selected group?')).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(withinModal.getByRole('button', {name: /Cancel/i}));

  // THEN
  expect(await screen.findByRole('heading', {name: "Groups (1 of 2)"})).toBeInTheDocument();
});

test('confirming the deletion successfully deletes a group', async () => {
  // GIVEN
  server.use(
    rest.get('/login/groups', (request, response, context) => {
      return response(
        context.status(200),
        context.json(["admin", "readonly"])
      );
    }),
    rest.delete(`/admin/groups/:id`, (request, response, context) => {
      return response(
        context.status(204)
      );
    })
  );
  const {addNotification} = renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole('tab', {name: 'Groups'}));

  const groupName = groups[0].group_name;
  const firstGroupRow = screen.getByRole('row', {name: groupName});
  await userEvent.click(firstGroupRow);
  await userEvent.click(screen.getByRole('button', {name: "Delete"}));

  const withinModal = within(await screen.findByRole('dialog'));

  // AND WHEN
  await userEvent.click(withinModal.getByRole('button', {name: /Ok/i}));

  // THEN
  expect(await screen.findByRole('heading', {name: "Groups (2)"})).toBeInTheDocument();

  expect(addNotification).toHaveBeenCalledWith({
    "content": `${groupName} was deleted.`,
    "dismissible": true,
    "header": "Group deleted successfully",
    "type": "success"
  });
});