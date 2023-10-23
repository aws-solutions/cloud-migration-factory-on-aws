// @ts-nocheck


/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  cleanup,
  screen,
  render,
  fireEvent,
  waitFor,
  waitForElementToBeRemoved,
  findByDisplayValue, findByText, findAllByDisplayValue, findAllByTestId
} from '@testing-library/react';
import React from "react";
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom'
import AdminPermissions from "./AdminPermissions";
import {setNestedValuePath} from "../resources/main";
const {promises: fsPromises} = require('fs');
afterEach(cleanup);

let props = {};
props.item = {}
var item = {
  "script": {
    "package_uuid": "d5ec74d4-9410-4525-83ce-c162ba36ed69"
  }
}
const mainSchemaFilename = 'default_schema.json'
const defaultRoles = 'default_roles.json'
const defaultPolicies = 'default_policies.json'
const defaultGroups = 'default_groups.json'
const defaultUsers = 'default_users.json'

const schemas = require('../../test_data/' + mainSchemaFilename)

// Function stubs
const handleUserInput = ev => {
  let valueArray = [];

  //Convert non-Array values to array in order to keep procedure simple.
  if(Array.isArray(ev)){
    valueArray = ev;
  } else {
    valueArray.push(ev);
  }

  for (const valueItem of valueArray) {
    setNestedValuePath(item, valueItem.field, valueItem.value);
  }
}

const handleStub = () => {

}

const setup = () => {
  const comp = render(
      <div>
        <AdminPermissions
          schema={schemas}
        />
        <div id='modal-root' />
      </div>
)
  return {
    ...comp
  }
}

jest.mock("../actions/AdminPermissionsHook", () => {
  const roles = require('../../test_data/' + defaultRoles)
  const policies = require('../../test_data/' + defaultPolicies)
  const groups = require('../../test_data/' + defaultGroups)
  const users = require('../../test_data/' + defaultUsers)

  return {
    useAdminPermissions: () => {
      return [{
        isLoading: false,
        data: {
          policies: policies,
          roles: roles,
          groups: groups,
          users: users
        },
        error: null
      }, {update: jest.fn()}];
    },
  };
});

test('Admin permissions screen loads and displays tabs.', () => {
  setup();
  expect(screen.getAllByText('Roles')).toBeTruthy();
  expect(screen.getAllByText('Policies')).toBeTruthy();
  expect(screen.getAllByText('Groups')).toBeTruthy();
  expect(screen.getAllByText('Users')).toBeTruthy();
});

test('Switch to Roles tab and select first role to show details.', async () => {
  setup();
  const roleName = "FactoryReadOnly";
  const groupsTab = await screen.getByTestId('roles')

  expect(groupsTab).toBeInTheDocument();
  await waitFor(() => {
    fireEvent.click(groupsTab)
  });

  expect(screen.getByText(roleName)).toBeTruthy();

  const tableItem = await screen.getByText(roleName);
  await waitFor(() => {
    fireEvent.click(tableItem)
  });

  expect(screen.getAllByText('Details')).toBeTruthy();

});

test('Switch to Groups tab.', async () => {
  setup();
  const groupsTab = await screen.getByTestId('groups')

  expect(groupsTab).toBeInTheDocument();
  await waitFor(() => {
    fireEvent.click(groupsTab)
  });

  expect(screen.getByText('admin')).toBeTruthy();
});

test('Switch to Policies tab and select first policy to show details.', async () => {
  setup();
  const policiesTab = await screen.getByTestId('policies')
  expect(policiesTab).toBeInTheDocument();
  await waitFor(() => {
    fireEvent.click(policiesTab)
  });

  expect(screen.getByText('Administrator')).toBeTruthy();

  const tableItem = await screen.getByText("Administrator");
  await waitFor(() => {
    fireEvent.click(tableItem)
  });

  expect(screen.getAllByText('Details')).toBeTruthy();
});

test('Switch to Users tab.', async () => {
  setup();
  const policiesUsers = await screen.getByTestId('users')
  expect(policiesUsers).toBeInTheDocument();
  await waitFor(() => {
    fireEvent.click(policiesUsers)
  });

  expect(screen.getByText('testuser@example.com')).toBeTruthy();
});

// test('Switch to Roles tab and select first role and click delete.', async () => {
//   const comp = setup();
//   const roleName = "FactoryReadOnly";
//   const groupsTab = await screen.getByTestId('roles')
//
//   expect(groupsTab).toBeInTheDocument();
//   await waitFor(() => {
//     userEvent.click(groupsTab)
//   });
//
//   expect(screen.getByText(roleName)).toBeTruthy();
//
//   const tableItem = await screen.getByText(roleName);
//   await waitFor(() => {
//     userEvent.click(tableItem)
//   });
//
//   const deleteButton = await screen.getByText('Delete');
//   console.log(deleteButton);
//   await waitFor(() => {
//     userEvent.click(deleteButton)
//   });
//   const someElement = comp.container.querySelector('#modal-root');
//   console.log(someElement);
//   expect(screen.getByText('Delete policy')).toBeTruthy();
// });

