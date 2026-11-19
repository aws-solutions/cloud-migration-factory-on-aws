/* eslint-disable @typescript-eslint/no-explicit-any */
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useEffect, useState } from "react";
import AdminApiClient from "../api_clients/adminApiClient";
import {
  Alert,
  Box,
  Button,
  ColumnLayout,
  Container,
  FormField,
  Header,
  Icon,
  Input,
  SpaceBetween,
  Spinner,
  StatusIndicator,
  Tabs,
  TabsProps,
} from "@cloudscape-design/components";

import SchemaAttributesTable from "../components/SchemaAttributesTable";
import { capitalize, getNestedValuePath } from "../resources/main";
import ToolHelp from "../components/ToolHelp";
import ToolHelpEdit from "../components/ToolHelpEdit";
import { NotificationContext } from "../contexts/NotificationContext";
import { Attribute, EntitySchema, SchemaMetaData, HelpContent, Tag, EntityName } from "../models";
import { ToolsContext } from "../contexts/ToolsContext";
import SchemaAttributeAmendModal from "../components/SchemaAttributeAmendModal";
import { CMFModal } from "../components/Modal";
import { Schemas } from "../utils/Constants";

type AdminSchemaMgmtParams = Readonly<{
  reloadSchema: (refresh?: boolean) => void;
  schemas: Record<string, EntitySchema>;
  schemaMetadata: SchemaMetaData[];
  enabledModules: string[];
}>;

const apiAdmin = new AdminApiClient();

const AdminSchemaMgmt = (props: AdminSchemaMgmtParams) => {
  const { addNotification } = useContext(NotificationContext);
  const { setHelpPanelContent } = useContext(ToolsContext);

  // The `schemaIsLoading` prop is intentionally set to false for refresh
  // So define local state for isReloadingSchema
  const [isReloadingSchema, setIsReloadingSchema] = useState(false);

  //Layout state management.
  const [editingSchemaInfoHelp, setEditingSchemaInfoHelp] = useState(false);
  const [editingSchemaInfoHelpTemp, setEditingSchemaInfoHelpTemp] = useState<HelpContent | undefined>(undefined);
  const [editingSchemaInfoHelpUpdate, setEditingSchemaInfoHelpUpdate] = useState(false);

  const [editingSchemaSettings, setEditingSchemaSettings] = useState(false);
  const [editingSchemaSettingsTemp, setEditingSchemaSettingsTemp] = useState<Record<string, any>>({});
  const [editingSchemaSettingsUpdate, setEditingSchemaSettingsUpdate] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [focusItem, setFocusItem] = useState<any>([]);
  const [selectedTab, setSelectedTab] = useState("wave");
  const [action, setAction] = useState<string>("add");
  const [schemaTabs, setSchemaTabs] = useState<any[]>([]);

  const [selectedSubTab, setSelectedSubTab] = useState("attributes");

  //Modals
  const [schemaModalVisible, setSchemaModalVisible] = useState(false);
  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = useState(false);
  const [isCancelConfirmationModalVisible, setCancelConfirmationModalVisible] = useState(false);
  const [isNewSchemaModalVisible, setNewSchemaModalVisible] = useState(false);
  const [newSchemaName, setNewSchemaName] = useState("");
  const [newSchemaNameError, setNewSchemaNameError] = useState<string>();
  const [newSchemaFriendlyName, setNewSchemaFriendlyName] = useState("");
  const [isSavingSchema, setIsSavingSchema] = useState(false);

  // Custom Assets
  const customSchemaCreationEnabled = props.enabledModules.includes("WPM");

  const reloadSchema = React.useCallback(() => {
    setIsReloadingSchema(true);
    // reloadSchema actually is an async function but defined as sync in TestUtils
    // Wrap with Promise.resolve() to avoid modifying TestUtils causing extensive impact
    Promise.resolve(props.reloadSchema(true)).finally(() => setIsReloadingSchema(false));
  }, [props]);

  function handleAddItem() {
    setAction("add");
    setSchemaModalVisible(true);
    setFocusItem({});
  }

  function handleEditItem() {
    setAction("edit");
    setSchemaModalVisible(true);
    setFocusItem(selectedItems[0]);
  }

  function handleEditSchemaHelp(helpText?: HelpContent) {
    setEditingSchemaInfoHelp(true);
    setEditingSchemaInfoHelpTemp(helpText);
  }

  function handleUserInputEditSchemaHelp(
    key: "header" | "content" | "content_links" | "content_html",
    update: string | Tag[]
  ) {
    const tempUpdate: HelpContent = Object.assign({}, editingSchemaInfoHelpTemp);
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    tempUpdate[key] = update;
    setEditingSchemaInfoHelpTemp(tempUpdate);
    setEditingSchemaInfoHelpUpdate(true);
  }

  function handleCancelEditSchemaHelp() {
    setEditingSchemaInfoHelp(false);
    setEditingSchemaInfoHelpUpdate(false);
    setEditingSchemaInfoHelpTemp(undefined);
    setCancelConfirmationModalVisible(false);
  }

  async function handleSaveSchemaHelp() {
    try {
      await apiAdmin.putSchema(selectedTab, { schema_name: selectedTab, help_content: editingSchemaInfoHelpTemp });

      addNotification({
        type: "success",
        dismissible: true,
        header: "Update schema help",
        content: "Schema updated successfully.",
      });

      setEditingSchemaInfoHelp(false);
      setEditingSchemaInfoHelpUpdate(false);
      setEditingSchemaInfoHelpTemp(undefined);

      reloadSchema();
    } catch (e: any) {
      console.log(e);
      addNotification({
        type: "error",
        dismissible: true,
        header: "Save schema help",
        content: e.response?.data?.cause ?? "Unknown error occurred",
      });
    }
  }

  function handleEditSchemaSettings(schema: object | undefined) {
    setEditingSchemaSettings(true);
    if (schema === undefined) {
      setEditingSchemaSettingsTemp({});
    } else {
      setEditingSchemaSettingsTemp(schema);
    }
  }

  function handleUserInputEditSchemaSettings(key: string, update: string) {
    const tempUpdate: Record<string, any> = Object.assign({}, setEditingSchemaSettingsTemp);
    tempUpdate[key] = update;
    setEditingSchemaSettingsTemp(tempUpdate);
    setEditingSchemaSettingsUpdate(true);
  }

  function handleCancelEditSchemaSettings() {
    setEditingSchemaSettings(false);
    setEditingSchemaSettingsUpdate(false);
    setEditingSchemaSettingsTemp({});
    setCancelConfirmationModalVisible(false);
  }

  async function handleSaveSchemaSettings(e: { preventDefault: () => void }) {
    e.preventDefault();
    try {
      await apiAdmin.putSchema(selectedTab, {
        schema_name: selectedTab,
        friendly_name: editingSchemaSettingsTemp.friendly_name,
      });

      addNotification({
        type: "success",
        dismissible: true,
        header: "Update schema settings",
        content: "Schema updated successfully.",
      });

      setEditingSchemaSettings(false);
      setEditingSchemaSettingsUpdate(false);
      setEditingSchemaSettingsTemp({});

      reloadSchema();
    } catch (e: any) {
      console.log(e);
      addNotification({
        type: "error",
        dismissible: true,
        header: "Save schema help",
        content: e.response?.data?.cause || "Unknown error occurred",
      });
    }
  }

  function handleItemSelectionChange(selection: Array<any>) {
    setSelectedItems(selection);

    if (selection.length !== 0) {
      setFocusItem(selection[0]);
    } else {
      setFocusItem({});
    }
  }

  const handleSave = async (
    editItem: {
      name: string;
    },
    action: string
  ) => {
    try {
      if (action === "edit") {
        await apiAdmin.putSchemaAttr(selectedTab, editItem, editItem.name);

        setSchemaModalVisible(false);
        addNotification({
          type: "success",
          dismissible: true,
          header: "Update attribute",
          content: editItem.name + " updated successfully.",
        });

        reloadSchema();

        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});
      } else {
        await apiAdmin.postSchemaAttr(selectedTab, editItem);

        setSchemaModalVisible(false);
        addNotification({
          type: "success",
          dismissible: true,
          header: "Add attribute",
          content: editItem.name + " added successfully.",
        });

        reloadSchema();
      }
    } catch (e: any) {
      console.log(e);

      setSchemaModalVisible(false);
      addNotification({
        type: "error",
        dismissible: true,
        header: "Save attribute",
        content: e.response.data?.message || "Unknown error occurred",
      });
    }
  };

  async function handleDeleteItem() {
    const currentItem = 0;

    setDeleteConfirmationModalVisible(false);

    try {
      await apiAdmin.delSchemaAttr(selectedTab, selectedItems[0].name);

      addNotification({
        type: "success",
        dismissible: true,
        header: "Attribute deleted successfully",
        content: selectedItems[0].name + " was deleted.",
      });

      //Unselect applications marked for deletion to clear apps.
      reloadSchema();
      setSelectedItems([]);
    } catch (e: any) {
      console.log(e);
      addNotification({
        type: "error",
        dismissible: true,
        header: "Attribute deletion failed",
        content: selectedItems[currentItem].name + " failed to delete.",
      });
    }
  }

  async function handleCreateNewSchema() {
    if (newSchemaNameError) {
      return;
    }

    try {
      // Create a new schema with the provided name and friendly name
      setIsSavingSchema(true);
      const schemaFriendlyName = newSchemaFriendlyName || capitalize(newSchemaName);
      await apiAdmin.postSchema({
        schema_name: newSchemaName,
        // Assume all the schemas created by user are of type 'custom'
        schema_type: "custom",
        friendly_name: schemaFriendlyName,
        attributes: [],
      });
      // Auto create default attributes
      await Promise.all(
        fixedAttributesForCustomAssetSchema(newSchemaName, schemaFriendlyName).map(({ schemaName, attribute }) =>
          apiAdmin.postSchemaAttr(schemaName, attribute)
        )
      );

      addNotification({
        type: "success",
        dismissible: true,
        header: "Schema created successfully",
        content: `Schema "${newSchemaName}" was created successfully.`,
      });

      // Reset form fields
      setNewSchemaName("");
      setNewSchemaFriendlyName("");
      setNewSchemaModalVisible(false);

      // Reload schemas to show the new one
      reloadSchema();

      // Select the newly created schema tab
      setSelectedTab(newSchemaName);
    } catch (e: any) {
      console.log(e);
      addNotification({
        type: "error",
        dismissible: true,
        header: "Schema creation failed",
        content: e.response?.data?.message || "Failed to create new schema. Please try again.",
      });
      setNewSchemaModalVisible(false);
    } finally {
      setIsSavingSchema(false);
    }
  }

  function getDeleteHandler(selectedItems: any[]) {
    if (selectedItems.length !== 0) {
      if (!selectedItems[0].system) {
        return async function () {
          setDeleteConfirmationModalVisible(true);
        };
      } else {
        return undefined;
      }
    } else {
      return async function () {
        setDeleteConfirmationModalVisible(true);
      };
    }
  }

  const getTabs = (
    schemaName: string,
    currentSchema: EntitySchema,
    currentHelpContent: HelpContent | undefined
  ): TabsProps.Tab => {
    const label = capitalize(schemaName);
    return {
      id: schemaName,
      label:
        currentSchema.schema_type === "user" ? (
          label
        ) : (
          <SpaceBetween direction="horizontal" size="xxs">
            {label}
            <span title="Custom Schema">
              <Icon name="star" />
            </span>
          </SpaceBetween>
        ),
      content: (
        <Tabs
          activeTabId={selectedSubTab}
          onChange={({ detail }) => setSelectedSubTab(detail.activeTabId)}
          tabs={[
            {
              label: "Attributes",
              id: "attributes",
              content: (
                <SchemaAttributesTable
                  items={currentSchema.attributes}
                  isLoading={isReloadingSchema}
                  error={!props.schemas ? "Error reading schema" : undefined}
                  selectedItems={selectedItems}
                  handleSelectionChange={handleItemSelectionChange}
                  handleAddItem={handleAddItem}
                  handleDeleteItem={getDeleteHandler(selectedItems)}
                  handleEditItem={handleEditItem}
                />
              ),
            },
            {
              label: "Info Panel",
              id: "infopanel",
              content: isReloadingSchema ? (
                <Spinner />
              ) : (
                <Container
                  className="custom-dashboard-container"
                  header={
                    <Header
                      variant="h2"
                      description="Define the content that will be provided to the user if they click the Info link next this table."
                      actions={
                        <SpaceBetween direction="horizontal" size="xs">
                          <Button
                            variant={editingSchemaInfoHelp ? "primary" : undefined}
                            disabled={!editingSchemaInfoHelp}
                            onClick={() => setCancelConfirmationModalVisible(true)}
                          >
                            Cancel
                          </Button>
                          <Button disabled={!editingSchemaInfoHelp} onClick={handleSaveSchemaHelp}>
                            Save
                          </Button>
                          <Button
                            variant="primary"
                            disabled={editingSchemaInfoHelp}
                            onClick={() => handleEditSchemaHelp(currentHelpContent ?? {})}
                          >
                            Edit
                          </Button>
                        </SpaceBetween>
                      }
                    >
                      Info panel guidance
                    </Header>
                  }
                >
                  {editingSchemaInfoHelp ? (
                    <ColumnLayout columns={2}>
                      <ToolHelpEdit
                        editingSchemaInfoHelpTemp={editingSchemaInfoHelpTemp}
                        handleUserInputEditSchemaHelp={handleUserInputEditSchemaHelp}
                      />
                      <Container key={"help_preview"} header={<Header variant="h2">Preview</Header>}>
                        <ToolHelp helpContent={editingSchemaInfoHelpTemp} />
                      </Container>
                    </ColumnLayout>
                  ) : (
                    <ToolHelp helpContent={currentHelpContent} />
                  )}
                </Container>
              ),
            },
            {
              label: "Schema Settings",
              id: "schema_settings",
              content: isReloadingSchema ? (
                <Spinner />
              ) : (
                <Container
                  className="custom-dashboard-container"
                  header={
                    <Header
                      variant="h2"
                      actions={
                        <SpaceBetween direction="horizontal" size="xs">
                          <Button
                            variant={editingSchemaSettings ? "primary" : undefined}
                            disabled={!editingSchemaSettings}
                            onClick={() => setCancelConfirmationModalVisible(true)}
                          >
                            Cancel
                          </Button>
                          <Button disabled={!editingSchemaSettings} onClick={handleSaveSchemaSettings}>
                            Save
                          </Button>
                          <Button
                            variant="primary"
                            disabled={editingSchemaSettings}
                            onClick={() => handleEditSchemaSettings(currentSchema)}
                          >
                            Edit
                          </Button>
                        </SpaceBetween>
                      }
                    >
                      General Schema Settings
                    </Header>
                  }
                >
                  {editingSchemaSettings ? (
                    <>
                      <FormField
                        key={"schema_friendly_name"}
                        label={"Schema friendly name"}
                        description={"Schema name shown on the user interface."}
                      >
                        <Input
                          onChange={(event) => handleUserInputEditSchemaSettings("friendly_name", event.detail.value)}
                          value={editingSchemaSettingsTemp.friendly_name ? editingSchemaSettingsTemp.friendly_name : ""}
                        />
                      </FormField>
                    </>
                  ) : (
                    <SpaceBetween size={"xxxs"}>
                      <Box margin={{ bottom: "xxxs" }} color="text-label">
                        {"Schema friendly name"}
                      </Box>
                      {getNestedValuePath(currentSchema, "friendly_name")
                        ? getNestedValuePath(currentSchema, "friendly_name")
                        : "-"}
                    </SpaceBetween>
                  )}
                </Container>
              ),
            },
          ]}
        />
      ),
    };
  };

  //On schema metadata change reload tabs.
  useEffect(() => {
    const tabs = [];
    if (props.schemas) {
      //Load tabs from schema.
      for (const schema of props.schemaMetadata) {
        const schemaName = schema["schema_name"];
        if (["user", "custom"].includes(schema["schema_type"])) {
          const currentSchema = props.schemas[schemaName];
          const currentHelpContent: HelpContent | undefined = getNestedValuePath(currentSchema, "help_content");
          tabs.push(getTabs(schemaName, currentSchema, currentHelpContent));
        }
      }

      // Add a "Create New Tab" button as the last tab
      if (customSchemaCreationEnabled) {
        tabs.push({
          label: (
            <Button iconName="add-plus" variant="inline-icon" ariaLabel="Add new schema tab">
              Add New Schema
            </Button>
          ),
          id: "add_new_schema_tab",
          content: <div></div>,
        });
      }

      setSchemaTabs(tabs);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    props.schemaMetadata,
    selectedItems,
    editingSchemaInfoHelp,
    editingSchemaInfoHelpTemp,
    selectedSubTab,
    editingSchemaSettings,
    editingSchemaSettingsTemp,
  ]);

  // Must be wrapped in useEffect, because React can't update a different component while this component is rendered.
  useEffect(() => {
    //Update help tools panel.
    setHelpPanelContent({
      header: "Attributes",
      content_text: "From this screen as administrator you can add, update and delete schema attributes.",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Validate New Schema name
  useEffect(() => {
    const schemaNameRegex = /^[a-z][a-z0-9_]{0,39}$/i;
    if (!newSchemaName) {
      setNewSchemaNameError("Schema name is required");
    } else if (!schemaNameRegex.test(newSchemaName)) {
      setNewSchemaNameError(
        "Schema name must be 1-40 characters long, start with a letter and contain only letters, numbers, and underscores."
      );
    } else if (props.schemas[newSchemaName]) {
      setNewSchemaNameError(`A schema with name "${newSchemaName}" already exists.`);
    } else {
      setNewSchemaNameError(undefined);
    }
  }, [newSchemaName, props.schemas]);

  const alert =
    editingSchemaInfoHelpUpdate || editingSchemaSettingsUpdate ? (
      <Alert type="warning"> There are unsaved updates that will be lost. </Alert>
    ) : (
      <></>
    );

  return (
    <div>
      {!props.schemas ? (
        <StatusIndicator type="loading">Loading schema...</StatusIndicator>
      ) : (
        <Tabs
          activeTabId={selectedTab}
          onChange={({ detail }) => {
            if (detail.activeTabId === "add_new_schema_tab") {
              setNewSchemaModalVisible(true);
            } else {
              setSelectedTab(detail.activeTabId);
            }
          }}
          tabs={schemaTabs}
        />
      )}

      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={"Delete attribute"}
      >
        {selectedItems.length === 1 ? (
          <SpaceBetween size="l">
            <p>Are you sure you wish to delete the selected attribute?</p>
            <Alert type="warning">
              No existing data stored in this attribute will be removed, it will just no longer be visible in the UI or
              avilable for new records.
            </Alert>
          </SpaceBetween>
        ) : (
          <p>
            Are you sure you wish to delete the {selectedItems.length} selected atrributes? No existing data stored in
            this attribute will be removed, it will just no longer be visible in the UI or available for new records.
          </p>
        )}
      </CMFModal>

      <CMFModal
        onDismiss={() => setCancelConfirmationModalVisible(false)}
        visible={isCancelConfirmationModalVisible}
        onConfirmation={editingSchemaInfoHelp ? handleCancelEditSchemaHelp : handleCancelEditSchemaSettings}
        header={"Cancel schema update"}
      >
        <p>Are you sure you wish to cancel the updates to the schema?</p>
        {alert}
      </CMFModal>

      <CMFModal
        onDismiss={() => setNewSchemaModalVisible(false)}
        visible={isNewSchemaModalVisible}
        onConfirmation={handleCreateNewSchema}
        header={"Create New Schema"}
        isLoading={isSavingSchema}
      >
        <SpaceBetween size="l">
          <FormField
            label="Schema Name"
            description="Technical name for the schema (lowercase, no spaces)"
            errorText={newSchemaNameError}
          >
            <Input
              value={newSchemaName}
              onChange={({ detail }) => setNewSchemaName(detail.value.toLowerCase().replace(/\s+/g, "_"))}
            />
          </FormField>
          <FormField label="Friendly Name" description="Display name for the schema as shown in the UI">
            <Input value={newSchemaFriendlyName} onChange={({ detail }) => setNewSchemaFriendlyName(detail.value)} />
          </FormField>
          <Alert type="info">
            Creating a new schema will add a new entity type to the system. You will need to define attributes for this
            schema after creation.
          </Alert>
        </SpaceBetween>
      </CMFModal>

      {schemaModalVisible ? (
        <SchemaAttributeAmendModal
          title={`${capitalize(action)} attribute`}
          onConfirmation={handleSave}
          closeModal={() => setSchemaModalVisible(false)}
          attribute={focusItem}
          action={action}
          schemas={props.schemas}
          activeSchemaName={selectedTab}
        />
      ) : (
        <></>
      )}
    </div>
  );
};

export default AdminSchemaMgmt;

// Fixed attributes we should auto create when a new custom asset schema is created
const fixedAttributesForCustomAssetSchema = (
  schemaName: string,
  schemaFriendlyName: string
): { schemaName: string; attribute: Attribute }[] => [
  {
    schemaName,
    attribute: {
      name: `${schemaName}_id`,
      description: `${schemaFriendlyName} Id`,
      hidden: true,
      required: true,
      system: true,
      type: "string",
    },
  },
  {
    schemaName,
    attribute: {
      name: `${schemaName}_name`,
      description: `${schemaFriendlyName} Name`,
      required: true,
      system: true,
      type: "string",
      validation_regex: "^(?!\\s*$).{1,255}$",
      validation_regex_msg: `${schemaFriendlyName} name must be specified, and be a maximum of 255 characters.`,
    },
  },
  {
    schemaName,
    attribute: {
      description: "Related Applications",
      help_content: {
        content_html: `Select applications that this ${schemaFriendlyName} is associated with.`,
        header: "Related Applications",
      },
      name: "app_ids",
      rel_display_attribute: "app_name",
      rel_entity: "app",
      rel_key: "app_id",
      required: false,
      system: true,
      type: "multivalue-relationship",
      listMultiSelect: true,
    },
  },
  {
    schemaName: Schemas.Application.name,
    attribute: {
      description: `Related ${schemaFriendlyName}s`,
      help_content: {
        content_html: `${schemaFriendlyName}s related to this application. To modify, edit the ${schemaFriendlyName} instead.`,
        header: `Related ${schemaFriendlyName}s`,
      },
      name: `${schemaName}_ids`,
      readonly: true,
      rel_display_attribute: `${schemaName}_name`,
      // Custom asset entity can have any name
      rel_entity: schemaName as EntityName,
      rel_key: `${schemaName}_id`,
      required: false,
      system: true,
      type: "multivalue-relationship",
      listMultiSelect: true,
    },
  },
];
