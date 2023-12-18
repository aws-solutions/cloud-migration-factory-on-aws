import {mockNotificationContext, TEST_SESSION_STATE} from "../__tests__/TestUtils";
import {render, screen, waitFor, waitForElementToBeRemoved, within} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {SessionContext} from "../contexts/SessionContext";
import React from "react";
import CredentialManager from "./CredentialManager";
import userEvent from "@testing-library/user-event";
import {server} from "../setupTests";
import {rest} from "msw";
import {generateTestCredentials} from "../__tests__/mocks/credentialmanager_api";
import {NotificationContext} from "../contexts/NotificationContext";

function renderCredentialManager() {
  return {
    ...mockNotificationContext,
    renderResult: render(
      <MemoryRouter initialEntries={['/credential-manager']}>
        <NotificationContext.Provider value={mockNotificationContext}>
          <SessionContext.Provider value={TEST_SESSION_STATE}>
            <div id='modal-root'/>
            <CredentialManager></CredentialManager>
          </SessionContext.Provider>
        </NotificationContext.Provider>
      </MemoryRouter>
    )
  };
}

test('it renders an empty table with "no applications" message', async () => {
  // WHEN
  renderCredentialManager();

  // THEN page should render in loading state
  expect(screen.getByRole('heading', {name: "Secrets (0)"})).toBeInTheDocument();
  expect(screen.getByText(/Loading secrets/i)).toBeInTheDocument();

  // AND WHEN server response came in
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading secrets/i));

  // THEN it should render the table
  const table = screen.getByRole('table');
  expect(table).toBeInTheDocument();
});

test('click on add button opens "Add application" form', async () => {
  // GIVEN
  renderCredentialManager();
  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Create secret"})).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole('button', {name: /Cancel/i}));

  // THEN
  expect(await screen.findByRole('heading', {name: 'Secrets (0)'})).toBeInTheDocument();
});

test('submitting the add form saves a username/password to API', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.post(`/admin/credentialmanager`, async (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(201),
      );
    }),
    rest.get('/credentialmanager', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestCredentials(1))
      );
    }),
  );

  renderCredentialManager();
  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Create secret"})).toBeInTheDocument();
  expect(await screen.findByRole('button', {name: /Save/i})).not.toBeEnabled();

  // AND WHEN we populate all fields
  await userEvent.type(screen.getByRole('textbox', {name: 'Secret Name'}), 'my-test-secret');
  await userEvent.type(screen.getByRole('textbox', {name: 'User Name'}), 'my-user-name');
  await userEvent.click(screen.getByRole('checkbox', {name: 'SSH key used'}));
  await userEvent.type(screen.getByLabelText("SSH Key"), 'some-key');

  await userEvent.click(await screen.findByRole('button', {name: /Save/i}));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.description).toEqual('Secret for Migration Factory');
    expect(captureRequest.user).toEqual('my-user-name');
    expect(captureRequest.isSSHKey).toEqual(true);
    expect(captureRequest.password).toBeTruthy();
  });
  await screen.findByRole('heading', {name: 'Secrets (1)'});
});

test('submitting the add form saves secret key/value to API', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.post(`/admin/credentialmanager`, async (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(201),
      );
    }),
    rest.get('/credentialmanager', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestCredentials(1))
      );
    }),
  );

  renderCredentialManager();
  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Create secret"})).toBeInTheDocument();
  expect(await screen.findByRole('button', {name: /Save/i})).not.toBeEnabled();

  // AND WHEN we populate all fields
  await userEvent.click(await screen.findByRole('radio', {name: 'Secret key/value'}));
  await userEvent.type(screen.getByRole('textbox', {name: 'Secret Name'}), 'my-test-secret');
  await userEvent.type(screen.getByRole('textbox', {name: 'Key'}), 'my-key');
  await userEvent.type(screen.getByRole('textbox', {name: 'Value'}), 'my-value');

  await userEvent.click(await screen.findByRole('button', {name: /Save/i}));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest).toEqual({
      "secretName": "my-test-secret",
      "secretType": "keyValue",
      "description": "Secret for Migration Factory",
      "secretKey": "my-key",
      "secretValue": "my-value"
    });
  });
  await screen.findByRole('heading', {name: 'Secrets (1)'});
});

test('submitting the add form saves plaintext secret to API', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.post(`/admin/credentialmanager`, async (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(201),
      );
    }),
    rest.get('/credentialmanager', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestCredentials(1))
      );
    }),
  );

  renderCredentialManager();
  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Create secret"})).toBeInTheDocument();
  expect(await screen.findByRole('button', {name: /Save/i})).not.toBeEnabled();

  // AND WHEN we populate all fields
  await userEvent.click(await screen.findByRole('radio', {name: 'Plaintext'}));
  await userEvent.type(screen.getByRole('textbox', {name: 'Secret Name'}), 'my-test-secret');
  await userEvent.type(screen.getAllByLabelText("Plaintext")[1], 'some-secret');
  await userEvent.type(screen.getByRole('textbox', {name: 'Description'}), 'my-description');

  await userEvent.click(await screen.findByRole('button', {name: /Save/i}));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest).toEqual({
      "secretName": "my-test-secret",
      "secretType": "plainText",
      "description": "my-description",
      "secretString": "some-secret",
    });
  });
  await screen.findByRole('heading', {name: 'Secrets (1)'});
});

test('handles an API error', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.post(`/admin/credentialmanager`, async (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(403),
      );
    }),
    rest.get('/credentialmanager', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestCredentials(1))
      );
    }),
  );

  const {addNotification} = renderCredentialManager();
  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Create secret"})).toBeInTheDocument();
  expect(await screen.findByRole('button', {name: /Save/i})).not.toBeEnabled();

  // AND WHEN we populate all fields
  await userEvent.click(await screen.findByRole('radio', {name: 'Plaintext'}));
  await userEvent.type(screen.getByRole('textbox', {name: 'Secret Name'}), 'my-test-secret');
  await userEvent.type(screen.getAllByLabelText("Plaintext")[1], 'some-secret');
  await userEvent.type(screen.getByRole('textbox', {name: 'Description'}), 'my-description');

  await userEvent.click(await screen.findByRole('button', {name: /Save/i}));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      "content": "Unknown error occurred.",
      "dismissible": true,
      "header": "add secret my-test-secret",
      "type": "error"
    });
  });
});

test('submitting the edit form saves the secret to API', async () => {
  // GIVEN
  server.use(
    rest.get('/credentialmanager', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestCredentials(1))
      );
    }),
    rest.put(`/admin/credentialmanager`, async (request, response, context) => {
      return response(
        context.status(200),
      );
    }),
  );

  const {addNotification} = renderCredentialManager();
  const editButton = screen.getByRole('button', {name: "Edit"});
  expect(editButton).toBeDisabled();

  await waitForElementToBeRemoved(() => screen.queryByText(/Loading secrets/i));
  const secretRowRadioButton = screen.getByRole('radio');

  // WHEN
  await userEvent.click(secretRowRadioButton);

  // THEN
  expect(editButton).not.toBeDisabled();

  // AND WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Edit secret"})).toBeInTheDocument();
  const saveButton = await screen.findByRole('button', {name: /Save/i});
  await waitFor(() => expect(saveButton).toBeEnabled());

  // AND WHEN
  await userEvent.click(saveButton);

  // THEN
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      "content": "dhdfh secret was saved successfully.",
      "dismissible": true,
      "header": "edit secret",
      "type": "success"
    });
  })
});

test('confirming the deletion successfully deletes a secret', async () => {
  // GIVEN
  const credentials = generateTestCredentials(2);
  server.use(
    rest.get('/credentialmanager', (request, response, context) => {
      return response(
        context.status(200),
        context.json(credentials)
      );
    }),
    rest.delete(`/admin/credentialmanager`, (request, response, context) => {
      return response(
        context.status(204)
      );
    })
  );

  const {addNotification} = renderCredentialManager();
  const deleteButton = screen.getByRole('button', {name: "Delete"});
  expect(deleteButton).toBeDisabled();

  await waitForElementToBeRemoved(() => screen.queryByText(/Loading secrets/i));
  const secretRowRadioButtons = screen.getAllByRole('radio');

  // WHEN
  await userEvent.click(secretRowRadioButtons[0]);
  await userEvent.click(secretRowRadioButtons[1]);

  // THEN
  expect(await screen.findByRole('heading', {name: "Secrets (1 of 2)"})).toBeInTheDocument();
  expect(deleteButton).not.toBeDisabled();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole('dialog'));
  expect(withinModal.getByRole('heading', {name: "Delete secret"})).toBeInTheDocument();
  expect(withinModal.getByText('Are you sure you wish to delete the selected secret?')).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole('button', {name: 'Ok'}));

  // THEN
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      "content": "dhdfh secret was deleted successfully.",
      "dismissible": true,
      "header": " secret", // sic!
      "type": "success"
    });
  });
  expect(await screen.findByRole('heading', {name: "Secrets (2)"})).toBeInTheDocument();
});
