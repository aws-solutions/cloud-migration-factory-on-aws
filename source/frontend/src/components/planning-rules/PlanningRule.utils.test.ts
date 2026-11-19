/* eslint-disable @typescript-eslint/no-explicit-any */
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { wpmSchemas, customAssetSchemas } from "../../../test_data";
import { RuleValidationError, validateGroupingRule, validatePrioritizingRule } from "./PlanningRule.utils";

const schemas = { ...wpmSchemas(), ...customAssetSchemas() };

const groupingRule = (): any => ({
  rule_type: "GROUPING_INCLUSIVE",
  relationships: [
    {
      asset_key: "server_ids",
      asset_type: "app",
    },
  ],
  rule_name: "Apps sharing Servers",
  status: "ENABLED",
});

const sortingRule = (): any => ({
  rule_type: "PRIORITIZING",
  sub_type: "SORTING",
  asset_type: "app",
  attr_key: "app_owner",
  rule_description: "Sort applications by department priority",
  rule_name: "sort-by-owner",
  sort_by_value: ["IT", "marketing", "sales", "finance", "security"],
  sort_level: 3,
  sort_order: "ASC",
  status: "DISABLED",
});

const scoringRule = (): any => ({
  rule_type: "PRIORITIZING",
  sub_type: "SCORING",
  asset_type: "server",
  attr_key: "storage_size",
  rule_description: "Score applications based on server storage size",
  rule_name: "score-by-server_storage_size",
  scoring_criteria: [
    {
      complexity_score: 20,
      upper_bound: 200,
    },
  ],
  status: "ENABLED",
});

const captureValidationErrors = (fn: () => unknown) => {
  try {
    fn();
    fail("Expected to throw RuleValidationError");
  } catch (error) {
    expect(error).toBeInstanceOf(RuleValidationError);
    return error instanceof RuleValidationError ? error.errors : undefined;
  }
};

describe("validateGroupingRule", () => {
  it("throws error for required properties", () => {
    const errors = captureValidationErrors(() => {
      validateGroupingRule({}, schemas);
    });
    expect(errors).toMatchSnapshot();
  });

  it("throws error for additional properties", () => {
    const errors = captureValidationErrors(() => {
      const rule = groupingRule();
      rule.additional = true;
      validateGroupingRule(rule, schemas);
    });
    expect(errors).toMatchSnapshot();
  });

  it("throws error for nested required properties", () => {
    const errors = captureValidationErrors(() => {
      const rule = groupingRule();
      rule.relationships[0] = {};
      validateGroupingRule(rule, schemas);
    });
    expect(errors).toMatchSnapshot();
  });

  it("throws error for nested additional properties", () => {
    const errors = captureValidationErrors(() => {
      const rule = groupingRule();
      rule.relationships[0].additional = true;
      validateGroupingRule(rule, schemas);
    });
    expect(errors).toMatchSnapshot();
  });

  it("throws error for empty relationships", () => {
    const errors = captureValidationErrors(() => {
      const rule = groupingRule();
      rule.relationships = [];
      validateGroupingRule(rule, schemas);
    });
    expect(errors).toMatchSnapshot();
  });

  it("throws error for invalid asset_type", () => {
    const errors = captureValidationErrors(() => {
      const rule = groupingRule();
      rule.relationships[0].asset_type = "invalid";
      validateGroupingRule(rule, schemas);
    });
    expect(errors).toMatchSnapshot();
  });

  it("throws error for invalid asset_key", () => {
    const errors = captureValidationErrors(() => {
      const rule = groupingRule();
      rule.relationships[0].asset_key = "invalid";
      validateGroupingRule(rule, schemas);
    });
    expect(errors).toMatchSnapshot();
  });

  it("throws error for invalid asset_key for custom asset", () => {
    const errors = captureValidationErrors(() => {
      const rule = groupingRule();
      rule.relationships[0].asset_type = "storage";
      rule.relationships[0].asset_key = "invalid";
      validateGroupingRule(rule, schemas);
    });
    expect(errors).toMatchSnapshot();
  });

  it("not throws for valid rule", () => {
    const rule = groupingRule();
    expect(() => validateGroupingRule(rule, schemas)).not.toThrow();
  });

  it("not throws for valid rule for custom asset", () => {
    const rule = groupingRule();
    rule.relationships[0].asset_type = "storage";
    rule.relationships[0].asset_key = "storage_type";
    expect(() => validateGroupingRule(rule, schemas)).not.toThrow();
  });
});

describe("validatePrioritizingRule", () => {
  it("throws error for required properties", () => {
    const errors = captureValidationErrors(() => {
      validatePrioritizingRule({}, schemas);
    });
    expect(errors).toMatchSnapshot();
  });

  describe("sorting rule", () => {
    it("throws error for additional properties", () => {
      const errors = captureValidationErrors(() => {
        const rule = sortingRule();
        rule.additional = true;
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error conditional requirement properties", () => {
      const errors = captureValidationErrors(() => {
        validatePrioritizingRule({ rule_type: "PRIORITIZING", sub_type: "SORTING" }, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for invalid asset_type", () => {
      const errors = captureValidationErrors(() => {
        const rule = sortingRule();
        rule.asset_type = "invalid";
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for invalid asset_key", () => {
      const errors = captureValidationErrors(() => {
        const rule = sortingRule();
        rule.attr_key = "invalid";
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for invalid asset_key for custom asset", () => {
      const errors = captureValidationErrors(() => {
        const rule = sortingRule();
        rule.asset_type = "app_group";
        rule.attr_key = "invalid";
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for relationship asset_key for custom asset", () => {
      const errors = captureValidationErrors(() => {
        const rule = sortingRule();
        rule.asset_type = "storage";
        rule.attr_key = "app_ids";
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("not throws for valid rule", () => {
      const rule = sortingRule();
      expect(() => validatePrioritizingRule(rule, schemas)).not.toThrow();
    });

    it("not throws for valid rule for custom asset", () => {
      const rule = sortingRule();
      rule.asset_type = "app_group";
      rule.attr_key = "priority";
      expect(() => validatePrioritizingRule(rule, schemas)).not.toThrow();
    });
  });

  describe("scoring rule", () => {
    it("throws error for additional properties", () => {
      const errors = captureValidationErrors(() => {
        const rule = scoringRule();
        rule.additional = true;
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error conditional requirement properties", () => {
      const errors = captureValidationErrors(() => {
        validatePrioritizingRule({ rule_type: "PRIORITIZING", sub_type: "SCORING" }, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for invalid asset_type", () => {
      const errors = captureValidationErrors(() => {
        const rule = scoringRule();
        rule.asset_type = "invalid";
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for invalid asset_key", () => {
      const errors = captureValidationErrors(() => {
        const rule = scoringRule();
        rule.attr_key = "invalid";
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for invalid asset_key for custom asset", () => {
      const errors = captureValidationErrors(() => {
        const rule = scoringRule();
        rule.asset_type = "app_group";
        rule.attr_key = "invalid";
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for relationship asset_key for custom asset", () => {
      const errors = captureValidationErrors(() => {
        const rule = scoringRule();
        rule.asset_type = "storage";
        rule.attr_key = "app_ids";
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for nested required properties", () => {
      const errors = captureValidationErrors(() => {
        const rule = scoringRule();
        rule.scoring_criteria[0] = {};
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for nested additional properties", () => {
      const errors = captureValidationErrors(() => {
        const rule = scoringRule();
        rule.scoring_criteria[0].additional = true;
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("throws error for empty scoring_criteria", () => {
      const errors = captureValidationErrors(() => {
        const rule = scoringRule();
        rule.scoring_criteria = [];
        validatePrioritizingRule(rule, schemas);
      });
      expect(errors).toMatchSnapshot();
    });

    it("not throws for valid rule", () => {
      const rule = scoringRule();
      expect(() => validatePrioritizingRule(rule, schemas)).not.toThrow();
    });

    it("not throws for valid rule for custom asset", () => {
      const rule = scoringRule();
      rule.asset_type = "app_group";
      rule.attr_key = "priority";
      expect(() => validatePrioritizingRule(rule, schemas)).not.toThrow();
    });
  });
});
