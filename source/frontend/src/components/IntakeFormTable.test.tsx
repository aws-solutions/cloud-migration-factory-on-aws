/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { cleanup, render, screen } from "@testing-library/react";
import IntakeFormTable from "./IntakeFormTable";

afterEach(cleanup);

test("IntakeFormTable displays the empty items table with header Import", () => {
  render(<IntakeFormTable schema={[]} items={[]} isLoading={false} errorLoading={null} />);

  expect(screen.getByText("Import")).toBeTruthy();
});
