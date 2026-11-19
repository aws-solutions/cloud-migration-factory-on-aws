import { validateCrossReferences } from "./step5-cross-reference-cleanup";
import { DeduplicatedEntity } from "./types";
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

const createMockDeduplicatedEntity = (
  entityName: string,
  attributes: Partial<Attribute>[],
  data: Record<string, Record<string, unknown>>
): DeduplicatedEntity => ({
  entityName,
  schema: createMockSchema(attributes, entityName),
  data,
});

describe("Step 5: Cross-Reference Cleanup", () => {
  it("should return entities unchanged when no errors provided", () => {
    const entities = [
      createMockDeduplicatedEntity("application", [{ name: "server_id", type: "string", rel_entity: "server" }], {
        app1: { server_id: "server-1" },
      }),
    ];

    const result = validateCrossReferences(entities);

    expect(result.cleanedEntities).toEqual(entities);
    expect(result.crossReferenceErrors).toHaveLength(0);
  });

  it("should remove entities with cross-reference errors", () => {
    const entities = [
      createMockDeduplicatedEntity("application", [{ name: "server_id", type: "string", rel_entity: "server" }], {
        app1: { server_id: "server-1" },
        app2: { server_id: "server-2" },
      }),
    ];

    const crossReferenceErrors = [
      {
        entityName: "application",
        uniqueKey: "app1",
        attributeName: "server_id",
        value: "server-1",
        crossReferenceAttributeName: "server_id",
        crossRefencedEntityName: "server",
        message: "server with unique key server-1 does not exist",
      },
    ];

    const result = validateCrossReferences(entities, crossReferenceErrors);

    expect(Object.keys(result.cleanedEntities[0].data)).toEqual(["app2"]);
    expect(result.crossReferenceErrors).toEqual(crossReferenceErrors);
  });

  it("should remove multiple entities with errors", () => {
    const entities = [
      createMockDeduplicatedEntity("application", [{ name: "server_id", type: "string", rel_entity: "server" }], {
        app1: { server_id: "server-1" },
        app2: { server_id: "server-2" },
        app3: { server_id: "server-3" },
      }),
    ];

    const crossReferenceErrors = [
      {
        entityName: "application",
        uniqueKey: "app1",
        attributeName: "server_id",
        value: "server-1",
        crossReferenceAttributeName: "server_id",
        crossRefencedEntityName: "server",
        message: "server with unique key server-1 does not exist",
      },
      {
        entityName: "application",
        uniqueKey: "app3",
        attributeName: "server_id",
        value: "server-3",
        crossReferenceAttributeName: "server_id",
        crossRefencedEntityName: "server",
        message: "server with unique key server-3 does not exist",
      },
    ];

    const result = validateCrossReferences(entities, crossReferenceErrors);

    expect(Object.keys(result.cleanedEntities[0].data)).toEqual(["app2"]);
    expect(result.crossReferenceErrors).toEqual(crossReferenceErrors);
  });
});
