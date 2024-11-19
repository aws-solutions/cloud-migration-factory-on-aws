import { render, screen, waitFor, waitForElementToBeRemoved, within } from "@testing-library/react";
import * as XLSX from "xlsx";
import UserPipelineTemplateTable from "./UserTablePipelineTemplates"
import { MemoryRouter } from "react-router-dom";
import { defaultTestProps, mockNotificationContext, TEST_SESSION_STATE } from "../__tests__/TestUtils";
import { SessionContext } from "../contexts/SessionContext";
import { rest } from "msw";
import { server } from "../setupTests";
import {
  generateSystemOwnedTestPipelineTemplates,
  generateTestApps,
  generateTestPipelineTemplates,
  generateTestPostPipelineTemplatesResponse,
  generateTestDeleteProtectedPipelineTemplates
} from "../__tests__/mocks/user_api";
import userEvent from "@testing-library/user-event";
import React from "react";
import { NotificationContext } from "../contexts/NotificationContext";

function renderUserPipelineTemplateTable(props = defaultTestProps) {
  return {
    ...mockNotificationContext,
    renderResult: render(
        <MemoryRouter initialEntries={["/pipeline_templates"]}>
          <NotificationContext.Provider value={mockNotificationContext}>
            <SessionContext.Provider value={TEST_SESSION_STATE}>
              <div id="modal-root" />
              <UserPipelineTemplateTable {...props}></UserPipelineTemplateTable>
            </SessionContext.Provider>
          </NotificationContext.Provider>
        </MemoryRouter>
    ),
  };
}

async function click_duplicate_button() {
  const actionsButton = screen.getByRole("button", { name: "Actions" });
  //const actionsButton = screen.getByText(/Actions/i);
  await userEvent.click(actionsButton);
  const duplicateButton = screen.getByRole("menuitem", { name: "Duplicate" });
  await userEvent.click(duplicateButton);
}

test('it renders an empty table with "no pipeline_templates" message', async () => {
  // WHEN
  renderUserPipelineTemplateTable();

  // THEN
  // page should render in loading state
  expect(screen.getByRole("heading", { name: "Pipeline Templates (0)" })).toBeInTheDocument();
  expect(screen.getByText("Loading pipeline_templates")).toBeInTheDocument();

  // after pipeline_template response came in, it should render the table
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipeline_templates/i));

  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];

  expect(await within(tbody).findByText("No pipeline_templates")).toBeInTheDocument();
  expect(within(tbody).getByRole("button", { name: "Add pipeline_template" })).toBeInTheDocument();
});

test("it renders a paginated table with 50 pipeline_templates", async () => {
  // GIVEN
  server.use(
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response(context.status(200), context.json(generateTestPipelineTemplates(50)));
      })
  );

  // WHEN
  renderUserPipelineTemplateTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipeline_templates/i));

  // THEN
  expect(screen.getByRole("heading", { name: "Pipeline Templates (50)" })).toBeInTheDocument();

  const table = screen.getByRole("table");
  const rows = within(table).getAllByRole("rowgroup")[1];

  // only 10 of the entries should be rendered, due to pagination
  const nameElements = within(rows).getAllByText(/unittest_pipeline_template(\d+)/);
  expect(nameElements).toHaveLength(20);
  expect(nameElements[0]).toHaveTextContent('unittest_pipeline_template0');
});

test("click on refresh button refreshes the table", async () => {
  // GIVEN
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestPipelineTemplates(1)));
    }),
    // second request to same endpoint gives a different response
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestPipelineTemplates(5)));
    })
  );

  renderUserPipelineTemplateTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipeline_templates/i));
  expect(screen.getByRole("heading", { name: "Pipeline Templates (1)" })).toBeInTheDocument();

  const refreshButton = screen.getByRole("button", { name: "Refresh" });

  // WHEN
  await userEvent.click(refreshButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipeline Templates (5)" })).toBeInTheDocument();
});

test('click on add button opens "Add pipeline Template" form', async () => {
  // GIVEN
  renderUserPipelineTemplateTable();

  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Add pipeline Template" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipeline Templates (0)" })).toBeInTheDocument();
});

test("submitting the Add form saves a new pipeline_template to API", async () => {
  // GIVEN
  let captureRequest: any;
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(generateTestPipelineTemplates(0)));
    }),
    rest.post(`/user/pipeline_template`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(201));
    }),
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(1)));
    })
  );

  const { addNotification } = renderUserPipelineTemplateTable();
  const addButton = screen.getByRole("button", { name: "Add" });

  // WHEN
  await userEvent.click(addButton);

  // THEN we see the Add form with a disabled save button until we enter valid values into all fields
  expect(await screen.findByRole("button", { name: /Save/i })).not.toBeEnabled();
  expect(screen.getAllByText("You must specify a valid value.")[0]).toBeInTheDocument();

  // AND WHEN we populate all fields
  const ptName = "My test pipeline name"
  const ptDescription = "My test pipeline description"
  await userEvent.type(screen.getByRole("textbox", { name: "pipeline_template_name" }), ptName);
  await userEvent.type(screen.getByRole("textbox", { name: "pipeline_template_description" }), ptDescription);

  // THEN expect no more validation errors
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  await waitFor(() => expect(saveButton).toBeEnabled());
  expect(screen.queryByText("You must specify a valid value.")).not.toBeInTheDocument();

  // AND WHEN we hit 'save'
  await userEvent.click(saveButton);

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.pipeline_template_name).toEqual("My test pipeline name");
  });

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: `${ptName} was Added successfully`,
      dismissible: true,
      header: "Add pipeline_template",
      type: "success",
    });
  });
});

test('click on row enables "Edit" button and shows "Details" tab', async () => {
  // GIVEN
  const pipeline_templates = generateTestPipelineTemplates(1);
  server.use(
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response(context.status(200), context.json(pipeline_templates));
      }),
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response(context.status(200), context.json(generateTestPipelineTemplates(1)));
      })
  );

  const { addNotification } = renderUserPipelineTemplateTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  expect(editButton).toBeDisabled();

  const pipeline_templateRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(pipeline_templateRowCheckbox);

  // THEN
  expect(editButton).not.toBeDisabled();
  expect(screen.getByRole("heading", { name: "Details" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Pipeline Template Tasks" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipeline Template Tasks (0)" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Visual Task Editor" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "unittest_pipeline_template0" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("tab", { name: "All attributes" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "All attributes" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit pipeline Template" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  expect(saveButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(saveButton);

  // THEN
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "No updates to save.",
      dismissible: true,
      header: "Edit pipeline_template",
      type: "warning",
    });
  });
});

test("system owned pipeline_template cannot be edited", async () => {
  // GIVEN
  let captureRequest: any;
  const pipeline_templates = generateSystemOwnedTestPipelineTemplates(1);
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(pipeline_templates));
    })
  );

  const { addNotification } = renderUserPipelineTemplateTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const pipeline_templateRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(pipeline_templateRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit pipeline Template" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  expect(saveButton).toBeEnabled();

  // AND WHEN we edit some data and hit 'save'
  const pipelineTemplateNameInput = screen.getByRole("textbox", { name: "pipeline_template_name" });
  await userEvent.type(pipelineTemplateNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "Protection is configured for this item.",
      dismissible: true,
      header: "Edit pipeline_template",
      type: "warning",
    });
  });
});

test("delete protected pipeline_template cannot be deleted", async () => {
  // GIVEN
  let captureRequest: any;
  const pipeline_templates = generateTestDeleteProtectedPipelineTemplates(1);
  server.use(
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response(context.status(200), context.json(pipeline_templates));
      })
  );

  // WHEN
  const { addNotification } = renderUserPipelineTemplateTable();

  //THEN
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  // WHEN
  const pipelineTemplateRowCheckbox = screen.getByRole("checkbox");
  await userEvent.click(pipelineTemplateRowCheckbox);
  await userEvent.click(deleteButton);
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipeline Templates (1 of 1)" })).toBeInTheDocument();
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "Deletion protection is enabled on this item.",
      dismissible: true,
      header: "Delete pipeline_template",
      type: "warning",
    });
  });
});

test("only one pipeline_template can be edited at a time", async () => {
  // GIVEN
  let captureRequest: any;
  const pipeline_templates = generateTestPipelineTemplates(2);
  server.use(
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response(context.status(200), context.json(pipeline_templates));
      })
  );

  // WHEN
  renderUserPipelineTemplateTable();
  const editButton = screen.getByRole("button", { name: "Edit" });

  // THEN
  expect(editButton).toBeDisabled();

  // WHEN Click the first checkbox
// WHEN
  const pipeline_templateRowCheckboxes = screen.getAllByRole('checkbox');
  await userEvent.click(pipeline_templateRowCheckboxes[0]);
  await userEvent.click(pipeline_templateRowCheckboxes[1]);

  // THEN expect the edit button be disabled
  expect(editButton).toBeDisabled();
});

test("system owned pipeline_template cannot be deleted", async () => {
  // GIVEN
  let captureRequest: any;
  const pipeline_templates = generateSystemOwnedTestPipelineTemplates(1);
  server.use(
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response(context.status(200), context.json(pipeline_templates));
      })
  );

  // WHEN
  const { addNotification } = renderUserPipelineTemplateTable();

  //THEN
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  // WHEN
  const pipelineTemplateRowCheckbox = screen.getByRole("checkbox");
  await userEvent.click(pipelineTemplateRowCheckbox);
  await userEvent.click(deleteButton);
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipeline Templates (1 of 1)" })).toBeInTheDocument();
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "Deletion protection is enabled on this item.",
      dismissible: true,
      header: "Delete pipeline_template",
      type: "warning",
    });
  });
});

test("submitting the edit form saves the pipeline_template to API", async () => {
  // GIVEN
  let captureRequest: any;
  const pipeline_templates = generateTestPipelineTemplates(1);
  server.use(
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response(context.status(200), context.json(pipeline_templates));
      }),
      rest.put(`/user/pipeline_template/${pipeline_templates[0].pipeline_template_id}`, async (request, response, context) => {
        request.json().then((body) => (captureRequest = body));
        return response(context.status(200));
      }),
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response(context.status(200), context.json(generateTestPipelineTemplates(1)));
      })
  );

  renderUserPipelineTemplateTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const pipeline_templateRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(pipeline_templateRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit pipeline Template" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  expect(saveButton).toBeEnabled();

  // AND WHEN we edit some data and hit 'save'
  const pipelineTemplateNameInput = screen.getByRole("textbox", { name: "pipeline_template_name" });
  await userEvent.type(pipelineTemplateNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest.pipeline_template_name).toEqual("unittest_pipeline_template0-some-name");
  });

  expect(await screen.findByRole("heading", { name: "Pipeline Templates (1)" })).toBeInTheDocument();
});

test("when update fails with pipeline_template error, display notification", async () => {
  // GIVEN
  let captureRequest: any;
  const pipeline_templates = generateTestPipelineTemplates(1);
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(pipeline_templates));
    }),
    rest.put(`/user/pipeline_template/${pipeline_templates[0].pipeline_template_id}`, async (request, response, context) => {
      request.json().then((body) => (captureRequest = body));
      return response(context.status(502));
    }),
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(generateTestPipelineTemplates(2)));
    })
  );

  const { addNotification } = renderUserPipelineTemplateTable();
  const editButton = screen.getByRole("button", { name: "Edit" });
  const pipelineTemplateRowCheckbox = screen.getByRole("checkbox");

  await userEvent.click(pipelineTemplateRowCheckbox);

  // WHEN
  await userEvent.click(editButton);

  // THEN
  expect(await screen.findByRole("heading", { name: "Edit pipeline Template" })).toBeInTheDocument();
  await screen.findByRole("button", { name: /Save/i });

  // AND WHEN we edit some data and hit 'save'
  const pipelineTemplateNameInput = screen.getByRole("textbox", { name: "pipeline_template_name" });
  await userEvent.type(pipelineTemplateNameInput, "-some-name");
  await userEvent.click(await screen.findByRole("button", { name: /Save/i }));

  // THEN verify the failure message
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "Unknown error occurred.",
      dismissible: true,
      header: "Edit pipeline_template",
      type: "error",
    });
  });
});

test('click on row enables "Delete" button, shows "Delete" modal', async () => {
  // GIVEN
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(generateTestPipelineTemplates(1)));
    })
  );

  renderUserPipelineTemplateTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const pipelineTemplateRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(pipelineTemplateRowCheckbox);

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipeline Templates (1 of 1)" })).toBeInTheDocument();
  expect(deleteButton).not.toBeDisabled();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(withinModal.getByRole("heading", { name: "Delete pipeline_templates" })).toBeInTheDocument();
  expect(withinModal.getByText("Are you sure you wish to delete the 1 selected pipeline templates?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(withinModal.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipeline Templates (1 of 1)" })).toBeInTheDocument();
});

test("confirming the deletion successfully deletes a pipeline_template", async () => {
  // GIVEN
  const pipeline_templates = generateTestPipelineTemplates(1);
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response.once(context.status(200), context.json(pipeline_templates));
    }),
    rest.delete(`/user/pipeline_template/:id`, (request, response, context) => {
      return response(context.status(204));
    })
  );

  const { addNotification } = renderUserPipelineTemplateTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();

  const pipelineTemplateRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(pipelineTemplateRowCheckbox);
  await userEvent.click(deleteButton);
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    content: "unittest_pipeline_template0 was deleted.",
    dismissible: true,
    header: "Pipeline template deleted successfully",
    type: "success",
  });
});

test("delete multiple pipeline_templates", async () => {
  // GIVEN
  const pipeline_templates = generateTestPipelineTemplates(2);
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response.once(context.status(200), context.json(pipeline_templates));
    }),
    rest.delete(`/user/pipeline_template/:id`, (request, response, context) => {
      return response(context.status(204));
    })
  );

  const { addNotification } = renderUserPipelineTemplateTable();
  const deleteButton = screen.getByRole("button", { name: "Delete" });
  expect(deleteButton).toBeDisabled();
  await userEvent.click(deleteButton);

  const pipelineTemplateRowCheckBoxes = screen.getAllByRole("checkbox");

  // WHEN
  await userEvent.click(pipelineTemplateRowCheckBoxes[0]);

  // THEN
  expect(await screen.findByRole("heading", { name: "Pipeline Templates (2 of 2)" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(deleteButton);

  // THEN
  const withinModal = within(await screen.findByRole("dialog"));
  expect(await withinModal.findByText("Are you sure you wish to delete the 2 selected pipeline templates?")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "Ok" }));

  // THEN
  expect(addNotification).toHaveBeenCalledWith({
    dismissible: false,
    header: "Deleting selected pipeline_templates...",
    loading: true,
    type: "success",
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: undefined,
      content: "unittest_pipeline_template0, unittest_pipeline_template1 were deleted.",
      dismissible: true,
      header: "Pipeline templates deleted successfully",
      type: "success",
    });
  });
});

test("click on export downloads an xlsx file", async () => {
  // GIVEN
  jest.spyOn(XLSX, "writeFile").mockImplementation(() => {});
  jest.spyOn(XLSX.utils, "json_to_sheet");

  const testPipelineTemplates = generateTestPipelineTemplates(2);
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(testPipelineTemplates));
    })
  );
  renderUserPipelineTemplateTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipeline_templates/i));

  const exportButton = screen.getByRole("button", { name: "Download" });

  // WHEN
  await userEvent.click(exportButton);

  // THEN
  expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(1);
  expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
});

test("selecting a row and click on export downloads an xlsx file", async () => {
  // GIVEN
  jest.spyOn(XLSX, "writeFile").mockImplementation(() => {});
  jest.spyOn(XLSX.utils, "json_to_sheet");

  const testPipelineTemplates = generateTestPipelineTemplates(2);
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(testPipelineTemplates));
    })
  );
  renderUserPipelineTemplateTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipeline_templates/i));

  await userEvent.click(screen.getAllByRole("row")[1]);
  const exportButton = screen.getByRole("button", { name: "Download" });

  // WHEN
  await userEvent.click(exportButton);

  // THEN
  expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(1);
  expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
});

test("buttons are enabled based on user permissions", async () => {
  // GIVEN
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(generateTestPipelineTemplates(2)));
    })
  );

  renderUserPipelineTemplateTable({
    ...defaultTestProps,
    userEntityAccess: {
      ...defaultTestProps.userEntityAccess,
      pipeline_template: {
        delete: true,
        create: true,
        update: true,
        read: true,
        attributes: [],
      },
    },
  });

  // WHEN
  await userEvent.click(screen.getByRole("checkbox"));

  // THEN
  expect(screen.getByRole("button", { name: "Actions" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Add" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Delete" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Edit" })).toBeDisabled();
});

test("submitting the Duplicate form saves a copy of an existing pipeline_template to API", async () => {
  // GIVEN
  let captureRequest: any;
  const pipeline_templates = generateTestPipelineTemplates(1);
  server.use(
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response(context.status(200), context.json(pipeline_templates));
      }),
      rest.post(`/user/pipeline_template`, async (request, response, context) => {
        request.json().then((body) => (captureRequest = body));
        return response(context.status(201), context.json(generateTestPostPipelineTemplatesResponse(2)));
      }),
      rest.get("/user/pipeline_template", (request, response, context) => {
        return response(context.status(200), context.json(generateTestPipelineTemplates(2)));
      }),
      rest.get("pipelines/templates", (request, response, context) => {
        return response(context.status(200), context.json(pipeline_templates));
      }),
      rest.post(`/pipelines/templates`, async (request, response, context) => {
        request.json().then((body) => (captureRequest = body));
        return response(context.status(201));
      }),
  );

  const { addNotification } = renderUserPipelineTemplateTable();
  const pipeline_templateRowCheckbox = screen.getByRole("checkbox");

  // WHEN
  await userEvent.click(pipeline_templateRowCheckbox);
  await click_duplicate_button();

  // THEN
  expect(await screen.findByRole("heading", { name: "Duplicate pipeline Template" })).toBeInTheDocument();
  const saveButton = await screen.findByRole("button", { name: /Save/i });
  expect(saveButton).toBeEnabled();

  // AND WHEN we edit some data and hit 'save'
  const ptName = pipeline_templates[0].pipeline_template_name;
  const pipelineTemplateNameInput = screen.getByRole("textbox", { name: "pipeline_template_name" });
  await userEvent.type(pipelineTemplateNameInput, "-duplicate1");
  await userEvent.click(saveButton);

  // THEN verify the in-progress notification
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledTimes(2)
  });

  await waitFor(() => {
    expect(addNotification).toHaveBeenNthCalledWith(1, {
      content: `Duplicating Pipeline Template: ${pipeline_templates[0].pipeline_template_name}`,
      dismissible: true,
      header: "Pipeline Template duplication",
      type: "in-progress",
    });
  });

  // THEN verify the API has received the expected update request
  await waitFor(() => {
    expect(captureRequest).toBeTruthy();
  });

  // THEN verify the success notification

  await waitFor(() => {
    expect(addNotification).toHaveBeenNthCalledWith(2, {
      content: `Duplicated Pipeline Template: ${ptName + "-duplicate1"}`,
      dismissible: true,
      header: "Pipeline Template duplication",
      type: "success",
    });
  });

  // WHEN
  await userEvent.click(screen.getByRole("button", { name: "Refresh" }));

  // THEN verify table with the duplicate pipeline_template
  expect(await screen.findByRole("heading", { name: "Pipeline Templates (1)" })).toBeInTheDocument();
});

test("selecting a row and click on visual task editor tab", async () => {
  // GIVEN
  jest.spyOn(XLSX, "writeFile").mockImplementation(() => {});
  jest.spyOn(XLSX.utils, "json_to_sheet");

  const testPipelineTemplates = generateTestPipelineTemplates(2);
  server.use(
    rest.get("/user/pipeline_template", (request, response, context) => {
      return response(context.status(200), context.json(testPipelineTemplates));
    })
  );
  renderUserPipelineTemplateTable();
  await waitForElementToBeRemoved(() => screen.queryByText(/Loading pipeline_templates/i));

  // WHEN
  await userEvent.click(screen.getAllByRole("row")[1]);

  // THEN
  expect(screen.getByRole("heading", { name: "Details" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("tab", { name: "Visual Task Editor" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "unittest_pipeline_template0" })).toBeInTheDocument();

});
