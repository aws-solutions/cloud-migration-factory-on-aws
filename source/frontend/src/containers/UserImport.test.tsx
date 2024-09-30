/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import React from "react";

import { defaultTestProps, mockNotificationContext, TEST_SESSION_STATE } from "../__tests__/TestUtils";
import { MemoryRouter } from "react-router-dom";
import { SessionContext } from "../contexts/SessionContext";
import { NotificationContext } from "../contexts/NotificationContext";
import { server } from "../setupTests";
import { rest } from "msw";
import userEvent from "@testing-library/user-event";
import {
  generateTestApps,
  generateTestDatabases,
  generateTestServers,
  generateTestWaves,
} from "../__tests__/mocks/user_api";
import UserImport from "./UserImport";
import * as XLSX from "xlsx";
import { generateTestCredentials } from "../__tests__/mocks/credentialmanager_api";
import { ExpandableSection, ProgressBar } from "@cloudscape-design/components";
import { CmfAddNotification } from "../models/AppChildProps";
import { v4 } from "uuid";
import { defaultSchemas } from "../../test_data/default_schema.ts";

// count the schemas of type 'user' in defaultSchemas.
// we don't want to hard code the number, so that the tests don't break when a new schema is added
const TOTAL_NUMBER_OF_ENTITY_TYPES = Object.values(defaultSchemas).filter((it) => it.schema_type === "user").length;

/*
The following tests test for valid input
import scenarios
                server wave app
scenario1       Create Create Create
scenario2       NoUpdate NoUpdate NoUpdate
scenario3       Update Update Update
 */
const renderUserImportComponent = (props = defaultTestProps) => {
  return {
    ...mockNotificationContext,
    container: render(
      <MemoryRouter initialEntries={["/import"]}>
        <NotificationContext.Provider value={mockNotificationContext}>
          <SessionContext.Provider value={TEST_SESSION_STATE}>
            <UserImport {...props} />
            <div id="modal-root" />
          </SessionContext.Provider>
        </NotificationContext.Provider>
      </MemoryRouter>
    ),
  };
};

async function assert_empty_import_page() {
  expect(screen.getByText("Intake forms should be in CSV/UTF8 or Excel/xlsx format.")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Select file to commit" })).toBeVisible();
  expect(screen.getByText("No file selected")).toBeVisible();
}

test("it should show the import page", async () => {
  renderUserImportComponent();
  await assert_empty_import_page();
  //TODO: remove the cancel button, disable the next button before file is selected
});

test("it should allow download the intake forms from the import page", async () => {
  renderUserImportComponent();

  const buttonActions = screen.getByRole("button", { name: "Actions" });
  await userEvent.click(buttonActions);
  const buttonTemplate = screen.getByRole("menuitem", { name: "Template with only required attributes" });
  await userEvent.click(buttonTemplate);

  expect(XLSX.writeFile).toHaveBeenCalledWith(
    expect.objectContaining({ SheetNames: ["mf_intake"] }),
    "cmf-intake-form-req.xlsx"
  );

  await userEvent.click(buttonActions);
  const buttonTemplateAll = screen.getByRole("menuitem", { name: "Template with all attributes" });
  await userEvent.click(buttonTemplateAll);

  expect(XLSX.writeFile).toHaveBeenLastCalledWith(
    expect.objectContaining({ SheetNames: ["mf_intake"] }),
    "cmf-intake-form-all.xlsx"
  );
});

function setup_all_get_handlers() {
  server.use(
    rest.get("/user/wave", (request, response, context) => {
      return response(context.status(200), context.json(generateTestWaves(5)));
    }),
    rest.get("/user/server", (request, response, context) => {
      return response(context.status(200), context.json(generateTestServers(5)));
    }),
    rest.get("/user/app", (request, response, context) => {
      return response(context.status(200), context.json(generateTestApps(5)));
    }),
    rest.get("/user/database", (request, response, context) => {
      return response(context.status(200), context.json(generateTestDatabases(5)));
    }),
    rest.get("/credentialmanager", (request, response, context) => {
      return response(context.status(200), context.json(generateTestCredentials(1)));
    })
  );
}

async function assert_upload_file_selected(fileName: string) {
  expect(
    screen.getByText((_: string, node: Element | null) => {
      // eslint-disable-next-line testing-library/no-node-access
      if (node && node.textContent === "Filename: " && node.nextSibling && node.nextSibling.textContent === fileName) {
        return true;
      }
      return false;
    })
  ).toBeInTheDocument();
}

async function select_upload_file_click_next(fileContents: any, fileName: string, fileType: string) {
  const file = new File([fileContents], fileName, { type: fileType });
  // const uploadFileButton = screen.getByRole("button", {name: "Select file"}); // this is the visible button, but
  // the actual input button to upload is hidden
  //no role selector for input type="file"
  // eslint-disable-next-line testing-library/no-node-access
  const uploadInput = document.querySelector("input[type='file']") as HTMLInputElement;
  await userEvent.upload(uploadInput, file);

  await assert_upload_file_selected(fileName);

  const nextButton = screen.getByRole("button", { name: "Next" });
  expect(nextButton).toBeEnabled();
  await userEvent.click(nextButton);
  await screen.findByText("Previous");
}

async function select_valid_file_upload_scenario1() {
  // server wave app
  // Create Create Create
  const validFileContents =
    "server_name,server_os_family,server_os_version,server_fqdn,r_type,app_name,aws_accountid,aws_region,wave_name\n" +
    "unittest1-NEW,linux,redhat,unittest1.testdomain.local,Rehost,Unit testing App 1-NEW,123456789012,us-east-2,Unit testing Wave 1-NEW";
  await select_upload_file_click_next(validFileContents, "valid.csv", "text/csv");
}

async function select_valid_file_upload_scenario2() {
  // server wave app
  // NoUpdate NoUpdate NoUpdate
  const validFileContents =
    "server_name,server_os_family,server_os_version,server_fqdn,r_type,app_name,aws_accountid,aws_region,wave_name\n" +
    "unittest1,linux,redhat,unittest1.testdomain.local,Rehost,Unit testing App 1,123456789012,us-east-2,Unit testing Wave 1";
  await select_upload_file_click_next(validFileContents, "valid.csv", "text/csv");
}

async function select_valid_file_upload_scenario3() {
  // server wave app
  // Update Update Update
  const validFileContents =
    "server_name,server_os_family,server_os_version,server_fqdn,r_type,app_name,aws_accountid,aws_region,wave_name,wave_status\n" +
    "unittest1,linux,redhat,unittest1-UPDATED.testdomain.local,Rehost,Unit testing App 1,123456789012,us-east-1,Unit testing Wave 1,Not started";
  await select_upload_file_click_next(validFileContents, "valid.csv", "text/csv");
}

async function assert_valid_file_review_changes_form_common() {
  await waitFor(() => {
    expect(screen.getByText("Your intake form has 0 validation errors.")).toBeVisible();
    expect(screen.getByText("Your intake form has 0 validation warnings.")).toBeVisible();
    expect(screen.getByText("Your intake form has 2 informational validation messages.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Previous" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Next" })).toBeVisible();
    expect(screen.getByPlaceholderText("Search data")).toBeInTheDocument();
  });
}

async function assert_valid_file_review_changes_form_scenario1() {
  await assert_valid_file_review_changes_form_common();
  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  expect(within(tbody).getAllByRole("row").length).toEqual(1);
  const row = within(tbody).getByRole("row");
  expect(within(row).getByRole("cell", { name: "unittest1-NEW" })).toBeVisible();
  expect(within(row).getByText("2 Validation Informational")).toBeVisible();
}

async function assert_valid_file_review_changes_form_scenario2() {
  await assert_valid_file_review_changes_form_common();
  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  expect(within(tbody).getAllByRole("row").length).toEqual(1);
  const row = within(tbody).getByRole("row");
  expect(within(row).getByRole("cell", { name: "unittest1" })).toBeVisible();
  expect(within(row).getByText("2 Validation Informational")).toBeVisible();
}

async function assert_valid_file_review_changes_form_scenario3() {
  await assert_valid_file_review_changes_form_scenario2();
}

describe("should show next page with cancel, previous and next buttons and data table, after valid intake file", () => {
  test("scenario1", async () => {
    setup_all_get_handlers();
    renderUserImportComponent();
    await select_valid_file_upload_scenario1();
    await assert_valid_file_review_changes_form_scenario1();
  });

  test("scenario2", async () => {
    setup_all_get_handlers();
    renderUserImportComponent();
    await select_valid_file_upload_scenario2();
    await assert_valid_file_review_changes_form_scenario2();
  });

  test("scenario3", async () => {
    setup_all_get_handlers();
    renderUserImportComponent();
    await select_valid_file_upload_scenario3();
    await assert_valid_file_review_changes_form_scenario3();
  });
});

test("Cancel button after valid file takes back to empty intake form - scenario1", async () => {
  setup_all_get_handlers();
  renderUserImportComponent();
  await select_valid_file_upload_scenario1();
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await assert_empty_import_page();
});

test("Previous button after valid file takes back to the uploaded file form - scenario1", async () => {
  setup_all_get_handlers();
  renderUserImportComponent();
  await select_valid_file_upload_scenario1();
  await userEvent.click(screen.getByRole("button", { name: "Previous" }));
  await assert_upload_file_selected("valid.csv");
});

function assert_two_headers(headerText1: string, headerText2: string, count: number) {
  //This is bad, but tests the function getSummary, can be removed when separate tests for the utils folder are added
  expect(
    screen.getAllByText((_: string, node: Element | null) => {
      // eslint-disable-next-line testing-library/no-node-access
      if (
        node &&
        node.textContent === headerText1 &&
        node.parentNode &&
        node.parentNode.nextSibling &&
        node.parentNode.nextSibling.textContent === headerText2
      ) {
        return true;
      }
      return false;
    }).length
  ).toEqual(count);
}

async function assert_upload_overview_common() {
  expect(screen.getByRole("heading", { name: "Upload data" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Upload Overview" })).toBeInTheDocument();

  //TODO: html can be in table so that the contents can be queries with within()
  expect(screen.getByRole("heading", { name: "Database" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Wave" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Application" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Server" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Template" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Pipeline" })).toBeInTheDocument();
}

describe("Next button after valid file takes to the upload overview page", () => {
  test("scenario1", async () => {
    // GIVEN
    setup_all_get_handlers();
    renderUserImportComponent();

    // WHEN
    await select_valid_file_upload_scenario1();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await assert_upload_overview_common();

    // THEN
    assert_two_headers("Create", "-", 4);
    assert_two_headers("Create", "1", 3);
    assert_two_headers("Update", "-", TOTAL_NUMBER_OF_ENTITY_TYPES);
    assert_two_headers("No Update", "-", TOTAL_NUMBER_OF_ENTITY_TYPES);
    expect(screen.getAllByRole("button", { name: "Details" }).length).toEqual(3);
  });

  test("scenario2", async () => {
    setup_all_get_handlers();
    renderUserImportComponent();
    await select_valid_file_upload_scenario2();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await assert_upload_overview_common();
    assert_two_headers("Create", "-", TOTAL_NUMBER_OF_ENTITY_TYPES);
    assert_two_headers("Update", "-", TOTAL_NUMBER_OF_ENTITY_TYPES);
    assert_two_headers("No Update", "1", 3);
    assert_two_headers("No Update", "-", TOTAL_NUMBER_OF_ENTITY_TYPES - 3);
    await expect(screen.getAllByRole("button", { name: "Details" }).length).toEqual(3);
  });

  test("scenario3", async () => {
    setup_all_get_handlers();
    renderUserImportComponent();
    await select_valid_file_upload_scenario3();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await assert_upload_overview_common();
    assert_two_headers("Create", "-", TOTAL_NUMBER_OF_ENTITY_TYPES);
    assert_two_headers("Update", "-", TOTAL_NUMBER_OF_ENTITY_TYPES - 3);
    assert_two_headers("Update", "1", 3);
    assert_two_headers("No Update", "-", TOTAL_NUMBER_OF_ENTITY_TYPES);
    await expect(screen.getAllByRole("button", { name: "Details" }).length).toEqual(3);
  });
});

test("Cancel button on the upload overview page takes back to empty intake - scenario1", async () => {
  setup_all_get_handlers();
  renderUserImportComponent();
  await select_valid_file_upload_scenario1();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await assert_empty_import_page();
});

test("Previous button on the upload overview page takes back to review page - scenario1", async () => {
  setup_all_get_handlers();
  renderUserImportComponent();
  await select_valid_file_upload_scenario1();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await userEvent.click(screen.getByRole("button", { name: "Previous" }));
  await assert_valid_file_review_changes_form_scenario1();
});

test("Clicking Upload on the overview page, uploads - scenario1", async () => {
  setup_all_get_handlers();
  server.use(
    rest.post("/user/wave", (request, response, context) => {
      return response.once(
        context.status(200),
        context.json({
          newItems: [
            {
              wave_name: "Unittest Wave 1",
              wave_id: "101",
              _history: {
                createdBy: {
                  userRef: "a16cd40f-95e0-4709-b7bd-0109e926b9e3",
                  email: "serviceaccount@example.com",
                },
                createdTimestamp: "2023-11-13T20:17:43.208085",
              },
            },
          ],
        })
      );
    }),
    rest.post("/user/app", (request, response, context) => {
      return response.once(
        context.status(200),
        context.json({
          newItems: [
            {
              app_name: "Unit testing App 1",
              aws_accountid: "123456789012",
              aws_region: "us-east-1",
              wave_id: "101",
              app_id: "101",
              _history: {
                createdBy: {
                  userRef: "a16cd40f-95e0-4709-b7bd-0109e926b9e3",
                  email: "serviceaccount@example.com",
                },
                createdTimestamp: "2023-11-13T20:17:44.737164",
              },
            },
          ],
        })
      );
    }),
    rest.post("/user/server", (request, response, context) => {
      return response.once(
        context.status(200),
        context.json({
          newItems: [
            {
              server_name: "unittest1",
              server_os_family: "linux",
              server_os_version: "redhat",
              server_fqdn: "unittest1.testdomain.local",
              r_type: "Rehost",
              app_id: "101",
              server_id: "101",
              _history: {
                createdBy: {
                  userRef: "a16cd40f-95e0-4709-b7bd-0109e926b9e3",
                  email: "serviceaccount@example.com",
                },
                createdTimestamp: "2023-11-13T20:17:46.669565",
              },
            },
          ],
        })
      );
    })
  );

  const { addNotification } = renderUserImportComponent();
  const addNotificationId = v4();
  const addNotificationMock = addNotification as jest.Mock;
  addNotificationMock.mockImplementation((notificationAddRequest: CmfAddNotification) => {
    return notificationAddRequest.id || addNotificationId;
  });
  await select_valid_file_upload_scenario1();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await userEvent.click(screen.getByRole("button", { name: "Upload" }));
  expect(screen.getAllByText("Intake form upload status.").length).toBeGreaterThan(1);
  expect(screen.getByText("Intake file upload completed successfully.")).toBeVisible();
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledTimes(8);
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: (
        <ProgressBar
          label={"Importing file valid.csv ..."}
          value={0}
          additionalInfo="Starting upload..."
          variant="flash"
        />
      ),
      dismissible: false,
      loading: true,
      type: "info",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: (
        <ProgressBar
          additionalInfo="Updating any related records with new wave IDs..."
          label="Importing file 'valid.csv' ..."
          value={16.666666666666668}
          variant="flash"
        />
      ),
      dismissible: false,
      id: addNotificationId,
      loading: true,
      type: "info",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      id: addNotificationId,
      type: "success",
      dismissible: true,
      header: "Import of valid.csv successful.",
    });
  });
});

test("Clicking Upload on the overview page, upload fails with api 200 with error messages - scenario1", async () => {
  setup_all_get_handlers();
  server.use(
    rest.post("/user/wave", (request, response, context) => {
      return response.once(
        context.status(200),
        context.json({
          errors: {
            validation_errors: [
              {
                error_detail: ["Simulated Error 1", "Simulated Error 2"],
              },
            ],
            unprocessed_items: [
              {
                error_detail: ["Unprocessed Item 1", "Unprocessed Item 2"],
              },
            ],
          },
        })
      );
    }),
    rest.post("/user/app", (request, response, context) => {
      return response.once(
        context.status(200),
        context.json({
          errors: {
            existing_name: ["field1", "field2"],
          },
        })
      );
    }),
    rest.post("/user/server", (request, response, context) => {
      return response.once(
        context.status(200),
        context.json({
          errors: [
            "Error Number 1",
            {
              cause: "Caused By 1",
            },
          ],
        })
      );
    })
  );

  const { addNotification } = renderUserImportComponent();
  await select_valid_file_upload_scenario1();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await userEvent.click(screen.getByRole("button", { name: "Upload" }));
  expect(screen.getAllByText("Intake form upload status.").length).toBeGreaterThan(1);
  expect(screen.getByText("Intake file upload completed successfully.")).toBeVisible();
  expect(screen.getByText("Errors returned during upload of 3 records.")).toBeVisible();
  expect(screen.getByRole("button", { name: "wave - Create failed" })).toBeVisible();
  expect(screen.getByRole("button", { name: "application - Create failed" })).toBeVisible();
  expect(screen.getByRole("button", { name: "server - Create failed" })).toBeVisible();

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledTimes(2);
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: (
        <ProgressBar
          label={"Importing file valid.csv ..."}
          value={0}
          additionalInfo="Starting upload..."
          variant="flash"
        />
      ),
      dismissible: false,
      loading: true,
      type: "info",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "error",
        dismissible: true,
        header: "Import of file 'valid.csv' had 3 errors.",
        content: (
          <ExpandableSection headerText="Error details">
            <ExpandableSection key="wave - Create failed" headerText="wave - Create failed">
              ["error_detail : Simulated Error 1,Simulated Error 2","error_detail : Unprocessed Item 1,Unprocessed Item
              2"]
            </ExpandableSection>
            <ExpandableSection key="application - Create failed" headerText="application - Create failed">
              ["field1 already exists.","field2 already exists."]
            </ExpandableSection>
            <ExpandableSection key="server - Create failed" headerText="server - Create failed">
              ["Error Number 1","Caused By 1"]
            </ExpandableSection>
          </ExpandableSection>
        ),
      })
    );
  });
});

test("Clicking Upload on the overview page, upload fails with api post 500 error - scenario1", async () => {
  setup_all_get_handlers();
  server.use(
    rest.post("/user/wave", (request, response, context) => {
      return response.once(context.status(500));
    }),
    rest.post("/user/app", (request, response, context) => {
      return response.once(context.status(500));
    }),
    rest.post("/user/server", (request, response, context) => {
      return response.once(context.status(500));
    })
  );

  const { addNotification } = renderUserImportComponent();
  await select_valid_file_upload_scenario1();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await userEvent.click(screen.getByRole("button", { name: "Upload" }));
  expect(screen.getAllByText("Intake form upload status.").length).toBeGreaterThan(1);
  expect(screen.getByText("Intake file upload completed successfully.")).toBeVisible();
  expect(screen.getByText("Errors returned during upload of 3 records.")).toBeVisible();
  expect(screen.getByRole("button", { name: "wave Create - Internal API error - Contact support" })).toBeVisible();
  expect(
    screen.getByRole("button", { name: "application Create - Internal API error - Contact support" })
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "server Create - Internal API error - Contact support" })).toBeVisible();

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledTimes(5);
  });
});

test("Clicking Upload on the overview page, uploads - scenario2", async () => {
  setup_all_get_handlers();

  renderUserImportComponent();
  await select_valid_file_upload_scenario2();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await userEvent.click(screen.getByRole("button", { name: "Upload" }));
  expect(screen.getByText("Commit intake")).toBeVisible();
  expect(screen.getByText("Nothing to be committed!")).toBeVisible();
});

test("Clicking Upload on the overview page, uploads - scenario3", async () => {
  setup_all_get_handlers();
  server.use(
    rest.put("/user/wave/:wave_id", (request, response, context) => {
      return response.once(context.status(200));
    }),
    rest.put("/user/app/:app_id", (request, response, context) => {
      return response.once(context.status(200));
    }),
    rest.put("/user/server/:server_id", (request, response, context) => {
      return response.once(context.status(200));
    })
  );

  const { addNotification } = renderUserImportComponent();
  await select_valid_file_upload_scenario3();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await userEvent.click(screen.getByRole("button", { name: "Upload" }));
  expect(screen.getAllByText("Intake form upload status.").length).toBeGreaterThan(1);
  expect(screen.getByText("Intake file upload completed successfully.")).toBeVisible();
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledTimes(5);
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: (
        <ProgressBar
          label={"Importing file valid.csv ..."}
          value={0}
          additionalInfo="Starting upload..."
          variant="flash"
        />
      ),
      dismissible: false,
      loading: true,
      type: "info",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        content: (
          <ProgressBar
            additionalInfo="Update wave records..."
            label="Importing file 'valid.csv' ..."
            value={33.333333333333336}
            variant="flash"
          />
        ),
        dismissible: false,
        loading: true,
        type: "info",
      })
    );
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "success",
        dismissible: true,
        header: "Import of valid.csv successful.",
      })
    );
  });
});

test("Clicking Upload on the overview page, uploads api errors - scenario3", async () => {
  setup_all_get_handlers();
  server.use(
    rest.put("/user/wave/:wave_id", (request, response, context) => {
      return response.once(context.status(500));
    }),
    rest.put("/user/app/:app_id", (request, response, context) => {
      return response.once(context.status(500));
    }),
    rest.put("/user/server/:server_id", (request, response, context) => {
      return response.once(context.status(500));
    })
  );

  const { addNotification } = renderUserImportComponent();
  await select_valid_file_upload_scenario3();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await userEvent.click(screen.getByRole("button", { name: "Upload" }));
  expect(screen.getAllByText("Intake form upload status.").length).toBeGreaterThan(1);
  expect(screen.getByText("Intake file upload completed successfully.")).toBeVisible();
  expect(screen.getByText("Errors returned during upload of 3 records.")).toBeVisible();
  expect(screen.getByRole("button", { name: "wave - Unit testing Wave 1 - Unknown error occurred" })).toBeVisible();
  expect(
    screen.getByRole("button", { name: "application - Unit testing App 1 - Unknown error occurred" })
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "server - unittest1 - Unknown error occurred" })).toBeVisible();

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledTimes(5);
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: (
        <ProgressBar
          label={"Importing file valid.csv ..."}
          value={0}
          additionalInfo="Starting upload..."
          variant="flash"
        />
      ),
      dismissible: false,
      loading: true,
      type: "info",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        content: (
          <ProgressBar
            additionalInfo="Update wave records..."
            label="Importing file 'valid.csv' ..."
            value={33.333333333333336}
            variant="flash"
          />
        ),
        dismissible: false,
        loading: true,
        type: "info",
      })
    );
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "error",
        dismissible: true,
        header: "Import of file 'valid.csv' had 3 errors.",
        content: expect.anything(),
      })
    );
  });
});

async function select_valid_file_warnings_upload() {
  const validFileContents =
    "server_name,server_os_familyNO,server_os_version,server_fqdn,r_type,app_name,aws_accountid,aws_region,wave_name\n" +
    "unittest1,linux,redhat,unittest1.testdomain.local,Rehost,Unit testing App 1,123456789012,us-east-2,Unit testing Wave 1";
  await select_upload_file_click_next(validFileContents, "valid.csv", "text/csv");
}

async function assert_valid_file_warnings_review_changes_form() {
  expect(screen.getByText("Your intake form has 0 validation errors.")).toBeVisible();
  expect(screen.getByText("Your intake form has 1 validation warnings.")).toBeVisible();
  expect(screen.getByText("Your intake form has 2 informational validation messages.")).toBeVisible();
  expect(screen.getByRole("button", { name: "Cancel" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Previous" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Next" })).toBeVisible();
  expect(screen.getByPlaceholderText("Search data")).toBeInTheDocument();
  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  expect(within(tbody).getAllByRole("row").length).toEqual(1);
  const row = within(tbody).getByRole("row");
  expect(within(row).getByRole("cell", { name: "unittest1" })).toBeVisible();
  expect(within(row).getByText("2 Validation Informational")).toBeVisible();
  expect(within(row).getByText("1 Validation Warnings")).toBeVisible();
}
test("should show next page with cancel, previous and next buttons and data table, after valid intake file with warnings", async () => {
  setup_all_get_handlers();
  renderUserImportComponent();
  await select_valid_file_warnings_upload();
  await assert_valid_file_warnings_review_changes_form();
});

async function select_invalid_file_upload() {
  const fileContents =
    "server_name,server_os_family,server_os_version,server_fqdn,r_type,app_name,aws_accountid,aws_region,wave_name,wave_status\n" +
    "unittest1,linux,redhat,unittest1.testdomain.local,Rehost,Unit testing App 1,123456789012,us-east-2,Unit testing Wave 1,Invalid wave status value";
  await select_upload_file_click_next(fileContents, "valid.csv", "text/csv");
}

async function assert_invalid_file_review_changes_form() {
  expect(screen.getByText("Your intake form has 1 validation errors.")).toBeVisible();
  expect(screen.getByText("Your intake form has 2 informational validation messages.")).toBeVisible();
  expect(screen.getByRole("button", { name: "Cancel" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Previous" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Next" })).toBeVisible();
  expect(screen.getByPlaceholderText("Search data")).toBeInTheDocument();
  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  expect(within(tbody).getAllByRole("row").length).toEqual(1);
  const row = within(tbody).getByRole("row");
  expect(within(row).getByRole("cell", { name: "unittest1" })).toBeVisible();
  expect(within(row).getByText("2 Validation Informational")).toBeVisible();
  expect(within(row).getByText("1 Validation Errors")).toBeVisible();
}
test("should show next page with cancel, previous and next buttons and data table, after invalid intake file", async () => {
  setup_all_get_handlers();
  renderUserImportComponent();
  await select_invalid_file_upload();
  await assert_invalid_file_review_changes_form();
  // nothing happens when you click next
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await assert_invalid_file_review_changes_form();
});
