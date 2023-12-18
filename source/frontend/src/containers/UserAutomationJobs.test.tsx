/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {render, screen, waitFor, waitForElementToBeRemoved, within} from "@testing-library/react";
import React from "react";
import "@testing-library/jest-dom"
import {defaultTestProps, mockNotificationContext, TEST_SESSION_STATE} from "../__tests__/TestUtils";
import {MemoryRouter} from "react-router-dom";
import {SessionContext} from "../contexts/SessionContext";
import UserAutomationJobs from "./UserAutomationJobs";
import {NotificationContext} from "../contexts/NotificationContext";
import {server} from "../setupTests";
import {rest} from "msw";
import {generateTestAutomationJobs, generateTestAutomationScripts} from "../__tests__/mocks/ssm_api";
import userEvent from "@testing-library/user-event";
import {generateTestApps, generateTestWaves} from "../__tests__/mocks/user_api";

const renderUserAutomationJobsComponent = () => {
    return {
        ...mockNotificationContext,
        result: render(
            <MemoryRouter initialEntries={["/automation/jobs"]}>
                <NotificationContext.Provider value={mockNotificationContext}>
                    <SessionContext.Provider value={TEST_SESSION_STATE}>
                        <UserAutomationJobs
                            {...defaultTestProps}
                        />
                        <div id="modal-root"/>
                    </SessionContext.Provider>
                </NotificationContext.Provider>
            </MemoryRouter>
        )
    };
}

test("it loads and displays the empty table.", async () => {
    renderUserAutomationJobsComponent();

    // page renders the loading state
    expect(screen.getByRole("heading", {name: "Jobs (0)"})).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Search jobs")).toBeInTheDocument();
    expect(screen.getByText("Loading jobs")).toBeInTheDocument();

    await waitForElementToBeRemoved(() => screen.queryByText("Loading jobs"));

    //empty table rendered
    const table = screen.getByRole("table");
    const tbody = within(table).getAllByRole("rowgroup")[1];
    const row1 = within(tbody).getByRole("row");

    expect(await within(row1).findByText("No jobs")).toBeInTheDocument();
    expect(await within(row1).findByText("No jobs to display.")).toBeInTheDocument();
});

async function assert_jobs_list_view(numItems: number, withLoading = true, selected = false) {
    if (withLoading) {
        await waitForElementToBeRemoved(screen.queryByText("Loading jobs"));
    }
    if (selected) {
        expect(screen.getByRole("heading", {name: "Jobs (1 of " + numItems + ")"})).toBeInTheDocument();
    } else {
        expect(screen.getByRole("heading", {name: "Jobs (" + numItems + ")"})).toBeInTheDocument();
    }
    expect(screen.getByText("Displaying only the last 30 days of jobs.")).toBeInTheDocument();
    const table = screen.getByRole("table");
    const tbody = within(table).getAllByRole("rowgroup")[1];
    expect(within(tbody).getAllByRole("row")).toHaveLength(numItems > 10 ? 10 : numItems);
}

async function select_a_row(rowIndex = 0) {
    const table = screen.getByRole("table");
    const tbody = within(table).getAllByRole("rowgroup")[1];
    const row1 = within(tbody).getAllByRole("row")[rowIndex];
    const radioButton1 = within(row1).getByRole("radio");
    await userEvent.click(radioButton1);
}

test("it renders a paginated table with 50 jobs", async () => {
    server.use(
        rest.get("/ssm/jobs", (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestAutomationJobs(50))
            );
        })
    );

    renderUserAutomationJobsComponent();

    await assert_jobs_list_view(50);
});

test("clicking the refresh button refreshes the table", async () => {
    server.use(
        rest.get("/ssm/jobs", (request, response, context) => {
            return response.once(
                context.status(200),
                context.json(generateTestAutomationJobs(5))
            );
        }),
        rest.get("/ssm/jobs", (request, response, context) => {
            return response.once(
                context.status(200),
                context.json(generateTestAutomationJobs(8))
            );
        }),
    );

    renderUserAutomationJobsComponent();

    await assert_jobs_list_view(5);
    const refreshButton = screen.getByRole("button", {name: "Refresh"});
    await userEvent.click(refreshButton);
    await assert_jobs_list_view(8, false);
});


test("clicking the refresh button refreshes the table and keeps the selection", async () => {
    server.use(
        rest.get("/ssm/jobs", (request, response, context) => {
            return response.once(
                context.status(200),
                context.json(generateTestAutomationJobs(5))
            );
        }),
        rest.get("/ssm/jobs", (request, response, context) => {
            return response.once(
                context.status(200),
                context.json(generateTestAutomationJobs(8))
            );
        }),
    );

    renderUserAutomationJobsComponent();

    await assert_jobs_list_view(5);
    await select_a_row();
    await assert_jobs_list_view(5, false, true);
    const refreshButton = screen.getByRole("button", {name: "Refresh"});
    await userEvent.click(refreshButton);
    await assert_jobs_list_view(8, false, true);
});

async function assert_selected_details() {
    const table = screen.getByRole("table");
    const tbody = within(table).getAllByRole("rowgroup")[1];
    const row1 = within(tbody).getAllByRole("row")[0];
    const selectedJobName = (within(row1).getAllByRole("cell")[1]).innerHTML;
    const detailsTabHeader = screen.getByRole("tab", {name: "Details"})
    const logTabHeader = screen.getByRole("tab", {name: "Log"});
    expect(detailsTabHeader).toBeInTheDocument();
    expect(logTabHeader).toBeInTheDocument();

    const detailsTabPanel = screen.getByRole("tabpanel", {name: "Details"});
    expect(within(detailsTabPanel).getAllByText(selectedJobName)[0]).toBeVisible();

    await userEvent.click(logTabHeader);
    const logTabPanel = screen.getByRole("tabpanel", {name: "Log"});
    expect(within(logTabPanel).queryByDisplayValue(/Successfully packaged/)).toBeVisible();
}

test("it shows the details when a row is selected", async () => {
    server.use(
        rest.get("/ssm/jobs", (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestAutomationJobs(5))
            );
        })
    );

    renderUserAutomationJobsComponent();

    await assert_jobs_list_view(5);
    await select_a_row();
    await assert_selected_details();
});

async function click_run_automations() {
    const actionsButton = screen.getByText(/Actions/i);
    await userEvent.click(actionsButton);
    const runAutomationButton = screen.getByRole("menuitem", {name: "Run Automation"});
    await userEvent.click(runAutomationButton);
}

async function assert_run_automations_view() {
    expect(await screen.findByRole('heading', {name: "Run Automation"})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Cancel"})).toBeEnabled();
    expect(screen.getByRole("button", {name: "Submit Automation Job"})).toBeDisabled();
    expect(screen.getAllByText("You must specify a valid value.").length).toEqual(3);
}

test("it shows the automation page when Actions > Run Automations is clicked", async () => {
    server.use(
        rest.get("/ssm/jobs", (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestAutomationJobs(5))
            );
        })
    );

    renderUserAutomationJobsComponent();
    await click_run_automations();
    await assert_run_automations_view();
});

test("clicking Cancel from Run Automations takes back to jobs list", async () => {
    server.use(
        rest.get("/ssm/jobs", (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestAutomationJobs(5))
            );
        })
    );

    renderUserAutomationJobsComponent();

    await click_run_automations();
    const cancelButton = screen.getByRole("button", {name: "Cancel"});
    await userEvent.click(cancelButton);
    await assert_jobs_list_view(5, false);
});

async function fill_in_automation_attributes() {
    const jobNameTextBox = screen.getByRole("textbox", {name: "Job Name"});
    await userEvent.type(jobNameTextBox, "Test Job");

    // select script name
    const buttonSelectScriptName = (screen.getByRole("button", {name: /script name/i})) as HTMLSelectElement;
    await userEvent.click(buttonSelectScriptName);
    const optionScript2 = screen.getByRole("option", {name: "0-Check MGN Prerequisites 1"});
    await userEvent.click(optionScript2);
    //fill in the param for the selected option
    const param1TextBox = screen.getByRole("textbox", {name: /replication server ip\./i});
    await userEvent.type(param1TextBox, "192.168.0.5");

    //select automation server
    const buttonAutomationServer = (screen.getByRole("button", {name: /Select Automation Server/i})) as HTMLSelectElement;
    await userEvent.click(buttonAutomationServer);
    const optionServer1 = screen.getByRole("option", {name: /Instance 001/i});
    await userEvent.click(optionServer1);
}

async function render_job_automations_and_submit() {
    server.use(
        rest.get("/ssm/jobs", (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestAutomationJobs(5))
            );
        }),
        rest.get("/ssm", (request, response, context) => {
            return response(
                context.status(200),
                context.json([
                    {
                        'mi_id': 'instance_001',
                        'online': true,
                        'mi_name': 'Instance 001'
                    },
                    {
                        'mi_id': 'instance_002',
                        'online': true,
                        'mi_name': 'Instance 002'
                    }
                ])
            );
        }),
        rest.get("/ssm/scripts", (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestAutomationScripts(5))
            );
        }),
    );

    const {addNotification} = renderUserAutomationJobsComponent();

    await click_run_automations();
    await fill_in_automation_attributes();

    expect(screen.queryByText("You must specify a valid value.")).not.toBeInTheDocument();

    const submitButton = screen.getByRole("button", {name: "Submit Automation Job"});
    await userEvent.click(submitButton);

    return addNotification;
}

test("clicking Submit Automation Job submits the job successfully", async () => {
    server.use(
        rest.post("/ssm", (request, response, context) => {
            return response(
                context.status(200),
                context.text("SSMId: instance_001+TEST_JOB_UUID+2023-12-08T15:43:21.398073")
            );
        }),
    );

    const addNotification = await render_job_automations_and_submit();

    await waitFor(() => {
        expect(addNotification).toHaveBeenCalledWith({
            "content": "Performing action - Submit Automation Job",
            "dismissible": false,
            "header": "Perform wave action",
            "loading": true,
            "type": "success",
        });
    });
    await waitFor(() => {
        expect(addNotification).toHaveBeenCalledWith({
            "content": "Submit Automation Job action successfully.",
            "dismissible": true,
            "header": "Perform wave action",
            "actionButtonLink": "/automation/jobs/TEST_JOB_UUID",
            "actionButtonTitle": "View Job",
            "type": "success",
            "id": undefined,
        });
    });
    await assert_jobs_list_view(5, false);
});

test("clicking Submit Automation Job submits, api error with error text", async () => {
    server.use(
        rest.post("/ssm", (request, response, context) => {
            return response(
                context.status(500),
                context.text("Error posting")
            );
        }),
    );

    const addNotification = await render_job_automations_and_submit();

    await waitFor(() => {
        expect(addNotification).toHaveBeenCalledWith({
            "content": "Performing action - Submit Automation Job",
            "dismissible": false,
            "header": "Perform wave action",
            "loading": true,
            "type": "success",
        });
    });
    await waitFor(() => {
        expect(addNotification).toHaveBeenCalledWith({
            "content": "Submit Automation Job action failed: Error posting",
            "dismissible": true,
            "header": "Perform wave action",
            "type": "error",
            "id": undefined,
        });
    });
});

async function click_actions_rehost_mgn() {
    const actionsButton = screen.getByText(/Actions/i);
    await userEvent.click(actionsButton);

    const rehostButton = screen.getByRole("menuitem", {name: "Rehost"});
    await userEvent.click(rehostButton);

    const mgnButton = screen.getByRole("menuitem", {name: "MGN"});
    await userEvent.click(mgnButton);
}

async function assert_mgn_server_migration_empty_view() {
    expect(screen.getByRole("heading", {name: "MGN server migration"})).toBeInTheDocument();
    expect(screen.getAllByText("You must specify a valid value.").length).toEqual(3);
    expect(screen.getByRole("button", {name: "Submit"})).toBeDisabled();
    expect(screen.getByRole("button", {name: "Cancel"})).toBeEnabled();
}

test("it shows the MGN Page when Actions > Rehost > MGN is clicked", async () => {
    server.use(
        rest.get("/ssm/jobs", (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestAutomationJobs(5))
            );
        })
    );

    renderUserAutomationJobsComponent();

    await click_actions_rehost_mgn();
    await assert_mgn_server_migration_empty_view();
});

test("click cancel on submit mgn server migration page", async () => {
    server.use(
        rest.get("/ssm/jobs", (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestAutomationJobs(5))
            );
        })
    );

    renderUserAutomationJobsComponent();

    await click_actions_rehost_mgn();
    await userEvent.click(screen.getByRole("button", {name: "Cancel"}));

    await assert_jobs_list_view(5, false);
});

async function fill_in_mgn_serer_migration_form() {
    const selectActionButton = screen.getByRole("button", {name: /Select Action/i});
    await userEvent.click(selectActionButton);
    const optionAction1 = screen.getByRole("option", {name: /validate launch template/i});
    await userEvent.click(optionAction1);

    const selectWaveButton = screen.getByRole("button", {name: /Wave/i});
    await userEvent.click(selectWaveButton);
    const optionWave1 = screen.getByRole("option", {name: /Unit testing Wave 0/i});
    await userEvent.click(optionWave1);

    const selectAppButton = screen.getByRole("button", {name: /Select Applications/i});
    await userEvent.click(selectAppButton);

    const optionApp1 = screen.getByRole("option", {name: /Unit testing App 0/i});
    await userEvent.click(optionApp1);
}

async function render_server_migration_and_submit() {
    server.use(
        rest.get("/ssm/jobs", (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestAutomationJobs(5))
            );
        }),
        rest.get('/user/wave', (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestWaves(2))
            );
        }),
        rest.get('/user/app', (request, response, context) => {
            return response(
                context.status(200),
                context.json(generateTestApps(2, {waveId: "0"}))
            );
        }),
    );

    const {addNotification} = renderUserAutomationJobsComponent();

    await click_actions_rehost_mgn();
    await fill_in_mgn_serer_migration_form();

    await userEvent.click(screen.getByRole("button", {name: "Submit"}));

    return addNotification;
}

test("submit mgn server migration successfully", async () => {
    server.use(
        rest.post('/mgn', (request, response, context) => {
            return response(
                context.status(200),
                context.text("Submitted to mgn")
            );
        }),
    );

    const addNotification = await render_server_migration_and_submit();

    await waitFor(() => {
        expect(addNotification).toHaveBeenCalledWith({
            "content": "Performing action - Submit",
            "dismissible": false,
            "header": "Perform wave action",
            "loading": true,
            "type": "success",
        });
    });
    await waitFor(() => {
        expect(addNotification).toHaveBeenCalledWith({
            "content": "Submitted to mgn",
            "dismissible": true,
            "header": "Perform wave action",
            "type": "success",
            "id": undefined,
        });
    });
    await assert_jobs_list_view(5, false);
});

test("submit mgn server migration api error", async () => {
    server.use(
        rest.post('/mgn', (request, response, context) => {
            return response(
                context.status(500),
                context.text("Errors submitting to mgn")
            );
        }),
    );

    const addNotification = await render_server_migration_and_submit();

    await waitFor(() => {
        expect(addNotification).toHaveBeenCalledWith({
            "content": "Performing action - Submit",
            "dismissible": false,
            "header": "Perform wave action",
            "loading": true,
            "type": "success",
        });
    });
    await waitFor(() => {
        expect(addNotification).toHaveBeenCalledWith({
            "content": "Submit action failed: Errors submitting to mgn",
            "dismissible": true,
            "header": "Perform wave action",
            "type": "error",
            "id": undefined,
        });
    });
});
