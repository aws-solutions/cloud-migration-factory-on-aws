/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  SpaceBetween, FormField, Multiselect, Grid, Select, Button
} from '@awsui/components-react';
import RelatedRecordPopover from "./RelatedRecordPopover";

const RelationshipAttribute = ({schemas, attribute, value, options, record, isReadonly, errorText, handleUserInput, displayHelpInfoLink}) => {

  const [localValue, setLocalValue] = useState(value);
  const [localRelatedRecord, setLocalRelatedRecord] = useState(record);
  const [localSchemas, setLocalSchemas] = useState(schemas);
  const [currentErrorText, setCurrentErrorText] = useState(errorText);
  const [localOptions, setLocalOptions] = useState([]);

  async function handleUpdate(event){
    setLocalValue(event.detail.selectedOption.value);
    handleUserInput(attribute, event.detail.selectedOption.value, currentErrorText)
  }

  function handleClearSelection(){
    setLocalValue('');
    handleUserInput(attribute, '', currentErrorText)
  }

  function displayRelatedRecordPopover(record){
    if ((localValue && localValue !== '') && !((record===null) || (attribute.listMultiSelect) || (attribute?.listvalue && attribute?.listvalue.includes(localValue)))){
      //TODO Implement way to provide this functionality with multiselect.
      return <RelatedRecordPopover key={attribute.name}
                            item={localRelatedRecord}
                            schema={localSchemas[attribute.rel_entity]}
                            schemas={localSchemas}>
        Related details
      </RelatedRecordPopover>
    } else {
      return undefined;
    }
  }

  function getUpdatedPolicies(event){
    if(event.detail.selectedOptions.length > 0 && event.detail.selectedOptions.find(valueItem => {return valueItem.value === '__system_all'})){
      return localOptions
        .filter(valueItem => {return valueItem.value !== '__system_all'})  // remove __system_all from the list as only used to select all.
        .map(valueItem => valueItem.value)
    } else if (event.detail.selectedOptions.length > 0){
      return event.detail.selectedOptions.map(valueItem => valueItem.value)
    } else {
      return [];
    }
  }

  function getPlaceholder(attribute, value){
    if (value?.value && value.value.length > 0){
      return value.value.length + ' ' + attribute.description + ' selected'
    } else {
      return "Select " + attribute.description
    }
  }


  useEffect(() => {
    setCurrentErrorText(errorText);
  }, [errorText]);

  useEffect( () => {
      setLocalValue(value);
  }, [value]);


  useEffect( () => {
    setLocalRelatedRecord(record);
  }, [record]);

  useEffect( () => {
    setLocalOptions(options);
  }, [options]);

  useEffect( () => {
    setLocalSchemas(schemas);
  }, [schemas]);

  return (

    <FormField
      key={attribute.name}
      label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
      description={attribute.long_desc}
      errorText={currentErrorText}
    >
      {attribute.listMultiSelect
        ?
        <Multiselect
          selectedOptions={localRelatedRecord == null ? [] : localRelatedRecord.map(item => {return {'label': item[attribute.rel_display_attribute], 'value': item[attribute.rel_key]}})}
          onChange={event => handleUserInput(attribute,
            getUpdatedPolicies(event),
            errorText
          )}
          loadingText={"Loading " + attribute.rel_entity + "s"}
          // statusType={undefined}
          options={localOptions}
          disabled={isReadonly}
          selectedAriaLabel={'selected'}
          filteringType="auto"
          placeholder={getPlaceholder(attribute, localValue)}
        />
        :
        <Grid
          gridDefinition={[{ colspan: 10}, { colspan: 2 }]}
        >
          <SpaceBetween
            size="xxxs"
            key={attribute.name}
          >
            <Select
              selectedOption={localValue}
              onChange={event => handleUpdate(event)}
              loadingText={"Loading " + attribute.rel_entity + "s"}
              statusType={localValue.status === 'loading' ? "loading" : undefined}
              options={localOptions}
              selectedAriaLabel={'selected'}
              disabled={isReadonly}
              placeholder={"Choose " + attribute.description}
            />
            {
              displayRelatedRecordPopover(attribute)
            }
          </SpaceBetween>
          <Button iconName="close" variant="normal" disabled={isReadonly} onClick={() => handleClearSelection()}>Clear</Button>
        </Grid>
      }
    </FormField>
  )


};

export default RelationshipAttribute;
