/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import dagre from "@dagrejs/dagre";
import { Edge, Node, Position } from "@xyflow/react";

import { EntitySchema } from "../../models";
import { Schemas } from "../../utils/Constants";

/**
 * Metadata for diagram nodes containing entity information and relationship data.
 */
export type NodeMetadata = {
  /** The entity data object */
  readonly entity: Record<string, unknown>;
  /** Schema definition for the entity */
  readonly schema: EntitySchema;
  /** Whether the node is currently selected */
  readonly selected?: boolean;
  /** Whether the entity has multiple parent entities */
  readonly hasMultipleParents?: boolean;
  /** Schema definition for parent entities */
  readonly parentSchema?: EntitySchema;
  /** List of parent entity objects */
  readonly parentEntities?: Record<string, unknown>[];
  /** Tooltip position */
  readonly tooltipPosition?: Position;
};

/**
 * Extended Node type that includes metadata and styling information.
 */
export type NodeWithMetadata = Node<NodeMetadata, keyof typeof nodeStyleConfig>;

/**
 * Result type for layout operations containing positioned nodes and edges.
 */
export type LayoutResult = { nodes: NodeWithMetadata[]; edges: Edge[] };

/**
 * Creates a unique node ID by combining entity type and ID.
 *
 * @param type - The entity type (e.g., "wave", "application")
 * @param id - The entity's unique identifier
 * @returns A string ID in the format "type-id"
 */
export const createNodeId = (type: string, id: string): string => `${type}-${id}`;

/**
 * Creates a unique edge ID by combining parent and child node IDs.
 *
 * @param parentNodeId - The ID of the parent node
 * @param currentNodeId - The ID of the child node
 * @returns A string ID in the format "parentNodeId-currentNodeId"
 */
export const createEdgeId = (parentNodeId: string, currentNodeId: string): string => `${parentNodeId}-${currentNodeId}`;

/**
 * Style configuration for different node types with background and border colors.
 */
export const nodeStyleConfig: Readonly<Record<string, { readonly background: string; readonly border: string }>> = {
  [Schemas.Wave.name]: {
    background: "#ffcce3",
    border: "#ff66b2",
  },
  [Schemas.MoveGroup.name]: {
    background: "#cce3ff",
    border: "#6699ff",
  },
  [Schemas.Application.name]: {
    background: "#e6ffcc",
    border: "#80ff00",
  },
  [Schemas.Database.name]: {
    background: "#fff2cc",
    border: "#ffcc00",
  },
  [Schemas.Server.name]: {
    background: "#e0e0e0",
    border: "#999999",
  },
};

/**
 * Extracts display data from an entity, separating the name from other attributes.
 * Handles relationship data and formats values for display.
 *
 * @param schema - Schema definition for the entity
 * @param entity - The entity data object
 * @param parentSchema - Optional schema definition for parent entities
 * @param parentEntities - Optional list of parent entity objects
 * @returns Object containing the entity name and formatted attribute values
 */
export const extractEntityData = (
  schema: EntitySchema,
  entity: Record<string, unknown>,
  parentSchema?: EntitySchema,
  parentEntities?: Record<string, unknown>[]
): { readonly name: string; readonly others: Record<string, string | number> } => {
  // Extract entity name and other non-relationship attributes
  const nameAttr = `${schema.schema_name}_name`;
  const name = entity[nameAttr] as string;
  const others: Record<string, string | number> = {};
  schema.attributes.forEach((attr) => {
    const val = entity[attr.name];
    if (val === undefined || val === null) return;
    if (["relationship", "multivalue-relationship"].includes(attr.type)) return;
    if (
      attr.name === nameAttr ||
      // Id/Ids of other entity but type is not relationship
      (!attr.name.startsWith(schema.schema_name) && (attr.name.endsWith("_id") || attr.name.endsWith("_ids")))
    )
      return;
    others[attr.description] = ["string", "number"].includes(typeof val)
      ? (val as string | number)
      : JSON.stringify(val);
  });

  // Append the "multivalue-relationship" attribute with lookup value if more than one
  // If only one then it is reflected by the edge
  const multivalueRelationshipAttr = schema.attributes.find(
    (attr) =>
      ["multivalue-string", "multivalue-relationship"].includes(attr.type) &&
      attr.rel_entity === parentSchema?.schema_name
  );
  const multivalueRelationship = multivalueRelationshipAttr && entity[multivalueRelationshipAttr.name];
  if (
    multivalueRelationshipAttr &&
    Array.isArray(multivalueRelationship) &&
    multivalueRelationship.length > 1 &&
    parentEntities
  ) {
    const parents = multivalueRelationship
      .map((id) => parentEntities.find((p) => p[`${parentSchema?.schema_name}_id`] === id))
      .filter((p) => !!p)
      .map((p) => p[`${parentSchema?.schema_name}_name`]);

    others[multivalueRelationshipAttr.description] = parents.join(", ");
  }
  return { name, others };
};

/**
 * Creates a hierarchical layout for nodes and edges using the Dagre library.
 * Positions nodes in a left-to-right flow with appropriate spacing.
 *
 * @param nodes - List of nodes to position
 * @param edges - List of edges connecting the nodes
 * @returns Layout result with positioned nodes and edges
 */
export const createDagreLayout = (nodes: NodeWithMetadata[], edges: Edge[]): LayoutResult => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 180;
  const nodeHeight = 50;

  dagreGraph.setGraph({
    rankdir: "LR",
    nodesep: 30,
    ranksep: 200,
    edgesep: 50,
    marginx: 50,
    marginy: 50,
  });

  // Add nodes to dagre
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  // Add edges to dagre
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Calculate layout
  dagre.layout(dagreGraph);

  // Transform the nodes
  const layoutedNodes = nodes.map((node) => {
    const dagreNode = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: dagreNode.x - nodeWidth / 2,
        y: dagreNode.y - nodeHeight / 2,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    };
  });

  return {
    nodes: layoutedNodes,
    edges,
  };
};

/**
 * Converts a snake_case string to PascalCase.
 *
 * @param str - The snake_case string to convert
 * @returns The string in PascalCase format
 */
export const snakeToPascalCase = (str: string): string =>
  str
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join("");
