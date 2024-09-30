import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { defaultTestProps, mockNotificationContext } from "../__tests__/TestUtils";
import userEvent from "@testing-library/user-event";
import React from "react";
import { NotificationContext } from "../contexts/NotificationContext";
import { PipelineTemplatesImport } from "./PipelineTemplatesImport.tsx";
import { API } from "@aws-amplify/api";

jest.mock("@aws-amplify/api", () => ({
  API: {
    post: jest.fn(),
  },
}));
afterEach(() => {
  jest.clearAllMocks();
});

function renderPage(props = defaultTestProps) {
  return {
    ...mockNotificationContext,
    renderResult: render(
      <MemoryRouter initialEntries={["/pipeline_templates/import"]}>
        <NotificationContext.Provider value={mockNotificationContext}>
          <Routes>
            <Route
              path={"/pipeline_templates/import"}
              element={<PipelineTemplatesImport {...props}></PipelineTemplatesImport>}
            />
            <Route path={"/pipeline_templates"} element={<h1>Pipeline Templates (0)</h1>} />
          </Routes>
        </NotificationContext.Provider>
      </MemoryRouter>
    ),
  };
}

test("pressing Cancel navigates to Pipeline Templates page", async () => {
  // WHEN
  renderPage();

  // THEN
  expect(screen.getByRole("heading", { name: "Select a file" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

  // THEN
  expect(await screen.findByText("Pipeline Templates (0)")).toBeInTheDocument();
});

test("pressing Next navigates to the next step", async () => {
  // GIVEN
  (API.post as jest.Mock).mockResolvedValueOnce({});

  // WHEN
  renderPage();

  // THEN
  expect(screen.getByRole("heading", { name: "Select a file" })).toBeInTheDocument();
  expect(screen.getByLabelText(/choose file/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "Next" }));

  // THEN
  expect(await screen.findByRole("heading", { name: "Upload data" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Previous" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "Submit" }));

  // THEN
  expect(await screen.findByText("Pipeline Templates (0)")).toBeInTheDocument();
});

test("uploading a file", async () => {
  // GIVEN
  renderPage();
  const fileContents = JSON.stringify([
    {
      template_name: "Rehost with Application Migration Service (MGN)",
      pipeline_template_description:
        "Facilitates server replications via Application Migration Service (MGN) for the selected wave",
      tasks: [
        {
          task_sequence_number: "1",
          pipeline_template_task_name: "2-verify_mgn_prerequisites",
          task_name: "verify_mgn_prerequisites",
        },
        {
          task_sequence_number: "2",
          pipeline_template_task_name: "2-install_mgn_agents",
          task_name: "install_mgn_agents",
        },
      ],
    },
  ]);

  const file = new File([fileContents], "test_pipeline_template_import.json", { type: "application/json" });

  // WHEN user uploads a file
  const uploadInput = document.querySelector("input[type='file']") as HTMLInputElement;
  await userEvent.upload(uploadInput, file);

  // THEN metadata of the uploaded file is displayed
  expect(await screen.findByText("test_pipeline_template_import.json")).toBeInTheDocument();
  expect(screen.getByText("0.45 KB")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /remove file 1/i })).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "Next" }));

  // THEN a preview of the uploaded data is displayed
  const codeView = await screen.findByTestId("code-view");
  expect(within(codeView).getByText(`"Rehost with Application Migration Service (MGN)"`)).toBeInTheDocument();
});
