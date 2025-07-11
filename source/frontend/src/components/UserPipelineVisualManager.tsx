/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useCallback, useContext, useEffect, useState } from "react";
import {
  Badge,
  Box,
  Button,
  ButtonDropdown,
  Container,
  ExpandableSection,
  Header,
  Icon,
  SpaceBetween,
  Spinner,
} from "@cloudscape-design/components";
import {
  ReactFlow,
  applyNodeChanges,
  Controls,
  Edge,
  Handle,
  MarkerType,
  MiniMap,
  Node,
  NodeChange,
  Position,
  ReactFlowInstance,
  ReactFlowProvider,
  useNodesInitialized, NodeProps,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import '@xyflow/react/dist/base.css';
import UserApiClient from "../api_clients/userApiClient.ts";
import { parsePUTResponseErrors } from "../resources/recordFunctions.ts";
import { NotificationContext } from "../contexts/NotificationContext.tsx";
import {Pipeline, TaskExecution} from "../models/Pipeline.ts";
import { SplitPanelContext } from "../contexts/SplitPanelContext.tsx";
import { ViewTaskExecution } from "./PipelineView.tsx";
import Audit from "./ui_attributes/Audit.tsx";

const iconTaskMapping: { [key: string]: any } = {
  Manual: "user-profile",
  Automated: "script",
  // Add other icon components as needed
};

export type TaskExecutionNode = Node<
  {
    task: TaskExecution;
    layoutDirectionTB?: boolean;
    handleSplitPanelOpen?: (open: boolean) => void;
    handleRefreshTasks?: () => Promise<void>;
  },
  'task'
>;

const PipelineTaskNode = (props: NodeProps<TaskExecutionNode>) => {
  const { addNotification } = useContext(NotificationContext);
  const [isActionProcessing, setIsActionProcessing] = useState<boolean>(false);
  const apiUser = new UserApiClient();

  const statusBadge = (status: string) => {
    let statusBadgeName: "grey" | "green" | "blue" | "red" = "grey";
    switch (status) {
      case "Complete":
        statusBadgeName = "green";
        break;
      case "Failed":
        statusBadgeName = "red";
        break;
      case "In Progress":
        statusBadgeName = "blue";
        break;
      case "Pending Approval":
        statusBadgeName = "blue";
        break;
      case "Abandoned":
        statusBadgeName = "grey";
        break;
    }

    return <Badge key={statusBadgeName} color={statusBadgeName}>{status}</Badge>;
  };

  // Determine which icon component to use
  const TaskIconName = iconTaskMapping[props.data?.task.script?.type] ? iconTaskMapping[props.data.task.script.type] : "bug";

  const allowStatusUpdateToSkip = ["Failed"];
  const allowStatusUpdateToRetry = ["Failed", "Complete", "Skip", "Abandoned"];
  const allowStatusUpdateToComplete = ["Pending Approval"];
  const allowStatusUpdateToAbandon = ["Pending Approval", "Not Started"];

  const handleAction = async (action: string) => {
    switch (action) {
      case "view_inputs":
        if (props.data?.handleSplitPanelOpen) {
          props.data?.handleSplitPanelOpen(true);
        }
        break;
      case "update_status_skip":
      case "update_status_retry":
      case "update_status_complete":
      case 'update_status_abandoned':
        await handleTaskExecutionStatusChange(action);
        break;
    }
  };

  const handleTaskExecutionStatusChange = async (
    action: "update_status_skip" | "update_status_retry" | "update_status_complete" | "update_status_abandoned"
  ) => {
    setIsActionProcessing(true);
    const schemaName = "task_execution";
    const humanReadableSchemaName = schemaName.split("_").join(" ");
    const selectedItem = props.data.task;

    const statusMap = {
      update_status_skip: "Skip",
      update_status_retry: "Retry",
      update_status_complete: "Complete",
      update_status_abandoned: "Abandoned",
    };

    if (!statusMap[action]) {
      addNotification({
        type: "error",
        dismissible: true,
        header: "Update " + humanReadableSchemaName,
        content: "Invalid status change.",
      });
    }

    try {
      await apiUser.putItem(
        selectedItem.task_execution_id,
        {
          task_execution_status: statusMap[action],
        },
        schemaName
      );

      if (props?.data.handleRefreshTasks)
      {
        props.data.handleRefreshTasks();
      }

      // Update local object with new status.
      props.data.task.task_execution_status = statusMap[action];
    } catch (e: any) {
      let errorsReturned = e.message;
      if (e.response?.data?.errors) {
        const errorResponse = e.response.data.errors;
        console.debug("PUT " + humanReadableSchemaName + " errors");
        console.debug(errorResponse);
        errorsReturned = parsePUTResponseErrors(errorResponse).join(",");
      }

      addNotification({
        type: "error",
        dismissible: true,
        header: "Update " + humanReadableSchemaName,
        content: errorsReturned,
      });
    }
    setIsActionProcessing(false);
  };

  const show_history = () => {
    return (
      <ExpandableSection headerText="Audit" variant="footer">
        <Audit item={props.data.task} />
      </ExpandableSection>
    );
  };

  return (
    <Container key={props.data.task.task_execution_id} footer={show_history()}>
      <Header
        actions={
          <ButtonDropdown
            loading={isActionProcessing}
            items={[
              {
                id: "view_inputs",
                text: "View Inputs & Logs",
              },
              {
                id: "update_status",
                text: "Update Status",
                items: [
                  {
                    id: "update_status_skip",
                    text: "Skip",
                    disabled: !allowStatusUpdateToSkip.includes(props.data.task.task_execution_status),
                  },
                  {
                    id: "update_status_retry",
                    text: "Retry",
                    disabled: !allowStatusUpdateToRetry.includes(props.data.task.task_execution_status),
                  },
                  {
                    id: "update_status_complete",
                    text: "Complete",
                    disabled: !allowStatusUpdateToComplete.includes(props.data.task.task_execution_status),
                  },
                  {
                    id: "update_status_abandoned",
                    text: "Abandoned",
                    disabled: !allowStatusUpdateToAbandon.includes(props.data.task.task_execution_status),
                  },
                ],
              },
            ]}
            onItemClick={(event) => handleAction(event.detail.id)}
            expandableGroups
          >
            Actions
          </ButtonDropdown>
        }
      >
        <SpaceBetween size={"xs"} direction={"horizontal"}>
          <Icon size={"large"} name={TaskIconName} />
          {props.data.task.task_execution_name}
        </SpaceBetween>
      </Header>
      <Box float={"right"}>{statusBadge(props.data.task.task_execution_status)}</Box>

      <Handle
        type="target"
        position={props.data.layoutDirectionTB ? Position.Top : Position.Left}
        className="w-16 !bg-teal-500"
      />
      <Handle
        type="source"
        position={props.data.layoutDirectionTB ? Position.Bottom : Position.Right}
        className="w-16 !bg-teal-500"
      />
    </Container>
  );
};

interface PipelineVisualManagerProps {
  schemaName: string;
  schemas: any; // Optional
  templateData?: any;
  handleRefreshTasks?: any;
  pipelineMetadata?: any;
}

const options = {
  includeHiddenNodes: false,
};

const PipelineVisualManager: React.FC<PipelineVisualManagerProps> = ({
  templateData,
  schemas,
  schemaName,
  handleRefreshTasks,
  pipelineMetadata
}) => {
  const { setContent, setSplitPanelOpen } = useContext(SplitPanelContext);
  const [selectedNode, setSelectedNode] = useState<Node>();
  const [directionTB, setDirectionTB] = useState(true);
  const [pipeline, setPipeline] = useState<Pipeline>();
  const [nodes, setNodes] = useState<Node[]>();
  const [edges, setEdges] = useState<Edge[]>();
  const nodesInitialized = useNodesInitialized(options);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance>();

  const onInit = (rf: ReactFlowInstance) => {
    setReactFlowInstance(rf);
  };

  useEffect(() => {
    if (reactFlowInstance && nodes?.length) reactFlowInstance.fitView();
    // setDirectionTB(!directionTB)
  }, [nodesInitialized]);

  useEffect(() => {
    if (!pipeline) {
      setSelectedNode(undefined);
      setNodes([]);
      setEdges([]);
      return;
    }

    const transformedData = transformDataForReactFlow(pipeline);

    const layouted = getLayoutedElements(transformedData.nodes, transformedData.edges);
    setNodes([...layouted.nodes]);
    setEdges([...layouted.edges]);
  }, [pipeline]);

  useEffect(() => {
    setPipeline(templateData);
  }, [templateData]);

  useEffect(() => {
    if (selectedNode) {
      setContent(
        <ViewTaskExecution schema={schemas[schemaName]} taskExecution={selectedNode.data.task} pipelineMetadata={pipelineMetadata} dataAll={undefined} />
      );
    }
  }, [selectedNode]);

  const handleRefresh = async () => {
    await handleRefreshTasks()
    if (selectedNode) {
      // updated selected node to reflect changes in side panel.
      const updatedSelectedNode = getExistingNode(selectedNode.id);
      if (updatedSelectedNode) {
        setSelectedNode(updatedSelectedNode);
      }
    }
  }

  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const getDefaultWidth = (node: TaskExecutionNode) => {
    let width = node.data?.task ? node.data.task.task_execution_name.length * 20 + 100: 15;

    return width < 200 ? 200 : width;
  };

  const getLayoutedElements = (nodes: Node[] | undefined, edges: Edge[] | undefined) => {
    const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: directionTB ? "TB" : "LR" });

    if (edges) {
      edges.forEach((edge: Edge) => g.setEdge(edge.source, edge.target));
    } else {
      edges = [];
    }

    if (nodes) {
      nodes.forEach((node: Node) => {
        let newData = node.data;
        newData.layoutDirectionTB = directionTB;
        g.setNode(node.id, {
          ...node,
          data: newData,
          width: node.measured?.width ?? getDefaultWidth(node as TaskExecutionNode),
          height: node.measured?.height ?? 225,
        });
      });
    } else {
      nodes = [];
    }

    dagre.layout(g);

    return {
      nodes: nodes.map((node: Node) => {
        const position = g.node(node.id);
        // We are shifting the dagre node position (anchor=center center) to the top left
        // so it matches the React Flow node anchor point (top left).
        const x = position.x - (node.measured?.width ?? 0) / 2;
        const y = position.y - (node.measured?.height ?? 0) / 2;

        return { ...node, position: { x, y } };
      }),
      edges,
    };
  };

  const getExistingNode = (nodeID: string) => {
    if (nodes) {
      return nodes.find((node: Node) => {
        if (node.id === nodeID) {
          return true;
        }
      });
    } else {
      return undefined;
    }
  };

  const transformDataForReactFlow = (pipeline: Pipeline) => {
    if (!pipeline?.pipeline_tasks) return { nodes: [], edges: [] };

    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    try {
      pipeline.pipeline_tasks.forEach((task: TaskExecution) => {
        const existingNode = getExistingNode(task.task_execution_id.toString()) as TaskExecutionNode;
        let node: TaskExecutionNode = {
          id: task.task_execution_id.toString(), // Convert ID to string
          type: "task", // Change to appropriate node type if needed
          data: {task: {} as TaskExecution} as any, // Directly specify the type as any
          position: { x: 0, y: 0 },
        };

        if (existingNode) {
          // existing node found, only update the data.
          node = existingNode;
          node.data = {task: {} as TaskExecution} as any;
        }

        // Iterate through keys of task object
        for (const key in task) {
          if (task.hasOwnProperty(key)) {
            node.data.task[key] = task[key];
          }
        }

        node.data.layoutDirectionTB = directionTB;

        node.data.handleSplitPanelOpen = setSplitPanelOpen;
        node.data.handleRefreshTasks = handleRefresh;

        // Add node to nodes array
        newNodes.push(node);

        if (task.task_successors) {
          for (const task_successor_id of task.task_successors) {
            const edge = {
              id: `${task.task_execution_id.toString()}-${task_successor_id}`, // Convert IDs to string
              source: task.task_execution_id.toString(), // Convert source ID to string
              target: task_successor_id, // Convert target ID to string
              markerEnd: {
                type: MarkerType.ArrowClosed,
              },
              animated: false,
            };
            newEdges.push(edge);
          }
        }
      });

      return { nodes: newNodes, edges: newEdges };
    } catch (error) {
      console.error("Error while transforming data for ReactFlow:", error);
      setNodes([]);
      setEdges([]);
      return { nodes: [], edges: [] };
    }
  };

  const onNodesChange = useCallback(processNodesChange, []);

  async function processNodesChange(changes: NodeChange[]) {
    setNodes((nds: any) => applyNodeChanges(changes, nds));
  }

  useEffect(() => {
    if (nodes) {
      const layouted = getLayoutedElements(nodes, edges);

      setNodes([...layouted.nodes]);
      setEdges([...layouted.edges]);

      if (reactFlowInstance) {
        reactFlowInstance.fitView();
      }
    }
  }, [directionTB]);

  const visualActions = () => {
    let actionButtons = [];

    actionButtons.push(<Button key={"refresh"} iconAlign="right" iconName="refresh" ariaLabel={"Refresh"} onClick={() => handleRefresh()}/>)
    actionButtons.push(<Button key={"direction"} onClick={() => setDirectionTB(!directionTB)}>Toggle layout direction</Button>);

    return actionButtons;
  };

  return (
    <Container header={<Header variant="h2" actions={<SpaceBetween direction="horizontal" size="s">{visualActions()}</SpaceBetween>}>{pipeline ? pipeline.pipeline_name : 'Pipeline Template View'}</Header>}>
      {!pipeline && !nodesInitialized ? (
        <Spinner size="large" />
      ) : (
        <>
          {/* Render React Flow component */}
          <div style={{ width: "100%", height: "85vh" }}>
            <ReactFlow
              onInit={onInit}
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes} // Pass custom node types
              onNodesChange={onNodesChange}
              onNodeClick={(event: React.MouseEvent, node: Node) => setSelectedNode(node)}
              panOnScroll={true}
              fitView={true}
            >
              <Controls />
              <MiniMap zoomable pannable />
            </ReactFlow>
          </div>
        </>
      )}
    </Container>
  );
};

const PipelineVisualManagerWrapper: React.FC<PipelineVisualManagerProps> = ({
  templateData,
  schemas,
  schemaName,
  handleRefreshTasks,
  pipelineMetadata
}) => {
  return (
    <ReactFlowProvider>
      <PipelineVisualManager {...{ templateData, schemas, schemaName, handleRefreshTasks, pipelineMetadata }} />
    </ReactFlowProvider>
  );
};

const nodeTypes = {
  task: PipelineTaskNode,
};

export { PipelineVisualManagerWrapper, nodeTypes };
