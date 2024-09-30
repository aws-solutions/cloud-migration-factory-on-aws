/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { Dispatch, SetStateAction, useState } from "react";
import { FileUpload, FormField } from "@cloudscape-design/components";

export const FileImportStep = ({ setFileJSON }: { setFileJSON: Dispatch<SetStateAction<Array<object> | null>> }) => {
  const [value, setValue] = useState<File[]>([]);

  const handleFileUpload = (file: File) => {
    const fileReader = new FileReader();
    fileReader.readAsText(file, "UTF-8");
    fileReader.onload = () => {
      try {
        const jsonContent = JSON.parse(fileReader.result as string);
        setFileJSON(jsonContent);
      } catch (error) {
        console.error("Error parsing JSON file:", error);
      }
    };
    fileReader.onerror = () => {
      console.error("Error reading file");
    };
    setValue([file]);
  };

  return (
    <FormField>
      <FileUpload
        onChange={({ detail }) => {
          handleFileUpload(detail.value[0]);
        }}
        value={value}
        i18nStrings={{
          uploadButtonText: (e) => (e ? "Choose files" : "Choose file"),
          dropzoneText: (e) => (e ? "Drop files to upload" : "Drop file to upload"),
          removeFileAriaLabel: (e) => `Remove file ${e + 1}`,
          limitShowFewer: "Show fewer files",
          limitShowMore: "Show more files",
          errorIconAriaLabel: "Error",
        }}
        showFileLastModified
        showFileSize
        showFileThumbnail
        multiple={false}
        tokenLimit={3}
      />
    </FormField>
  );
};
