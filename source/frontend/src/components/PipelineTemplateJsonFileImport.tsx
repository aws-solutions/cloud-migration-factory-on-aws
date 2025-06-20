/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { Dispatch, SetStateAction, useContext, useState } from "react";
import { FileUpload, FormField } from "@cloudscape-design/components";
import { NotificationContext } from "../contexts/NotificationContext.tsx";
export interface FileContent {
  fileFormat: string;
  content: string;
}

interface FileImportStepProps {
  setFileJSON: Dispatch<SetStateAction<FileContent | null>>;
  acceptedFileTypes?: string;
}

const createFileContent = (format: string, content: string): FileContent => ({
  fileFormat: format,
  content: content,
});

const FILE_TYPES = {
  json: {
    format: "cmf-json",
    parseContent: (content: string) => {
      JSON.parse(content); // Validate JSON structure
      return content;      
    }
  },
  csv: {
    format: "lucid-csv",
    parseContent: (content: string) => content,
  },
  drawio: {
    format: "drawio",
    parseContent: (content: string) => content,
  },
} as const;

export const FileImportStep = ({ setFileJSON, acceptedFileTypes }: FileImportStepProps) => {
  const [value, setValue] = useState<File[]>([]);
  const { addNotification } = useContext(NotificationContext);

  const handleFileUpload = (file: File) => {
    const fileReader = new FileReader();
    fileReader.readAsText(file, "UTF-8");
    fileReader.onload = () => {
      try {
        const fileContent = fileReader.result as string;
        const fileExtension = file.name.split(".").pop()?.toLowerCase();
        // Validate empty content
        if (!fileContent || fileContent.trim().length === 0) {
          throw new Error("File is empty. Please upload a file with template.");
        }
        if (!fileExtension || !(fileExtension in FILE_TYPES)) {
          throw new Error(`Unsupported file type: ${fileExtension}`);
        }

        const { format, parseContent } = FILE_TYPES[fileExtension as keyof typeof FILE_TYPES];
        setFileJSON(createFileContent(format, parseContent(fileContent)));
      } catch (error) {
        addNotification({
          type: "error",
          dismissible: true,
          header: "Error parsing file",
          content:  error instanceof Error ? error.message : "Invalid file content"
        });
        console.error("Error parsing uploaded file:", error);
        setFileJSON(null);
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
        accept={acceptedFileTypes}
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
