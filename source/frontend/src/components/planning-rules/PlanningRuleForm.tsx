/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { ReactNode } from "react";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import { SpaceBetween, Container, Header, Textarea, Button, Box, Spinner } from "@cloudscape-design/components";
import ToolsApiClient from "../../api_clients/toolsApiClient";
import UserApiClient from "../../api_clients/userApiClient";
import { WPMRule, WPMRuleData, WPMRuleGenerationType } from "../../models/WpmRule";
import { Schemas } from "../../utils/Constants";
import { NotificationContext } from "../../contexts/NotificationContext";
import { parsePUTResponseErrors, UNEXPECTED_ERROR } from "../../resources/recordFunctions";
import {
  castToRuleGenerationType,
  convertNumericProperties,
  RuleValidationError,
  validateGroupingRule,
  validatePrioritizingRule,
} from "./PlanningRule.utils";
import { EntitySchema } from "../../models";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const environment = (window as any).env;

type PlanningRuleFormProps = {
  readonly schemas: Record<string, EntitySchema>;
};

const toolsApiClient = new ToolsApiClient();
const userApiClient = new UserApiClient();

const PlanningRuleForm = ({ schemas }: PlanningRuleFormProps) => {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const { addNotification } = React.useContext(NotificationContext);
  const isEditMode = location.pathname.includes("/edit");

  const [editingRule, setEditingRule] = React.useState<WPMRule | undefined>(location.state?.rule);
  const [userInput, setUserInput] = React.useState("");
  const [ruleJson, setRuleJson] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [isLoadingRule, setIsLoadingRule] = React.useState(false);

  const ruleTypeParam = React.useMemo(() => new URLSearchParams(location.search).get("type"), [location.search]);

  // Deduce the rule generation type based on the URL querystring param and default to grouping
  // (only if the add/edit URL is accessed directly without the type querystring param)
  const ruleGenerationType: WPMRuleGenerationType = React.useMemo(
    () => castToRuleGenerationType(ruleTypeParam, "GROUPING"),
    [ruleTypeParam]
  );

  React.useEffect(() => {
    if (isEditMode && params.id && !editingRule) {
      setIsLoadingRule(true);

      userApiClient
        .getItem(params.id, Schemas.WPMRule.name, ruleTypeParam || "")
        .then(convertNumericProperties)
        .then((rule: WPMRule) => {
          setEditingRule(rule);
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          const { _history, rule_id, ...ruleWithoutSystemFields } = rule;
          setRuleJson(JSON.stringify(ruleWithoutSystemFields, null, 2));
        })
        .catch(() => {
          addNotification({
            type: "error",
            dismissible: true,
            header: "Load Rule",
            content: "Failed to load rule",
          });
          navigate("/admin/wave-planning", { state: { activeTab: "planning-rules" } });
        })
        .finally(() => setIsLoadingRule(false));
    } else if (isEditMode && editingRule) {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { _history, rule_id, ...ruleWithoutSystemFields } = editingRule;
      setRuleJson(JSON.stringify(ruleWithoutSystemFields, null, 2));
    }
  }, [isEditMode, params.id, editingRule, addNotification, location.search, navigate, ruleTypeParam]);

  const handleGenerateRule = async () => {
    if (!userInput.trim()) {
      addNotification({
        type: "error",
        dismissible: true,
        header: "Generate Rule",
        content: "Please enter a rule description",
      });
      return;
    }
    setIsLoading(true);
    try {
      const result = await toolsApiClient.generateRule(ruleGenerationType, userInput);
      setRuleJson(JSON.stringify(result, null, 2));
    } catch (err) {
      addNotification({
        type: "error",
        dismissible: true,
        header: "Generate Rule",
        content: (err as Error).message,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveRule = async () => {
    // For default rules, only update status
    if (editingRule?.isDefault) {
      const newStatus = editingRule.status === "ENABLED" ? "DISABLED" : "ENABLED";
      const updatedRule = {
        ...editingRule,
        status: newStatus,
      };
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { _history, rule_id, ...ruleWithoutId } = updatedRule;

      setIsSaving(true);
      try {
        const result = await userApiClient.putItem(
          editingRule.rule_id || "",
          ruleWithoutId,
          Schemas.WPMRule.name,
          editingRule.rule_type
        );

        if (result?.errors) {
          const errorMessages = parsePUTResponseErrors(result.errors);
          addNotification({
            type: "error",
            dismissible: true,
            header: "Update Rule",
            content: errorMessages.join(", "),
          });
        } else {
          addNotification({
            type: "success",
            dismissible: true,
            header: "Update Rule",
            content: "Rule status updated successfully!",
          });
          navigate("/admin/wave-planning", { state: { activeTab: "planning-rules" } });
        }
      } catch (err: unknown) {
        addNotification({
          type: "error",
          dismissible: true,
          header: "Update Rule",
          content: (err as Error).message || "An error occurred while updating the rule",
        });
      } finally {
        setIsSaving(false);
      }
      return;
    }

    // For custom rules, use full JSON validation
    if (!ruleJson.trim()) {
      addNotification({
        type: "error",
        dismissible: true,
        header: "Save Rule",
        content: "No rule to save",
      });
      return;
    }

    let parsedRule;
    try {
      parsedRule = JSON.parse(ruleJson);
    } catch (err) {
      addNotification({
        type: "error",
        dismissible: true,
        header: "Save Rule",
        content: "Invalid JSON format" + JSON.stringify(err),
      });
      return;
    }

    let wpmRule: WPMRuleData;
    try {
      if (ruleGenerationType === "PRIORITIZING") {
        wpmRule = validatePrioritizingRule(parsedRule, schemas);
      } else {
        wpmRule = validateGroupingRule(parsedRule, schemas);
      }
    } catch (e) {
      console.warn("Validating rule failed", e);
      let content: string | ReactNode;
      if (e instanceof RuleValidationError && e.errors.length > 0) {
        content = (
          <ul>
            {e.errors.map((em, i) => (
              <li key={i}>{em}</li>
            ))}
          </ul>
        );
      } else {
        content = e instanceof Error ? e.message : UNEXPECTED_ERROR;
      }
      addNotification({
        type: "error",
        dismissible: true,
        header: "Rule JSON Validation Failed",
        content,
      });
      return;
    }

    setIsSaving(true);
    try {
      let result;

      if (isEditMode && editingRule && editingRule.rule_id) {
        result = await userApiClient.putItem(editingRule.rule_id, wpmRule, Schemas.WPMRule.name, wpmRule.rule_type);
      } else {
        result = await userApiClient.createRule(wpmRule);
      }

      // Check if response contains errors
      if (result?.errors) {
        const errorMessages = parsePUTResponseErrors(result.errors);
        addNotification({
          type: "error",
          dismissible: true,
          header: isEditMode ? "Update Rule" : "Save Rule",
          content: errorMessages.join(", "),
        });
      } else {
        addNotification({
          type: "success",
          dismissible: true,
          header: isEditMode ? "Update Rule" : "Save Rule",
          content: isEditMode ? "Rule updated successfully!" : "Rule saved successfully!",
        });
        navigate("/admin/wave-planning", { state: { activeTab: "planning-rules" } });
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      addNotification({
        type: "error",
        dismissible: true,
        header: isEditMode ? "Update Rule" : "Save Rule",
        content: err.message || "An error occurred while saving the rule",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const pageTitle = isEditMode ? `Edit Rule: ${editingRule?.rule_name || "Loading..."}` : "Rule Generator";
  const placeholder = React.useMemo(() => {
    if (ruleGenerationType === "PRIORITIZING") {
      return "Example: Score applications based on server storage size. Less sizes means less app complexity scores.";
    } else if (ruleGenerationType === "GROUPING") {
      return "Example: Group applications based on server operating system family.";
    }
    return "";
  }, [ruleGenerationType]);

  if (isLoadingRule) {
    return (
      <SpaceBetween size="l">
        <Button
          variant="link"
          onClick={() => navigate("/admin/wave-planning", { state: { activeTab: "planning-rules" } })}
          iconName="arrow-left"
        >
          Back to Planning Rules
        </Button>
        <Container header={<Header variant="h1">Loading Rule...</Header>}>
          <Box textAlign="center">
            <Spinner size="large" />
            <Box variant="p" margin={{ top: "s" }}>
              Loading rule data...
            </Box>
          </Box>
        </Container>
      </SpaceBetween>
    );
  }

  return (
    <SpaceBetween size="l">
      <Button
        variant="link"
        onClick={() => navigate("/admin/wave-planning", { state: { activeTab: "planning-rules" } })}
        iconName="arrow-left"
      >
        Back to Planning Rules
      </Button>
      <Container header={<Header variant="h1">{pageTitle}</Header>}>
        <SpaceBetween size="m">
          {editingRule?.isDefault && <Box>This is a system default rule. You can only enable or disable it.</Box>}

          {environment.GENAI_SUPPORTED === "true" && !(editingRule?.isDefault === true) && (
            <Container header={<Header variant="h2">Rule Description Prompt</Header>}>
              <SpaceBetween size="m">
                <Box>
                  <Box>
                    {`Describe your ${ruleGenerationType.toLowerCase()} rule in natural language and AI will generate the
                    structured JSON rule.`}
                  </Box>
                </Box>
                <Textarea
                  value={userInput}
                  onChange={({ detail }) => setUserInput(detail.value)}
                  placeholder={placeholder}
                  rows={4}
                  disabled={editingRule?.isDefault}
                />
                <Button
                  variant="primary"
                  onClick={handleGenerateRule}
                  loading={isLoading}
                  iconName="gen-ai"
                  disabled={editingRule?.isDefault}
                >
                  Generate Rule
                </Button>
              </SpaceBetween>
            </Container>
          )}

          <Container header={<Header variant="h2">Rule JSON</Header>}>
            <SpaceBetween size="m">
              <Textarea
                value={ruleJson}
                onChange={({ detail }) => setRuleJson(detail.value)}
                rows={20}
                placeholder="Generated rule will appear here or enter rule JSON manually..."
                disabled={editingRule?.isDefault}
              />
              <Button variant="primary" onClick={handleSaveRule} loading={isSaving} iconName="upload">
                {editingRule?.isDefault
                  ? editingRule.status === "ENABLED"
                    ? "Disable Rule"
                    : "Enable Rule"
                  : isEditMode
                    ? "Update Rule"
                    : "Save Rule"}
              </Button>
            </SpaceBetween>
          </Container>
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );
};

export default PlanningRuleForm;
