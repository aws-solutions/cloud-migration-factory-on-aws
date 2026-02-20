/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { getSheetData } from "./get-sheet-header-data-worker";

describe("getSheetData", () => {
  test("preserves AWS account IDs with leading zeros in preview values", async () => {
    const csvContent =
      "server_name,aws_accountid\n" + "server1,012345678901\n" + "server2,001122334455\n" + "server3,000000000000\n";

    const csvFile = new File([csvContent], "test.csv", { type: "text/csv" });

    const sheets = await getSheetData(csvFile);

    expect(sheets).toHaveLength(1);
    expect(sheets[0].name).toBe("Sheet1");

    const accountIdHeader = sheets[0].headers.find((h) => h.name === "aws_accountid");
    expect(accountIdHeader).toBeDefined();
    expect(accountIdHeader?.previewValues).toContain("012345678901");
    expect(accountIdHeader?.previewValues).toContain("001122334455");
    expect(accountIdHeader?.previewValues).toContain("000000000000");
  });
});
