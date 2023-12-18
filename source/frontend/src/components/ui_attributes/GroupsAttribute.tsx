// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';
import {FormField, Multiselect, SpaceBetween} from '@awsui/components-react';
import {useValueLists} from "../../actions/ValueListsHook";

const GroupsAttribute = ({attribute, value, isReadonly, errorText, handleUserInput, displayHelpInfoLink}) => {

  const [localValue, setLocalValue] = useState([]);
  const [currentErrorText, setCurrentErrorText] = useState(errorText);
  const [currentVLErrorText, setCurrentVLErrorText] = useState(errorText);
  const [localOptions, setLocalOptions] = useState([]);

  const [{ isLoading: isLoadingVL, data: dataVL}, {update: updateVL , addValueListItem } ] = useValueLists();

  function returnStatusType() {
    if (attribute.listValueAPI && isLoadingVL && currentVLErrorText){
      return "error";
    } else if (attribute.listValueAPI && isLoadingVL) {
      return "loading"
    } else {
      return undefined
    }
  }

  function returnPlaceHolderText(){
    if ((localValue && localValue.length === 0) || (!localValue)) {
      return "Select " + attribute.description;
    } else {
      return localValue.length + ' ' + attribute.description + ' selected';
    }
  }

  function handleUpdate(detail){
    setLocalValue(detail.value);
    handleUserInput(detail)
  }

  useEffect( () => {
    if (attribute.type === 'groups' && attribute.listValueAPI) {
      addValueListItem(attribute.listValueAPI);
    }
    updateVL();
  }, [attribute])

  useEffect( () => {
    if ('listValueAPI' in attribute && !isLoadingVL && attribute.listValueAPI in dataVL) {
      //Attributes value list is obtained from a dynamic API call.
      let options = [];
      if (dataVL[attribute.listValueAPI].errorMessage !== undefined) {
        setCurrentVLErrorText(dataVL[attribute.listValueAPI].errorMessage);
        setLocalOptions(options);
      } else {
        options = dataVL[attribute.listValueAPI].values.map((item) => {
          return (
            {label: item, value: item}
          )
        });
        setLocalOptions(options);
      }
    }

  }, [isLoadingVL])

  useEffect(() => {
    setCurrentErrorText(errorText);
  }, [errorText]);

  useEffect( () => {
      setLocalValue(value);
  }, [value]);


  return (
    <FormField
      key={attribute.name}
      label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
      description={attribute.long_desc}
      errorText={currentErrorText}
    >
      <Multiselect
        selectedOptions={localValue == null ? [] : localValue.map(item => {return {label: item.group_name, value: item.group_name}})}
        onChange={event => handleUpdate({
          field: attribute.name,
          value: event.detail.selectedOptions.map(item => {return {group_name: item.value}}),
          validationError: currentErrorText
        })}
        statusType={returnStatusType()}
        loadingText={"Loading values..."}
        errortext={currentVLErrorText ? currentVLErrorText : undefined}
        options={localOptions}
        disabled={isReadonly}
        selectedAriaLabel={'Selected'}
        filteringType="auto"
        ariaLabel={attribute.name}
        placeholder={returnPlaceHolderText()}
      />
    </FormField>
  )
};

export default GroupsAttribute;
