// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from "react";
import {CodeEditor, FormField, SpaceBetween} from "@cloudscape-design/components";

import ace from "ace-builds";
import 'ace-builds/src-noconflict/mode-json';
import 'ace-builds/src-noconflict/theme-textmate';
import 'ace-builds/src-noconflict/theme-monokai';
import 'ace-builds/src-noconflict/worker-json';
import 'ace-builds/src-noconflict/theme-dawn';
import 'ace-builds/src-noconflict/theme-github';
import 'ace-builds/src-noconflict/ext-language_tools';

ace.config?.set("basePath", "/assets/ace-builds/src-noconflict/");

// Attribute Display message content
const JsonAttribute = ({ attribute, item, handleUserInput, errorText, displayHelpInfoLink }) => {
  const locaStorageKeys = {
    codePrefs: "Code_Editor_Preferences",
  };
  const [localJson, setLocalJson] = useState(convertObjectToString(item));
  const [jsonError, setJsonError] = useState(errorText ? errorText : null);
  const [preferences, setPreferences] = useState(
    localStorage[locaStorageKeys.codePrefs] ? JSON.parse(localStorage.getItem(locaStorageKeys.codePrefs)) : {}
  );

  useEffect(() => {
    localStorage.setItem(locaStorageKeys.codePrefs, JSON.stringify(preferences));
  }, [preferences]);

  function convertObjectToString(jsonObject) {
    if (jsonObject instanceof Object) {
      return JSON.stringify(jsonObject, undefined, 4);
    } else if (jsonObject) {
      return jsonObject;
    } else {
      return "";
    }
  }

  function handleUpdate(event) {
    setLocalJson(event.detail.value);
    handleUserInput({ field: attribute.name, value: event.detail.value, validationError: errorText });
  }

  useEffect(() => {
    setJsonError(errorText);
  }, [errorText]);

  return (
    <FormField
      label={attribute.label}
      description={
        attribute.description ? (
          <SpaceBetween direction="horizontal" size="xs">
            {attribute.description}
            {displayHelpInfoLink(attribute)}{" "}
          </SpaceBetween>
        ) : (
          <SpaceBetween direction="horizontal" size="xs">
            {attribute.name}
            {displayHelpInfoLink(attribute)}{" "}
          </SpaceBetween>
        )
      }
      errorText={jsonError ? jsonError : null}
    >
      <CodeEditor
        ace={ace}
        language="json"
        ariaLabel={attribute.name}
        value={localJson}
        onChange={(event) => handleUpdate(event)}
        preferences={preferences}
        onPreferencesChange={(e) => setPreferences(e.detail)}
        loading={false}
        i18nStrings={{
          loadingState: "Loading code editor",
          errorState: "There was an error loading the code editor.",
          errorStateRecovery: "Retry",
          editorGroupAriaLabel: "Code editor",
          statusBarGroupAriaLabel: "Status bar",
          cursorPosition: (row, column) => `Ln ${row}, Col ${column}`,
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
          preferencesModalDarkThemes: "Dark themes",
        }}
      />
    </FormField>
  );
};

export default JsonAttribute;
