// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';
import {Button, FormField, Grid, Multiselect, Select, SpaceBetween} from '@awsui/components-react';
import {useValueLists} from "../../actions/ValueListsHook";

const ListAttribute = ({attribute, value, isReadonly, errorText, handleUserInput, displayHelpInfoLink}) => {

  const [localValue, setLocalValue] = useState('');
  const [currentErrorText, setCurrentErrorText] = useState(errorText);
  const [currentVLErrorText, setCurrentVLErrorText] = useState(undefined);
  const [localOptions, setLocalOptions] = useState([]);

  const [{ isLoading: isLoadingVL, data: dataVL}, {update: updateVL , addValueListItem } ] = useValueLists();

  function handleUpdate(detail){
    setLocalValue(detail.value);
    handleUserInput([detail])
  }

  function getStatusType(attribute){
    if (attribute.listValueAPI && isLoadingVL){
      return "loading";
    } else if (currentVLErrorText){
      return "error";
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

  useEffect( () => {

    if (!attribute) {
      return;
    }

    if (attribute.type === 'list' && attribute.listValueAPI) {
      addValueListItem(attribute.listValueAPI);
      updateVL();
    }
  }, [attribute]);

  function getTags(item) {
    const tags = [];
    for (const key in item) {
      //Add value of child key to tags, if not the main key
      if (key !== attribute.labelKey) {
        tags.push(item[key])
      }
    }
    return tags;
  }

  useEffect( () => {
    if ('listvalue' in attribute) {
      let options = attribute.listvalue.split(',');
      options = options.map((item) => {
        return (
          {label: item, value: item}
        )
      })

      setLocalOptions(options);
    } else if ('listValueAPI' in attribute && !isLoadingVL && attribute.listValueAPI in dataVL) {
      //Attributes value list is obtained from a dynamic API call.
      if (dataVL[attribute.listValueAPI].errorMessage !== undefined) {
        let options = [];
        let errorMessage = dataVL[attribute.listValueAPI].errorMessage;
        if (errorMessage) {
          setCurrentVLErrorText(errorMessage);
        }
        setCurrentVLErrorText(undefined);
        setLocalOptions(options);
        return options;
      } else {
        let options = dataVL[attribute.listValueAPI].values.map((item) => {
          return (
            {label: item[attribute.labelKey], value: item[attribute.valueKey], tags: getTags(item)}

          )
        });

        setLocalOptions(options);
      }
    }

  }, [attribute, dataVL]);

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
      {attribute.listMultiSelect
        ?
        <Multiselect
          selectedOptions={localValue == null ? [] : localValue.map(item => {return {'value': item, 'label': item}})}
          onChange={event => handleUpdate({
            field: attribute.name,
            value: event.detail.selectedOptions.map(item => {return item.value}),
            validationError: currentErrorText
          })}
          statusType={getStatusType(attribute)}
          loadingText={"Loading values..."}
          errortext={currentVLErrorText ? currentVLErrorText : undefined}
          options={localOptions}
          disabled={isReadonly}
          selectedAriaLabel={'Selected'}
          filteringType="auto"
          ariaLabel={attribute.name}
          placeholder={getPlaceholder(attribute, value)}
        />
        :
        <Grid
          gridDefinition={[{ colspan: 10}, { colspan: 2 }]}
        >
          <Select
            selectedOption={localValue ? {
              label: localValue,
              value: localValue
            } : null}
            onChange={event => handleUpdate({
              field: attribute.name,
              value: event.detail.selectedOption.value,
              validationError: currentErrorText
            })}
            statusType={getStatusType(attribute)}
            loadingText={"Loading values..."}
            errortext={currentVLErrorText ? currentVLErrorText : undefined}
            options={localOptions}
            disabled={isReadonly}
            selectedAriaLabel={'Selected'}
            placeholder={"Select " + attribute.description}
            ariaLabel={attribute.name}
          />
          <Button iconName="close" variant="normal" ariaLabel={attribute.name + '-clear'} disabled={isReadonly} onClick={() => handleUpdate({
            field: attribute.name,
            value: ''
          })}>Clear</Button>
        </Grid>
      }
    </FormField>
  )
};

export default ListAttribute;
