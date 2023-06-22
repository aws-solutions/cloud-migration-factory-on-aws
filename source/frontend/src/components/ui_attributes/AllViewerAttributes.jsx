  /*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
  ExpandableSection,
  Box,
  SpaceBetween
 } from '@awsui/components-react';

  import TextAttribute from './TextAttribute.jsx'
  import RelatedRecordPopover from "./RelatedRecordPopover.jsx";
  import {getNestedValuePath} from "../../resources/main";
  import {getRelationshipRecord, getRelationshipValue} from "../../resources/recordFunctions";

const AllViewerAttributes = (props) =>
   {
     function addCheckboxAttribute(attribute){
       const attributeValue = getNestedValuePath(props.item, attribute.name);
       return (
         attributeValue !== undefined
           ?
           <TextAttribute key={attribute.name}
                          label={attribute.description}
           >{attributeValue ? "enabled" : "disabled"}</TextAttribute>
           :
           null
       )
     }

     function addMultiStringAttribute(attribute){
       const attributeValue = getNestedValuePath(props.item, attribute.name);
       return (
         attributeValue || displayEmpty
           ?
           <TextAttribute key={attribute.name}
                          label={attribute.description}
           >{attributeValue
             ?
             attributeValue.join('\n')
             :
             '-'}
           </TextAttribute>
           :
           null
       )
     }

     function addJSONAttribute(attribute){
       let valueJson = '';
       const attributeValue = getNestedValuePath(props.item, attribute.name);
       if (attributeValue) {
         valueJson = attributeValue instanceof Object ? JSON.stringify(attributeValue, undefined, 4) : attributeValue;
       }
       return (
         attributeValue || displayEmpty
           ?
           <div key={attribute.name}>
             <Box margin={{bottom: 'xxxs'}} color="text-label">
               {attribute.description}
             </Box>
             {
               getJSONDisplayValue(valueJson)
             }
           </div>
           :
           null
       )
     }

     function addTextAttribute(attribute){
       return (
         <TextAttribute key={attribute.name}
                        label={attribute.description}
         >{'unsupported value type for viewer'}</TextAttribute>
       )
     }

     function addTagAttribute(attribute){
       const attributeValue = getNestedValuePath(props.item, attribute.name);

       let tags = [];
       if (attributeValue) {
         tags = attributeValue.map((item, index) => {
           return item.key + ' : ' + item.value;
         });
       }
       return (
         attributeValue || displayEmpty
           ?
           <TextAttribute key={attribute.name}
                          label={attribute.description}
           >{tags.join('\n')}</TextAttribute>
           :
           null
       )
     }

     function addListAttribute(attribute){
       const attributeValue = getNestedValuePath(props.item, attribute.name);
       return (
         attributeValue || displayEmpty
           ?
           <TextAttribute key={attribute.name}
                          label={attribute.description}
           >{attributeValue ? attributeValue : '-'}</TextAttribute>
           :
           null
       )
     }

     function createMutipleRelationshipList(actualValuesNames, actualValue) {
       let multipleApps = [];
       if (actualValuesNames) {
         for (const subValueIdx in actualValue) {
           if (actualValue[subValueIdx] === 'tbc') {
             multipleApps.push(
               <p>{actualValuesNames[subValueIdx] ? (actualValuesNames[subValueIdx] + ' [NEW]') : actualValue[subValueIdx]}</p>);
           }
         }
       }

       return multipleApps;
     }

     function getMultiRelationshipDisplayValues(relatedSchema,attribute,value,actualValue, record) {
       let multipleApps = [];
       if ((value.status === 'loaded' || value.status === 'not found') && ( actualValue )){
         for(const subRecord in record) {
           multipleApps.push(
             <RelatedRecordPopover key={attribute.name + subRecord}
                                   item={record[subRecord]}
                                   schema={props.schemas[relatedSchema]}
                                   schemas={props.schemas}
                                   dataAll={props.dataAll}
             >
               {value.value[subRecord] ? value.value[subRecord] : '-'}
             </RelatedRecordPopover>
           );
         }

         let actualValuesNames = getNestedValuePath(props.item, "__" + attribute.name); //Only used when importing data.

         multipleApps = createMutipleRelationshipList(actualValuesNames,actualValue);

         return (
           <div key={attribute.name}>
             <Box margin={{ bottom: 'xxxs' }} color="text-label">
               {attribute.description}
             </Box>
             <div>
               <SpaceBetween size={'xxs'} direction={'vertical'}>
                 {multipleApps}
               </SpaceBetween>
             </div>
           </div>
         );
       } else {
         return (
           <TextAttribute
             key={attribute.name}
             label={attribute.description}
             loading={value.status === 'loading'}
             loadingText={value.status}
           >{value.value ? value.value.join(',') : '-'}
           </TextAttribute>
         );
       }
     }

     function addRelationshipAttribute(attribute){
       let attributeValue = getNestedValuePath(props.item, attribute.name);
       let relatedValue = getRelationshipValue(props.dataAll, attribute, getNestedValuePath(props.item, attribute.name))
       let relatedRecord = getRelationshipRecord(props.dataAll, attribute, getNestedValuePath(props.item, attribute.name))
       const relatedSchema = attribute.rel_entity;

       if (attribute.listMultiSelect){
         if (displayEmpty || attributeValue){
           return getMultiRelationshipDisplayValues(relatedSchema,attribute,relatedValue,attributeValue, relatedRecord);
         } else {
           return null;
         }
       } else {
         return (
           getSingleRelationshipDisplayValue(relatedSchema,attribute,relatedValue,attributeValue, relatedRecord, displayEmpty)
         )
       }
     }

     function addPasswordAttribute(attribute){
       const attributeValue = getNestedValuePath(props.item, attribute.name);
       return (
         attributeValue || displayEmpty
           ?
           <TextAttribute
             key={attribute.name}
             label={attribute.description}
           >{attributeValue ? '[value set]' : '-'}</TextAttribute>
           :
           null
       )
     }

     function addEmbeddedEntityAttribute(attribute){
        let currentLookupValue = getNestedValuePath(props.item, attribute.lookup)
        let embedded_value = getRelationshipValue(props.dataAll, attribute, currentLookupValue)
        //let embedded_record = getRelationshipRecord(attribute, getNestedValuePath(props.item, attribute.name))
        const embedded_relatedSchema = attribute.rel_entity;

        if (embedded_value.status === 'loading') {
          //Data not loaded for embedded entity.
          return (
            <TextAttribute
              key={attribute.name}
              label={attribute.description}
              loading={embedded_value.status === 'loading'}
              loadingText={embedded_value.status}
            >{'-'}
            </TextAttribute>
          )
        }

        if (embedded_value.status === 'not found') {
          //Data not loaded for embedded entity.
          return (
            <TextAttribute
              key={attribute.name}
              label={attribute.description}
            >{'ERROR: Script not found based on UUID : ' + currentLookupValue}
            </TextAttribute>
          )
        }

        if (!props.schemas[embedded_relatedSchema]) {
          //Valid schema not found, display text.
          return (
            <TextAttribute
              key={attribute.name}
              label={attribute.description}
            >{attribute.rel_entity ? 'Schema ' + attribute.rel_entity + ' not found.' : '-'}</TextAttribute>
          )
        }

        //check if this new embedded item has already been stored in the state, if not create it.
        if (embedded_value.value != null) {
          //Remove any invalid items where name key is not defined. This should not be the case but possible with script packages where incorrectly written.
          embedded_value.value = embedded_value.value.filter((item) => {
            return item.name !== undefined;
          });
          embedded_value.value = embedded_value.value.map((item, index) => {
            //prepend the embedded_entity name to all attribute names in order to store them under a single key.
            let appendedName = attribute.name + '.' + item.name;
            if (item.__orig_name){
              //Item has already been updated name.
              return (
                item
              )
            } else {
              //Store original name of item.
              item.__orig_name = item.name;
              item.name = appendedName;
              item.group = attribute.description;
              return (
                item
              )
            }
          });
        } else {
          embedded_value.value = [];
        }

        return (
          <SpaceBetween
            size="xxxs"
            key={attribute.name}
          >
            <AllViewerAttributes
              schema={{"attributes": embedded_value.value}}
              schemas={props.schemas}
              hideAudit={true}
              item={props.item}
              dataAll={props.dataAll}
            />
          </SpaceBetween>
        )
     }

     function addPolicyAttribute(attribute){
        let valueJson = '';
        const attributeValue = getNestedValuePath(props.item, attribute.name);
        if (attributeValue) {
          valueJson = attributeValue;
        }

        return (
          <div key={attribute.name}>
            <Box margin={{bottom: 'xxxs'}} color="text-label">
              {attribute.description}
            </Box>
            {valueJson.map((policy, index) => {
              let finalMsg = [];

              if (policy.create) {
                finalMsg.push('Create')
              }

              if (policy.read) {
                finalMsg.push('Read')
              }

              if (policy.update) {
                finalMsg.push('Update')
              }

              if (policy.delete) {
                finalMsg.push('Delete')
              }

              return <div key={policy.schema_name}>{policy.friendly_name ? policy.friendly_name : policy.schema_name + ' ['+ finalMsg.join(' ') +']'}</div>})}

          </div>
        );
     }
     function addDefaultAttribute(attribute){
        const attributeValue = getNestedValuePath(props.item, attribute.name)
        return (
          attributeValue || displayEmpty
            ?
            <TextAttribute
              key={attribute.name}
              label={attribute.description}
            >{attributeValue ? attributeValue : '-'}</TextAttribute>
            :
            null
        )
     }

     function getDisplayValue(value, returnText='%s'){
       if (value) {
         return returnText.replace('%s', value);
       } else {
         return '-';
       }
     }
     function getJSONDisplayValue(valueJson){
       if (valueJson){
         if(valueJson.length > 450){
           return <ExpandableSection header={valueJson.substring(0, 450) + " ..."}>
                    {valueJson}
           </ExpandableSection>
         } else {
           return valueJson
         }
       } else {
         return '-'
       }
     }

     function getSingleRelationshipDisplayValue(relatedSchema, attribute, value, actualValue, record, displayEmpty){
       if (value.value || displayEmpty){
         if (value.status === 'loaded' && value.value !== null) {
           return <div key={attribute.name}>
             <Box margin={{ bottom: 'xxxs' }} color="text-label">
               {attribute.description}
             </Box>
             <div>
               <RelatedRecordPopover key={attribute.name}
                                     item={record}
                                     schema={props.schemas[relatedSchema]}
                                     schemas={props.schemas}
                                     dataAll={props.dataAll}
               >
                 {value.value}
               </RelatedRecordPopover>
             </div>
           </div>
         } else if (value.status === 'not found') {
           if (actualValue === 'tbc' && getNestedValuePath(props.item, "__" + attribute.name)) {
             return <TextAttribute
               key={attribute.name}
               label={attribute.description}
               loading={false}
               loadingText={value.status}
             >{getDisplayValue(getNestedValuePath(props.item, "__" + attribute.name), '%s [NEW]')}
             </TextAttribute>
           } else {
             return <TextAttribute
               key={attribute.name}
               label={attribute.description}
               loading={false}
               loadingText={value.status}
             >{
               getDisplayValue(getNestedValuePath(props.item, attribute.name), "Not found: " + attribute.rel_entity + "[" + attribute.rel_key + "]=%s")
               }
             </TextAttribute>
           }
         } else {
           return <TextAttribute
             key={attribute.name}
             label={attribute.description}
             loading={value.status === 'loading'}
             loadingText={value.status}
           >{getDisplayValue(getNestedValuePath(props.item, attribute.name) )}
           </TextAttribute>
         }

       } else {
         return null
       }
     }

     let allAttributes = [];
     //TODO - finish this sort script to allow grouped attributes to be created together
     let sortedSchemaAttributes = props.schema.attributes.sort(function (a, b) {
       if (a.group && b.group){
         return a.group > b.group ? 1 : -1;
       }
       else if (!a.group && b.group){
         return -1;
       }
       else if (a.group && !b.group) {
         return 1;
       }
     });

     //TODO Add to state in future and possibly store in user profile.
     let displayEmpty = props.hideEmpty ? false : true;

     allAttributes = sortedSchemaAttributes.map((attribute, indx) => {
       if (!attribute.hidden) {

         switch (attribute.type) {
           case 'checkbox': {
             return addCheckboxAttribute(attribute);
           }
           case 'multivalue-string':{
             return addMultiStringAttribute(attribute);
           }
           case 'json': {
             return addJSONAttribute(attribute);
           }
           case 'textarea': {
             return addTextAttribute(attribute);
           }
           case 'tag': {
              return addTagAttribute(attribute);
           }
           case 'list': {
             return addListAttribute(attribute);
           }
           case 'relationship': {
             return addRelationshipAttribute(attribute);
           }
           case 'password': {
             return addPasswordAttribute(attribute);
           }
           case 'embedded_entity': {
             return addEmbeddedEntityAttribute(attribute);
           }
           case 'policy':{
             return addPolicyAttribute(attribute);
           }
           default: {
             return addDefaultAttribute(attribute);
           }
         }

       }
       return null;
     });

     return (
       <SpaceBetween
         size="s"
       >
         {allAttributes}
       </SpaceBetween>


     );
   }

export default AllViewerAttributes;
