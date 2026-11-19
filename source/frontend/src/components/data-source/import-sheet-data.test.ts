import { read, WorkBook } from "xlsx";
import { ImportSheetData } from "./import-sheet-data";
import { processSheetData, SheetNotFoundError } from "./import-sheet-data-utils";
import { ImportSheetDataWorkerProps } from "./data-source-types";
import { DataValidationResult, EntityForValidation, validateData } from "../data-validation";
import { EntitySchema } from "../../models";

// Mock external dependencies
jest.mock("xlsx", () => ({
  read: jest.fn(),
}));

jest.mock("./import-sheet-data-utils", () => {
  const actual = jest.requireActual("./import-sheet-data-utils");
  return {
    ...actual,
    processSheetData: jest.fn(),
  };
});

jest.mock("../data-validation", () => ({
  validateData: jest.fn(),
}));

const mockedRead = read as jest.MockedFunction<typeof read>;
const mockedProcessSheetData = processSheetData as jest.MockedFunction<typeof processSheetData>;
const mockedValidateData = validateData as jest.MockedFunction<typeof validateData>;

interface TestFixtures {
  workbook: WorkBook;
  entities: EntityForValidation[];
  validationResult: DataValidationResult;
  schemas: Record<string, EntitySchema>;
  props: ImportSheetDataWorkerProps;
  event: MessageEvent<ImportSheetDataWorkerProps>;
}

/**
 * Creates standard test fixtures for import sheet data tests
 */
function createTestFixtures(): TestFixtures {
  // Create mock workbook
  const workbook: WorkBook = { Sheets: {}, SheetNames: [] };

  // Create mock schemas
  const schemas: Record<string, EntitySchema> = {
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
          name: "server_os_family",
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

  // Create mock entities for validation
  const entities: EntityForValidation[] = [
    {
      entityName: "server",
      schema: schemas.server,
      data: { server1: [{ server_name: "server1", server_os_family: "linux" }] },
    },
    {
      entityName: "application",
      schema: schemas.application,
      data: { app1: [{ app_name: "app1" }] },
    },
  ];

  // Create mock validation result
  const validationResult: DataValidationResult = {
    entities: [
      {
        entityName: "server",
        schema: schemas.server,
        data: { server1: { server_name: "server1", server_os_family: "linux" } },
      },
      {
        entityName: "application",
        schema: schemas.application,
        data: { app1: { app_name: "app1" } },
      },
    ],
    issues: {
      deduplicationErrors: [],
      deduplicationWarnings: [],
      requiredAttributeErrors: [],
      validationErrors: [],
      validationWarnings: [],
      crossReferenceErrors: [],
    },
    dependencyGraph: {
      dependencies: {},
    },
    entitiesToUpdate: {},
    backendValidationRequests: [],
  };

  // Create mock file
  const file = new File(["test content"], "test.xlsx");

  // Create mock props
  const props: ImportSheetDataWorkerProps = {
    schemas,
    dataSourceFile: file,
    sheetToEntityMappings: [],
  };

  // Create mock event
  const event = { data: props } as MessageEvent<ImportSheetDataWorkerProps>;

  return {
    workbook,
    entities,
    validationResult,
    schemas,
    props,
    event,
  };
}

/**
 * Creates validation result with errors for testing error scenarios
 */
function createValidationResultWithErrors(schemas: Record<string, EntitySchema>): DataValidationResult {
  return {
    entities: [
      {
        entityName: "server",
        schema: schemas.server,
        data: { server1: { server_name: "server1", server_os_family: "linux" } },
      },
    ],
    issues: {
      deduplicationErrors: [],
      deduplicationWarnings: [],
      requiredAttributeErrors: [
        {
          entityName: "application",
          uniqueKey: "app1",
          attributeName: "app_name",
          value: "",
          message: "Required attribute 'app_name' is missing or empty",
        },
      ],
      validationErrors: [],
      validationWarnings: [],
      crossReferenceErrors: [],
    },
    dependencyGraph: {
      dependencies: {},
    },
    entitiesToUpdate: {},
    backendValidationRequests: [],
  };
}

describe("ImportSheetData", () => {
  let postMessageMock: jest.Mock;
  let importSheetData: ImportSheetData;
  let fixtures: TestFixtures;

  beforeEach(() => {
    jest.clearAllMocks();
    postMessageMock = jest.fn();
    importSheetData = new ImportSheetData(postMessageMock);
    fixtures = createTestFixtures();
  });

  describe("handleOnMessage", () => {
    it("should process valid input successfully with validation", async () => {
      // Setup mocks using fixtures
      mockedRead.mockReturnValue(fixtures.workbook);
      mockedProcessSheetData.mockReturnValue(fixtures.entities);
      mockedValidateData.mockReturnValue(fixtures.validationResult);

      // Execute the method
      await importSheetData.handleOnMessage(fixtures.event);

      // Verify behavior
      expect(postMessageMock).toHaveBeenCalledWith({ state: "working" });
      expect(mockedRead).toHaveBeenCalled();
      expect(mockedProcessSheetData).toHaveBeenCalledWith(
        fixtures.props.sheetToEntityMappings,
        fixtures.workbook,
        fixtures.props.schemas
      );

      // Verify validateData was called with the correct entities
      expect(mockedValidateData).toHaveBeenCalledWith(fixtures.entities);

      // Verify the final result includes both entities and validationResult
      expect(postMessageMock).toHaveBeenLastCalledWith({
        state: "complete",
        result: {
          validationResult: fixtures.validationResult,
        },
      });
    });

    it("should handle validation errors in the data", async () => {
      // Setup mocks using fixtures
      const validationResultWithErrors = createValidationResultWithErrors(fixtures.schemas);

      mockedRead.mockReturnValue(fixtures.workbook);
      mockedProcessSheetData.mockReturnValue(fixtures.entities);
      mockedValidateData.mockReturnValue(validationResultWithErrors);

      // Execute the method
      await importSheetData.handleOnMessage(fixtures.event);

      // Verify the final result includes both entitiesForValidation and validationResult with errors
      expect(postMessageMock).toHaveBeenLastCalledWith({
        state: "complete",
        result: {
          validationResult: validationResultWithErrors,
        },
      });
    });

    it("should handle missing props", async () => {
      // Create event with undefined data
      const eventWithoutData = { data: undefined } as MessageEvent<ImportSheetDataWorkerProps | undefined>;

      // Execute the method
      await importSheetData.handleOnMessage(eventWithoutData);

      // Verify error handling
      expect(postMessageMock).toHaveBeenCalledWith({ state: "working" });
      expect(postMessageMock).toHaveBeenCalledWith({
        state: "error",
        result: new Error("No input props provided"),
      });
    });

    it("should handle workbook loading error", async () => {
      // Setup mock error
      const mockError = new Error("Failed to load workbook");
      mockedRead.mockImplementation(() => {
        throw mockError;
      });

      // Execute the method
      await importSheetData.handleOnMessage(fixtures.event);

      // Verify error handling
      expect(postMessageMock).toHaveBeenCalledWith({
        state: "error",
        result: mockError,
      });
    });

    it("should handle processSheetData error", async () => {
      // Setup mock error
      const mockError = new Error("Processing failed");
      mockedRead.mockReturnValue(fixtures.workbook);
      mockedProcessSheetData.mockImplementation(() => {
        throw mockError;
      });

      // Execute the method
      await importSheetData.handleOnMessage(fixtures.event);

      // Verify error handling
      expect(postMessageMock).toHaveBeenCalledWith({
        state: "error",
        result: mockError,
      });
    });

    it("should handle validateData error", async () => {
      // Setup mock error
      const mockError = new Error("Validation failed");
      mockedRead.mockReturnValue(fixtures.workbook);
      mockedProcessSheetData.mockReturnValue(fixtures.entities);
      mockedValidateData.mockImplementation(() => {
        throw mockError;
      });

      // Execute the method
      await importSheetData.handleOnMessage(fixtures.event);

      // Verify error handling
      expect(mockedValidateData).toHaveBeenCalled();
      expect(postMessageMock).toHaveBeenCalledWith({
        state: "error",
        result: mockError,
      });
    });

    it("should handle SheetNotFoundError with user-friendly message", async () => {
      // Setup mock SheetNotFoundError
      const sheetName = "MissingSheet";
      const mockError = new SheetNotFoundError(sheetName);
      mockedRead.mockReturnValue(fixtures.workbook);
      mockedProcessSheetData.mockImplementation(() => {
        throw mockError;
      });

      // Execute the method
      await importSheetData.handleOnMessage(fixtures.event);

      // Verify error handling with user-friendly message
      expect(postMessageMock).toHaveBeenCalledWith({
        state: "error",
        result: new Error(
          `Import failed: Sheet MissingSheet not found in workbook. Please verify that the file you've imported matches the selected data source.`
        ),
      });
    });
  });
});
