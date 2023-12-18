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

import policies from "../../test_data/default_policies.json";
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

test('click on add button opens "Add policy" form', async () => {
  // GIVEN
  renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole('tab', {name: 'Policies'}));

  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Add policy"})).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole('button', {name: /Cancel/i}));

  // THEN
  const dialog = await screen.findByRole('dialog', {name: 'Unsaved changes'});
  expect(dialog).toBeInTheDocument();

  // AND WHEN
  screen.logTestingPlaygroundURL(dialog)
  await userEvent.click(await within(dialog).findByRole('button', {name: /Ok/i}));

  // THEN
  expect(await screen.findByRole('heading', {name: 'Policies (0)'})).toBeInTheDocument();
});

test('submitting the "Add policy" form saves a new policy to API', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.post(`/admin/policy`, async (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(201),
      );
    }),
  );

  renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole('tab', {name: 'Policies'}));

  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Add policy"})).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.type(screen.getByRole('textbox', {name: 'Policy Name'}), 'my-test-policy');

  await userEvent.click(screen.getByRole('button', {name: /Save/i}));

  // THEN verify the API has received the expected request
  await waitFor(() => {
    expect(captureRequest.policy_name).toEqual('my-test-policy');
  })
  expect(await screen.findByRole('heading', {name: 'Policies (0)'})).toBeInTheDocument();
});

test('click on a row enables `edit` button and shows details', async () => {
  // GIVEN
  server.use(
    rest.get('/admin/policy', (request, response, context) => {
      return response(
        context.status(200),
        context.json(policies)
      );
    }),
  );
  renderAdminPermissionsComponent();
  const policyName = policies[0].policy_name;

  await userEvent.click(screen.getByRole('tab', {name: 'Policies'}));
  const firstPolicyRow = screen.getByRole('row', {name: policyName});

  const editButton = screen.getByRole('button', {name: "Edit"});
  expect(editButton).toBeDisabled();

  // WHEN
  await userEvent.click(firstPolicyRow);

  // THEN
  expect(editButton).toBeEnabled();
  expect(screen.getByRole('tab', {name: 'Details'})).toBeInTheDocument();

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole('heading', {name: 'Edit policy'})).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole('button', {name: /Cancel/i}));

  // THEN
  expect(await screen.findByRole('heading', {name: "Policies (1 of 2)"})).toBeInTheDocument();
});

test('submitting the "Edit policy" form saves the updated policy to API', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.get('/admin/policy', (request, response, context) => {
      return response(
        context.status(200),
        context.json(policies)
      );
    }),
    rest.put(`/admin/policy/:id`, async (request, response, context) => {
      request.json().then(body => {
        return captureRequest = body;
      });
      return response(
        context.status(201),
      );
    }),
  );

  renderAdminPermissionsComponent();
  await userEvent.click(screen.getByRole('tab', {name: 'Policies'}));

  const policyName = policies[0].policy_name;
  const firstRoleRow = screen.getByRole('row', {name: policyName});

  const editButton = screen.getByRole('button', {name: "Edit"});
  await userEvent.click(firstRoleRow);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Edit policy"})).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.type(screen.getByRole('textbox', {name: 'Policy Name'}), 'updated-policy');

  await userEvent.click(screen.getByRole('button', {name: /Save/i}));

  // THEN verify the API has received the expected request
  await waitFor(() => {
    expect(captureRequest.policy_name).toEqual(policyName + 'updated-policy');
  })
  expect(await screen.findByRole('heading', {name: `Policies (${policies.length})`})).toBeInTheDocument();
});

test('click on `delete` shows the Delete modal', async () => {
  // GIVEN
  server.use(
    rest.get('/admin/policy', (request, response, context) => {
      return response(
        context.status(200),
        context.json(policies)
      );
    }),
  );
  renderAdminPermissionsComponent();
  const policyName = policies[0].policy_name;

  await userEvent.click(screen.getByRole('tab', {name: 'Policies'}));
  const firstRoleRow = screen.getByRole('row', {name: policyName});
  await userEvent.click(firstRoleRow);

  // WHEN
  await userEvent.click(screen.getByRole('button', {name: "Delete"}));

  // THEN
  const withinModal = within(await screen.findByRole('dialog'));
  expect(withinModal.getByRole('heading', {name: "Delete policy"})).toBeInTheDocument();
  expect(withinModal.getByText('Are you sure you wish to delete the selected policy?')).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(withinModal.getByRole('button', {name: /Cancel/i}));

  // THEN
  expect(await screen.findByRole('heading', {name: "Policies (1 of 2)"})).toBeInTheDocument();
});

test('confirming the deletion successfully deletes a policy', async () => {
  // GIVEN
  server.use(
    rest.get('/admin/policy', (request, response, context) => {
      return response(
        context.status(200),
        context.json(policies)
      );
    }),
    rest.delete(`/admin/policy/:id`, (request, response, context) => {
      return response(
        context.status(204)
      );
    })
  );

  const {addNotification} = renderAdminPermissionsComponent();
  const policyName = policies[0].policy_name;

  await userEvent.click(screen.getByRole('tab', {name: 'Policies'}));
  const firstRoleRow = screen.getByRole('row', {name: policyName});
  await userEvent.click(firstRoleRow);
  await userEvent.click(screen.getByRole('button', {name: "Delete"}));

  const withinModal = within(await screen.findByRole('dialog'));

  // AND WHEN
  await userEvent.click(withinModal.getByRole('button', {name: /Ok/i}));

  // THEN
  expect(await screen.findByRole('heading', {name: "Policies (2)"})).toBeInTheDocument();

  expect(addNotification).toHaveBeenCalledWith({
    "content": `${policyName} was deleted.`,
    "dismissible": true,
    "header": "Policy deleted successfully",
    "type": "success"
  });
});
