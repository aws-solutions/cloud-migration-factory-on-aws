/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */


import React, {useEffect, useState} from 'react';
import {Button, Form, Header, SpaceBetween} from '@awsui/components-react';

import AllAttributes from './ui_attributes/AllAttributes'
import {capitalize, setNestedValuePath} from "../resources/main";
import {ClickEvent} from "../models/Events";
import {UserAccess} from "../models/UserAccess";
import {EntitySchema} from "../models/EntitySchema";
import {CMFModal} from "./Modal";

type ItemAmendParams = {
  item: any;
  handleSave: (arg0: any, arg1: any) => any;
  action: string;
  handleCancel: () => void;
  schemaName: string;
  schemas: Record<string, EntitySchema>;
  userAccess: UserAccess;
};


//Component used for providing generic edit record/item screen.
// All schema entities use this component.
const ItemAmend = (props: ItemAmendParams) => {

  const [localItem, setLocalItem] = useState(props.item);
  const [dataChanged, setDataChanged] = useState(false);
  const [validForm, setFormValidation] = useState(false);
  const [formErrors, setFormErrors] = useState<any[]>([]); //List of error messages on this form, these are displayed in the bottom of the form.
  const [isSaving, setIsSaving] = useState(false);

  const [isUnsavedConfirmationModalVisible, setUnsavedConfirmationModalVisible] = useState(false)


  async function handleUserInput(value: any[]) {
    let valueArray = [];
    let newRecord = Object.assign({}, localItem);

    //Convert non-Array values to array in order to keep procedure simple.
    if (Array.isArray(value)) {
      valueArray = value;
    } else {
      valueArray.push(value);
    }

    for (const valueItem of valueArray) {
      if (Array.isArray(valueItem.value)) {
        handleArrayInput(valueItem, newRecord);
      }
      else {
        setNestedValuePath(newRecord, valueItem.field, valueItem.value);
      }
    }

    setLocalItem(newRecord);
    setDataChanged(true);
  }

  const handleArrayInput = (valueItem: any, newRecord: any) => {
    if (valueItem.value.length > 0) {
      //Check first item to see if tag structure.
      if ((valueItem.value[0].existing === true || valueItem.value[0].existing === false) && 'key' in valueItem.value[0] && 'value' in valueItem.value[0]) {
        //It's a tag field!!
        handleTagField(valueItem, newRecord);
      }
      else {
        //Not a tag field just an array.
        //newRecord[value.field] = value.value;
        setNestedValuePath(newRecord, valueItem.field, valueItem.value);
      }
    }
    else {
      // Array to be emptied. Set as empty.
      setNestedValuePath(newRecord, valueItem.field, []);
    }
  }

  const handleTagField = (valueItem: any, newRecord: any) => {
    let updatedTags = valueItem.value.map((item: { existing: boolean | undefined; key: any; value: any; markedForRemoval: any; }) => {
      if (item.existing === false) {
        return {key: item.key, value: item.value};
      }

      if (item.existing && !item.markedForRemoval) {
        return {key: item.key, value: item.value};
      }
      return null;
    });

    setNestedValuePath(newRecord, valueItem.field, updatedTags);
  }

  const handleSave: any = async (e: ClickEvent) => {
    e.preventDefault();

    setIsSaving(true);

    await props.handleSave(localItem, props.action);

    setIsSaving(false);
  };

  const handleCancel: any = (e: ClickEvent) => {
    e.preventDefault();

    if (dataChanged) {
      setUnsavedConfirmationModalVisible(true);
    } else {
      props.handleCancel();
    }
  };

  function handleUpdateFormErrors(newErrors: any[]) {
    setFormErrors(newErrors);
  }

  useEffect(() => {
    if (formErrors.length === 0) {
      setFormValidation(true);
    } else {
      setFormValidation(false);
    }
  }, [formErrors]);


  function headerText() {
    let text = props.action ? capitalize(props.action + ' ' + props.schemaName) : capitalize(props.schemaName);

    if (props.schemas[props.schemaName].friendly_name) {
      text = props.action ? capitalize(props.action + ' ' + props.schemas[props.schemaName].friendly_name) : props.schemas[props.schemaName].friendly_name!;
    }

    return text;
  }

  return (
    <>
      <Form
        header={<Header variant="h1">{headerText()}</Header>}
        actions={
          // located at the bottom of the form
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={handleCancel} ariaLabel={'cancel'} variant="link">Cancel</Button>
            <Button onClick={handleSave} ariaLabel={'save'} disabled={!validForm} variant="primary" loading={isSaving}>
              Save
            </Button>
          </SpaceBetween>
        }
        errorText={formErrors.length > 0 ? formErrors.map((error: any, index: number) => {
            const displayKey = index;
            let errorReason = error.validation_regex_msg ? error.validation_regex_msg : 'You must specify a value.';
            return <p key={displayKey}>{error.description + ' - ' + errorReason}</p>
          }
        ) : undefined
        }
      >
        <AllAttributes
          schema={props.schemas[props.schemaName]}
          schemaName={props.schemaName}
          schemas={props.schemas}
          userAccess={props.userAccess}
          item={localItem}
          handleUserInput={handleUserInput}
          handleUpdateValidationErrors={handleUpdateFormErrors}
        />
      </Form>

      <CMFModal
        onDismiss={() => setUnsavedConfirmationModalVisible(false)}
        onConfirmation={props.handleCancel}
        visible={isUnsavedConfirmationModalVisible}
        header={'Unsaved changes'}
      >
        Changes made will be lost if you continue, are you sure?
      </CMFModal>
    </>
  );
};

export default ItemAmend;
