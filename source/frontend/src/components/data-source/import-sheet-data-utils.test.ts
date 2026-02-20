import { WorkBook, utils } from "xlsx";
import { processSheetData, SheetNotFoundError } from "./import-sheet-data-utils";
import { SheetToEntityMapping } from "./data-source-types";
import { EntitySchema } from "../../models";
import { EntityForValidation } from "../data-validation";

jest.mock("xlsx", () => ({
  utils: {
    sheet_to_json: jest.fn(),
  },
}));

const mockedUtils = utils as jest.Mocked<typeof utils>;

describe("import-sheet-data-utils", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("processSheetData", () => {
    // Create mock schemas for testing
    const mockSchemas: Record<string, EntitySchema> = {
      server: {
        schema_name: "server",
        schema_type: "entity",
        attributes: [
          {
            name: "server_name",
            type: "string",
            required: true,
          },
          {
            name: "environment",
            type: "string",
            required: false,
          },
        ],
      } as EntitySchema,
      application: {
        schema_name: "application",
        schema_type: "entity",
        attributes: [
          {
            name: "app_name",
            type: "string",
            required: true,
          },
        ],
      } as EntitySchema,
    };

    it("should process sheet data correctly and return EntityForValidation array", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "ServerName",
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
            {
              name: "Environment",
              entityAttributes: [
                {
                  attributeName: "environment",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [
        { ServerName: "server1", Environment: "prod" },
        { ServerName: "server2", Environment: "dev" },
      ];

      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      // Verify the result is an array of EntityForValidation objects
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBe(1);

      // Verify the first entity is a server entity
      const serverEntity = result[0];
      expect(serverEntity.entityName).toBe("server");
      expect(serverEntity.schema).toBe(mockSchemas.server);

      // Verify the data is a Record with the correct entries
      expect(typeof serverEntity.data).toBe("object");
      expect(Object.keys(serverEntity.data).length).toBe(2);
      expect("server1" in serverEntity.data).toBe(true);
      expect("server2" in serverEntity.data).toBe(true);

      // Verify the data values are arrays of records
      const server1Data = serverEntity.data["server1"];
      expect(Array.isArray(server1Data)).toBe(true);
      expect(server1Data?.length).toBe(1);
      expect(server1Data?.[0]).toEqual({ server_name: "server1", environment: "prod" });

      const server2Data = serverEntity.data["server2"];
      expect(Array.isArray(server2Data)).toBe(true);
      expect(server2Data?.length).toBe(1);
      expect(server2Data?.[0]).toEqual({ server_name: "server2", environment: "dev" });
    });

    it("should handle entity identifiers with _name suffix", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "ServerName",
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [{ ServerName: "test-server" }];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      expect(result.length).toBe(1);
      const serverEntity = result[0] as EntityForValidation;
      expect(serverEntity.entityName).toBe("server");

      const serverData = serverEntity.data;
      expect("test-server" in serverData).toBe(true);

      const records = serverData["test-server"];
      expect(records).toHaveLength(1);
      expect(records?.[0]).toEqual({ server_name: "test-server" });
    });

    it("should throw SheetNotFoundError when sheet is not found", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {},
        SheetNames: [],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "NonExistentSheet",
          headers: [],
          entityNames: [],
          isSelected: false,
        },
      ];

      expect(() => processSheetData(mappings, mockWorkbook, mockSchemas)).toThrow(SheetNotFoundError);
    });

    it("should handle empty headers", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [],
          entityNames: [],
          isSelected: false,
        },
      ];

      mockedUtils.sheet_to_json.mockReturnValue([{ col1: "value1" }]);

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      expect(result.length).toBe(0);
    });

    it("should handle multiple entity types", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "ServerName",
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
            {
              name: "AppName",
              entityAttributes: [
                {
                  attributeName: "app_name",
                  entityName: "application",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [{ ServerName: "server1", AppName: "app1" }];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      expect(result.length).toBe(2);

      // Find server entity
      const serverEntity = result.find((entity) => entity.entityName === "server");
      expect(serverEntity).toBeDefined();
      expect("server1" in (serverEntity?.data || {})).toBe(true);

      // Find application entity
      const appEntity = result.find((entity) => entity.entityName === "application");
      expect(appEntity).toBeDefined();
      expect("app1" in (appEntity?.data || {})).toBe(true);
    });

    it("should cast non-string entity identifiers to strings", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "ServerName",
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [
        { ServerName: 123 }, // Number should be cast to string
        { ServerName: "valid-server" }, // Already a string
      ];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      // Should process both records
      expect(result.length).toBe(1);
      const serverEntity = result[0];
      expect(Object.keys(serverEntity.data).length).toBe(2);
      expect("123" in serverEntity.data).toBe(true);
      expect("valid-server" in serverEntity.data).toBe(true);

      // Verify the data values
      const server123Data = serverEntity.data["123"];
      expect(server123Data?.[0]).toEqual({ server_name: "123" });

      const serverValidData = serverEntity.data["valid-server"];
      expect(serverValidData?.[0]).toEqual({ server_name: "valid-server" });
    });

    it("should skip records with undefined and null entity identifiers and log warning", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "ServerName",
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [
        { ServerName: undefined }, // Invalid: undefined
        { ServerName: null }, // Invalid: null
        { ServerName: "valid-server" }, // Valid: string
      ];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      const consoleSpy = jest.spyOn(console, "warn").mockImplementation();

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      // Should only process the valid record
      expect(result.length).toBe(1);
      const serverEntity = result[0];
      expect(Object.keys(serverEntity.data).length).toBe(1);
      expect("valid-server" in serverEntity.data).toBe(true);

      // Should log warning for undefined identifier
      expect(consoleSpy).toHaveBeenCalledWith(
        "Skipping record for entity 'server' with invalid identifier 'undefined' (type: undefined). Attribute: server_name"
      );
      expect(consoleSpy).toHaveBeenCalledWith(
        "Skipping record for entity 'server' with invalid identifier 'null' (type: object). Attribute: server_name"
      );

      consoleSpy.mockRestore();
    });

    it("should skip records with empty string identifiers after trimming and log warning", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "ServerName",
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [
        { ServerName: "   " }, // Invalid: only whitespace
        { ServerName: "" }, // Invalid: empty string
        { ServerName: "valid-server" }, // Valid: string
      ];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      const consoleSpy = jest.spyOn(console, "warn").mockImplementation();

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      // Should only process the valid record
      expect(result.length).toBe(1);
      const serverEntity = result[0];
      expect(Object.keys(serverEntity.data).length).toBe(1);
      expect("valid-server" in serverEntity.data).toBe(true);

      // Should log warnings for empty identifiers
      expect(consoleSpy).toHaveBeenCalledWith(
        "Skipping record for entity 'server' with empty identifier after trimming. Attribute: server_name"
      );
      expect(consoleSpy).toHaveBeenCalledTimes(2); // Once for each empty identifier

      consoleSpy.mockRestore();
    });

    it("should throw error when header name is undefined", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              name: undefined as any,
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [{ ServerName: "server1" }];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      expect(() => processSheetData(mappings, mockWorkbook, mockSchemas)).toThrow("Header name is not defined.");
    });

    it("should handle empty array from sheet_to_json", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "ServerName",
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      mockedUtils.sheet_to_json.mockReturnValue([]);

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      expect(result.length).toBe(0);
    });

    it("should handle multiple rows mapping to same entity identifier", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "ServerName",
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
            {
              name: "Environment",
              entityAttributes: [
                {
                  attributeName: "environment",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [
        { ServerName: "server1", Environment: "prod" },
        { ServerName: "server1", Environment: "dev" },
      ];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      expect(result.length).toBe(1);
      const serverEntity = result[0];
      expect(serverEntity.entityName).toBe("server");

      const serverData = serverEntity.data;
      expect("server1" in serverData).toBe(true);

      const records = serverData["server1"];
      expect(records).toHaveLength(2);
      expect(records?.[0]).toEqual({ server_name: "server1", environment: "prod" });
      expect(records?.[1]).toEqual({ server_name: "server1", environment: "dev" });
    });

    it("should throw error when schema is not found for entity type", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "UnknownName",
              entityAttributes: [
                {
                  attributeName: "unknown_entity_name",
                  entityName: "unknown_entity",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [{ UnknownName: "unknown1" }];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      expect(() => processSheetData(mappings, mockWorkbook, mockSchemas)).toThrow(
        "Schema not found for entity type: unknown_entity"
      );
    });

    it("should trim whitespace from identifiers and treat them as same entity", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "ServerName",
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [{ ServerName: "xyz" }, { ServerName: " xyz " }];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      expect(result.length).toBe(1);
      const serverEntity = result[0];
      expect(Object.keys(serverEntity.data).length).toBe(1);
      expect("xyz" in serverEntity.data).toBe(true);

      const records = serverEntity.data["xyz"];
      expect(records).toHaveLength(2);
      expect(records?.[0]).toEqual({ server_name: "xyz" });
      expect(records?.[1]).toEqual({ server_name: "xyz" });
    });

    it("should filter out attributes not defined in schema", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "ServerName",
              entityAttributes: [
                {
                  attributeName: "server_name",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
            {
              name: "RemovedAttribute",
              entityAttributes: [
                {
                  attributeName: "app_source",
                  entityName: "server",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [{ ServerName: "server1", RemovedAttribute: "some_value" }];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      expect(result.length).toBe(1);
      const serverEntity = result[0];
      const records = serverEntity.data["server1"];
      expect(records).toHaveLength(1);
      expect(records?.[0]).toEqual({ server_name: "server1" });
      expect(records?.[0]).not.toHaveProperty("app_source");
    });

    it("should use schema_type + _name pattern for entity identifiers", () => {
      const mockWorkbook: WorkBook = {
        Sheets: {
          TestSheet: {},
        },
        SheetNames: ["TestSheet"],
      };

      const mappings: SheetToEntityMapping[] = [
        {
          sheetName: "TestSheet",
          headers: [
            {
              name: "AppName",
              entityAttributes: [
                {
                  attributeName: "app_name",
                  entityName: "application",
                },
              ],
              previewValues: [],
            },
            {
              name: "SomeName",
              entityAttributes: [
                {
                  attributeName: "some_name",
                  entityName: "application",
                },
              ],
              previewValues: [],
            },
          ],
          entityNames: [],
          isSelected: false,
        },
      ];

      const mockRows = [{ AppName: "app1", SomeName: "value1" }];
      mockedUtils.sheet_to_json.mockReturnValue(mockRows);

      const result = processSheetData(mappings, mockWorkbook, mockSchemas);

      expect(result.length).toBe(1);
      const appEntity = result[0];
      expect(appEntity.entityName).toBe("application");
      expect("app1" in appEntity.data).toBe(true);
      expect("value1" in appEntity.data).toBe(false);
    });
  });
});
