/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {FormField, Input, SpaceBetween, TagEditor, Textarea} from "@awsui/components-react";
import React from "react";
import {HelpContent, Tag} from "../models/HelpContent";

interface ToolHelpEditParams {
  editingSchemaInfoHelpTemp: HelpContent | undefined,
  handleUserInputEditSchemaHelp: (key: 'header' | 'content' | 'content_links' | 'content_html', value: string | Tag[]) => void
}

const ToolHelpEdit = ({editingSchemaInfoHelpTemp, handleUserInputEditSchemaHelp}: ToolHelpEditParams) => {

  if (editingSchemaInfoHelpTemp) {
    return <SpaceBetween direction={'vertical'} size={'xxl'}>
      <FormField
        key={'help_header'}
        label={'Help title'}
        description={'Enter the content title.'}
      >
        <Input
          onChange={event => handleUserInputEditSchemaHelp('header', event.detail.value)}
          value={editingSchemaInfoHelpTemp.header ? editingSchemaInfoHelpTemp.header : ''}
        />
      </FormField>
      <FormField
        key={'help_content'}
        label={'Help content'}
        description={'Enter the content for the main help section, Use p, a, h3, h4, h5, span, div, ul, ol, li, code, pre, dl, dt, dd, hr, br, i, em, b, strong html tags to format the content.'}
      >
        <Textarea
          onChange={event => handleUserInputEditSchemaHelp('content_html', event.detail.value)}
          value={editingSchemaInfoHelpTemp.content_html ? editingSchemaInfoHelpTemp.content_html : ''}
        />
      </FormField>
      <FormField
        key={'help_links'}
        label={'Help links'}
        description={'Add any links to relevant content.'}
      >
        <TagEditor
          allowedCharacterPattern={undefined}
          i18nStrings={{
            keyPlaceholder: "Enter label",
            valuePlaceholder: "Enter URL",
            addButton: "Add new URL",
            removeButton: "Remove",
            undoButton: "Undo",
            undoPrompt:
              "This URL will be removed upon saving changes",
            loading:
              "Loading URLs",
            keyHeader: "Label",
            valueHeader: "URL",
            optional: "optional",
            keySuggestion: "Custom URL label",
            valueSuggestion: "Custom URL",
            emptyTags:
              "No URLs defined.",
            tooManyKeysSuggestion:
              "You have more labels than can be displayed",
            tooManyValuesSuggestion:
              "You have more URLs than can be displayed",
            keysSuggestionLoading: "Loading URL labels",
            keysSuggestionError:
              "URL labels could not be retrieved",
            valuesSuggestionLoading: "Loading URLs",
            valuesSuggestionError:
              "URLs could not be retrieved",
            emptyKeyError: "You must specify a URL label",
            maxKeyCharLengthError:
              "The maximum number of characters you can use in a URL label is 128.",
            maxValueCharLengthError:
              "The maximum number of characters you can use in a URL is 256.",
            duplicateKeyError:
              "You must specify a unique URL label.",
            invalidKeyError:
              "Invalid label. Labels can only contain alphanumeric characters, spaces and any of the following: _.:/=+@-",
            invalidValueError:
              "Invalid URL. URLs can only contain alphanumeric characters, spaces and any of the following: _.:/=+@-",
            awsPrefixError: "Cannot start with aws:",
            tagLimit: availableTags =>
              availableTags === 1
                ? "You can add up to 1 more URL."
                : "You can add up to " +
                availableTags +
                " more URLs.",
            tagLimitReached: tagLimit =>
              tagLimit === 1
                ? "You have reached the limit of 1 URL."
                : "You have reached the limit of " +
                tagLimit +
                " URLs.",
            tagLimitExceeded: tagLimit =>
              tagLimit === 1
                ? "You have exceeded the limit of 1 URL."
                : "You have exceeded the limit of " +
                tagLimit +
                " URLs.",
            enteredKeyLabel: key => 'Use "' + key + '"',
            enteredValueLabel: value => 'Use "' + value + '"'
          }}
          tags={editingSchemaInfoHelpTemp.content_links ?? []}
          onChange={({detail}) => handleUserInputEditSchemaHelp('content_links', detail.tags as Tag[])}
        />
      </FormField>
    </SpaceBetween>
  } else {
    return null
  }
};

export default ToolHelpEdit;