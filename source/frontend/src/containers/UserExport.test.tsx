import { defaultTestProps, TEST_SESSION_STATE } from "../__tests__/TestUtils";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionContext } from "../contexts/SessionContext";
import React from "react";
import userEvent from "@testing-library/user-event";
import * as XLSX from "xlsx";
import UserExport from "./UserExport";
import { ToolsContext } from "../contexts/ToolsContext";

function renderUserExportComponent(props = defaultTestProps) {
  const helpPanelMockContext = {
    setHelpPanelContent: jest.fn(),
    setHelpPanelContentFromSchema: jest.fn(),
    setToolsOpen: jest.fn(),
    toolsState: {
      toolsOpen: false,
    },
  };

  return {
    renderResult: render(
      <MemoryRouter initialEntries={["/export"]}>
        <ToolsContext.Provider value={helpPanelMockContext}>
          <SessionContext.Provider value={TEST_SESSION_STATE}>
            <div id="modal-root" />
            <UserExport></UserExport>
          </SessionContext.Provider>
        </ToolsContext.Provider>
      </MemoryRouter>
    ),
    helpPanelMockContext,
  };
}

test("the download button downloads an xlsx file", async () => {
  // GIVEN
  jest.spyOn(XLSX.utils, "json_to_sheet");

  const { helpPanelMockContext } = renderUserExportComponent();
  const downloadButton = screen.getByRole("button", { name: "Download All Data" });

  // WHEN
  await userEvent.click(downloadButton);

  // THEN
  expect(XLSX.utils.json_to_sheet).toHaveBeenCalledTimes(4); // 1 sheet per entity type
  expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
  expect(helpPanelMockContext.setHelpPanelContent).toHaveBeenCalledWith({
    header: "Export",
    content_text:
      "From here you can export all the data from the Migration Factory into a single multi tabbed Excel spreadsheet.",
  });
});

// TODO unit tests for the logic in xlsx.export.ts (no component test, no rendering necessary)
