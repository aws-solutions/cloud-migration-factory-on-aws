import { createBidirectionalReferences } from "./step2-bidirectional-references";
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

describe("Step 2: Bidirectional Cross-References", () => {
  it("should create bidirectional reference for single cross-reference", () => {
    const entities = {
      server: createMockDeduplicatedEntity(
        "server",
        [
          { name: "name", type: "string" },
          { name: "app_id", type: "string", rel_entity: "application" },
        ],
        { "server-1": { name: "Web Server", app_id: "app-1" } }
      ),
      application: createMockDeduplicatedEntity(
        "application",
        [
          { name: "name", type: "string" },
          { name: "server_id", type: "string", rel_entity: "server" },
        ],
        { "app-1": { name: "Web App" } }
      ),
    };

    const result = createBidirectionalReferences(entities);

    expect(result.entities.application.data["app-1"]?.server_id).toBe("server-1");
    expect(result.errors).toHaveLength(0);
  });

  it("should create bidirectional reference for list of cross-references", () => {
    const entities = {
      server: createMockDeduplicatedEntity(
        "server",
        [
          { name: "name", type: "string" },
          { name: "app_ids", type: "multivalue-string", rel_entity: "application", listMultiSelect: true },
        ],
        { "server-1": { name: "Web Server", app_ids: ["app-1", "app-2"] } }
      ),
      application: createMockDeduplicatedEntity(
        "application",
        [
          { name: "name", type: "string" },
          { name: "server_id", type: "string", rel_entity: "server" },
        ],
        {
          "app-1": { name: "Web App" },
          "app-2": { name: "API App" },
        }
      ),
    };

    const result = createBidirectionalReferences(entities);

    expect(result.entities.application.data["app-1"]?.server_id).toBe("server-1");
    expect(result.entities.application.data["app-2"]?.server_id).toBe("server-1");
    expect(result.errors).toHaveLength(0);
  });

  it("should create error when single cross-reference attribute has conflicting value", () => {
    const entities = {
      application: createMockDeduplicatedEntity(
        "application",
        [
          { name: "name", type: "string" },
          { name: "server_id", type: "string", rel_entity: "server" },
        ],
        { "app-1": { name: "Web App", server_id: "server-1" } }
      ),
      server: createMockDeduplicatedEntity(
        "server",
        [
          { name: "name", type: "string" },
          { name: "primary_app_id", type: "string", rel_entity: "application" },
        ],
        { "server-1": { name: "Web Server", primary_app_id: "app-2" } }
      ),
    };

    const result = createBidirectionalReferences(entities);

    expect(result.errors).toHaveLength(1);
    expect(result.errors[0]).toMatchObject({
      entityName: "server",
      uniqueKey: "server-1",
      attributeName: "primary_app_id",
      value: "app-2",
    });
    expect(result.errors[0].message).toContain(
      "Cannot create bidirectional reference: attribute 'primary_app_id' already has value 'app-2', cannot set to 'app-1'"
    );
  });

  it("should not create duplicate when target list already contains reference", () => {
    const entities = {
      application: createMockDeduplicatedEntity(
        "application",
        [
          { name: "name", type: "string" },
          { name: "server_id", type: "string", rel_entity: "server" },
        ],
        { "app-1": { name: "Web App", server_id: "server-1" } }
      ),
      server: createMockDeduplicatedEntity(
        "server",
        [
          { name: "name", type: "string" },
          { name: "app_ids", type: "multivalue-string", rel_entity: "application", listMultiSelect: true },
        ],
        { "server-1": { name: "Web Server", app_ids: ["app-1", "app-2"] } }
      ),
    };

    const result = createBidirectionalReferences(entities);

    expect(result.entities.server.data["server-1"]?.app_ids).toEqual(["app-1", "app-2"]);
    expect(result.errors).toHaveLength(0);
  });
});
