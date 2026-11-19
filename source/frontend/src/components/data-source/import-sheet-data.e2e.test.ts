/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { WebWorkerMessage } from "../../actions/WorkerHook";
import { ImportSheetData } from "./import-sheet-data";
import { ImportSheetDataWorkerProps, SheetToEntityMapping } from "./data-source-types";
import { EntitySchema } from "../../models";

// These tests use the real xlsx library (no mocking) to verify end-to-end behavior

interface ServerEntityData {
  entityName: string;
  data: Record<string, { aws_accountid: string }>;
}

interface ImportResult {
  validationResult: {
    entities: ServerEntityData[];
  };
}

describe("ImportSheetData - end-to-end tests", () => {
  const createServerSchema = (): EntitySchema =>
    ({
      schema_name: "server",
      schema_type: "user",
      attributes: [
        { name: "server_name", type: "string", required: true },
        { name: "aws_accountid", type: "string", required: false },
      ],
    }) as EntitySchema;

  test("preserves AWS account IDs with leading zeros when importing CSV", async () => {
    // Create a CSV with AWS account IDs that have leading zeros
    const csvContent =
      "server_name,aws_accountid\n" + "server1,012345678901\n" + "server2,001122334455\n" + "server3,000000000000\n";

    const csvFile = new File([csvContent], "test.csv", { type: "text/csv" });

    const schemas: Record<string, EntitySchema> = {
      server: createServerSchema(),
    };

    const sheetToEntityMappings: SheetToEntityMapping[] = [
      {
        sheetName: "Sheet1", // xlsx reads CSV as "Sheet1"
        headers: [
          {
            name: "server_name",
            entityAttributes: [{ attributeName: "server_name", entityName: "server" }],
            previewValues: [],
          },
          {
            name: "aws_accountid",
            entityAttributes: [{ attributeName: "aws_accountid", entityName: "server" }],
            previewValues: [],
          },
        ],
        entityNames: ["server"],
        isSelected: true,
      },
    ];

    const props: ImportSheetDataWorkerProps = {
      schemas,
      dataSourceFile: csvFile,
      sheetToEntityMappings,
    };

    const event = { data: props } as MessageEvent<ImportSheetDataWorkerProps>;

    // Capture the postMessage calls
    const messages: WebWorkerMessage<unknown>[] = [];
    const postMessageMock = jest.fn((msg: WebWorkerMessage<unknown>) => messages.push(msg));

    const importSheetData = new ImportSheetData(postMessageMock);
    await importSheetData.handleOnMessage(event);

    // Find the complete message and cast to expected type
    const completeMessage = messages.find((msg) => msg.state === "complete");
    expect(completeMessage).toBeDefined();
    expect(completeMessage?.result).toBeDefined();

    const result = completeMessage?.result as ImportResult;
    const serverEntity = result.validationResult.entities.find((e) => e.entityName === "server");

    expect(serverEntity).toBeDefined();
    if (!serverEntity) {
      throw new Error("serverEntity should be defined");
    }

    // The data structure is: { [identifier]: [records] }
    // Verify the AWS account IDs preserve leading zeros
    expect(serverEntity.data["server1"]).toBeDefined();
    expect(serverEntity.data["server2"]).toBeDefined();
    expect(serverEntity.data["server3"]).toBeDefined();

    // Each record is an object with the attributes
    expect(serverEntity.data["server1"].aws_accountid).toBe("012345678901");
    expect(serverEntity.data["server2"].aws_accountid).toBe("001122334455");
    expect(serverEntity.data["server3"].aws_accountid).toBe("000000000000");
  });
});
