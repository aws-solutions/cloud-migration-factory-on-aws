// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';
import {
  Checkbox, SpaceBetween,
} from '@awsui/components-react';

// Attribute Display message content
const CheckboxAttribute = ({attribute, value, isReadonly, handleUserInput, displayHelpInfoLink}) => {

  const [localValue, setLocalValue] = useState(value);

  function handleUpdate(update){
    setLocalValue(update.value);
    handleUserInput(update)
  }

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  return (
    <Checkbox
      key={attribute.name}
      onChange={event => handleUpdate({field: attribute.name, value: event.detail.checked, validationError: null})}
      checked={localValue}
      disabled={isReadonly}
      ariaLabel={attribute.name}
    >
      {attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
    </Checkbox>
  )
};

export default CheckboxAttribute;
