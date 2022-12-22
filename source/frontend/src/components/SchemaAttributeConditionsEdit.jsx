/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  FormField,
  Input,
  SpaceBetween,
  Select,
  Container,
  Header,
  Button, Multiselect
} from "@awsui/components-react";
import React from "react";
import {capitalize} from "../resources/main";

const SchemaAttributeConditionsEdit = ({editingSchemaConditionsTemp, handleUserInputEditSchemaConditions, schemaAttributes, editDisabled}) => {

  //Selection options.
  const outcomeValues = [{label: 'Required', value: 'required'}, {label: 'Not required', value: 'not_required'}, {label: 'Hidden', value: 'hidden'}, {label: 'Not hidden', value: 'not_hidden'}];
  const comparatorOperators = [{label: '=', value: '='}, {label: '!=', value: '!='}, {label: '!empty', value: '!empty'}, {label: 'empty', value: 'empty'}];

  //Data access keys.
  const trueOutcomeKey = 'true';
  const falseOutcomeKey = 'false';
  const queriesKey = 'conditions.queries';
  const queriesAttributeKey = 'attribute';
  const queriesComparatorKey = 'comparator';
  const queriesValueKey = 'value';
  const outcomesKey = 'conditions.outcomes';

  //UI Messages.
  const messages = {
    conditionsContainerHeader: 'If this...',
    outcomesContainerHeader: 'then...',
    attributeFieldNameLabel: 'Attribute',
    valueFieldNameLabel: 'Attribute Value',
    comparatorFieldNameLabel: 'Matching Operator',
    selectOutcomePlaceholder: 'Select outcome.',
    addButtonLabel: 'Add',
    deleteButtonLabel: 'Delete',
    elseFieldNameLabel: 'Attribute will be',
    thenFieldNameLabel: 'Attribute will be'
  }


  let conditions = [];
  let outcomes = [];

  if (editingSchemaConditionsTemp.queries) {
    conditions = editingSchemaConditionsTemp.queries.map((query, index) => {
      return <Container key={queriesKey + '.'+ index} header={<Header
        variant="h2"
        actions={
          <SpaceBetween
            direction="horizontal"
            size="xs"
          >
            <Button onClick={() => handleUserInputEditSchemaConditions(queriesKey + '.'+ index + '', undefined)} disabled={editDisabled}>{messages.deleteButtonLabel}</Button>
          </SpaceBetween>
        }
      >
        {'Condition ' + (index + 1)}
      </Header>}>

        <SpaceBetween size={'xl'} direction={'vertical'}>
          <FormField
            label={messages.attributeFieldNameLabel}
          >
            <Select
              selectedOption={query.attribute ? {value: query.attribute, label: query.attribute} : ''}
              onChange={event => handleUserInputEditSchemaConditions(queriesKey + '.'+ index + '.' + queriesAttributeKey, event.detail.selectedOption.value)}
              options={
                schemaAttributes.map((item) => {
                  return {label: item.name, value: item.name};
                })
              }
              selectedAriaLabel={'selected'}
              disabled={editDisabled}
            />
          </FormField>
          <FormField
            label={messages.comparatorFieldNameLabel}
          >
            <Select
              selectedOption={query.comparator ? {value: query.comparator, label: query.comparator} : ''}
              onChange={event => handleUserInputEditSchemaConditions(queriesKey + '.'+ index + '.' + queriesComparatorKey, event.detail.selectedOption.value)}
              options={comparatorOperators}
              selectedAriaLabel={'selected'}
              disabled={editDisabled}
            />
          </FormField>
          {query.comparator !== '!empty' && query.comparator !== 'empty' ?
            <FormField
              label={messages.valueFieldNameLabel}
            >
              <Input
                onChange={event => handleUserInputEditSchemaConditions(queriesKey + '.' + index + '.' + queriesValueKey, event.detail.value)}
                value={query.value ? query.value : ''}
                disabled={editDisabled}
              />
            </FormField>
          :
            undefined
          }

        </SpaceBetween>
      </Container>
    })

      outcomes.push(<Container key={outcomesKey + '.' + trueOutcomeKey} header={<Header
          variant="h2"
          actions={
            <SpaceBetween
              direction="horizontal"
              size="xs"
            >
            </SpaceBetween>
          }
        >
          Then...
        </Header>}>
        <FormField
          label={messages.thenFieldNameLabel}
        >
          <Multiselect
            selectedOptions={editingSchemaConditionsTemp.outcomes ? editingSchemaConditionsTemp.outcomes[trueOutcomeKey] ? editingSchemaConditionsTemp.outcomes[trueOutcomeKey].map((item) => {
              return {label: item, value: item}
            }) : [] : []}
            onChange={event => handleUserInputEditSchemaConditions(outcomesKey + '.' + trueOutcomeKey, event.detail.selectedOptions ? event.detail.selectedOptions.map(item => {
              return item.value
            }) : [])}
            options={outcomeValues}
            selectedAriaLabel={'selected'}
            disabled={editDisabled}
            placeholder={editingSchemaConditionsTemp.outcomes ? editingSchemaConditionsTemp.outcomes[trueOutcomeKey] ? editingSchemaConditionsTemp.outcomes[trueOutcomeKey].length > 0 ? editingSchemaConditionsTemp.outcomes[trueOutcomeKey].join(', ') + ' selected' : messages.selectOutcomePlaceholder : messages.selectOutcomePlaceholder : messages.selectOutcomePlaceholder}
          />
        </FormField>
        </Container>
      );

      outcomes.push(<Container key={outcomesKey + '.' + falseOutcomeKey} header={<Header
          variant="h2"
          actions={
            <SpaceBetween
              direction="horizontal"
              size="xs"
            >
            </SpaceBetween>
          }
        >
          Else...
        </Header>}>
        <FormField
          label={messages.elseFieldNameLabel}
        >
          <Multiselect
            selectedOptions={editingSchemaConditionsTemp.outcomes ? editingSchemaConditionsTemp.outcomes[falseOutcomeKey] ? editingSchemaConditionsTemp.outcomes[falseOutcomeKey].map((item) => {
              return {label: item, value: item}
            }) : [] : []}
            onChange={event => handleUserInputEditSchemaConditions(outcomesKey + '.' + falseOutcomeKey, event.detail.selectedOptions ? event.detail.selectedOptions.map(item => {
              return item.value
            }) : [])}
            options={outcomeValues}
            selectedAriaLabel={'selected'}
            disabled={editDisabled}
            placeholder={editingSchemaConditionsTemp.outcomes ? editingSchemaConditionsTemp.outcomes[falseOutcomeKey] ? editingSchemaConditionsTemp.outcomes[falseOutcomeKey].length > 0 ? editingSchemaConditionsTemp.outcomes[falseOutcomeKey].join(', ') + ' selected' : messages.selectOutcomePlaceholder : messages.selectOutcomePlaceholder : messages.selectOutcomePlaceholder}
          />
        </FormField>
        </Container>
      );


  }

  if (editingSchemaConditionsTemp) {
    return (<Container header={<Header
      variant="h2"
    >
      Conditions and Outcomes
    </Header>}>
      <SpaceBetween direction={'vertical'} size={'xs'}>
      <Container
        header={
        <Header
          variant="h2"
          actions={
            <SpaceBetween
              direction="horizontal"
              size="xs"
            >
              <Button onClick={() => handleUserInputEditSchemaConditions(queriesKey + '.+1', {})} disabled={editDisabled}>{messages.addButtonLabel}</Button>
            </SpaceBetween>
          }
        >
          {messages.conditionsContainerHeader}
      </Header>}
      >
        <SpaceBetween direction={'vertical'} size={'xs'}>
          {conditions}
        </SpaceBetween>
      </Container>
      {editingSchemaConditionsTemp.queries
        ? editingSchemaConditionsTemp.queries.length > 0
          ?
              <SpaceBetween direction={'vertical'} size={'xs'}>
                {outcomes}
              </SpaceBetween>
          : undefined
        : undefined
      }
    </SpaceBetween>
    </Container>);
  } else {
    return null
  }
};

export default SchemaAttributeConditionsEdit;