/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

//Component used for providing generic edit record/item screen.
// All schema entities use this component.

import React, {useState} from 'react';
import {
  SpaceBetween,
  Form,
  Header,
  Button
} from '@awsui/components-react';

import {useModal} from '../actions/Modal.js';
import AllAttributes from './ui_attributes/AllAttributes.jsx'
import {setNestedValuePath} from "../resources/main";

const PolicyAmend = (props) => {

  const [localItem, setLocalItem] = useState(props.item);
  const [dataChanged, setDataChanged] = useState(false);
  const [validForm, setFormValidation] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  //Modals
  const { show: showUnsavedConfirmation, RenderModal: UnSavedModal } = useModal()

  async function handleUserInput (value){
    let valueArray = [];
    let localFormValidation = true;
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
          if(valueItem.value[0].existing && valueItem.value[0].key && valueItem.value[0].value){
            //Its a tag field!!
            let updatedTags = valueItem.value.map((item, index) => {
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
            setNestedValuePath(newRecord, valueItem.field, valueItem.value);
          }
        }
      }
      else {
        setNestedValuePath(newRecord, valueItem.field, valueItem.value);
      }

      if (valueItem.validationError){
        if (valueItem.validationError !== null){
          //Error found so set error flag for record.
          if (localFormValidation) localFormValidation = false
        }
      }
    }

    setFormValidation(localFormValidation)
    setLocalItem(newRecord);
    setDataChanged(true);
  }

  function handleSave (e){
    e.preventDefault();

    setIsSaving(true);

    props.handleSave(localItem, props.action);
  }

  function handleCancel (e){
    e.preventDefault();

    if (dataChanged){
      showUnsavedConfirmation();
    } else {
      props.handleCancel(e);
    }
  }

  function handleUpdateFormErrors (newErrors){

    if (newErrors.length > 0){
      setFormValidation(false);
    } else {
      setFormValidation(true);
    }
  }

  return (
    <div>
      <Form
        header={<Header variant="h1">{(props.action ? props.action + ' ' + props.schemaName : props.schemaName)}</Header>}
        actions={
          // located at the bottom of the form
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={handleCancel} variant="link">Cancel</Button>
            <Button onClick={handleSave} disabled={!validForm} variant="primary" loading={isSaving}>
              Save wave
            </Button>
          </SpaceBetween>
        }
      >
          <SpaceBetween size="l">
            <AllAttributes
                schema={props.schemas[props.schemaName]}
                schemas={props.schemas}
                item={localItem}
                handleUserInput={handleUserInput}
                handleUpdateValidationErrors={handleUpdateFormErrors}/>
          </SpaceBetween>
      </Form>
      <UnSavedModal title={'Unsaved changes'} onConfirmation={props.handleCancel}>Changes made will be lost if you continue, are you sure?</UnSavedModal>
    </div>
  );
};

export default PolicyAmend;
