/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import {
  applyEdgeChanges,
  applyNodeChanges,
  Controls,
  Edge,
  EdgeChange,
  Handle,
  MiniMap,
  Node,
  NodeChange,
  NodeProps,
  NodeToolbar,
  Position,
  ReactFlow,
  Viewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Spinner } from "@cloudscape-design/components";

import { Application, Database, EntitySchema, MoveGroup, Server, Wave } from "../../models";
import { Schemas } from "../../utils/Constants";
import {
  createDagreLayout,
  createEdgeId,
  createNodeId,
  extractEntityData,
  nodeStyleConfig,
  NodeWithMetadata,
  snakeToPascalCase,
} from "./ERDiagram.util";

// CloudScape sticky table header z-index
const CLOUDSCAPE_STICKY_TABLE_HEADER_Z_INDEX = 800;
// ReactFlow wrapper z-index should be higher so that the tooltip is not covered by the sticky table header
const REACT_FLOW_Z_INDEX = CLOUDSCAPE_STICKY_TABLE_HEADER_Z_INDEX + 1;
// ReactFlow Legend should be higher than tooltip
const REACT_FLOW_LEGEND_Z_INDEX = REACT_FLOW_Z_INDEX + 1;

// An internal component which shows a legend in the bottom-right corner of the diagram
// based on the schema names provided using the matching styles
const Legend = ({ schemaNames }: { schemaNames: string[] }) => {
  const legendStyle: React.CSSProperties = {
    position: "absolute",
    bottom: "20px",
    right: "20px",
    background: "white",
    padding: "0.4rem",
    fontSize: "0.75rem",
    borderRadius: "5px",
    border: "1px solid #ccc",
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    opacity: 0.75,
    zIndex: REACT_FLOW_LEGEND_Z_INDEX,
  };

  const legendItemStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  };

  const legendBoxStyle = (color: string, borderColor: string): React.CSSProperties => ({
    width: "16px",
    height: "16px",
    background: color,
    border: `1px solid ${borderColor}`,
    borderRadius: "3px",
  });

  return (
    <div style={legendStyle}>
      {Object.entries(nodeStyleConfig).map(([type, style]) =>
        schemaNames.includes(type) ? (
          <div key={type} style={legendItemStyle}>
            <div style={legendBoxStyle(style.background, style.border)} />
            <span>{type}</span>
          </div>
        ) : undefined
      )}
    </div>
  );
};

/**
 * Props interface for the ERDiagram component.
 * Defines the data required to render the entity relationship diagram.
 */
export interface ERDiagramProps {
  /** Schema definitions for all entity types */
  readonly schemas: Record<string, EntitySchema>;
  /** Optional list of application entities to display */
  readonly applications?: Application[];
  /** Optional list of database entities to display */
  readonly databases?: Database[];
  /** Optional list of server entities to display */
  readonly servers?: Server[];
  /** Optional list of move group entities to display */
  readonly moveGroups?: MoveGroup[];
  /** Optional list of wave entities to display */
  readonly waves?: Wave[];
  /** Optional list of selected waves to filter the diagram */
  readonly selectedWaves?: Wave[];
  /** Optional list of selected move groups to filter the diagram */
  readonly selectedMoveGroups?: MoveGroup[];
  /** Optional isLoading flag */
  readonly isLoading?: boolean;
}

const edgeType = "default";
const initialPosition: Readonly<Node["position"]> = { x: 0, y: 0 };

// An internal base Node component that renders the entity node based on the node metadata
// with tooltip and bold the node border and text if the node has multiple parents
const BaseNode = ({
  data: { selected, hasMultipleParents, entity, schema, parentEntities, parentSchema, tooltipPosition },
  style,
}: NodeProps<NodeWithMetadata> & {
  readonly style: React.CSSProperties;
}) => {
  // Bold text and border if the node has multiple parents, some of which may not shown due to filtering
  const nodeStyle = React.useMemo(
    () => ({
      ...style,
      borderWidth: hasMultipleParents ? "4px" : "1px", // Thicken border for multiple
      fontWeight: hasMultipleParents ? "bold" : "normal", // Bold text for multiple
    }),
    [style, hasMultipleParents]
  );

  const elementStyles = React.useMemo<Record<string, React.CSSProperties>>(
    () => ({
      tooltip: {
        background: "white",
        border: "1px solid #ccc",
        borderRadius: "5px",
        padding: "8px",
        fontSize: "0.7rem",
        boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
        minWidth: "180px",
        maxWidth: "250px",
      },
      dl: {
        margin: 0,
        padding: 0,
      },
      dt: {
        fontWeight: "600",
        color: "#666",
        marginTop: "3px",
        fontSize: "0.7rem",
      },
      dd: {
        margin: "0 0 0 0",
        color: "#333",
        wordWrap: "break-word",
      },
    }),
    []
  );

  const { name, others } = extractEntityData(schema, entity, parentSchema, parentEntities);

  return (
    <>
      <NodeToolbar isVisible={selected} position={tooltipPosition} style={{ position: "fixed" }}>
        <div style={elementStyles.tooltip}>
          <dl style={elementStyles.dl}>
            {Object.entries(others).map(([key, value]) => (
              <React.Fragment key={key}>
                <dt style={elementStyles.dt}>{key}</dt>
                <dd style={elementStyles.dd}>{value}</dd>
              </React.Fragment>
            ))}
          </dl>
        </div>
      </NodeToolbar>
      <div style={nodeStyle}>
        <Handle type="target" position={Position.Left} />
        <div>{name}</div>
        <Handle type="source" position={Position.Right} />
      </div>
    </>
  );
};

// An internal function that returns the typed BaseNode
const createCustomNode = (type: keyof typeof nodeStyleConfig) => {
  const CustomNode = (props: NodeProps<NodeWithMetadata>) => (
    <BaseNode
      {...props}
      style={{
        background: nodeStyleConfig[type].background,
        border: `1px solid ${nodeStyleConfig[type].border}`,
        borderRadius: "5px",
        padding: "10px",
        width: 180,
      }}
    />
  );
  CustomNode.displayName = `${snakeToPascalCase(type)}Node`; // Set display name
  return React.memo(CustomNode);
};

const ERDiagram = ({
  schemas,
  applications,
  databases,
  servers,
  moveGroups,
  waves,
  selectedMoveGroups,
  selectedWaves,
  isLoading,
}: ERDiagramProps) => {
  const reactflowRef = React.useRef<HTMLDivElement>(null);
  // Calculate the type of entities for Legend component
  const schemaNamesWithData = React.useMemo(() => {
    const schemaNames = [];
    if (applications?.length) schemaNames.push(Schemas.Application.name);
    if (databases?.length) schemaNames.push(Schemas.Database.name);
    if (servers?.length) schemaNames.push(Schemas.Server.name);
    if (selectedMoveGroups?.length || moveGroups?.length) schemaNames.push(Schemas.MoveGroup.name);
    if (selectedWaves?.length || waves?.length) schemaNames.push(Schemas.Wave.name);
    return schemaNames;
  }, [
    applications?.length,
    databases?.length,
    servers?.length,
    selectedMoveGroups?.length,
    moveGroups?.length,
    selectedWaves?.length,
    waves?.length,
  ]);

  // Calculate the visible waves, move groups and apps
  const visibleWaves = React.useMemo(() => selectedWaves ?? waves, [selectedWaves, waves]);
  const waveIdSet = React.useMemo(
    () => (visibleWaves ? new Set(visibleWaves?.map((w) => w.wave_id)) : undefined),
    [visibleWaves]
  );

  const visibleMoveGroups = React.useMemo(() => {
    const mgs = selectedMoveGroups ?? moveGroups;
    // if waveIdSet is undefined then no waves provided, return all provided move groups
    return mgs?.filter((mg) => (waveIdSet ? mg.wave_id && waveIdSet.has(mg.wave_id) : true));
  }, [moveGroups, selectedMoveGroups, waveIdSet]);

  // Return a set of move_group_id, or undefined if move_groups are not provided as prop (e.g. showing ERD of app & assets only)
  const moveGroupIdSet = React.useMemo(
    () => (visibleMoveGroups ? new Set(visibleMoveGroups.map((mg) => mg.move_group_id)) : undefined),
    [visibleMoveGroups]
  );

  const visibleApps = React.useMemo(() => {
    // if moveGroupIdSet is undefined then no move group provided, return all provided apps
    return applications?.filter((app) =>
      moveGroupIdSet ? app.move_group_ids?.some((id) => moveGroupIdSet.has(id)) : true
    );
  }, [applications, moveGroupIdSet]);

  const appIdSet = React.useMemo(() => new Set(visibleApps?.map((app) => app.app_id)), [visibleApps]);

  const belongsToSelection = React.useCallback(
    (entity: Database | Server) => {
      const appIds = entity.app_ids ?? [];
      const belongToApp = appIds.some((id) => appIdSet.has(id));
      // Always true if no move groups provided otherwise only if the asset belongs to the move groups provided
      const belongToGroup = moveGroupIdSet && entity.move_group_id ? moveGroupIdSet.has(entity.move_group_id) : true;
      return belongToApp && belongToGroup;
    },
    [appIdSet, moveGroupIdSet]
  );

  // Memorize the initial nodes and edges with the initial position
  const initialElements = React.useMemo(() => {
    const edges: Edge[] = [];
    const nodes: NodeWithMetadata[] = [];

    visibleWaves?.forEach((wave) => {
      nodes.push({
        id: createNodeId(Schemas.Wave.name, wave.wave_id),
        type: Schemas.Wave.name,
        data: { entity: wave, schema: schemas[Schemas.Wave.name] },
        position: initialPosition,
      });
    });

    // Add Move Group nodes
    visibleMoveGroups?.forEach((moveGroup) => {
      const nodeId = createNodeId(Schemas.MoveGroup.name, moveGroup.move_group_id);
      nodes.push({
        id: nodeId,
        type: Schemas.MoveGroup.name,
        data: { entity: moveGroup, schema: schemas[Schemas.MoveGroup.name] },
        position: initialPosition,
      });

      // Add edge from Wave to MoveGroup
      if (moveGroup.wave_id) {
        const waveNodeId = createNodeId(Schemas.Wave.name, moveGroup.wave_id);
        edges.push({
          id: createEdgeId(waveNodeId, nodeId),
          source: waveNodeId,
          target: nodeId,
          type: edgeType,
        });
      }
    });

    // Add Application nodes
    visibleApps?.forEach((app) => {
      const nodeId = createNodeId(Schemas.Application.name, app.app_id);
      nodes.push({
        id: nodeId,
        type: Schemas.Application.name,
        data: {
          entity: app,
          schema: schemas[Schemas.Application.name],
          parentEntities: moveGroups,
          parentSchema: schemas[Schemas.MoveGroup.name],
          hasMultipleParents: moveGroups && (app.move_group_ids?.length ?? 0) > 1,
        },
        position: initialPosition,
      });

      // Add edge from Move Group to App
      app.move_group_ids?.forEach((mgId) => {
        const moveGroupNodeId = createNodeId(Schemas.MoveGroup.name, mgId);
        edges.push({
          id: createEdgeId(moveGroupNodeId, nodeId),
          source: moveGroupNodeId,
          target: nodeId,
          type: edgeType,
        });
      });
    });

    // Add Database nodes
    databases?.forEach((db) => {
      if (belongsToSelection(db)) {
        const nodeId = createNodeId(Schemas.Database.name, db.database_id);
        nodes.push({
          id: nodeId,
          type: Schemas.Database.name,
          data: {
            entity: db,
            schema: schemas[Schemas.Database.name],
            parentEntities: applications,
            parentSchema: schemas[Schemas.Application.name],
            hasMultipleParents: applications && (db.app_ids?.length ?? 0) > 1,
          },
          position: initialPosition,
        });

        // Add edge from App to DB
        const appIds = db.app_ids ?? [];
        appIds.forEach((appId) => {
          const appNodeId = createNodeId(Schemas.Application.name, appId);
          edges.push({
            id: createEdgeId(appNodeId, nodeId),
            source: appNodeId,
            target: nodeId,
            type: edgeType,
          });
        });
      }
    });

    // Add Server nodes
    servers?.forEach((svr) => {
      if (belongsToSelection(svr)) {
        const nodeId = createNodeId(Schemas.Server.name, svr.server_id);
        nodes.push({
          id: nodeId,
          type: Schemas.Server.name,
          data: {
            entity: svr,
            schema: schemas[Schemas.Server.name],
            parentEntities: applications,
            parentSchema: schemas[Schemas.Application.name],
            hasMultipleParents: applications && (svr.app_ids?.length ?? 0) > 1,
          },
          position: initialPosition,
        });

        // Add edge from App to Server
        const appIds = svr.app_ids ?? [];
        appIds.forEach((appId) => {
          const appNodeId = createNodeId(Schemas.Application.name, appId);
          edges.push({
            id: createEdgeId(appNodeId, nodeId),
            source: appNodeId,
            target: nodeId,
            type: edgeType,
          });
        });
      }
    });
    return { edges, nodes };
  }, [
    visibleWaves,
    visibleMoveGroups,
    visibleApps,
    databases,
    servers,
    schemas,
    moveGroups,
    belongsToSelection,
    applications,
  ]);

  const [layoutType] = React.useState("grid");

  // Calculate and memorize layout based on the layout type - only `grid` supported at the moment
  const layoutedElements = React.useMemo(() => {
    switch (layoutType) {
      case "grid":
        return createDagreLayout(initialElements.nodes, initialElements.edges);
      default:
        return initialElements;
    }
  }, [initialElements, layoutType]);

  // Define viewPort state for node offset position calculation
  // Which is updated on initial render, zooming and panning in the 'onMoveEnd' callback
  const [viewPort, setViewPort] = React.useState<Viewport>({ x: 0, y: 0, zoom: 1 });

  // Define state for the laid out nodes so that they can be moved around by drag and drop
  const [nodes, setNodes] = React.useState(layoutedElements.nodes);
  const [edges, setEdges] = React.useState(layoutedElements.edges);
  React.useEffect(() => {
    setNodes(layoutedElements.nodes);
    setEdges(layoutedElements.edges);
  }, [layoutedElements]);

  const [hoveredNode, setHoveredNode] = React.useState<string | null>(null);

  // Callback function that updates the node and edge states for movement
  const onNodesChange = React.useCallback((changes: NodeChange<NodeWithMetadata>[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds));
  }, []);

  const onEdgesChange = React.useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds));
  }, []);

  // Helper function to traverse the graph to find out all ancestors
  const findAncestors = React.useCallback(
    (nodeId: string): Set<string> => {
      const ancestors = new Set<string>();
      const queue = [nodeId];

      while (queue.length > 0) {
        const currentId = queue.pop();
        edges.forEach((edge) => {
          if (edge.target === currentId && !ancestors.has(edge.source)) {
            ancestors.add(edge.source);
            queue.push(edge.source);
          }
        });
      }
      return ancestors;
    },
    [edges]
  );

  // Helper function to traverse the graph to find out all descendants
  const findDescendants = React.useCallback(
    (nodeId: string): Set<string> => {
      const descendants = new Set<string>();
      const queue = [nodeId];

      while (queue.length > 0) {
        const currentId = queue.pop();
        edges.forEach((edge) => {
          if (edge.source === currentId && !descendants.has(edge.target)) {
            descendants.add(edge.target);
            queue.push(edge.target);
          }
        });
      }
      return descendants;
    },
    [edges]
  );

  // Callback function that updates the node style and metadata for highlighting on hover
  const getNodeMetadataAndStyle = React.useCallback(
    (node: NodeWithMetadata) => {
      const { data, style } = node;
      if (!hoveredNode) return { data, style };

      const ancestors = findAncestors(hoveredNode);
      const descendants = findDescendants(hoveredNode);
      const isInHierarchy = node.id === hoveredNode || ancestors.has(node.id) || descendants.has(node.id);

      // Calculate tooltip position for the hovered node
      let tooltipPosition;
      if (node.id === hoveredNode && reactflowRef.current) {
        // Calculate absolute position of the node in the window
        const nodeAbsoluteY = node.position.y * viewPort.zoom + viewPort.y;

        // Get the reactflow container's position
        const containerRect = reactflowRef.current.getBoundingClientRect();
        // Calculate absolute Y position relative to window
        const absoluteY = containerRect.top + nodeAbsoluteY;

        // Compare with window height
        const windowHeight = window.innerHeight;
        const remainingSpace = windowHeight - absoluteY;

        // Position tooltip based on available window space
        tooltipPosition = absoluteY > remainingSpace ? Position.Top : Position.Bottom;
      }

      return {
        style: {
          ...node.style,
          opacity: isInHierarchy ? 1 : 0.25,
        },
        data: {
          ...node.data,
          selected: node.id === hoveredNode ? true : undefined,
          tooltipPosition,
        },
      };
    },
    [hoveredNode, findAncestors, findDescendants, viewPort]
  );

  // Callback function that updates the edge style for highlighting on hover
  const getEdgeStyle = React.useCallback(
    (edge: Edge) => {
      if (!hoveredNode) return {};

      const ancestors = findAncestors(hoveredNode);
      const descendants = findDescendants(hoveredNode);

      const isInHierarchyPath =
        (ancestors.has(edge.source) && ancestors.has(edge.target)) || // Ancestor path
        (descendants.has(edge.source) && descendants.has(edge.target)) || // Descendant path
        (edge.source === hoveredNode && descendants.has(edge.target)) || // Direct descendant
        (edge.target === hoveredNode && ancestors.has(edge.source)); // Direct ancestor

      return {
        stroke: isInHierarchyPath ? "#ff0072" : "#999",
        strokeWidth: isInHierarchyPath ? 2 : 1,
        opacity: isInHierarchyPath ? 1 : 0.25,
      };
    },
    [hoveredNode, findAncestors, findDescendants]
  );

  // Memorized elements when node and edge states update
  const styledElements = React.useMemo(() => {
    return {
      nodes: nodes.map((node) => ({
        ...node,
        ...getNodeMetadataAndStyle(node),
      })),
      edges: edges.map((edge) => ({
        ...edge,
        style: getEdgeStyle(edge),
      })),
    };
  }, [nodes, edges, getNodeMetadataAndStyle, getEdgeStyle]);

  // Memorized nodeTypes and related typed BaseNode
  const nodeTypes = React.useMemo(
    () => ({
      [Schemas.Wave.name]: createCustomNode(Schemas.Wave.name),
      [Schemas.MoveGroup.name]: createCustomNode(Schemas.MoveGroup.name),
      [Schemas.Application.name]: createCustomNode(Schemas.Application.name),
      [Schemas.Database.name]: createCustomNode(Schemas.Database.name),
      [Schemas.Server.name]: createCustomNode(Schemas.Server.name),
    }),
    []
  );

  // Increase the reactflow wrapper z-index so that the tooltip can show above sticky table header
  React.useEffect(() => {
    if (reactflowRef.current) {
      const rfWrapper = reactflowRef.current;
      const origZIndex = rfWrapper.style.zIndex;
      rfWrapper.style.zIndex = `${REACT_FLOW_Z_INDEX}`;
      return () => {
        rfWrapper.style.zIndex = origZIndex;
      };
    }
  }, []);

  if (isLoading)
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
        <Spinner size="large" />
      </div>
    );

  return (
    <>
      <Legend schemaNames={schemaNamesWithData} />
      <ReactFlow
        ref={reactflowRef}
        style={{ flex: 1 }}
        nodeTypes={nodeTypes}
        nodes={styledElements.nodes}
        edges={styledElements.edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeMouseEnter={(_, node) => setHoveredNode(node.id)}
        onNodeMouseLeave={() => setHoveredNode(null)}
        onMoveEnd={(_, viewPort) => setViewPort(viewPort)}
        fitView
      >
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const type = node.type as keyof typeof nodeStyleConfig;
            return nodeStyleConfig[type]?.border || "#eee";
          }}
          position="top-right"
          zoomable
          pannable
        />
      </ReactFlow>
    </>
  );
};

/**
 * Entity Relationship Diagram component that visualizes relationships between different entities.
 * Displays a hierarchical diagram showing connections between waves, move groups, applications, databases, and servers.
 * Make sure you define a parent container with a specific size suitable for your use case for the diagram to display correctly.
 * Refer to https://reactflow.dev/learn/troubleshooting#004 for details.
 * @param props - Component properties defined by ERDiagramProps interface
 * @returns A React component that renders an interactive entity relationship diagram
 */
export default React.memo(ERDiagram) as typeof ERDiagram;
