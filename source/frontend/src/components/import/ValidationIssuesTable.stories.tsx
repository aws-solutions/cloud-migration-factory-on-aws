/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import type { Meta, StoryObj } from "@storybook/react";

import { DataValidationResult, EntityDependencyGraph } from "../data-validation";
import { wpmSchemas } from "../../../test_data";
import ValidationResultsTable from "./ValidationIssuesTable";

const meta: Meta<typeof ValidationResultsTable> = {
  title: "ValidationResultsTable",
  component: ValidationResultsTable,
  parameters: {
    layout: "top",
    docs: {
      description: {
        component: "A UI component that displays validation errors and warnings from data imports in a table format.",
      },
    },
  },
  tags: ["autodocs"],
};

export default meta;

type Story = StoryObj<typeof meta>;

// Create sample validation results with different types of errors and warnings
const createSampleValidationResult = (options: {
  withErrors?: boolean;
  withWarnings?: boolean;
  withMultipleIssues?: boolean;
  entityCount?: number;
}): DataValidationResult => {
  const { withErrors = true, withWarnings = true, withMultipleIssues = false, entityCount = 3 } = options;

  // Create empty dependency graph
  const dependencyGraph: EntityDependencyGraph = {
    dependencies: {},
  };

  // Create sample entities
  const entities = Array.from({ length: entityCount }).map((_, index) => ({
    entityName: `entity${index + 1}`,
    schema: {
      schema_name: `entity${index + 1}`,
      schema_type: "entity",
      attributes: [],
    },
    data: {},
  }));

  // Create sample validation issues
  const issues = {
    deduplicationErrors: withErrors
      ? [
          {
            entityName: "server",
            uniqueKey: "server1",
            attributeName: "hostname",
            value: "server1.example.com",
            conflictingValues: ["server1-new.example.com"],
            message:
              "Conflicting values for required attribute 'hostname': 'server1.example.com' vs 'server1-new.example.com'",
          },
        ]
      : [],
    deduplicationWarnings: withWarnings
      ? [
          {
            entityName: "server",
            uniqueKey: "server2",
            attributeName: "description",
            value: "Web server",
            conflictingValues: ["Primary web server"],
            message: "Conflicting values for optional attribute 'description': 'Web server' vs 'Primary web server'",
          },
        ]
      : [],
    requiredAttributeErrors: withErrors
      ? [
          {
            entityName: "application",
            uniqueKey: "app1",
            attributeName: "name",
            value: "",
            message: "Required attribute 'name' is missing or empty",
          },
        ]
      : [],
    validationErrors: withErrors
      ? [
          {
            entityName: "database",
            uniqueKey: "db1",
            attributeName: "port",
            value: "invalid",
            message: "Expected type 'number' but got 'string'",
          },
          ...(withMultipleIssues
            ? [
                {
                  entityName: "database",
                  uniqueKey: "db1",
                  attributeName: "engine",
                  value: "",
                  message: "Required attribute 'engine' is missing or empty",
                },
              ]
            : []),
        ]
      : [],
    validationWarnings: withWarnings
      ? [
          {
            entityName: "server",
            uniqueKey: "server3",
            attributeName: "ip_address",
            value: "invalid-ip",
            message: "Value invalid-ip does not match required pattern: ^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$",
          },
          ...(withMultipleIssues
            ? [
                {
                  entityName: "server",
                  uniqueKey: "server3",
                  attributeName: "environment",
                  value: "unknown",
                  message: "Value 'unknown' is not in the allowed list: ['dev', 'test', 'prod']",
                },
              ]
            : []),
        ]
      : [],
    crossReferenceErrors: withErrors
      ? [
          {
            entityName: "server",
            uniqueKey: "server4",
            attributeName: "application_id",
            value: "app99",
            crossReferenceAttributeName: "application_id",
            crossRefencedEntityName: "application",
            message: "application with unique key app99 does not exist",
          },
        ]
      : [],
  };

  return {
    entities,
    issues,
    dependencyGraph,
    entitiesToUpdate: {},
    backendValidationRequests: [],
  };
};

// Default story with both errors and warnings
export const Default: Story = {
  args: {
    validationResult: createSampleValidationResult({
      withErrors: true,
      withWarnings: true,
      withMultipleIssues: true,
    }),
  },
};

// Story with only errors
export const ErrorsOnly: Story = {
  args: {
    validationResult: createSampleValidationResult({
      withErrors: true,
      withWarnings: false,
    }),
  },
};

// Story with only warnings
export const WarningsOnly: Story = {
  args: {
    validationResult: createSampleValidationResult({
      withErrors: false,
      withWarnings: true,
    }),
  },
};

// Story with entity filter
export const WithEntityFilter: Story = {
  args: {
    validationResult: createSampleValidationResult({
      withErrors: true,
      withWarnings: true,
    }),
    entityFilter: "server",
  },
};

// Story with no validation issues
export const NoIssues: Story = {
  args: {
    validationResult: createSampleValidationResult({
      withErrors: false,
      withWarnings: false,
    }),
  },
};

// Story with many validation issues to demonstrate pagination
export const WithPagination: Story = {
  args: {
    validationResult: (() => {
      const result = createSampleValidationResult({
        withErrors: true,
        withWarnings: true,
        entityCount: 5,
      });

      // Add more validation errors to demonstrate pagination
      for (let i = 0; i < 15; i++) {
        result.issues.validationErrors.push({
          entityName: `entity${(i % 5) + 1}`,
          uniqueKey: `item${i + 1}`,
          attributeName: `field${i + 1}`,
          value: `invalid${i + 1}`,
          message: `Validation error ${i + 1}`,
        });
      }

      return result;
    })(),
  },
};

// Story with single issues per entity/key (no grouping)
export const SingleIssuesPerEntity: Story = {
  args: {
    validationResult: createSampleValidationResult({
      withErrors: true,
      withWarnings: true,
      withMultipleIssues: false,
    }),
  },
};

const schemas = wpmSchemas();
// Story with multiple issues for the same entity/key (with grouping)
export const MultipleIssuesPerEntity: Story = {
  render: () => {
    const result = createSampleValidationResult({
      withErrors: true,
      withWarnings: true,
    });

    // Add multiple issues for the same entity/key
    const entityName = "server";
    const uniqueKey = "server-multi";

    // Add 3 different issues for the same entity/key
    result.issues.validationErrors.push(
      {
        entityName,
        uniqueKey,
        attributeName: "hostname",
        value: "",
        message: "Required attribute 'hostname' is missing",
      },
      {
        entityName,
        uniqueKey,
        attributeName: "ip_address",
        value: "invalid",
        message: "Invalid IP address format",
      },
      {
        entityName,
        uniqueKey,
        attributeName: "os_type",
        value: "unknown",
        message: "Invalid OS type",
      }
    );

    return <ValidationResultsTable schemas={schemas} validationIssues={result.issues} />;
  },
};
