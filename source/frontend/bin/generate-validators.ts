import fs from "fs";

import Ajv, { _, CodeKeywordDefinition } from "ajv";
import standaloneCode from "ajv/dist/standalone";

const ASSET_TYPE_KEYWORD = "assetType";
const ASSET_KEY_KEYWORD = "assetKey";

const assetTypeKeywordDef: CodeKeywordDefinition = {
  keyword: ASSET_TYPE_KEYWORD,
  type: "string",
  $data: true,
  code(ctx) {
    const { gen, data } = ctx;
    const allowedValues = gen.const("schemaNames", _`this.schemaNames`);
    gen.if(_`!${allowedValues}.includes(${data})`, () => {
      ctx.error();
    });
  },
  error: {
    message: "must be equal to one of the allowed values",
    // Similar code here - can't find a way to return the error params in code function
    params(ctx) {
      const { gen } = ctx;
      const allowedValues = gen.const("schemaNames", _`this.schemaNames`);
      return _`{ allowedValues: ${allowedValues} }`;
    },
  },
} as const;

const assetKeyKeywordDef: CodeKeywordDefinition = {
  keyword: ASSET_KEY_KEYWORD,
  type: "string",
  metaSchema: {
    type: "string",
    enum: ["all", "non-relationship"],
  },
  code(ctx) {
    const { gen, schema, data, it } = ctx;
    const schemas = gen.const("schemas", _`this.schemas`);
    const allowedValues = gen.const(
      "allowedValues",
      _`(${schemas}[${it.parentData}.asset_type]?.attributes)
        ?.filter(attr => ${
          schema === "non-relationship" ? _`!["relationship", "multivalue-relationship"].includes(attr.type)` : _`true`
        })
        ?.map(attr => attr.name)`
    );
    gen.if(_`${allowedValues} !== undefined && !${allowedValues}.includes(${data})`, () => {
      ctx.error();
    });
  },
  error: {
    message: "must be equal to one of the allowed values",
    // Similar code here - can't find a way to return the error params in code function
    params(ctx) {
      const { gen, schema, it } = ctx;
      const schemas = gen.const("schemas", _`this.schemas`);
      const allowedValues = gen.const(
        "allowedValues",
        _`(${schemas}[${it.parentData}.asset_type]?.attributes || [])
        .filter(attr => ${
          schema === "non-relationship" ? _`!["relationship", "multivalue-relationship"].includes(attr.type)` : _`true`
        })
        .map(attr => attr.name)`
      );
      return _`{ allowedValues: ${allowedValues} }`;
    },
  },
} as const;

// Schema for basic properties of Prioritizing rule
const PRIORITIZING_RULE_SCHEMA_BASE_PROPERTIES = {
  rule_type: { type: "string", enum: ["PRIORITIZING"] },
  rule_name: { type: "string" },
  rule_description: { type: "string", nullable: true },
  sub_type: { type: "string", enum: ["SCORING", "SORTING"] },
  status: { type: "string", enum: ["ENABLED", "DISABLED"] },
  asset_type: { type: "string", [ASSET_TYPE_KEYWORD]: true },
  attr_key: { type: "string", [ASSET_KEY_KEYWORD]: "non-relationship" },
} as const;

// Basic properties of Prioritizing rule without schema, used by if/then/else
const PRIORITIZING_RULE_SCHEMA_BASE_PROPERTIES_WITHOUT_SCHEMA = Object.fromEntries(
  Object.keys(PRIORITIZING_RULE_SCHEMA_BASE_PROPERTIES).map((key) => [key, {}])
);

const PRIORITIZING_RULE_SCHEMA = {
  $id: "#/definitions/PRIORITIZING_RULE",
  type: "object",
  properties: PRIORITIZING_RULE_SCHEMA_BASE_PROPERTIES,
  required: ["rule_type", "rule_name", "sub_type", "status", "asset_type", "attr_key"],
  if: {
    required: ["sub_type"],
    properties: { sub_type: { const: "SORTING" } },
  },
  then: {
    properties: {
      ...PRIORITIZING_RULE_SCHEMA_BASE_PROPERTIES_WITHOUT_SCHEMA,
      sort_order: { type: "string", enum: ["ASC", "DSC"] },
      sort_level: { type: "number" },
      sort_by_value: { type: "array", items: { type: "string" } },
    },
    required: ["sort_order", "sort_level"],
    additionalProperties: false,
  },
  else: {
    if: {
      required: ["sub_type"],
      properties: { sub_type: { const: "SCORING" } },
    },
    then: {
      properties: {
        ...PRIORITIZING_RULE_SCHEMA_BASE_PROPERTIES_WITHOUT_SCHEMA,
        scoring_criteria: {
          type: "array",
          minItems: 1,
          items: {
            type: "object",
            properties: {
              value: { type: "string" },
              lower_bound: { type: "number" },
              upper_bound: { type: "number" },
              name: { type: "string" },
              pattern: { type: "string" },
              complexity_score: { type: "number", minimum: 0, maximum: 100 },
            },
            required: ["complexity_score"],
            additionalProperties: false,
          },
        },
      },
      required: ["scoring_criteria"],
      additionalProperties: false,
    },
  },
} as const;

// JSON schema for grouping rule
const GROUPING_RULE_SCHEMA = {
  $id: "#/definitions/GROUPING_RULE",
  type: "object",
  properties: {
    rule_type: {
      type: "string",
      enum: ["GROUPING_INCLUSIVE", "GROUPING_EXCLUSIVE"],
    },
    rule_name: { type: "string" },
    rule_description: { type: "string", nullable: true },
    relationships: {
      type: "array",
      items: {
        type: "object",
        properties: {
          asset_type: {
            type: "string",
            [ASSET_TYPE_KEYWORD]: true,
          },
          asset_key: { type: "string", [ASSET_KEY_KEYWORD]: "all" },
        },
        required: ["asset_type", "asset_key"],
        additionalProperties: false,
      },
      minItems: 1,
    },
    status: { type: "string", enum: ["ENABLED", "DISABLED"] },
  },
  required: ["rule_type", "rule_name", "relationships", "status"],
  additionalProperties: false,
} as const;

const ajv = new Ajv({
  schemas: [PRIORITIZING_RULE_SCHEMA, GROUPING_RULE_SCHEMA],
  code: { source: true, esm: true },
  allErrors: true,
  passContext: true,
});

ajv.addKeyword(assetTypeKeywordDef);
ajv.addKeyword(assetKeyKeywordDef);

const moduleCode = standaloneCode(ajv, {
  prioritizingRuleValidate: "#/definitions/PRIORITIZING_RULE",
  groupingRuleValidate: "#/definitions/GROUPING_RULE",
});

fs.writeFileSync("vendor/validators.mjs", moduleCode);
