import {defaultTestProps, mockNotificationContext, TEST_SESSION_STATE} from "../__tests__/TestUtils";
import {render, screen, waitFor, waitForElementToBeRemoved, within} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {SessionContext} from "../contexts/SessionContext";
import React from "react";
import UserTableWaves from "./UserTableWaves";
import {server} from "../setupTests";
import {rest} from "msw";
import {generateTestApps, generateTestWaves} from "../__tests__/mocks/user_api";
import userEvent from "@testing-library/user-event";
import * as XLSX from "xlsx";
import {NotificationContext} from "../contexts/NotificationContext";
import {defaultSchemas} from "../../test_data/default_schema";
import {ToolsContext} from "../contexts/ToolsContext";
import AuthenticatedRoutes from "../AuthenticatedRoutes";

function renderUserWavesTable(props = defaultTestProps) {
  return {
    ...mockNotificationContext,
    renderResult: render(
      <MemoryRouter initialEntries={['/waves']}>
        <NotificationContext.Provider value={mockNotificationContext}>
          <SessionContext.Provider value={TEST_SESSION_STATE}>
            <div id='modal-root'/>
            <UserTableWaves
              {...props}
            ></UserTableWaves>
          </SessionContext.Provider>
        </NotificationContext.Provider>
      </MemoryRouter>
    )
  }
}

test('it renders an empty table with "no waves" message', async () => {
  // WHEN
  renderUserWavesTable();

  // THEN
  // page should render in loading state
  expect(screen.getByRole('heading', {name: "Waves (0)"})).toBeInTheDocument();
  expect(screen.getByText('Loading waves')).toBeInTheDocument();

  // after server response came in, it should render the table
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading waves/i));

  const table = screen.getByRole('table');
  const tbody = within(table).getAllByRole('rowgroup')[1];

  expect(await within(tbody).findByText('No waves')).toBeInTheDocument();
  expect(within(tbody).getByRole('button', {name: "Add wave"})).toBeInTheDocument();
});

test('it updates the help tools panel', async () => {
  // GIVEN
  const {renderResult} = renderUserWavesTable();

  const mockToolsContext = {
    setHelpPanelContent: jest.fn(),
    setHelpPanelContentFromSchema: jest.fn(),
    setToolsOpen: jest.fn(),
    toolsState: {
      toolsOpen: false,
      helpPanelContent: undefined
    }
  };

  // WHEN re-rendering with different props
  renderResult.rerender(
    <MemoryRouter initialEntries={['/waves']}>
      <NotificationContext.Provider value={mockNotificationContext}>
        <ToolsContext.Provider value={mockToolsContext}>
          <UserTableWaves
            {...defaultTestProps}
          ></UserTableWaves>
        </ToolsContext.Provider>
      </NotificationContext.Provider>
    </MemoryRouter>
  )

  // THEN
  expect(mockToolsContext.setHelpPanelContentFromSchema).toHaveBeenCalledWith(defaultSchemas, "wave");
});

test('it renders a paginated table with 50 waves', async () => {
  // GIVEN
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestWaves(50))
      );
    })
  );

  // WHEN
  renderUserWavesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading waves/i));

  // THEN
  expect(screen.getByRole('heading', {name: "Waves (50)"})).toBeInTheDocument();

  const table = screen.getByRole('table');
  const rows = within(table).getAllByRole('rowgroup')[1];

  // only 10 of the entries should be rendered, due to pagination
  expect(within(rows).getAllByText("foo@example.com")).toHaveLength(10);
});

test('click on refresh button refreshes the table', async () => {
  // GIVEN
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response.once(
        context.status(200),
        context.json(generateTestWaves(1))
      );
    }),
    // second request to same endpoint gives a different response
    rest.get('/user/wave', (request, response, context) => {
      return response.once(
        context.status(200),
        context.json(generateTestWaves(5))
      );
    })
  );

  renderUserWavesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading waves/i));
  expect(screen.getByRole('heading', {name: "Waves (1)"})).toBeInTheDocument();

  const refreshButton = screen.getByRole('button', {name: "Refresh"});

  // WHEN
  await userEvent.click(refreshButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Waves (5)"})).toBeInTheDocument();
});

test('click on add button opens "Add wave" form', async () => {
  // GIVEN
  renderUserWavesTable();

  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Add wave"})).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole('button', {name: /Cancel/i}));

  // THEN
  expect(await screen.findByRole('heading', {name: 'Waves (0)'})).toBeInTheDocument();
});

test('submitting the add form saves a new wave to API', async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestWaves(2))
      );
    }),
    rest.post(`/user/wave`, async (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(201),
      );
    }),
    rest.get('/user/app', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestApps(2))
      );
    }),
  );

  renderUserWavesTable();
  const addButton = screen.getByRole('button', {name: "Add"});

  // WHEN
  await userEvent.click(addButton);

  // THEN we see the Add form with a disabled save button until we enter valid values into all fields
  expect(await screen.findByRole('button', {name: /Save/i})).not.toBeEnabled();
  expect(screen.getAllByText('You must specify a valid value.')[0]).toBeInTheDocument();

  // AND WHEN we populate all fields
  await userEvent.type(screen.getByRole('textbox', {name: 'Wave Name'}), 'my-test-wave');

  await userEvent.click(screen.getByLabelText('Wave Status'));
  await userEvent.click(await screen.findByText('Not started'));

  // THEN expect no more validation errors
  expect(screen.queryByText('You must specify a valid value.')).not.toBeInTheDocument()

  // AND WHEN we hit 'save'
  await userEvent.click(await screen.findByRole('button', {name: /Save/i}));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.wave_name).toEqual('my-test-wave');
  })
  await screen.findByRole('heading', {name: 'Waves (2)'});
});

test('click on row enables "Edit" button and shows "Details" tab', async () => {
  // GIVEN
  const waves = generateTestWaves(1);
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(waves)
      );
    }),
    rest.get('/user/app', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestApps(2))
      );
    }),
  );

  const {addNotification} = renderUserWavesTable();
  const editButton = screen.getByRole('button', {name: "Edit"});
  expect(editButton).toBeDisabled();

  const waveRowCheckbox = screen.getByRole('checkbox');

  // WHEN
  await userEvent.click(waveRowCheckbox);

  // THEN
  expect(editButton).not.toBeDisabled();
  expect(screen.getByRole("heading", {name: "Details"})).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole('tab', {name: 'All attributes'}));

  // THEN
  expect(await screen.findByRole('heading', {name: "All attributes"})).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Edit wave"})).toBeInTheDocument();
  const saveButton = await screen.findByRole('button', {name: /Save/i});
  expect(saveButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(saveButton);

  // THEN
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      "content": "No updates to save.",
      "dismissible": true,
      "header": "Save wave",
      "type": "warning"
    });
  })
});

test('submitting the edit form saves the wave to API', async () => {
  // GIVEN
  let captureRequest: any;
  const waves = generateTestWaves(1);
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(waves)
      );
    }),
    rest.put(`/user/wave/${waves[0].wave_id}`, async (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(200),
      );
    }),
  );

  renderUserWavesTable();
  const editButton = screen.getByRole('button', {name: "Edit"});
  const waveRowCheckbox = screen.getByRole('checkbox');

  await userEvent.click(waveRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Edit wave"})).toBeInTheDocument();
  const saveButton = await screen.findByRole('button', {name: /Save/i});
  expect(saveButton).toBeEnabled();

  // AND WHEN we edit some data and hit 'save'
  const waveNameInput = screen.getByRole('textbox', {name: 'Wave Name'});
  await userEvent.type(waveNameInput, '-some-name');
  await userEvent.click(await screen.findByRole('button', {name: /Save/i}));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.wave_name).toEqual('Unit testing Wave 0-some-name');
  })
  await screen.findByRole('heading', {name: 'Waves (1)'});
});

test('when update fails with server error, display notification', async () => {
  // GIVEN
  let captureRequest: any;
  const waves = generateTestWaves(1);
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(waves)
      );
    }),
    rest.put(`/user/wave/${waves[0].wave_id}`, async (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(502),
      );
    }),
    rest.get('/user/app', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestApps(2))
      );
    }),
  );

  const {addNotification} = renderUserWavesTable();
  const editButton = screen.getByRole('button', {name: "Edit"});
  const waveRowCheckbox = screen.getByRole('checkbox');

  await userEvent.click(waveRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Edit wave"})).toBeInTheDocument();
  const saveButton = await screen.findByRole('button', {name: /Save/i});

  // AND WHEN we edit some data and hit 'save'
  const waveNameInput = screen.getByRole('textbox', {name: 'Wave Name'});
  await userEvent.type(waveNameInput, '-some-name');
  await userEvent.click(await screen.findByRole('button', {name: /Save/i}));

  // THEN verify the failure message
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      "content": "Unknown error occurred.",
      "dismissible": true,
      "header": "Edit wave",
      "type": "error"
    });
  });
});

test('when update fails with 200 success response, parse error', async () => {
  // GIVEN
  let captureRequest: any;
  const waves = generateTestWaves(1);
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(waves)
      );
    }),
    rest.put(`/user/wave/${waves[0].wave_id}`, async (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(200),
        context.json({
          errors: { // TODO get a real example of the error payload
            validation_errors: [
              {
                'prop1': ['message'],
              }
            ],
            existing_name: ['prop2'],
            unprocessed_items: {
              baz: {error_detail: 'baz'}
            }
          }
        })
      );
    }),
    rest.get('/user/app', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestApps(2))
      );
    }),
  );

  const {addNotification} = renderUserWavesTable();
  const editButton = screen.getByRole('button', {name: "Edit"});
  const waveRowCheckbox = screen.getByRole('checkbox');

  await userEvent.click(waveRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole('heading', {name: "Edit wave"})).toBeInTheDocument();
  const saveButton = await screen.findByRole('button', {name: /Save/i});

  // AND WHEN we edit some data and hit 'save'
  const waveNameInput = screen.getByRole('textbox', {name: 'Wave Name'});
  await userEvent.type(waveNameInput, '-some-name');
  await userEvent.click(saveButton);

  // THEN verify the failure message
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      "content": "prop1 : message" + "," + "prop2 already exists.",
      "dismissible": true,
      "header": "Update wave",
      "type": "error"
    });
  });
});

test('click on row enables "Delete" button, shows "Delete" modal', async () => {
  // GIVEN
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestWaves(1))
      );
    })
  );

  renderUserWavesTable();
  const deleteButton = screen.getByRole('button', {name: "Delete"});
  expect(deleteButton).toBeDisabled();

  const waveRowCheckbox = screen.getByRole('checkbox');

  // WHEN
  await userEvent.click(waveRowCheckbox);

  // THEN
  expect(await screen.findByRole('heading', {name: "Waves (1 of 1)"})).toBeInTheDocument();
  expect(deleteButton).not.toBeDisabled();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const deleteModal = await screen.findByRole('dialog', {name: "Delete waves"});
  expect(within(deleteModal).getByText('Are you sure you wish to delete the 1 selected waves?')).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(within(deleteModal).getByRole('button', {name: /Cancel/i}));

  // THEN
  expect(await screen.findByRole('heading', {name: "Waves (1 of 1)"})).toBeInTheDocument();
});

test('confirming the deletion successfully deletes a wave', async () => {
  // GIVEN
  const waves = generateTestWaves(1);
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response.once(
        context.status(200),
        context.json(waves)
      );
    }),
    rest.delete(`/user/wave/:id`, (request, response, context) => {
      return response(
        context.status(204)
      );
    })
  );

  const {addNotification} = renderUserWavesTable();
  const deleteButton = screen.getByRole('button', {name: "Delete"});
  expect(deleteButton).toBeDisabled();

  const waveRowCheckbox = screen.getByRole('checkbox');

  // WHEN
  await userEvent.click(waveRowCheckbox);
  await userEvent.click(deleteButton);
  await userEvent.click(screen.getByRole('button', {name: 'Ok'}));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    "content": "Unit testing Wave 0 was deleted.",
    "dismissible": true,
    "header": "Wave deleted successfully",
    "type": "success"
  });
  expect(await screen.findByRole('heading', {name: "Waves (0)"})).toBeInTheDocument();
});

test('delete multiple waves', async () => {
  // GIVEN
  const waves = generateTestWaves(2);
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response.once(
        context.status(200),
        context.json(waves)
      );
    }),
    rest.delete(`/user/wave/:id`, (request, response, context) => {
      return response(
        context.status(204)
      );
    })
  );

  const {addNotification} = renderUserWavesTable();
  const deleteButton = screen.getByRole('button', {name: "Delete"});
  expect(deleteButton).toBeDisabled();
  await userEvent.click(deleteButton);

  const waveRowCheckBoxes = screen.getAllByRole('checkbox');

  // WHEN
  await userEvent.click(waveRowCheckBoxes[0]);

  // THEN
  expect(await screen.findByRole('heading', {name: 'Waves (2 of 2)'})).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole('dialog'));
  expect(await withinModal.findByText('Are you sure you wish to delete the 2 selected waves?')).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole('button', {name: 'Ok'}));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    "dismissible": false,
    "header": "Deleting selected waves...",
    loading: true,
    "type": "success"
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      "id": undefined,
      "content": "Unit testing Wave 0, Unit testing Wave 1 were deleted.",
      "dismissible": true,
      "header": "Waves deleted successfully",
      "type": "success"
    });
  });
});

test('click on export downloads an xlsx file', async () => {
  // GIVEN
  jest.spyOn(XLSX, 'writeFile').mockImplementation(() => {
  });
  jest.spyOn(XLSX.utils, 'json_to_sheet');

  const testWaves = generateTestWaves(2);
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(testWaves)
      );
    })
  );
  renderUserWavesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading waves/i));

  const exportButton = screen.getByRole('button', {name: "Download"});

  // WHEN
  await userEvent.click(exportButton);

  // THEN
  expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(1);
  expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
});

test('selecting a row and click on export downloads an xlsx file', async () => {
  // GIVEN
  jest.spyOn(XLSX, 'writeFile').mockImplementation(() => {
  });
  jest.spyOn(XLSX.utils, 'json_to_sheet');

  const testWaves = generateTestWaves(2);
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(testWaves)
      );
    })
  );
  renderUserWavesTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading waves/i));

  await userEvent.click(screen.getAllByRole('row')[1]);
  const exportButton = screen.getByRole('button', {name: "Download"});

  // WHEN
  await userEvent.click(exportButton);

  // THEN
  expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(1);
  expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
});

test('buttons are disabled based on user permissions', async () => {
  // GIVEN
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(generateTestWaves(2))
      );
    })
  );

  renderUserWavesTable({
    ...defaultTestProps,
    userEntityAccess: {
      ...defaultTestProps.userEntityAccess,
      wave: {
        delete: false,
        create: false,
        update: false,
        read: true,
        attributes: []
      },
    }
  });

  // WHEN
  await userEvent.click(screen.getByRole('checkbox'));

  // THEN
  expect(screen.getByRole('button', {name: "Add"})).toBeDisabled();
  expect(screen.getByRole('button', {name: "Edit"})).toBeDisabled();
  expect(screen.getByRole('button', {name: "Delete"})).toBeDisabled();
});


test('Run Automation', async () => {
  // GIVEN
  const waves = generateTestWaves(1);
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(waves)
      );
    }),
  );

  renderUserWavesTable();
  const actionsButton = screen.getByRole('button', {name: "Actions"});
  expect(actionsButton).toBeDisabled();

  const waveRowCheckbox = screen.getByRole('checkbox');

  // WHEN
  await userEvent.click(waveRowCheckbox);

  // THEN
  expect(actionsButton).not.toBeDisabled();

  // AND WHEN
  await userEvent.click(actionsButton);
  await userEvent.click(await screen.findByRole('menuitem', {name: "Run Automation"}));

  // THEN
  expect(await screen.findByRole('heading', {name: "Run Automation"})).toBeInTheDocument();

  // TODO fill out the form and submit - what entity data do we need to add to the schema in order to have values for the dropwdowns?
});

test('MGN server migration', async () => {
  // GIVEN
  let captureRequest: any;
  const waves = generateTestWaves(1);
  const applications = generateTestApps(2, {waveId: waves[0].wave_id});
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(waves)
      );
    }),
    rest.get('/user/app', (request, response, context) => {
      return response(
        context.status(200),
        context.json(applications)
      );
    }),
    rest.post('/mgn', (request, response, context) => {
      request.json().then(body => captureRequest = body);
      return response(
        context.status(201)
      );
    }),
  );

  renderUserWavesTable();
  const actionsButton = screen.getByRole('button', {name: "Actions"});

  // WHEN selecting a wave and navigating through the action menu
  await userEvent.click(screen.getByRole('checkbox'));
  await userEvent.click(actionsButton);
  await userEvent.click(await screen.findByRole('menuitem', {name: "Rehost"}));
  await userEvent.click(await screen.findByRole('menuitem', {name: "MGN"}));

  // THEN MGN server migration form should open with wave preselected
  expect(await screen.findByRole('heading', {name: "MGN server migration"})).toBeInTheDocument();
  expect(await screen.findByRole('button', {name: /wave unit testing wave 0/i})).toBeInTheDocument()

  // WHEN
  await userEvent.click(screen.getByLabelText('Action'));
  await userEvent.click(await screen.findByText('Validate Launch Template'));

  await userEvent.click(screen.getByLabelText('Applications'));
  await userEvent.click(await screen.findByText(applications[0].app_name));

  // THEN
  const submitBtn = await screen.findByRole('button', {name: "Submit"});
  expect(submitBtn).toBeEnabled();

  // WHEN
  await userEvent.click(submitBtn);

  // THEN
  await waitFor(() => {
    expect(captureRequest.action).toEqual('Validate Launch Template');
  })
});


test('it deep links to Add form', async () => {
  // GIVEN
  const addWaveRoute = '/waves/add';

  // WHEN
  render(
    <MemoryRouter initialEntries={[addWaveRoute]}>
      <NotificationContext.Provider value={mockNotificationContext}>
        <SessionContext.Provider value={TEST_SESSION_STATE}>
          <div id='modal-root'/>
          <AuthenticatedRoutes
            childProps={defaultTestProps}
          ></AuthenticatedRoutes>
        </SessionContext.Provider>
      </NotificationContext.Provider>
    </MemoryRouter>
  )

  // THEN
  expect(await screen.findByRole('heading', {name: "Add wave"})).toBeInTheDocument();
});

test('it deep links to Edit form', async () => {
  // GIVEN
  const waves = generateTestWaves(1);
  server.use(
    rest.get('/user/wave', (request, response, context) => {
      return response(
        context.status(200),
        context.json(waves)
      );
    }),
  );

  const editWaveRoute = `/waves/edit/${waves[0].wave_id}`;

  // WHEN
  render(
    <MemoryRouter initialEntries={[editWaveRoute]}>
      <NotificationContext.Provider value={mockNotificationContext}>
        <SessionContext.Provider value={TEST_SESSION_STATE}>
          <div id='modal-root'/>
          <AuthenticatedRoutes
            childProps={defaultTestProps}
          ></AuthenticatedRoutes>
        </SessionContext.Provider>
      </NotificationContext.Provider>
    </MemoryRouter>
  )

  // THEN
  expect(await screen.findByRole('heading', {name: "Edit wave"})).toBeInTheDocument();
});