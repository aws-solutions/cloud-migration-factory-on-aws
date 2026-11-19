import { validateData } from "./index";
import { EntityForValidation } from "./types";
import { EntitySchema, Attribute } from "../../models";

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

const createMockEntityForValidation = (
  entityName: string,
  attributes: Partial<Attribute>[],
  data: Record<string, Record<string, unknown>[]>
): EntityForValidation => ({
  entityName,
  schema: createMockSchema(attributes, entityName),
  data,
});

describe("Data Validation Integration", () => {
  it("should process complete validation pipeline", () => {
    const entities: EntityForValidation[] = [
      createMockEntityForValidation(
        "application",
        [
          { name: "name", type: "string", required: true },
          { name: "server_id", type: "string", rel_entity: "server" },
        ],
        { app1: [{ name: "App One", server_id: "server-1" }] }
      ),
      createMockEntityForValidation(
        "server",
        [
          { name: "name", type: "string" },
          { name: "app_ids", type: "list", rel_entity: "application", listMultiSelect: true },
        ],
        { "server-1": [{ name: "Server One" }] }
      ),
    ];

    const result = validateData(entities);

    // Check bidirectional references were created
    expect(result.entities[1].data["server-1"]?.app_ids).toEqual(["app1"]);

    // Check dependency graph
    expect(result.dependencyGraph.dependencies["application"]).toEqual(["server"]);
    expect(result.dependencyGraph.dependencies["server"]).toEqual(["application"]);

    // Check no validation errors
    expect(result.issues.deduplicationErrors).toHaveLength(0);
    expect(result.issues.validationErrors).toHaveLength(0);
    expect(result.issues.crossReferenceErrors).toHaveLength(0);

    // Should have no entities to update since all references exist in current file
    expect(result.entitiesToUpdate).toEqual({});

    // Should have backendValidationRequests field
    expect(result.backendValidationRequests).toEqual([]);
  });

  it("should handle multiple validation issues", () => {
    const entities: EntityForValidation[] = [
      createMockEntityForValidation(
        "application",
        [
          { name: "name", type: "string", required: true },
          { name: "port", type: "number", required: true },
        ],
        {
          app1: [{ name: "Valid name", port: "invalid" }], // Invalid type for port
          app2: [{ name: "Missing port" }], // Missing port
        }
      ),
    ];

    const result = validateData(entities);

    expect(result.issues.requiredAttributeErrors).toHaveLength(1);
    expect(result.issues.validationErrors).toHaveLength(1);
  });

  it("should collect backend validation requests for missing references", () => {
    const entities: EntityForValidation[] = [
      createMockEntityForValidation(
        "application",
        [
          { name: "name", type: "string", required: true },
          { name: "server_id", type: "string", rel_entity: "server" },
        ],
        { app1: [{ name: "App One", server_id: "backend-server-1" }] }
      ),
    ];

    const result = validateData(entities);

    // Should collect backend validation requests
    expect(result.backendValidationRequests).toHaveLength(1);
    expect(result.backendValidationRequests[0]).toEqual({
      entityType: "server",
      references: new Set(["backend-server-1"]),
      validationItems: [
        {
          entityName: "application",
          uniqueKey: "app1",
          attributeName: "server_id",
          referencedKeys: ["backend-server-1"],
        },
      ],
    });

    // No cross-reference errors in worker context
    expect(result.issues.crossReferenceErrors).toHaveLength(0);
    expect(result.entitiesToUpdate).toEqual({});
  });
});
