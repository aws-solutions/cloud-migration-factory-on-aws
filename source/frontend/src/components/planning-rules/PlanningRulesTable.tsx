/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import React from "react";
import { useNavigate } from "react-router-dom";
import { SpaceBetween, Table } from "@cloudscape-design/components";
import TableHeader from "../TableHeader";
import { WPMGroupingRule, WPMPrioritizingRule, WPMRule, WPMRuleGenerationType, WPMRuleInDB } from "../../models";
import { Schemas } from "../../utils/Constants";
import { useGetItems } from "../../actions/ItemsHook";
import UserApiClient from "../../api_clients/userApiClient";
import { NotificationContext } from "../../contexts/NotificationContext";
import { convertNumericProperties } from "./PlanningRule.utils";

const schemaName = Schemas.WPMRule.name;

const userApi = new UserApiClient();

const PlanningRulesTable = () => {
  const navigate = useNavigate();
  const { addNotification } = React.useContext(NotificationContext);
  const [rulesLoadingState, { update: updateRules }] = useGetItems<WPMRuleInDB>(schemaName);
  const [selectedGroupingItems, setSelectedGroupingItems] = React.useState<WPMRule[]>([]);
  const [selectedPrioritizingItems, setSelectedPrioritizingItems] = React.useState<WPMRule[]>([]);
  const [isDeletingGrouping, setIsDeletingGrouping] = React.useState(false);
  const [isDeletingPrioritizing, setIsDeletingPrioritizing] = React.useState(false);

  const refreshRules = React.useCallback(() => updateRules(schemaName), [updateRules]);

  const groupingRules = React.useMemo(
    () =>
      rulesLoadingState.data
        .map(convertNumericProperties)
        .filter((rule): rule is WPMGroupingRule =>
          ["GROUPING_INCLUSIVE", "GROUPING_EXCLUSIVE"].includes(rule.rule_type)
        ),
    [rulesLoadingState.data]
  );

  const prioritizingRules = React.useMemo(
    () =>
      rulesLoadingState.data
        .map(convertNumericProperties)
        .filter((rule): rule is WPMPrioritizingRule => rule.rule_type === "PRIORITIZING"),
    [rulesLoadingState.data]
  );

  const handleDeleteRules = React.useCallback(
    (
      ruleTypeName: string,
      selectedItems: WPMRule[],
      setSelection: (selection: WPMRule[]) => void,
      setIsDeleting: (value: boolean) => void
    ) =>
      async () => {
        const currentSelectedItem = selectedItems;
        setIsDeleting(true);
        // Clear selection so as to disable delete button when deletion is in progress
        setSelection([]);
        try {
          await Promise.all(
            selectedItems
              .filter((rule): rule is WPMRule & { rule_id: string } => Boolean(rule.rule_id))
              .map((rule) => userApi.deleteItem(rule.rule_id, Schemas.WPMRule.name, rule.rule_type))
          );
          refreshRules();
        } catch (e) {
          setSelection(currentSelectedItem);
          addNotification({
            type: "error",
            dismissible: true,
            header: `Delete ${ruleTypeName} Rules`,
            content: (e as Error).message || `Failed to delete ${ruleTypeName.toLowerCase()} rules`,
          });
        } finally {
          setIsDeleting(false);
        }
      },
    [addNotification, refreshRules]
  );

  const handleRefreshClick = React.useCallback(() => {
    setSelectedGroupingItems([]);
    setSelectedPrioritizingItems([]);
    refreshRules();
  }, [refreshRules]);

  const handleAdd = React.useCallback(
    (ruleType: WPMRuleGenerationType) => () => navigate(`/admin/wave-planning/planning-rules/add?type=${ruleType}`),
    [navigate]
  );

  const handleEdit = React.useCallback(
    (selectedItems: WPMRule[]) => () => {
      if (selectedItems.length === 1) {
        const rule = selectedItems[0];
        // Type is required to get the record in the form
        navigate(`/admin/wave-planning/planning-rules/edit/${rule.rule_id}?type=${rule.rule_type}`);
      }
    },
    [navigate]
  );

  const columnDefinitions = React.useMemo(
    () => [
      {
        id: "rule_name",
        header: "Rule Name",
        cell: (item: WPMRule) => item.rule_name,
        isRowHeader: true,
      },
      {
        id: "rule_id",
        header: "Rule ID",
        cell: (item: WPMRule) => item.rule_id,
      },
      {
        id: "rule_type",
        header: "Rule Type",
        cell: (item: WPMRule) => item.rule_type.replace(/_/g, " "),
      },
      {
        id: "status",
        header: "Status",
        cell: (item: WPMRule) => item.status,
      },
      {
        id: "description",
        header: "Description",
        cell: (item: WPMRule) => item.rule_description || "-",
      },
    ],
    []
  );

  return (
    <SpaceBetween direction="vertical" size="l">
      <Table
        columnDefinitions={columnDefinitions}
        items={groupingRules}
        resizableColumns
        stickyHeader={true}
        selectionType="multi"
        onRowClick={(event) => setSelectedGroupingItems([event.detail.item])}
        onSelectionChange={(event) => setSelectedGroupingItems(event.detail.selectedItems)}
        selectedItems={selectedGroupingItems}
        loading={rulesLoadingState.isLoading || isDeletingGrouping}
        header={
          <TableHeader
            title="Grouping Rules"
            selectedItems={selectedGroupingItems}
            counter={`(${groupingRules.length})`}
            handleRefreshClick={handleRefreshClick}
            handleDeleteClick={handleDeleteRules(
              "Grouping",
              selectedGroupingItems,
              setSelectedGroupingItems,
              setIsDeletingGrouping
            )}
            handleEditClick={handleEdit(selectedGroupingItems)}
            handleAddClick={handleAdd("GROUPING")}
            handleActionSelection={undefined}
            actionsButtonDisabled={true}
            actionItems={[]}
            disabledButtons={{ delete: selectedGroupingItems.some((rule) => rule.isDefault) }}
            description=""
            handleDuplicateClick={undefined}
            handleDownload={undefined}
            info=""
          />
        }
      />

      <Table
        columnDefinitions={columnDefinitions}
        items={prioritizingRules}
        resizableColumns
        stickyHeader={true}
        selectionType="multi"
        onRowClick={(event) => setSelectedPrioritizingItems([event.detail.item])}
        onSelectionChange={(event) => setSelectedPrioritizingItems(event.detail.selectedItems)}
        selectedItems={selectedPrioritizingItems}
        loading={rulesLoadingState.isLoading || isDeletingPrioritizing}
        header={
          <TableHeader
            title="Prioritizing Rules"
            selectedItems={selectedPrioritizingItems}
            counter={`(${prioritizingRules.length})`}
            handleRefreshClick={handleRefreshClick}
            handleDeleteClick={handleDeleteRules(
              "Prioritizing",
              selectedPrioritizingItems,
              setSelectedPrioritizingItems,
              setIsDeletingPrioritizing
            )}
            handleEditClick={handleEdit(selectedPrioritizingItems)}
            handleAddClick={handleAdd("PRIORITIZING")}
            handleActionSelection={undefined}
            actionsButtonDisabled={true}
            actionItems={[]}
            disabledButtons={{ delete: selectedPrioritizingItems.some((rule) => rule.isDefault) }}
            description=""
            handleDuplicateClick={undefined}
            handleDownload={undefined}
            info=""
          />
        }
      />
    </SpaceBetween>
  );
};

export default PlanningRulesTable;
