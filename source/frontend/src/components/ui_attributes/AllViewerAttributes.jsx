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
             const lValue = getNestedValuePath(props.item, attribute.name);
             return (
               lValue || displayEmpty
                 ?
                   <TextAttribute key={attribute.name}
                                  label={attribute.description}
                   >{lValue ? "enabled" : "disabled"}</TextAttribute>
                 :
                 null
             )
           }
           case 'multivalue-string':{
             const lValue = getNestedValuePath(props.item, attribute.name);
             return (
               lValue || displayEmpty
                 ?
                   <TextAttribute key={attribute.name}
                     label={attribute.description}
                   >{lValue
                     ?
                       lValue.join('\n')
                     :
                        '-'}
                   </TextAttribute>
                 :
                  null
             )
           }
           case 'json': {
             let valueJson = '';
             const lValue = getNestedValuePath(props.item, attribute.name);
             if (lValue) {
               valueJson = lValue instanceof Object ? JSON.stringify(lValue, undefined, 4) : lValue;
             }
             return (
               lValue || displayEmpty
                 ?
                   <div key={attribute.name}>
                     <Box margin={{bottom: 'xxxs'}} color="text-label">
                       {attribute.description}
                     </Box>
                     {
                       valueJson
                         ?
                         valueJson.length > 450 ?
                           <ExpandableSection header={valueJson.substring(0, 450) + " ..."}>
                             {valueJson}
                           </ExpandableSection>
                           :
                           valueJson
                         :
                         '-'
                     }
                   </div>
                 :
                  null
             )
           }
           case 'textarea': {
             return (
               <TextAttribute key={attribute.name}
                              label={attribute.description}
               >{'unsupported value type for viewer'}</TextAttribute>
             )
           }
           case 'tag': {
             const lValue = getNestedValuePath(props.item, attribute.name);

             let tags = [];
             if (lValue) {
               tags = lValue.map((item, index) => {
                 return item.key + ' : ' + item.value;
               });
             }
             return (
               lValue || displayEmpty
                 ?
                   <TextAttribute key={attribute.name}
                                  label={attribute.description}
                   >{tags.join('\n')}</TextAttribute>
                 :
                  null
             )
           }
           case 'list': {
             const lValue = getNestedValuePath(props.item, attribute.name);
             return (
               lValue || displayEmpty
                 ?
                   <TextAttribute key={attribute.name}
                                  label={attribute.description}
                   >{lValue ? lValue : '-'}</TextAttribute>
                 :
                  null
             )
           }
             case 'relationship': {
               let actualValue = getNestedValuePath(props.item, attribute.name);
               let value = getRelationshipValue(props.dataAll, attribute, getNestedValuePath(props.item, attribute.name))
               let record = getRelationshipRecord(props.dataAll, attribute, getNestedValuePath(props.item, attribute.name))
               const relatedSchema = attribute.rel_entity;

               if (!props.schemas[relatedSchema]) {
                 //Valid schema not found, display text.
               }

               if (attribute.listMultiSelect){
                 let multipleApps = [];

                 if (displayEmpty || actualValue){

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

                     if (actualValuesNames) {
                       for (const subValueIdx in actualValue) {
                         if (actualValue[subValueIdx] === 'tbc') {
                           multipleApps.push(
                             <p>{actualValuesNames[subValueIdx] ? (actualValuesNames[subValueIdx] + ' [NEW]') : actualValue[subValueIdx]}</p>);
                         }
                       }
                     }

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
                 } else {
                   return null;
                 }
               } else {
                 return (
                   value.value || displayEmpty
                     ?
                     (value.status === 'loaded' && value.value !== null)
                       ?
                       <div key={attribute.name}>
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
                               {value.value ? value.value : '-'}
                           </RelatedRecordPopover>
                         </div>
                       </div>
                       :
                       value.status === 'not found'
                         ?
                         actualValue === 'tbc' && getNestedValuePath(props.item, "__" + attribute.name)
                           ?
                           <TextAttribute
                             key={attribute.name}
                             label={attribute.description}
                             loading={false}
                             loadingText={value.status}
                           >{getNestedValuePath(props.item, "__" + attribute.name) ? (getNestedValuePath(props.item, "__" + attribute.name) + ' [NEW]'): '-'}
                           </TextAttribute>
                           :
                         <TextAttribute
                           key={attribute.name}
                           label={attribute.description}
                           loading={false}
                           loadingText={value.status}
                         >{getNestedValuePath(props.item, attribute.name) ? ("Not found: " + attribute.rel_entity + "[" + attribute.rel_key + "]=" + getNestedValuePath(props.item, attribute.name)) : '-'}
                         </TextAttribute>
                         :
                         <TextAttribute
                           key={attribute.name}
                           label={attribute.description}
                           loading={value.status === 'loading'}
                           loadingText={value.status}
                         >{getNestedValuePath(props.item, attribute.name) ? (getNestedValuePath(props.item, attribute.name)) : '-'}
                         </TextAttribute>
                     :
                     null
                 )
               }
             }
           case 'password': {
             const lValue = getNestedValuePath(props.item, attribute.name);
             return (
               lValue || displayEmpty
                 ?
                 <TextAttribute
                   key={attribute.name}
                   label={attribute.description}
                 >{lValue ? '[value set]' : '-'}</TextAttribute>
                 :
                 null
             )
           }
           case 'embedded_entity': {
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

             let updateEmbeddedAttributes = [];
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
           case 'policy':{
             let valueJson = '';
             const lValue = getNestedValuePath(props.item, attribute.name);
             if (lValue) {
               valueJson = lValue;
             }

             return (
               <div key={attribute.name}>
                 <Box margin={{bottom: 'xxxs'}} color="text-label">
                   {attribute.description}
                 </Box>
                 {valueJson.map((policy, index) => {
                 let createmsg = '';
                 let readmsg = '';
                 let updatemsg = '';
                 let deletemsg = '';

                 policy.create ? createmsg = 'Create': createmsg = ''
                 policy.read ? readmsg = 'Read': readmsg = ''
                 policy.update ? updatemsg = 'Update': updatemsg = ''
                 policy.delete ? deletemsg = 'Delete': deletemsg = ''

                 let finalmsg = createmsg + ' ' + readmsg  + ' ' +  updatemsg  + ' ' +  deletemsg

                 return <div>{policy.friendly_name ? policy.friendly_name : policy.schema_name + ' ['+ finalmsg +']'}</div>})}

               </div>
             );
           }
           default:
             const lValue = getNestedValuePath(props.item, attribute.name)
             return (
               lValue || displayEmpty //check if empty.
               ?
                 <TextAttribute
                   key={attribute.name}
                   label={attribute.description}
                 >{lValue ? lValue : '-'}</TextAttribute>
               :
               null
             )
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
