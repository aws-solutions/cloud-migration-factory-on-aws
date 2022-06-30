import React from 'react';
import { Flashbar } from '@awsui/components-react';

// Flash message content
const FlashMessage = (props) => {
  return <Flashbar items={props.notifications} />;
};

export default FlashMessage;
