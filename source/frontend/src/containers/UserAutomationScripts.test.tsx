/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { render, screen, waitFor, waitForElementToBeRemoved, within } from "@testing-library/react";
import React from "react";
import "@testing-library/jest-dom";
import { defaultTestProps, mockNotificationContext, TEST_SESSION_STATE } from "../__tests__/TestUtils";
import UserAutomationScripts from "./UserAutomationScripts";
import { MemoryRouter } from "react-router-dom";
import { SessionContext } from "../contexts/SessionContext";
import { NotificationContext } from "../contexts/NotificationContext";
import { server } from "../setupTests";
import { rest } from "msw";
import { generateTestAutomationScripts } from "../__tests__/mocks/ssm_api";
import userEvent from "@testing-library/user-event";

const renderUserAutomationScriptsComponent = (props = defaultTestProps) => {
  return {
    ...mockNotificationContext,
    container: render(
      <MemoryRouter initialEntries={["/automation/scripts"]}>
        <NotificationContext.Provider value={mockNotificationContext}>
          <SessionContext.Provider value={TEST_SESSION_STATE}>
            <UserAutomationScripts {...props} />
            <div id="modal-root" />
          </SessionContext.Provider>
        </NotificationContext.Provider>
      </MemoryRouter>
    ),
  };
};

test("Automation scripts page loads and displays the empty table.", async () => {
  renderUserAutomationScriptsComponent();

  expect(screen.getByRole("heading", { name: "Automation Scripts (0)" })).toBeInTheDocument();
  expect(screen.getByPlaceholderText("Search automation scripts")).toBeInTheDocument();
  expect(screen.getByText("Loading scripts")).toBeInTheDocument();

  await waitForElementToBeRemoved(() => screen.queryByText("Loading scripts"));
  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  expect(within(tbody).getAllByRole("row").length).toEqual(1);
});

test("it renders a paginated table with 50 scripts", async () => {
  server.use(
    rest.get("/ssm/scripts", (request, response, context) => {
      return response(context.status(200), context.json(generateTestAutomationScripts(50)));
    })
  );

  renderUserAutomationScriptsComponent();

  await waitForElementToBeRemoved(() => screen.queryByText("Loading scripts"));

  expect(screen.getByRole("heading", { name: "Automation Scripts (50)" })).toBeInTheDocument();

  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  expect(within(tbody).getAllByRole("row")).toHaveLength(10);
});

test("clicking the refresh button refreshes the table", async () => {
  server.use(
    rest.get("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestAutomationScripts(5)));
    }),
    rest.get("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestAutomationScripts(8)));
    })
  );

  renderUserAutomationScriptsComponent();

  await waitForElementToBeRemoved(() => screen.queryByText("Loading scripts"));

  expect(screen.getByRole("heading", { name: "Automation Scripts (5)" })).toBeInTheDocument();
  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  expect(within(tbody).getAllByRole("row")).toHaveLength(5);

  const refreshButton = screen.getByRole("button", { name: "Refresh" });
  await userEvent.click(refreshButton);

  expect(screen.getByRole("heading", { name: "Automation Scripts (8)" })).toBeInTheDocument();
  const table2 = screen.getByRole("table");
  const tbody2 = within(table2).getAllByRole("rowgroup")[1];
  expect(within(tbody2).getAllByRole("row")).toHaveLength(8);
});

test("clicking the refresh button after selecting row, refreshes the table and keeps selection", async () => {
  server.use(
    rest.get("/ssm/scripts", (request, response, context) => {
      return response(context.status(200), context.json(generateTestAutomationScripts(5)));
    })
  );

  renderUserAutomationScriptsComponent();

  await waitForElementToBeRemoved(() => screen.queryByText("Loading scripts"));

  expect(screen.getByRole("heading", { name: "Automation Scripts (5)" })).toBeInTheDocument();
  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  expect(within(tbody).getAllByRole("row")).toHaveLength(5);

  const row1 = within(tbody).getAllByRole("row")[0];
  const checkBox1 = within(row1).getByRole("checkbox");
  await userEvent.click(checkBox1);

  expect(screen.getByRole("heading", { name: "Automation Scripts (1 of 5)" })).toBeInTheDocument();

  const refreshButton = screen.getByRole("button", { name: "Refresh" });
  await userEvent.click(refreshButton);

  expect(screen.getByRole("heading", { name: "Automation Scripts (1 of 5)" })).toBeInTheDocument();
  const table2 = screen.getByRole("table");
  const tbody2 = within(table2).getAllByRole("rowgroup")[1];
  expect(within(tbody2).getAllByRole("row")).toHaveLength(5);
});

async function render_click_add() {
  server.use(
    rest.get("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestAutomationScripts(8)));
    })
  );

  const { addNotification } = renderUserAutomationScriptsComponent();
  await waitForElementToBeRemoved(() => screen.queryByText("Loading scripts"));

  expect(screen.getByRole("heading", { name: "Automation Scripts (8)" })).toBeVisible();

  await userEvent.click(screen.getByRole("button", { name: "Add" }));

  expect(await screen.findByRole("heading", { name: "Select script package zip file" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Automation Scripts (8)" })).not.toBeInTheDocument();

  return addNotification;
}

async function add_form_click_cancel() {
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));
  expect(screen.getByRole("heading", { name: "Automation Scripts (8)" })).toBeVisible();
}

async function add_form_select_file() {
  let nextButton = screen.getByRole("button", { name: "Next" });
  // expect(nextButton).toBeDisabled(); //not sure why this is not working even though attr aria-disabled="true"
  expect(nextButton.getAttribute("aria-disabled")).toEqual("true");

  const file = new File(["Some zip"], "test_package.zip", { type: "application/zip" });
  // const uploadFileButton = screen.getByRole("button", {name: "Select file"}); // this is the visible button, but
  // the actual input button to upload is hidden
  //no role selector for input type="file"
  const uploadInput = document.querySelector("input[type='file']") as HTMLInputElement;
  await userEvent.upload(uploadInput, file);

  nextButton = screen.getByRole("button", { name: "Next" });
  expect(nextButton).toBeEnabled();
  expect(nextButton.getAttribute("aria-disabled")).toEqual(null);
}

async function add_form_click_next() {
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(screen.getByRole("heading", { name: "Select script to package" })).toBeVisible();
}

async function add_form_script_details_click_cancel() {
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.getByRole("heading", { name: "Automation Scripts (8)" })).toBeVisible();
}

async function add_form_script_details_click_previous() {
  await userEvent.click(screen.getByRole("button", { name: "Previous" }));
  expect(screen.getByRole("heading", { name: "Select script to package" })).toBeVisible();
}

async function add_form_script_details_click_upload() {
  await userEvent.type(screen.getByRole("textbox", { name: "Script Name" }), "test package");
  await userEvent.click(screen.getByRole("button", { name: "Upload" }));
}

test("it shows add page form when Add button is clicked, and cancel closes the form", async () => {
  await render_click_add();
  await add_form_click_cancel();
});

test("it renders the table view back when click add, upload file, click next, click cancel", async () => {
  await render_click_add();
  await add_form_select_file();
  await add_form_click_next();
  await add_form_script_details_click_cancel();
});

test("it renders the table view back when click add, upload file, click next, click previous", async () => {
  await render_click_add();
  await add_form_select_file();
  await add_form_click_next();
  await add_form_script_details_click_previous();
});

test("it shows success notification when click add, upload file, click next, upload success", async () => {
  server.use(
    rest.post("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(200));
    })
  );
  const addNotification = await render_click_add();
  await add_form_select_file();
  await add_form_click_next();

  server.use(
    rest.get("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestAutomationScripts(9)));
    })
  );

  await add_form_script_details_click_upload();
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "Uploading script - test_package.zip",
      dismissible: false,
      header: "Uploading script",
      loading: true,
      type: "success",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Uploading script",
      content: "test_package.zip script upload successfully.",
    });
  });
  expect(screen.getByRole("heading", { name: "Automation Scripts (9)" })).toBeVisible();
});

test("it shows error notification when click add, upload file, click next, upload error", async () => {
  server.use(
    rest.post("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(500, "Invalid zip file."), context.text("Invalid zip file."));
    })
  );
  const addNotification = await render_click_add();
  await add_form_select_file();
  await add_form_click_next();
  await add_form_script_details_click_upload();
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "Uploading script - test_package.zip",
      dismissible: false,
      header: "Uploading script",
      loading: true,
      type: "success",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "error",
      dismissible: true,
      header: "Uploading script",
      content: 'test_package.zip script upload failed: "Invalid zip file."',
    });
  });
});

async function render_and_select_row(selRowIndex = 0) {
  server.use(
    rest.get("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestAutomationScripts(8)));
    })
  );

  const { addNotification } = renderUserAutomationScriptsComponent();
  await waitForElementToBeRemoved(() => screen.queryByText("Loading scripts"));

  expect(screen.getByRole("heading", { name: "Automation Scripts (8)" })).toBeInTheDocument();

  const buttonActions = screen.getByRole("button", { name: "Actions" });
  expect(buttonActions).toBeDisabled();

  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  const row1 = within(tbody).getAllByRole("row")[selRowIndex];
  const checkBox1 = within(row1).getByRole("checkbox");
  await userEvent.click(checkBox1);

  expect(screen.getByRole("heading", { name: "Automation Scripts (1 of 8)" })).toBeVisible();

  const selectedScriptName = within(row1).getAllByRole("cell")[1].innerHTML;
  expect(screen.getByRole("tab", { name: "Details" })).toBeInTheDocument();
  const detailsPanel = screen.getByRole("tabpanel", { name: "Details" });
  expect(detailsPanel).toBeVisible();
  expect(within(detailsPanel).getByText(selectedScriptName)).toBeInTheDocument();
  expect(buttonActions).toBeEnabled();

  return addNotification;
}

async function deselect_row(selRowIndex = 0) {
  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  const row1 = within(tbody).getAllByRole("row")[selRowIndex];
  const checkBox1 = within(row1).getByRole("checkbox");
  await userEvent.click(checkBox1);

  expect(screen.getByRole("heading", { name: "Automation Scripts (8)" })).toBeVisible();

  expect(screen.queryByRole("tab", { name: "Details" })).not.toBeInTheDocument();
}

async function select_second_row() {
  const table = screen.getByRole("table");
  const tbody = within(table).getAllByRole("rowgroup")[1];
  const row2 = within(tbody).getAllByRole("row")[1];
  const checkBox1 = within(row2).getByRole("checkbox");
  await userEvent.click(checkBox1);

  expect(screen.getByRole("heading", { name: "Automation Scripts (2 of 8)" })).toBeVisible();
  expect(screen.queryByRole("tab", { name: "Details" })).not.toBeInTheDocument();
}

async function click_change_default_version() {
  const buttonActions = screen.getByRole("button", { name: "Actions" });
  await userEvent.click(buttonActions);

  const buttonChangeDefaultVersion = screen.getByRole("menuitem", { name: "Change default version" });
  await userEvent.click(buttonChangeDefaultVersion);

  expect(screen.getByRole("heading", { name: "Change default script version" })).toBeVisible();
}

async function select_another_version_save() {
  const buttonSelect = screen.getByRole("button", { name: /script default version 1/i }) as HTMLSelectElement;
  await userEvent.click(buttonSelect);
  const option2 = screen.getByRole("option", { name: "2" });
  await userEvent.click(option2);
  expect(
    screen.getByText(
      "Saving will change default script to use version 2 instead of version 1 for all automation future jobs."
    )
  ).toBeVisible();
  const buttonSave = screen.getByRole("button", { name: "Save" });
  expect(buttonSave).toBeEnabled();
  await userEvent.click(buttonSave);
}

test("it shows details and actions button is enabled when a row is selected", async () => {
  await render_and_select_row();
  await deselect_row();
});

test("it shows no details when 2 rows are selected", async () => {
  await render_and_select_row();
  await select_second_row();
});

test("it brings change default version form menu actions and cancel brings back to the table", async () => {
  await render_and_select_row();
  await click_change_default_version();

  const buttonCancel = screen.getByRole("button", { name: "Cancel" });
  await userEvent.click(buttonCancel);

  expect(screen.getByRole("heading", { name: "Automation Scripts (1 of 8)" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Change default script version" })).not.toBeInTheDocument();
});

test("it brings change default version form menu actions and download selected version", async () => {
  server.use(
    rest.get("/ssm/scripts/:script_id/:version/download", (request, response, context) => {
      return response.once(
        context.status(200),
        context.json({
          script_file: "test_script_file",
          script_name: "test_script_name",
          script_version: "test_script_version",
        })
      );
    })
  );
  const addNotification = await render_and_select_row();
  await click_change_default_version();

  const buttonDownload = screen.getByRole("button", { name: "Download selected version" });
  await userEvent.click(buttonDownload);

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "Downloading script default version - 0-Check MGN Prerequisites 0",
      dismissible: false,
      header: "Download script",
      loading: true,
      type: "success",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Download script",
      content: "0-Check MGN Prerequisites 0 script downloaded.",
    });
  });
  expect(screen.getByRole("heading", { name: "Change default script version" })).toBeVisible();
});

test("it doesn't change the default version form menu actions if there is only one version", async () => {
  await render_and_select_row();
  await click_change_default_version();

  const buttonSave = screen.getByRole("button", { name: "Save" });
  expect(buttonSave).toBeDisabled();
});

test("it changes the default version form menu actions when another version is selected", async () => {
  server.use(
    rest.put("/ssm/scripts/:script_id", (request, response, context) => {
      return response.once(context.status(200));
    }),
    rest.get("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestAutomationScripts(9)));
    })
  );

  const addNotification = await render_and_select_row(1);
  await click_change_default_version();
  await select_another_version_save();

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "Changing script default version - 0-Check MGN Prerequisites 1",
      dismissible: false,
      header: "Change script default version",
      loading: true,
      type: "success",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Change script default version",
      content: "0-Check MGN Prerequisites 1 script default version changed to use version 2.",
    });
  });
  expect(screen.getByRole("heading", { name: "Automation Scripts (9)" })).toBeVisible();
});

test("it doesn't change the default version form menu actions when another version is selected when API errors", async () => {
  server.use(
    rest.put("/ssm/scripts/:script_id", (request, response, context) => {
      return response.once(context.status(500), context.text("Network Error"));
    }),
    rest.get("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestAutomationScripts(8)));
    })
  );

  const addNotification = await render_and_select_row(1);
  await click_change_default_version();
  await select_another_version_save();

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "Changing script default version - 0-Check MGN Prerequisites 1",
      dismissible: false,
      header: "Change script default version",
      loading: true,
      type: "success",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "error",
      dismissible: true,
      header: "Change script default version",
      content: "0-Check MGN Prerequisites 1 script version change failed: Network Error",
    });
  });
  expect(screen.getByRole("heading", { name: "Automation Scripts (1 of 8)" })).toBeVisible();
});

async function click_add_new_version() {
  const buttonActions = screen.getByRole("button", { name: "Actions" });
  await userEvent.click(buttonActions);

  const buttonAddNewVersion = screen.getByRole("menuitem", { name: "Add new version" });
  await userEvent.click(buttonAddNewVersion);

  expect(screen.getByRole("heading", { name: "Select script package zip file" })).toBeVisible();
}

async function new_version_form_click_cancel() {
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.getByRole("heading", { name: "Automation Scripts (1 of 8)" })).toBeVisible();
}

test("it shows the form when Actions > Add new version clicked", async () => {
  await render_and_select_row();
  await click_add_new_version();
});

test("it goes back to table view when Actions > Add new version, then Cancel", async () => {
  await render_and_select_row();
  await click_add_new_version();
  await new_version_form_click_cancel();
});

test("it shows success notification when Actions > Add new version, then Next, upload success", async () => {
  const addNotification = await render_and_select_row();
  await click_add_new_version();
  await add_form_select_file();
  await add_form_click_next();

  server.use(
    rest.put("/ssm/scripts/:script_id", (request, response, context) => {
      return response.once(context.status(200));
    })
  );

  server.use(
    rest.get("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestAutomationScripts(9)));
    })
  );

  await add_form_script_details_click_upload();
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "Uploading script - test_package.zip",
      dismissible: false,
      header: "Uploading script",
      loading: true,
      type: "success",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Uploading script",
      content: "test_package.zip script upload successfully.",
    });
  });
  expect(screen.getByRole("heading", { name: "Automation Scripts (9)" })).toBeVisible();
});

test("it shows error notification when Actions > Add new version, then Next, upload error", async () => {
  const addNotification = await render_and_select_row();
  await click_add_new_version();
  await add_form_select_file();
  await add_form_click_next();

  server.use(
    rest.put("/ssm/scripts/:script_id", (request, response, context) => {
      return response.once(context.status(500), context.text("Invalid zip file."));
    })
  );

  server.use(
    rest.get("/ssm/scripts", (request, response, context) => {
      return response.once(context.status(200), context.json(generateTestAutomationScripts(9)));
    })
  );

  await add_form_script_details_click_upload();
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      content: "Uploading script - test_package.zip",
      dismissible: false,
      header: "Uploading script",
      loading: true,
      type: "success",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "error",
      dismissible: true,
      header: "Uploading script",
      content: 'test_package.zip script upload failed: "Invalid zip file."',
    });
  });
});

async function click_download_default_version() {
  const buttonActions = screen.getByRole("button", { name: "Actions" });
  await userEvent.click(buttonActions);

  const buttonDownload = screen.getByRole("menuitem", { name: "Download default version" });
  await userEvent.click(buttonDownload);
}

async function click_download_latest_version() {
  const buttonActions = screen.getByRole("button", { name: "Actions" });
  await userEvent.click(buttonActions);

  const buttonDownload = screen.getByRole("menuitem", { name: "Download latest version" });
  await userEvent.click(buttonDownload);
}

test("it shows success notification when Actions > Download default version success", async () => {
  server.use(
    rest.get("/ssm/scripts/:script_id/1/download", (request, response, context) => {
      return response.once(
        context.status(200),
        context.json({
          script_file: "test_script_file",
          script_name: "test_script_name",
          script_version: "test_script_version",
        })
      );
    })
  );

  const addNotification = await render_and_select_row(1);
  await click_download_default_version();

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: false,
      header: "Download script",
      loading: true,
      content: "Downloading script default version - 0-Check MGN Prerequisites 1",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Download script",
      content: "0-Check MGN Prerequisites 1 script downloaded.",
    });
  });
});

test("it shows error notification when Actions > Download default version failure", async () => {
  server.use(
    rest.get("/ssm/scripts/:script_id/1/download", (request, response, context) => {
      return response.once(context.status(500), context.text("Unexpected Error."));
    })
  );

  const addNotification = await render_and_select_row();
  await click_download_default_version();

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: false,
      header: "Download script",
      loading: true,
      content: "Downloading script default version - 0-Check MGN Prerequisites 0",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "error",
      dismissible: true,
      header: "Download script",
      content: "0-Check MGN Prerequisites 0 script download failed: Unexpected Error.",
    });
  });
});

test("it shows success notification when Actions > Download latest version success", async () => {
  server.use(
    rest.get("/ssm/scripts/:script_id/2/download", (request, response, context) => {
      return response.once(
        context.status(200),
        context.json({
          script_file: "test_script_file",
          script_name: "test_script_name",
          script_version: "test_script_version",
        })
      );
    })
  );

  const addNotification = await render_and_select_row(1); //second row contains versions
  await click_download_latest_version();

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: false,
      header: "Download script",
      loading: true,
      content: "Downloading script default version - 0-Check MGN Prerequisites 1",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: true,
      header: "Download script",
      content: "0-Check MGN Prerequisites 1 script downloaded.",
    });
  });
});

test("it shows error notification when Actions > Download latest version failure", async () => {
  server.use(
    rest.get("/ssm/scripts/:script_id/2/download", (request, response, context) => {
      return response.once(context.status(500), context.text("Unexpected Error."));
    })
  );

  const addNotification = await render_and_select_row(1); //second row contains versions
  await click_download_latest_version();

  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "success",
      dismissible: false,
      header: "Download script",
      loading: true,
      content: "Downloading script default version - 0-Check MGN Prerequisites 1",
    });
  });
  await waitFor(() => {
    expect(addNotification).toHaveBeenCalledWith({
      type: "error",
      dismissible: true,
      header: "Download script",
      content: "0-Check MGN Prerequisites 1 script download failed: Unexpected Error.",
    });
  });
});

test("it deep links to add form", async () => {
  server.use(
    rest.get("/ssm/scripts", (request, response, context) => {
      return response(context.status(200), context.json(generateTestAutomationScripts(8)));
    })
  );

  render(
    <MemoryRouter initialEntries={["/automation/scripts/add"]}>
      <NotificationContext.Provider value={mockNotificationContext}>
        <SessionContext.Provider value={TEST_SESSION_STATE}>
          <UserAutomationScripts {...defaultTestProps} />
          <div id="modal-root" />
        </SessionContext.Provider>
      </NotificationContext.Provider>
    </MemoryRouter>
  );
  await waitForElementToBeRemoved(() => screen.queryByText("Loading scripts"));
  expect(screen.getByRole("heading", { name: "Select script package zip file" })).toBeVisible();
});

test("it shows disabled buttons based on permission", async () => {
  server.use(
    rest.get("/ssm/scripts", (request, response, context) => {
      return response(context.status(200), context.json(generateTestAutomationScripts(5)));
    })
  );

  renderUserAutomationScriptsComponent({
    ...defaultTestProps,
    userEntityAccess: {
      ...defaultTestProps.userEntityAccess,
      script: {
        create: false,
        update: false,
        attributes: [],
      },
    },
  });

  await waitForElementToBeRemoved(() => screen.queryByText("Loading scripts"));
  expect(screen.getByRole("heading", { name: "Automation Scripts (5)" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Actions" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Add" })).toBeDisabled();
});
