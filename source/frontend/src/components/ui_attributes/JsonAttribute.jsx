import React, { useState, useEffect } from 'react';
import {
FormField,
Textarea,
CodeEditor
} from '@awsui/components-react';

import ace from 'ace-builds';
import "ace-builds/webpack-resolver";

// Attribute Display message content
const JsonAttribute = ({attribute, item, handleUserInput, errorText}) => {
  const locaStorageKeys = {
    codePrefs: "Code_Editor_Preferences",
  }
  const [localJson, setLocalJson] = useState(item instanceof Object ? JSON.stringify(item, undefined, 4) : item ? item : "");
  const [jsonError, setJsonError] = useState(errorText ? errorText : null);
  const [preferences, setPreferences] = useState(localStorage[locaStorageKeys.codePrefs] ? JSON.parse(localStorage.getItem(locaStorageKeys.codePrefs)) : {});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    localStorage.setItem(locaStorageKeys.codePrefs, JSON.stringify(preferences));
  }, [preferences]);

  function handleUpdate(event){
    setLocalJson(event.detail.value);
    handleUserInput({field: attribute.name, value: event.detail.value, validationError: errorText})
  }

  useEffect(() => {
    setJsonError(errorText);
  }, [errorText]);


 return (
   <FormField
     label={attribute.label}
     description={attribute.description}
     errorText={jsonError ? jsonError : null}
   >
      <CodeEditor
      ace={ace}
      language='json'
      value={localJson}
      onChange={event => handleUpdate(event)}
      preferences={preferences}
      onPreferencesChange={e => setPreferences(e.detail)}
      loading={loading}
      i18nStrings={{
        loadingState: "Loading code editor",
        errorState:
          "There was an error loading the code editor.",
        errorStateRecovery: "Retry",
        editorGroupAriaLabel: "Code editor",
        statusBarGroupAriaLabel: "Status bar",
        cursorPosition: (row, column) =>
          `Ln ${row}, Col ${column}`,
        errorsTab: "Errors",
        warningsTab: "Warnings",
        preferencesButtonAriaLabel: "Preferences",
        paneCloseButtonAriaLabel: "Close",
        preferencesModalHeader: "Preferences",
        preferencesModalCancel: "Cancel",
        preferencesModalConfirm: "Confirm",
        preferencesModalWrapLines: "Wrap lines",
        preferencesModalTheme: "Theme",
        preferencesModalLightThemes: "Light themes",
        preferencesModalDarkThemes: "Dark themes"
      }}
    />
    </FormField>
 )

};

export default JsonAttribute;
