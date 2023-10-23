// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  SpaceBetween, FormField, Multiselect, Spinner
} from '@awsui/components-react';

const PoliciesAttribute = ({attribute, value, isReadonly, options, errorText, handleUserInput, displayHelpInfoLink}) => {

  const [localValue, setLocalValue] = useState(value);
  const [selectedOptions, setSelectedOptions] = useState([]);
  const [currentErrorText, setCurrentErrorText] = useState(errorText);
  const [resolvedOptions, setResolvedOptions] = useState(true);

  function handleUpdate(attribute, value, validationError){
    setLocalValue(value);
    handleUserInput(attribute, value, validationError)
  }

  function getStatusType(){
    if(localValue && resolvedOptions){
      return "loading"
    } else {
      return undefined;
    }
  }

  function getPlaceholder(attribute, value){
    if (value && value.length > 0){
      return value.length + ' ' + attribute.description + ' selected'
    } else {
      return "Select " + attribute.description
    }
  }

  function getUpdatedPolicies(event){
    if(event.detail.selectedOptions.length > 0 && event.detail.selectedOptions.find(valueItem => {return valueItem.value === '__system_all'})){
      return options
        .filter(valueItem => {return valueItem.value !== '__system_all'})  // remove __system_all from the list as only used to select all.
        .map(valueItem => {return {policy_id: valueItem.value}})
    } else if (event.detail.selectedOptions.length > 0){
      return event.detail.selectedOptions.map(valueItem => {return {policy_id: valueItem.value}})
    } else {
      return [];
    }
  }

  useEffect( () => {

    let selectedOptions = [];
    if (localValue && options.length > 1 && localValue.length > 0) {
        selectedOptions = options.filter(itemOption => {
          for (const selectedOption of localValue) {
            if (selectedOption.policy_id === itemOption.value) {
              //Valid selection.
              return true;
            }
          }
          //Selection not valid.
          return false;
        });
      setSelectedOptions(selectedOptions)
    }

  }, [localValue, options])

  useEffect(() => {
    setCurrentErrorText(errorText);
  }, [errorText]);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  useEffect(() => {
    if (options.length > 1){
      setResolvedOptions(false);
    } else {
      setResolvedOptions(true);
    }
  }, [options]);

  return (
    <FormField
      key={attribute.name}
      label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
      description={attribute.long_desc}
      errorText={currentErrorText}
    >
      <Multiselect
        selectedOptions={selectedOptions}
        disabled={isReadonly}
        onChange={event => handleUpdate(attribute,
          getUpdatedPolicies(event),
          errorText
        )}
        statusType={getStatusType()}
        loadingText={"Loading values..."}
        errortext={currentErrorText}
        options={options}
        selectedAriaLabel={'Selected'}
        filteringType="auto"
        placeholder={getPlaceholder(attribute,localValue)}
        ariaLabel={attribute.name}
      />
      {resolvedOptions ? <div><Spinner size="normal" /> Resolving IDs.. </div>: undefined}
    </FormField>
  )
};

export default PoliciesAttribute;
