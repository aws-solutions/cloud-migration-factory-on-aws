import React from 'react';
import {
    ColumnLayout,
    ExpandableSection,
    SpaceBetween
} from '@awsui/components-react';

import TextAttribute from "./TextAttribute";

// Attribute Display message content
function returnLocaleDateTime(stringDateTime) {
    var originalDate = new Date(stringDateTime);
    var newDate = new Date(originalDate.getTime() - originalDate.getTimezoneOffset()*60*1000);

    return newDate.toLocaleString();
}

const Audit = ({item}) => {
  return (
          <ColumnLayout columns={2} variant="text-grid">
              <div>
                  <SpaceBetween size="l">
                      <TextAttribute
                          label={'Created by'}
                      >{item['_history'] ? item['_history']['createdBy'] ? item['_history']['createdBy']['email'] ? item['_history']['createdBy']['email'] : '-' : '-' : '-'}</TextAttribute>
                      <TextAttribute
                          label={'Created on'}
                      >{item['_history'] ? item['_history']['createdTimestamp'] ? returnLocaleDateTime(item['_history']['createdTimestamp']) : '-' : '-'}</TextAttribute>
                  </SpaceBetween>
              </div>
              <div>
                  <SpaceBetween size="l">
                      <TextAttribute
                          label={'Last modified by'}
                      >{item['_history'] ? item['_history']['lastModifiedBy'] ? item['_history']['lastModifiedBy']['email'] ? item['_history']['lastModifiedBy']['email'] : '-' : '-' : '-'}</TextAttribute>
                      <TextAttribute
                          label={'Last updated on'}
                      >{item['_history'] ? item['_history']['lastModifiedTimestamp'] ? returnLocaleDateTime(item['_history']['lastModifiedTimestamp']) : '-' : '-'}</TextAttribute>
                  </SpaceBetween>
              </div>
          </ColumnLayout>
  )
};

export default Audit;
