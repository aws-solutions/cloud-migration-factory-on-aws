import React from 'react';
import {
  SpaceBetween,
  Form,
  Container,
  Header,
  Button
 } from '@awsui/components-react';
import AllAttributes from './ui_attributes/AllAttributes.jsx'

import { useModal } from '../actions/Modal.js';
import { setNestedValuePath } from '../resources/main';
import { useState } from 'react';

const AutomationTools = (props) => {

  const [localTool, setLocalTool] = useState(props.selectedItems ? populateTool(props.selectedItems) : {});
  const [dataChanged, setDataChanged] = useState(false);
  const [validForm, setFormValidation] = useState(true);
  //const [preformingAction, setPreformingAction] = useState(false);

  const [formErrors, setFormErrors] = useState([]);

  //Modals
  const { show: showUnsavedConfirmaton, hide: hideUnsavedConfirmaton, RenderModal: UnSavedModal } = useModal()


  function populateTool (items) {

    if (items.length == 0) {
      return {};
    }

    let relationshipAttributes = props.schema.attributes.filter(function (item) {
      return item.type === 'relationship';
    });

    if (relationshipAttributes.length > 0){
      //some values to prepopulate.
      let newTool = {};
      for (let attrIdx = 0; attrIdx < relationshipAttributes.length; attrIdx++){
        if(items[0][relationshipAttributes[attrIdx].rel_key]){
          newTool[relationshipAttributes[attrIdx].name] = items[0][relationshipAttributes[attrIdx].rel_key];
        }
      }
      return newTool;
    } else {
      return {};
    }

  }

  function handleUserInput (value){

    let newItem = Object.assign({}, localTool);

    if(Array.isArray(value)){
      //Multiple values set.
      for (const item of value){
        setNestedValuePath(newItem, item.field, item.value);
      }
    } else {
      setNestedValuePath(newItem, value.field, value.value);
    }

    //newItem[value.field] = value.value;
    // if (value.validationError){
    //   if (value.validationError !== null){
    //     setFormValidation(false)
    //   } else {
    //     setFormValidation(true)
    //   }
    // } else {
    //   setFormValidation(true)
    // }

    setLocalTool(newItem);
    setDataChanged(true);

  }

  function handleAction (e, actionId){


      props.handleAction(localTool, actionId);

  }

  function handleUpdateFormErrors (newErrors){

    setFormErrors(newErrors);

    if (newErrors.length > 0){
      setFormValidation(false);
    } else {
      setFormValidation(true);
    }

  }

  function handleCancel (e){

    if (dataChanged){
      showUnsavedConfirmaton();
    } else {
      props.handleCancel(e);
    }
  }

  function getActionButtons() {

    let allActions = props.schema.actions.map((action, indx) => {
      return (
        <Button id={action.id} onClick={e => handleAction(e, action.id)} disabled={!validForm} variant={action.awsuiStyle} loading={props.performingAction}>
          {action.name}
        </Button>
      )
    });
    return allActions;
  }

  return (
    <div>
      <Form
        header={<Header variant="h1">{props.schema.description}</Header>}
        actions={
          // located at the bottom of the form
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={handleCancel} variant="link">Cancel</Button>
            {getActionButtons()}
          </SpaceBetween>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          <Container header={<Header variant="h2">{props.schema.friendly_name + ' Attributes'}</Header>}>
            <SpaceBetween size="l">
              <AllAttributes
                  schema={props.schema}
                  schemas={props.schemas}
                  schemaName={props.schemaName}
                  userAccess={props.userAccess}
                  hideAudit={true}
                  item={localTool}
                  handleUserInput={handleUserInput}
                  handleUpdateValidationErrors={handleUpdateFormErrors}/>
            </SpaceBetween>
          </Container>
        </SpaceBetween>
      </Form>
      <UnSavedModal title={'No action'} onConfirmation={props.handleCancel}>You have not performed an action, are you sure?</UnSavedModal>
    </div>
  );
};

export default AutomationTools;
