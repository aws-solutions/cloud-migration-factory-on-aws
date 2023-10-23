// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useState} from 'react';
import {
  SpaceBetween,
  Form,
  Header,
  Button
} from '@awsui/components-react';
import AllAttributes from './ui_attributes/AllAttributes'

import {useModal} from '../actions/Modal';

const AutomationScriptAmend = (props) => {

  const [localItem, setLocalItem] = useState(props.item);
  const [dataChanged, setDataChanged] = useState(false);
  const [validForm, setFormValidation] = useState(false);

  //Modals
  const { show: showUnsavedConfirmaton, RenderModal: UnSavedModal } = useModal()

  function handleUserInput (value){

    let newRecord = Object.assign({}, localItem);

    if (Array.isArray(value.value)){
      if(value.value.length > 0){
        //Check first item to see if tag structure.
        if(value.value[0].existing && value.value[0].key && value.value[0].value){
          //Its a tag field!!
          let updatedTags = value.value.map((item, index) => {
            if (item.existing === false)
            {
              return {key: item.key, value: item.value};
            }

            if (item.existing && !item.markedForRemoval) {
              return {key: item.key, value: item.value};
            }

            return null;

          });

          newRecord[value.field] = updatedTags;

        } else {
          //Not a tag field just an array.
          newRecord[value.field] = value.value;
        }
      }
    }
    else {
      newRecord[value.field] = value.value;
    }

    if (value.validationError){
      if (value.validationError !== null){
        setFormValidation(false)
      } else {
        setFormValidation(true)
      }
    } else {
      setFormValidation(true)
    }

    setLocalItem(newRecord);
    setDataChanged(true);
  }

  function handleSave (e){

    props.handleSave(localItem, props.action)
  }

  function handleCancel (e){

    if (dataChanged){
      showUnsavedConfirmaton();
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
        header={<Header variant="h1">{props.action} Automation Script</Header>}
        actions={
          // located at the bottom of the form
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={handleCancel} variant="link">Cancel</Button>
            <Button onClick={handleSave} disabled={!validForm || !dataChanged} variant="primary">
              Save application
            </Button>
          </SpaceBetween>
        }
      >
          <SpaceBetween size="l">
            <AllAttributes
                schema={props.schema}
                schemas={props.schema}
                item={localItem}
                handleUserInput={handleUserInput}
                handleUpdateValidationErrors={handleUpdateFormErrors}/>
          </SpaceBetween>
      </Form>
      <UnSavedModal title={'Unsaved changes'} onConfirmation={props.handleCancel}>Changes made will be lost if you continue, are you sure?</UnSavedModal>
    </div>
  );
};

export default AutomationScriptAmend;
