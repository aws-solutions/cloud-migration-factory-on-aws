import { validateAttributes } from "./step4-attribute-validation";
import { DeduplicatedEntity } from "./types";
import { EntitySchema, Attribute } from "../../models";
import UserApiClient from "../../api_clients/userApiClient";

jest.mock("../../api_clients/userApiClient");
const mockUserApiClient = UserApiClient as jest.MockedClass<typeof UserApiClient>;

const createMockSchema = (attributes: Partial<Attribute>[], entityName?: string): EntitySchema => ({
  schema_type: "test",
  schema_name: entityName || "test-schema",
  attributes: attributes.map((attr) => ({
    name: attr.name || "test-attr",
    description: attr.description || "Test attribute",
    type: attr.type || "string",
    required: attr.required || false,
    default: attr.default,
    validation_regex: attr.validation_regex,
    validation_regex_msg: attr.validation_regex_msg,
    rel_entity: attr.rel_entity,
    ...attr,
  })) as Attribute[],
});

const createMockDeduplicatedEntity = (
  entityName: string,
  attributes: Partial<Attribute>[],
  data: Record<string, Record<string, unknown>>
): DeduplicatedEntity => ({
  entityName,
  schema: createMockSchema(attributes, entityName),
  data,
});

describe("Step 4: Attribute Validation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUserApiClient.mockImplementation(
      () =>
        ({
          getItem: jest.fn().mockRejectedValue(new Error("Not found")),
          getItems: jest.fn().mockResolvedValue([]),
        }) as unknown as UserApiClient
    );
  });
  it("should remove entity for missing required field", async () => {
    const entities = {
      application: createMockDeduplicatedEntity("application", [{ name: "name", type: "string", required: true }], {
        app1: { description: "Test app" },
      }),
    };

    const result = validateAttributes(entities);

    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].message).toBe("Required attribute 'name' is missing or empty");
    expect(Object.keys(result.validatedEntities[0].data).length).toBe(0);
  });

  it("should remove entity for required field type error", async () => {
    const entities = {
      application: createMockDeduplicatedEntity("application", [{ name: "name", type: "number", required: true }], {
        app1: { name: "abc" },
      }),
    };

    const result = validateAttributes(entities);

    expect(result.validationErrors).toHaveLength(1);
    expect(Object.keys(result.validatedEntities[0].data).length).toBe(0);
  });

  it("should create warning and keep entity for optional field type error", async () => {
    const entities = {
      application: createMockDeduplicatedEntity(
        "application",
        [
          { name: "name", type: "string" },
          { name: "port", type: "number", required: false },
        ],
        { app1: { name: "App One", port: "not-a-number" } }
      ),
    };

    const result = validateAttributes(entities);

    expect(result.validationWarnings).toHaveLength(1);
    expect(result.validatedEntities[0].data["app1"]?.port).toBe("not-a-number");
  });

  it("should apply default values", async () => {
    const entities = {
      application: createMockDeduplicatedEntity(
        "application",
        [{ name: "status", type: "string", default: "active" }],
        { app1: { name: "App One" } }
      ),
    };

    const result = validateAttributes(entities);

    expect(result.validatedEntities[0].data["app1"]).toEqual({
      name: "App One",
      status: "active",
    });
  });

  it("should validate regex patterns", async () => {
    const entities = {
      application: createMockDeduplicatedEntity(
        "application",
        [
          {
            name: "email",
            type: "string",
            required: true,
            validation_regex: "^[\\w-\\.]+@([\\w-]+\\.)+[\\w-]{2,4}$",
          },
        ],
        { app1: { email: "invalid-email" } }
      ),
    };

    const result = validateAttributes(entities);

    expect(result.validationErrors).toHaveLength(1);
    expect(Object.keys(result.validatedEntities[0].data).length).toBe(0);
  });

  it("should validate list values", async () => {
    const entities = {
      application: createMockDeduplicatedEntity(
        "application",
        [
          {
            name: "aws_region",
            type: "list",
            required: true,
            listvalue: "us-east-1,us-west-2,eu-west-1",
          },
        ],
        { app1: { aws_region: "invalid-region" } }
      ),
    };

    const result = validateAttributes(entities);

    expect(result.validationErrors).toHaveLength(1);
    expect(result.validationErrors[0].message).toBe(
      "Value 'invalid-region' does not match any of the allowed values: us-east-1,us-west-2,eu-west-1"
    );
    expect(Object.keys(result.validatedEntities[0].data).length).toBe(0);
  });

  it("should collect backend validation requests without making API calls", async () => {
    const mockApiClient = {
      getItem: jest.fn(),
      getItems: jest.fn(),
    };
    mockUserApiClient.mockImplementation(() => mockApiClient as unknown as UserApiClient);

    const entities = {
      application: createMockDeduplicatedEntity(
        "application",
        [{ name: "server_id", type: "relationship", rel_entity: "server" }],
        { app1: { server_id: "server1" } }
      ),
    };

    const result = validateAttributes(entities);

    // No API calls should be made in worker context
    expect(mockApiClient.getItems).not.toHaveBeenCalled();
    expect(mockApiClient.getItem).not.toHaveBeenCalled();

    // Should collect backend validation requests
    expect(result.backendValidationRequests).toHaveLength(1);
    expect(result.backendValidationRequests[0]).toEqual({
      entityType: "server",
      references: new Set(["server1"]),
      validationItems: [
        {
          entityName: "application",
          uniqueKey: "app1",
          attributeName: "server_id",
          referencedKeys: ["server1"],
        },
      ],
    });

    // No cross-reference errors in worker context
    expect(result.crossReferenceErrors).toHaveLength(0);
  });

  it("should collect large reference sets for backend validation", async () => {
    const mockApiClient = {
      getItem: jest.fn(),
      getItems: jest.fn(),
    };
    mockUserApiClient.mockImplementation(() => mockApiClient as unknown as UserApiClient);

    const largeData: Record<string, Record<string, unknown>> = {};
    for (let i = 1; i <= 1000; i++) {
      largeData[`app${i}`] = { server_id: `server${i}` };
    }

    const entities = {
      application: createMockDeduplicatedEntity(
        "application",
        [{ name: "server_id", type: "relationship", rel_entity: "server" }],
        largeData
      ),
    };

    const result = validateAttributes(entities);

    // No API calls in worker context
    expect(mockApiClient.getItems).not.toHaveBeenCalled();
    expect(mockApiClient.getItem).not.toHaveBeenCalled();

    // Should collect all references for backend validation
    expect(result.backendValidationRequests).toHaveLength(1);
    expect(result.backendValidationRequests[0].references.size).toBe(1000);
    expect(result.backendValidationRequests[0].validationItems).toHaveLength(1000);
  });

  it("should collect references for backend validation", async () => {
    const mockApiClient = {
      getItem: jest.fn(),
      getItems: jest.fn(),
    };
    mockUserApiClient.mockImplementation(() => mockApiClient as unknown as UserApiClient);

    const entities = {
      application: createMockDeduplicatedEntity(
        "application",
        [{ name: "server_id", type: "relationship", rel_entity: "server" }],
        { app1: { server_id: "invalid-server" } }
      ),
    };

    const result = validateAttributes(entities);

    // No API calls in worker context
    expect(mockApiClient.getItems).not.toHaveBeenCalled();

    // Should collect reference for backend validation
    expect(result.backendValidationRequests).toHaveLength(1);
    expect(result.backendValidationRequests[0].references.has("invalid-server")).toBe(true);

    // No cross-reference errors in worker context - will be handled by main thread
    expect(result.crossReferenceErrors).toHaveLength(0);
  });

  it("should convert list type values to strings", async () => {
    const entities = {
      application: createMockDeduplicatedEntity("application", [{ name: "regions", type: "list" }], {
        app1: { regions: ["us-east-1", 123, true] },
      }),
    };

    const result = validateAttributes(entities);

    expect(result.validatedEntities[0].data["app1"]?.regions).toEqual(["us-east-1", "123", "true"]);
  });

  it("should convert single list type values to strings", async () => {
    const entities = {
      application: createMockDeduplicatedEntity("application", [{ name: "region", type: "list" }], {
        app1: { region: 123 },
      }),
    };

    const result = validateAttributes(entities);

    expect(result.validatedEntities[0].data["app1"]?.region).toBe("123");
  });

  it("should set server_os_family to TBC for invalid values", async () => {
    const entities = {
      server: createMockDeduplicatedEntity(
        "server",
        [{ name: "server_os_family", type: "list", listvalue: "TBC,windows,linux" }],
        {
          server1: { server_os_family: "invalid-os" },
          server2: { server_os_family: "windows" },
          server3: { server_os_family: "Linux" },
          server4: { server_os_family: "TBC" },
          server5: { server_os_family: "tbc" },
        }
      ),
    };

    const result = validateAttributes(entities);

    expect(result.validatedEntities[0].data["server1"]?.server_os_family).toBe("TBC");
    expect(result.validatedEntities[0].data["server2"]?.server_os_family).toBe("windows");
    expect(result.validatedEntities[0].data["server3"]?.server_os_family).toBe("Linux");
    expect(result.validatedEntities[0].data["server4"]?.server_os_family).toBe("TBC");
    expect(result.validatedEntities[0].data["server5"]?.server_os_family).toBe("tbc");
  });
});
