/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useCallback, useContext, useEffect, useState } from "react";
import { Button, Container, Header, Icon, RadioGroup, SpaceBetween, Spinner } from "@cloudscape-design/components";
import {
  ReactFlow,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  Controls,
  Edge,
  EdgeChange,
  Handle,
  MarkerType,
  MiniMap,
  Node,
  NodeChange,
  Position,
  ReactFlowInstance,
  ReactFlowProvider,
  Viewport,
  NodeProps
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import '@xyflow/react/dist/base.css';
import ItemAmendModal from "./ItemAmendModal.tsx";
import UserApiClient from "../api_clients/userApiClient.ts";
import { getChanges } from "../resources/main.ts";
import { apiActionErrorHandler, parsePUTResponseErrors } from "../resources/recordFunctions.ts";
import { NotificationContext } from "../contexts/NotificationContext.tsx";
import { CMFModal } from "./Modal.tsx";
import {PipelineTemplate, PipelineTemplateTask} from "../models/Pipeline.ts";

type EditorAction = "Add" | "Edit";

const iconTaskMapping: { [key: string]: any } = {
  Manual: "user-profile",
  Automated: "script",
  // Add other icon components as needed
};

export type TaskNode = Node<
  {
    task: PipelineTemplateTask;
    layoutDirectionTB?: boolean;
  },
  'task'
>;

const PipelineTemplateTaskNode = (props: NodeProps<TaskNode>) => {
  // Determine which icon component to use
  const TaskIconName = iconTaskMapping[props.data?.task?.script?.type] ? iconTaskMapping[props.data.task.script.type] : "bug";

  return (
    <Container
      header={
        <SpaceBetween size={"xs"} direction={"horizontal"}>
          <RadioGroup
            onChange={({ detail }) => {}}
            value={props?.selected ? "selected" : null}
            items={[{ value: "selected", label: "" }]}
          />
          <Icon size={"medium"} name={TaskIconName} />
          {props.data.task.pipeline_template_task_name}
        </SpaceBetween>
      }
    >
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

interface PipelineTemplateVisualEditorProps {
  schemaName: string;
  schemas: any; // Optional
  userEntityAccess: any; // Optional
  pipelineTemplate?: any;
  handleRefresh: any;
}

const options = {
  includeHiddenNodes: false,
};

const PipelineTemplateVisualEditor: React.FC<PipelineTemplateVisualEditorProps> = ({
  pipelineTemplate,
  schemas,
  schemaName,
  userEntityAccess,
  handleRefresh,
}) => {
  const { addNotification } = useContext(NotificationContext);
  const [isAddTaskModalVisible, setIsAddTaskModalVisible] = useState(false);
  const [selectedNode, setSelectedNode] = useState<Node>();
  const [taskAdd, setTaskAdd] = useState<PipelineTemplateTask | undefined>(undefined);
  const [directionTB, setDirectionTB] = useState(true);
  const [nodes, setNodes] = useState<Node[]>();
  const [edges, setEdges] = useState<Edge[]>();
  const [viewPort, setViewPort] = useState<Viewport>()
  const [action, setAction] = useState<EditorAction>("Add");
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance>();
  const [isDeleteConfirmationModalVisible, setIsDeleteConfirmationModalVisible] = useState(false);

  useEffect(() => {
    if (reactFlowInstance && nodes?.length) {
      let beforeViewPort = undefined;
      if(viewPort){
        beforeViewPort = viewPort;
      }
      reactFlowInstance.fitView();
      if(beforeViewPort) {
        setViewPort(beforeViewPort);
      }
    }
  }, [reactFlowInstance, nodes?.length]);

  useEffect(() => {
    setSelectedNode(undefined);

    if (!pipelineTemplate) {
      console.debug("Clearing Nodes and Edges as no pipeline template.");
      setNodes([]);
      setEdges([]);
      return;
    }

    const transformedData = transformDataForReactFlow(pipelineTemplate);

    const layouted = getLayoutedElements(transformedData.nodes, transformedData.edges);
    console.debug("Setting Nodes and Edges after pipelineTemplate change.");
    setNodes([...layouted.nodes]);
    setEdges([...layouted.edges]);
  }, [pipelineTemplate]);

  function setCurrentTask(id: string) {
    if (!pipelineTemplate?.pipeline_template_tasks) return;

    const selectedTask = pipelineTemplate.pipeline_template_tasks.find((task: PipelineTemplateTask) => {
      return task.pipeline_template_task_id === id;
    });
    setTaskAdd(selectedTask);
  }

  useEffect(() => {
    if (selectedNode) {
      setCurrentTask(selectedNode.id);
    }
  }, [selectedNode]);

  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const getDefaultWidth = (node: TaskNode) => {
    let width = node.data?.task ? node.data?.task.pipeline_template_task_name.length * 15 : 15;

    return width < 100 ? 100 : width;
  };

  const getLayoutedElements = (nodes: Node[] | undefined, edges: Edge[] | undefined) => {
    console.debug("starting getLayoutedElements");
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
          width: node.measured?.width ?? getDefaultWidth(node as TaskNode),
          height: node.measured?.height ?? 100,
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
      console.warn("no nodes");
      return undefined;
    }
  };

  const getExistingTask = (taskID: string) => {
    if (pipelineTemplate?.pipeline_template_tasks) {
      return pipelineTemplate?.pipeline_template_tasks.find((task: PipelineTemplateTask) => {
        if (task.pipeline_template_task_id === taskID) {
          return true;
        }
      });
    } else {
      console.warn("no tasks present on pipeline template");
      return undefined;
    }
  };

  const transformDataForReactFlow = (pipelineTemplate: PipelineTemplate) => {
    console.debug("starting transformDataForReactFlow");
    if (!pipelineTemplate?.pipeline_template_tasks) return { nodes: [], edges: [] };

    const newNodes: TaskNode[] = [];
    const newEdges: Edge[] = [];

    try {
      pipelineTemplate.pipeline_template_tasks.forEach((task: PipelineTemplateTask) => {
        const existingNode = getExistingNode(task.pipeline_template_task_id.toString()) as TaskNode;
        let node: TaskNode = {
          id: task.pipeline_template_task_id.toString(), // Convert ID to string
          type: "task", // Change to appropriate node type if needed
          data: {task: {} as PipelineTemplateTask} as any, // Directly specify the type as any
          position: { x: 0, y: 0 },
        };

        if (existingNode) {
          // existing node found, only update the data.
          node = existingNode;
          node.data.task = {} as PipelineTemplateTask;
        }

        node.data.layoutDirectionTB = directionTB;

        // Iterate through keys of task object and add to node.data
        for (const key in task) {
          if (task.hasOwnProperty(key)) {
            node.data.task[key] = task[key];
          }
        }

        // Add node to nodes array
        newNodes.push(node);

        if (task.task_successors) {
          for (const task_successor_id of task.task_successors) {
            const edge = {
              id: `${task.pipeline_template_task_id.toString()}-${task_successor_id}`, // Convert IDs to string
              source: task.pipeline_template_task_id.toString(), // Convert source ID to string
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
  const onEdgesChange = useCallback(processEdgesChange, []);

  async function deleteNode(templateTaskId: string | undefined) {
    if (!templateTaskId) return;

    const apiUser = new UserApiClient();
    setIsDeleteConfirmationModalVisible(false);
    await apiUser.deleteItem(templateTaskId, "pipeline_template_task");
    await handleRefresh();
  }

  async function processNodesChange(changes: NodeChange[]) {
    console.debug("starting processNodesChange");
    for (const change of changes) {
      if (change.type === "remove") {
        setIsDeleteConfirmationModalVisible(true);
      }
    }
    console.debug("Setting Nodes after Node change event.");
    setNodes((nds: any) => applyNodeChanges(changes, nds));
  }

  async function processEdgesChange(changes: EdgeChange[]) {
    console.debug("starting processEdgesChange");
    setEdges((eds: any) => applyEdgeChanges(changes, eds));
  }

  const onConnect = useCallback(connectNodes, []);

  async function connectNodes(params: any) {
    // get source node to retrieve existing successors to be able to append new.
    const sourceTask = getExistingTask(params.source);
    if (sourceTask) {
      const apiUser = new UserApiClient();
      let newTaskSuccessors = sourceTask.task_successors;
      if (newTaskSuccessors.length > 0) {
        if (!newTaskSuccessors.includes(params.target)) {
          console.debug("new task successor added.");
          newTaskSuccessors.push(params.target);
        } else {
          console.warn("Successor task already exists.");
          return;
        }
      } else {
        newTaskSuccessors = [params.target];
      }
      const updatedNode = {
        task_successors: newTaskSuccessors,
      };
      await apiUser.putItem(params.source, updatedNode, "pipeline_template_task");
      setEdges((eds: any) => addEdge(params, eds));

      await handleRefresh();
    } else {
      console.error(`Source node not found ${params.source}`);
    }
  }

  const nodeClick = (clickedNode: Node) => {
    setSelectedNode(clickedNode);
    if (nodes) {
      const updatedNodes = nodes.map((node) => {
        node.selected = clickedNode.id === node.id;
        return node;
      });
      setNodes(updatedNodes);
    }
  };

  function showAddNode(edge?: Edge) {
    setAction("Add");
    if (pipelineTemplate) {
      const newNode = {
        pipeline_template_task_name: "",
        task_id: "",
        pipeline_template_task_id: "",
        pipeline_template_id: pipelineTemplate.pipeline_template_id,
        task_successors: edge ? [edge.target] : [],
      };

      setTaskAdd(newNode);
    }
    setIsAddTaskModalVisible(true);
  }

  function showEditNode(node?: Node) {
    if (node) {
      setSelectedNode(node);
      setCurrentTask(node.id);
    } else if (selectedNode) {
      // Use existing selectedNode
      setCurrentTask(selectedNode.id);
    } else {
      return;
    }

    setAction("Edit");
    setIsAddTaskModalVisible(true);
  }

  async function doubleclickEdge(event: React.MouseEvent, edge: Edge) {
    showAddNode(edge);
  }

  async function doubleclickNode(event: React.MouseEvent, node: Node) {
    showEditNode(node);
  }

  const onModalCancel = () => {
    setIsAddTaskModalVisible(false);
    setTaskAdd(undefined);
  };

  async function saveNewTask(amendedItem: any, action: string) {
    setIsAddTaskModalVisible(false);
    let amendedItemCopy: Record<string, any> = { ...amendedItem };
    let result;

    if (!pipelineTemplate) {
      console.error("No pipeline template!");
      return;
    }

    try {
      const apiUser = new UserApiClient();
      if (action === "Edit") {
        let pipeline_template_task_id = amendedItemCopy.pipeline_template_task_id;
        amendedItemCopy = getChanges(
          amendedItemCopy,
          pipelineTemplate.pipeline_template_tasks,
          "pipeline_template_task_id"
        );
        if (!amendedItemCopy) {
          // no changes to original record.
          return;
        }
        result = await apiUser.putItem(pipeline_template_task_id, amendedItemCopy, "pipeline_template_task");
      } else {
        delete amendedItemCopy.pipeline_template_task_id;
        result = await apiUser.postItem(
          { ...amendedItemCopy, pipeline_template_id: pipelineTemplate.pipeline_template_id },
          "pipeline_template_task"
        );
      }

      if (result["errors"]) {
        let errorsReturned = parsePUTResponseErrors(result["errors"]).join(",");
        console.error(errorsReturned);
        addNotification({
          type: "error",
          dismissible: true,
          header: `${action} ${schemaName}`,
          content: errorsReturned,
        });
      } else {
        console.info("saved successfully.");
        addNotification({
          type: "success",
          dismissible: true,
          header: `${action} ${schemaName}`,
          content: amendedItem.pipeline_template_task_name + " saved successfully.",
        });
        await handleRefresh();
      }
    } catch (e: any) {
      console.debug(e);
      apiActionErrorHandler(action, schemaName, e, addNotification);
    }
  }

  useEffect(() => {
    if (nodes) {
      const layouted = getLayoutedElements(nodes, edges);

      console.debug("Setting nodes and edges after layout direction change.");
      setNodes([...layouted.nodes]);
      setEdges([...layouted.edges]);

      if (reactFlowInstance) {
        reactFlowInstance.fitView();
      }
    }
  }, [directionTB]);

  return (
    <>
      <Container
        header={
          <Header
            variant="h2"
            actions={
              <SpaceBetween direction="horizontal" size="s">
                <Button disabled={!selectedNode} onClick={() => setIsDeleteConfirmationModalVisible(true)}>
                  Delete
                </Button>
                <Button disabled={!selectedNode} onClick={() => showEditNode()}>
                  Edit
                </Button>
                <Button variant={"primary"} onClick={() => showAddNode()}>
                  Add
                </Button>
                <Button onClick={() => setDirectionTB(!directionTB)}>Toggle layout direction</Button>
              </SpaceBetween>
            }
          >
            {pipelineTemplate ? pipelineTemplate.pipeline_template_name : "Pipeline Template View"}
          </Header>
        }
      >
        {pipelineTemplate === null ? (
          <Spinner size="large" />
        ) : (
          <>
            {/* Render React Flow component */}
            <div style={{ width: "100%", height: "85vh" }}>
              <ReactFlow
                onInit={(instance) => setReactFlowInstance(instance)}
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes} // Pass custom node types
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={(event: React.MouseEvent, node: Node) => nodeClick(node)}
                onEdgeDoubleClick={(event: React.MouseEvent, edge: Edge) => doubleclickEdge(event, edge)}
                onNodeDoubleClick={(event: React.MouseEvent, node: Node) => doubleclickNode(event, node)}
                onConnect={onConnect}
                panOnScroll={true}
                fitView={true}
                viewport={viewPort}
                onViewportChange={(viewport: Viewport) => setViewPort(viewport)}
              >
                <Controls />
                <MiniMap zoomable pannable />
              </ReactFlow>
            </div>
          </>
        )}
      </Container>
      {isAddTaskModalVisible ? (
        <ItemAmendModal
          visible={isAddTaskModalVisible}
          item={taskAdd}
          schemas={schemas}
          activeSchemaName={schemaName}
          action={action}
          userAccess={userEntityAccess}
          closeModal={onModalCancel}
          onConfirmation={(localItem, action) => saveNewTask(localItem, action)}
        />
      ) : (
        <></>
      )}
      {isDeleteConfirmationModalVisible ? (
        <CMFModal
          onDismiss={() => setIsDeleteConfirmationModalVisible(false)}
          visible={isDeleteConfirmationModalVisible}
          onConfirmation={() => deleteNode(selectedNode?.id)}
          header={"Delete template task"}
        >
          <p>Are you sure you wish to delete the task '{(selectedNode as TaskNode).data.task.pipeline_template_task_name}'?</p>
        </CMFModal>
      ) : null}
    </>
  );
};

const PipelineTemplateVisualEditorWrapper: React.FC<PipelineTemplateVisualEditorProps> = ({
  pipelineTemplate,
  schemas,
  schemaName,
  userEntityAccess,
  handleRefresh,
}) => {
  return (
    <ReactFlowProvider>
      <PipelineTemplateVisualEditor {...{ pipelineTemplate, schemas, schemaName, userEntityAccess, handleRefresh }} />
    </ReactFlowProvider>
  );
};

const nodeTypes = {
  task: PipelineTemplateTaskNode,
};

export { PipelineTemplateVisualEditorWrapper, nodeTypes };
