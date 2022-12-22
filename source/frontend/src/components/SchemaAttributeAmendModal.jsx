/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import ReactDOM from 'react-dom'
import {
  Modal,
  Button,
  SpaceBetween,
  Box,
  Container,
  Header,
  FormField,
  Input,
  Select,
  Multiselect,
  Checkbox,
  Alert,
  ExpandableSection,
  Link,
  Textarea
} from '@awsui/components-react';
import {getNestedValuePath, setNestedValuePath} from "../resources/main";
import ToolHelpEdit from "./ToolHelpEdit";
import ToolHelp from "./ToolHelp";
import {Tabs} from "@awsui/components-react";
import SchemaAttributeConditionsEdit from "./SchemaAttributeConditionsEdit";

type Props = {
  children: React.ReactChild,
  closeModal: () => void,
  confirmAction: () => void
};

const SchemaAttributeAmendModal = React.memo(({ children, closeModal , confirmAction, title , attribute , action, schema, activeSchema}: Props) => {
  const domEl = document.getElementById('modal-root')
  const [localAttr, setLocalAttr] = useState(attribute);
  const [testRegexStr, setTestRegexStr] = useState('');
  const [saving, setSaving] = useState(false);


  function handleUserInput (value){

    let newAttr = Object.assign({}, localAttr);
    setNestedValuePath(newAttr, value.field, value.value);

    if (value.field === "rel_entity")
    {
      newAttr['rel_display_attribute'] = '';
      newAttr['rel_key'] = '';
    }

    setLocalAttr(newAttr);

  }

  function handleUserInputEditSchemaHelp(key, update)
  {
    let tempUpdate = Object.assign({}, localAttr);
    if (!tempUpdate.help_content){
      tempUpdate['help_content'] = {};
    }
    tempUpdate['help_content'][key] = update
    setLocalAttr(tempUpdate);
  }

  function handleUserInputEditSchemaConditions(key, update)
  {
    let tempUpdate = Object.assign({}, localAttr)

    setNestedValuePath(tempUpdate, key, update)
    setLocalAttr(tempUpdate);

  }

  function handleSave (e){

    setSaving(true);

    confirmAction(localAttr, action);

  }
  function returnValidationMessage(regex , value , errorMessage){
    try {
      return !value.match(regex) ? errorMessage : undefined;
    } catch (e) {
      return "Error in validation regular expression format: " + e.message;

    }
  }

  if (!domEl) return null



  return ReactDOM.createPortal(
    <Modal
      onDismiss={confirmAction ? closeModal : undefined}
      visible={true}
      closeAriaLabel="Close"
      size="medium"
      footer={confirmAction ?
            (
              <Box float="right">
                <SpaceBetween direction="horizontal" size="xs">
                  <Button onClick={closeModal} variant="link">Cancel</Button>
                  <Button onClick={handleSave} loading={saving} variant="primary">Save</Button>
                </SpaceBetween>
              </Box>
          )
          :
          undefined
      }
      header={title}
    >
        <SpaceBetween size="l">
          <Alert
          visible={!localAttr.system ? false : true}
          type="warning"
        >
          This is a system defined attribute, Programmatic name and Type cannot be altered.
        </Alert>
        <FormField
          label="Programmatic name"
          description=""
        >
          <Input
            value={localAttr.name}
            onChange={event => handleUserInput({field: 'name', value: event.detail.value})}
            readOnly={localAttr.system ? localAttr.system : false}
          />
         </FormField>

         <FormField
           label="Display name"
           description=""
         >
           <Input
             value={localAttr.description}
             onChange={event => handleUserInput({field: 'description', value: event.detail.value})}
           />
          </FormField>

          <FormField
            label="Long description"
            description=""
          >
            <Input
              value={localAttr.long_desc}
              onChange={event => handleUserInput({field: 'long_desc', value: event.detail.value})}
            />
           </FormField>

         <FormField
           label="Type"
           description=""
         >
          {!localAttr.system ?
            (
             <Select
              selectedOption={localAttr.type ? {label: localAttr.type, value: localAttr.type} : null}
              onChange={event => {
                handleUserInput({field: 'type', value: event.detail.selectedOption.value});
                }
              }
              readOnly={localAttr.system ? localAttr.system : false}
              options={
                [
                    { label: 'string', value: 'string' },
                    { label: 'password', value: 'password' },
                    { label: 'date', value: 'date' },
                    { label: 'checkbox', value: 'checkbox' },
                    { label: 'textarea', value: 'textarea' },
                    { label: 'tag', value: 'tag' },
                    { label: 'list', value: 'list' },
                    { label: 'multivalue-string', value: 'multivalue-string' },
                    { label: 'relationship', value: 'relationship' },
                    { label: 'json', value: 'json' }
                ]
              }
              selectedAriaLabel={'selected'}
              />
            )
            :
            <Input
              value={localAttr.type}
              readOnly
            />
          }
          </FormField>

          {localAttr.type !== "relationship"
          ?
            undefined
          :
            <SpaceBetween size="l">
              <FormField
                label="Relationship entity"
                description=""
              >
                  {!localAttr.system
                    ?
                      <Select
                       selectedOption={localAttr.rel_entity ? {label: localAttr.rel_entity, value: localAttr.rel_entity} : null}
                       onChange={event => {
                         handleUserInput({field: 'rel_entity', value: event.detail.selectedOption.value});
                       }}
                       options={
                         [
                             { label: 'application', value: 'application' },
                             { label: 'server', value: 'server' },
                             { label: 'wave', value: 'wave' },
                             { label: 'secret', value: 'secret'}
                         ]
                       }
                       selectedAriaLabel={'selected'}
                       />
                     :
                       <Input
                         value={localAttr.rel_entity}
                         readOnly
                       />
                 }
               </FormField>
               <FormField
                 label="Relationship key"
                 description=""
                 errorText={!localAttr.rel_key ? "You must select an attribute to be the key." : null }
               >
                 {!localAttr.system
                   ?
                     <Select
                      selectedOption={localAttr.rel_key ? {label: localAttr.rel_key, value: localAttr.rel_key} : null}
                      onChange={event => handleUserInput({field: 'rel_key', value: event.detail.selectedOption.value})}
                      options={
                        localAttr.rel_entity
                          ?
                            schema[localAttr.rel_entity].attributes.map((item, index) => {
                              return { label: item.name, value: item.name };
                            })
                          :
                            []
                      }
                      selectedAriaLabel={'selected'}
                      />
                  :
                    <Input
                      value={localAttr.rel_key}
                      readOnly
                    />
                  }
                </FormField>
               <FormField
                 label="Relationship display value"
                 description=""
                 errorText={!localAttr.rel_display_attribute ? "You must select an attribute to be displayed." : null }
               >
                 {!localAttr.system
                   ?
                     <Select
                      selectedOption={localAttr.rel_display_attribute ? {label: localAttr.rel_display_attribute, value: localAttr.rel_entity} : null}
                      onChange={event => handleUserInput({field: 'rel_display_attribute', value: event.detail.selectedOption.value})}
                      options={
                        localAttr.rel_entity
                          ?
                            schema[localAttr.rel_entity].attributes.map((item, index) => {
                              return { label: item.name, value: item.name };
                            })
                          :
                            []
                      }
                      selectedAriaLabel={'selected'}
                      />
                    :
                    <Input
                      value={localAttr.rel_display_attribute}
                      readOnly
                    />
                  }
                </FormField>
                <FormField
                  label="Relationship display select tags"
                  description="Select the additional values that will be displayed as tags in the selections list."
                  errorText={!localAttr.rel_display_attribute ? "You must select an attribute to be displayed." : null }
                >
                  {!localAttr.system
                    ?
                    <Multiselect
                      //selectedOptions={localAttr.rel_additional_attributes ? {label: localAttr.rel_additional_attributes, value: localAttr.rel_entity} : null}
                      selectedOptions={localAttr.rel_additional_attributes == null ? [] : localAttr.rel_additional_attributes.map(item => {return {label: item, value: item}})}
                      //onChange={event => handleUserInput({field: 'rel_additional_attributes', value: event.detail.selectedOption.value})}
                      onChange={event => handleUserInput({
                        field: 'rel_additional_attributes',
                        value: event.detail.selectedOptions != null ? event.detail.selectedOptions.map(valueItem => valueItem.value) : [],
                      })}
                      options={
                        localAttr.rel_entity
                          ?
                          schema[localAttr.rel_entity].attributes.map((item, index) => {
                            return { label: item.name, value: item.name };
                          })
                          :
                          []
                      }
                      selectedAriaLabel={'selected'}
                      filteringType="auto"
                    />
                    :
                    <Input
                      value={localAttr.rel_additional_attributes}
                      readOnly
                    />
                  }
                </FormField>
                <FormField
                  label="Value list"
                  description="Optional - Comma delimited list of additional values that can be selected."
                >
                < Input
                value={localAttr.listvalue}
                onChange={event => handleUserInput({field: 'listvalue', value: event.detail.value})}
                readOnly={localAttr.system}
                />
                </FormField>
                <FormField
                  label="Relationship filter attribute"
                  description="Select an attribute that will be used to filter the available options."
                >
                  {!localAttr.system
                    ?
                    <Select
                      selectedOption={localAttr.rel_filter_attribute_name ? {label: localAttr.rel_filter_attribute_name, value: localAttr.rel_entity} : null}
                      onChange={event => handleUserInput({field: 'rel_filter_attribute_name', value: event.detail.selectedOption.value})}
                      options={
                        localAttr.rel_entity
                          ?
                          schema[localAttr.rel_entity].attributes.map((item, index) => {
                            return { label: item.name, value: item.name };
                          })
                          :
                          []
                      }
                      selectedAriaLabel={'selected'}
                    />
                    :
                    <Input
                      value={localAttr.rel_display_attribute}
                      readOnly
                    />
                  }
                </FormField>
                <FormField
                  label="Filter attribute"
                  description="Select an attribute that will provide the filter value."
                >
                  {!localAttr.system
                    ?
                    <Select
                      selectedOption={localAttr.source_filter_attribute_name ? {label: localAttr.source_filter_attribute_name, value: localAttr.rel_entity} : null}
                      onChange={event => handleUserInput({field: 'source_filter_attribute_name', value: event.detail.selectedOption.value})}
                      options={
                          schema[activeSchema].attributes.map((item, index) => {
                            return { label: item.name, value: item.name };
                          })
                      }
                      selectedAriaLabel={'selected'}
                    />
                    :
                    <Input
                      value={localAttr.rel_display_attribute}
                      readOnly
                    />
                  }
                </FormField>
              </SpaceBetween>
          }

            {localAttr.type === 'list' ?
               <FormField
                 label="Value list"
                 description="Comma delimited list of options."
               >
                 <Input
                   value={localAttr.listvalue}
                   onChange={event => handleUserInput({field: 'listvalue', value: event.detail.value})}
                 />
                </FormField>
              :
              null
            }

          {localAttr.type === 'list' || localAttr.type === 'relationship' ?
            <FormField
              label="Multi Select"
              description="Allow user to select multiple values."
            >
              <Checkbox
                onChange={event => handleUserInput({field: 'listMultiSelect', value: event.detail.checked})}
                checked={localAttr.listMultiSelect}
                disabled={localAttr.system ? true : false}
              >
                {'Multiple selection possible'}
              </Checkbox>
            </FormField>
            :
            null
          }

             <FormField
               label="Required"
               description=""
             >
               <Checkbox
                  onChange={event => handleUserInput({field: 'required', value: event.detail.checked})}
                  checked={localAttr.required}
                  disabled={localAttr.system ? true : false}
                >
                  {'Attribute has to be populated'}
                </Checkbox>
              </FormField>

            <FormField
                label="Hidden"
                description=""
            >
                <Checkbox
                    onChange={event => handleUserInput({field: 'hidden', value: event.detail.checked})}
                    checked={localAttr.hidden}
                    disabled={localAttr.system ? true : false}
                >
                    {'Attribute will not be displayed on screen.'}
                </Checkbox>
            </FormField>
            <ExpandableSection header="Conditional Hidden or Required">
              <SchemaAttributeConditionsEdit
                schemaAttributes={schema[activeSchema].attributes}
                editingSchemaConditionsTemp={getNestedValuePath(localAttr, 'conditions') ? getNestedValuePath(localAttr, 'conditions') : {}}
                handleUserInputEditSchemaConditions={handleUserInputEditSchemaConditions}
                editDisabled={localAttr.system && (localAttr.required || localAttr.hidden) ? true : false}
              />
            </ExpandableSection>

            <ExpandableSection header="Info panel">
              <Tabs
                tabs={
                  [{
                  label: 'Edit',
                  id: 'edit_info',
                  content:
                    <ToolHelpEdit
                      editingSchemaInfoHelpTemp={getNestedValuePath(localAttr, 'help_content') ? getNestedValuePath(localAttr, 'help_content') : {}}
                      handleUserInputEditSchemaHelp={handleUserInputEditSchemaHelp}
                    />
                },
                  {
                    label: 'Preview',
                    id: 'preview_help',
                    content:
                      <ToolHelp
                        helpContent={getNestedValuePath(localAttr, 'help_content')}
                      />
                  }
                ]
              }
              />

            </ExpandableSection>

            <ExpandableSection header="Advanced options">
                <SpaceBetween size="l">
                    <Container
                        className="custom-dashboard-container"
                        header={
                            <Header variant="h2" description="Define groups and order for attribute to help the users understand the context of the attribute and group similar attributes.">
                                Attribute Grouping & Positioning (optional)
                            </Header>
                        }
                    >
                          <FormField
                            label="UI Group"
                            description="Supply a group or container name for this attribute to be displayed in. If not provided Default will be used."
                         >
                            <Input
                                value={localAttr.group}
                                onChange={event => handleUserInput({field: 'group', value: event.detail.value})}
                            />
                          </FormField>
                        <FormField
                            label="Order in group"
                            description="Provide the order in the group. if not provided the order will be alphabetical based on the display name."
                            errorText={localAttr.group_order ? isNaN(parseInt(localAttr.group_order)) ? 'Must be a whole number.' : undefined : undefined}
                        >
                            <Input
                                value={localAttr.group_order}
                                onChange={event => handleUserInput({field: 'group_order', value: event.detail.value})}
                            />
                        </FormField>
                    </Container>

                 <Container
                     className="custom-dashboard-container"
                     header={
                       <Header variant="h2" description="Define a regular expression which will be used to validate the content entered by a user.">
                         Input validation(optional)
                       </Header>
                     }
                   >
                    <SpaceBetween size="l">
                       <FormField
                         label="Validation regular expresssion"
                         description=<div>
                            A full description of this syntax and its constructs can be viewed in the Java documentation, here:
                             <Link
                              external
                              externalIconAriaLabel="Opens regex specification in a new tab"
                              href="https://docs.oracle.com/javase/6/docs/api/java/util/regex/Pattern.html"
                            />
                         </div>
                       >
                        <SpaceBetween size="l">
                           <Input
                             value={localAttr.validation_regex}
                             onChange={event => handleUserInput({field: 'validation_regex', value: event.detail.value})}
                           />
                         </SpaceBetween>
                        </FormField>

                        <FormField
                          label="Validation help message"
                          description=""
                        >
                          <Input
                            value={localAttr.validation_regex_msg}
                            onChange={event => handleUserInput({field: 'validation_regex_msg', value: event.detail.value})}
                          />
                         </FormField>

                         <Container
                             className="custom-dashboard-container"
                             header={
                               <Header variant="h2" description="Test the validation by entering text below, this will not be saved.">
                                 Validation simulator
                               </Header>
                             }
                           >
                         <FormField
                           label="Test validation"
                           description="Enter text to verify the outcome of your regular expression."
                           errorText={returnValidationMessage(localAttr.validation_regex, testRegexStr, localAttr.validation_regex_msg)}
                         >
                           <Input
                             value={testRegexStr}
                             onChange={event => setTestRegexStr(event.detail.value)}
                           />
                          </FormField>
                          </Container>
                        </SpaceBetween>
                   </Container>

                    <Container
                      className="custom-dashboard-container"
                      header={
                        <Header variant="h2" description="The data provided here will be output when the user requires examples of the data format during intake form loading and/or field input.">
                          Example data
                        </Header>
                      }
                    >
                      <FormField
                        label="Intake form example data"
                        description="Supply an example that will be shown to a user required to load data to this attribute."
                      >
                        <Input
                          value={localAttr.sample_data_intake}
                          onChange={event => handleUserInput({field: 'sample_data_intake', value: event.detail.value})}
                        />
                      </FormField>
                      <FormField
                        label="User Interface example data"
                        description="Supply an example that will be shown to a user required to enter data to this attribute."
                      >
                        <Input
                          value={localAttr.sample_data_form}
                          onChange={event => handleUserInput({field: 'sample_data_form', value: event.detail.value})}
                        />
                      </FormField>
                      <FormField
                        label="API example data"
                        description="Supply an example that will be shown to a user required to enter data to this attribute."
                      >
                        <Input
                          value={localAttr.sample_data_api}
                          onChange={event => handleUserInput({field: 'sample_data_api', value: event.detail.value})}
                        />
                      </FormField>
                    </Container>
                  </SpaceBetween>
             </ExpandableSection>
          </SpaceBetween>
        {children}
    </Modal>,
    domEl
  )
});

export default SchemaAttributeAmendModal;
