/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useState} from "react";
import {Button, Container, Form, Header, SpaceBetween} from "@cloudscape-design/components";
import AllAttributes from "./ui_attributes/AllAttributes";

import {setNestedValuePath} from "../resources/main";
import {EntitySchema} from "../models/EntitySchema";
import {UserAccess} from "../models/UserAccess";
import {CMFModal} from "./Modal";

type AutomationToolsParams = {
  selectedItems: any;
  schema: EntitySchema;
  handleAction: (arg0: {}, arg1: any) => void;
  handleCancel: () => void;
  performingAction: boolean | undefined;
  schemas: Record<string, EntitySchema>;
  schemaName: string;
  userAccess: UserAccess;
};

type AttributeUpdateRequest = {
  field: string;
  value: any;
  validationError?: any;
};

const AutomationTools = (props: AutomationToolsParams) => {
  const [localTool, setLocalTool] = useState(props.selectedItems ? populateTool(props.selectedItems) : {});
  const [dataChanged, setDataChanged] = useState(false);
  const [validForm, setFormValidation] = useState(true);

  const [isNoActionModalVisible, setNoActionModalVisible] = useState(false);

  function populateTool(items: any[]) {
    if (items.length == 0) {
      return {};
    }

    let relationshipAttributes = props.schema.attributes.filter(function (item: { type: string }) {
      return item.type === "relationship";
    });

    if (relationshipAttributes.length > 0) {
      //some values to prepopulate.
      let newTool: any = {};
      for (const relAttribute of relationshipAttributes) {
        if (items[0][relAttribute.rel_key!]) {
          newTool[relAttribute.name] = items[0][relAttribute.rel_key!];
        }
      }
      return newTool;
    } else {
      return {};
    }
  }

  function handleUserInput(value: AttributeUpdateRequest[] | AttributeUpdateRequest) {
    let newItem = Object.assign({}, localTool);

    if (Array.isArray(value)) {
      for (const item of value) {
        setNestedValuePath(newItem, item.field, item.value);
      }
    } else {
      setNestedValuePath(newItem, value.field, value.value);
    }

    setLocalTool(newItem);
    setDataChanged(true);
  }

  function handleAction(e: CustomEvent<any>, actionId: any) {
    props.handleAction(localTool, actionId);
  }

  function handleUpdateFormErrors(newErrors: any[]) {
    if (newErrors.length > 0) {
      setFormValidation(false);
    } else {
      setFormValidation(true);
    }
  }

  function handleCancel() {
    if (dataChanged) {
      setNoActionModalVisible(true);
    } else {
      props.handleCancel();
    }
  }

  function getActionButtons() {
    return props.schema.actions?.map((action: any) => {
      return (
        <Button
          key={action.id}
          id={action.id}
          onClick={(e) => handleAction(e, action.id)}
          disabled={!validForm}
          variant={action.awsuiStyle}
          loading={props.performingAction}
        >
          {action.name}
        </Button>
      );
    });
  }

  return (
    <div>
      <Form
        header={<Header variant="h1">{props.schema.description}</Header>}
        actions={
          // located at the bottom of the form
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={handleCancel} variant="link">
              Cancel
            </Button>
            {getActionButtons()}
          </SpaceBetween>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          <Container header={<Header variant="h2">{props.schema.friendly_name + " Attributes"}</Header>}>
            <SpaceBetween size="l">
              <AllAttributes
                schema={props.schema}
                schemas={props.schemas}
                schemaName={props.schemaName}
                userAccess={props.userAccess}
                hideAudit={true}
                item={localTool}
                handleUserInput={handleUserInput}
                handleUpdateValidationErrors={handleUpdateFormErrors}
              />
            </SpaceBetween>
          </Container>
        </SpaceBetween>
      </Form>

      <CMFModal
        onDismiss={() => setNoActionModalVisible(false)}
        visible={isNoActionModalVisible}
        header={"No action"}
        onConfirmation={props.handleCancel}
      >
        You have not performed an action, are you sure?
      </CMFModal>
    </div>
  );
};

export default AutomationTools;
