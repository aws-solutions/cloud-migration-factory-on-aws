/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

//Component used for providing generic edit record/item screen.
// All schema entities use this component.

import React, {useEffect, useState} from 'react';
import {
  SpaceBetween,
  Form,
  Header,
  Button
} from '@awsui/components-react';

import {useModal} from '../actions/Modal.js';
import AllAttributes from './ui_attributes/AllAttributes.jsx'
import {capitalize, setNestedValuePath} from "../resources/main";

const ItemAmend = (props) => {

  const [localItem, setLocalItem] = useState(props.item);
  const [dataChanged, setDataChanged] = useState(false);
  const [validForm, setFormValidation] = useState(false);
  const [formErrors, setFormErrors] = useState([]); //List of error messages on this form, these are displayed in the bottom of the form.
  const [isSaving, setIsSaving] = useState(false);

  //Modals
  const { show: showUnsavedConfirmaton, RenderModal: UnSavedModal } = useModal()

  async function handleUserInput (value){
    let valueArray = [];
    let newRecord = Object.assign({}, localItem);

    //Convert non-Array values to array in order to keep procedure simple.
    if(Array.isArray(value)){
      valueArray = value;
    } else {
      valueArray.push(value);
    }

    for (const valueItem of valueArray){
      if (Array.isArray(valueItem.value)){
        if(valueItem.value.length > 0){
          //Check first item to see if tag structure.
          if((valueItem.value[0].existing === true || valueItem.value[0].existing === false) && 'key' in valueItem.value[0] && 'value' in valueItem.value[0]){
            //It's a tag field!!
            let updatedTags = valueItem.value.map((item) => {
              if (item.existing === false)
              {
                return {key: item.key, value: item.value};
              }

              if (item.existing && !item.markedForRemoval) {
                return {key: item.key, value: item.value};
              }

              return null;

            });

            setNestedValuePath(newRecord, valueItem.field, updatedTags);

          } else {
            //Not a tag field just an array.
            //newRecord[value.field] = value.value;
            setNestedValuePath(newRecord, valueItem.field, valueItem.value);
          }
        } else {
          // Array to be emptied. Set as empty.
          setNestedValuePath(newRecord, valueItem.field, []);
        }
      }
      else {
        setNestedValuePath(newRecord, valueItem.field, valueItem.value);
      }
    }

    setLocalItem(newRecord);
    setDataChanged(true);
  }

  async function handleSave (e){
    e.preventDefault();

    setIsSaving(true);

    await props.handleSave(localItem, props.action);

    setIsSaving(false);
  }

  function handleCancel (e){
    e.preventDefault();

    if (dataChanged){
      showUnsavedConfirmaton();
    } else {
      props.handleCancel(e);
    }
  }

  function handleUpdateFormErrors (newErrors){
    setFormErrors(newErrors);
  }

  useEffect(() => {
    if (formErrors.length === 0){
      setFormValidation(true);
    } else {
      setFormValidation(false);
    }
  }, [formErrors]);


  function headerText() {
    let text = props.action ? capitalize(props.action + ' ' + props.schemaName) : capitalize(props.schemaName);

    if (props.schemas[props.schemaName].friendly_name) {
      text = props.action ? capitalize(props.action + ' ' + props.schemas[props.schemaName].friendly_name) : props.schemas[props.schemaName].friendly_name;
    }

    return text;
  }

  return (
    <div>
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
        errorText={formErrors.length > 0 ? formErrors.map(error => {
            let errorReason = error.validation_regex_msg ? error.validation_regex_msg : 'You must specify a value.';
            return <p key={error.description + ' - ' + errorReason}>{error.description + ' - ' + errorReason}</p>}): undefined
        }
      >
          <SpaceBetween size="l">
            <AllAttributes
                schema={props.schemas[props.schemaName]}
                schemaName={props.schemaName}
                schemas={props.schemas}
                userAccess={props.userAccess}
                item={localItem}
                handleUserInput={handleUserInput}
                handleUpdateValidationErrors={handleUpdateFormErrors}
                setHelpPanelContent={props.setHelpPanelContent}
            />

          </SpaceBetween>
      </Form>
      <UnSavedModal title={'Unsaved changes'} onConfirmation={props.handleCancel}>Changes made will be lost if you continue, are you sure?</UnSavedModal>
    </div>
  );
};

export default ItemAmend;
