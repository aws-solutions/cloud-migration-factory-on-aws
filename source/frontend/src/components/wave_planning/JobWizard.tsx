/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * JobWizard.tsx
 *
 * This component implements a multi-step wizard for creating and managing migration jobs
 * in the Cloud Migration Factory solution. It guides users through the process of:
 * 1. Creating a migration job
 * 2. Selecting applications to include in the job
 * 3. Managing move groups (logical groupings of applications and their dependencies)
 * 4. Organizing migration waves (time-based groupings of move groups)
 *
 * The wizard integrates with AWS backend services to persist data at each step
 * and provides validation to ensure proper migration planning.
 */

import React from "react";
import {
  Box,
  ButtonDropdown,
  Link,
  NonCancelableCustomEvent,
  SpaceBetween,
  Wizard,
  WizardProps,
} from "@cloudscape-design/components";
import { ToolsContext } from "../../contexts/ToolsContext.tsx";
import ItemAmend from "../ItemAmend.tsx";
import { useGetItems } from "../../actions/ItemsHook.ts";
import UserApiClient from "../../api_clients/userApiClient.ts";
import { tryParseFloat } from "../../resources/main.ts";
import { NotificationContext } from "../../contexts/NotificationContext.tsx";
import { parsePUTResponseErrors, UNEXPECTED_ERROR } from "../../resources/recordFunctions.ts";
import { useNavigate } from "react-router-dom";
import ManageMoveGroupStep from "./ManageMoveGroupStep.tsx";
import { useMFApps } from "../../actions/ApplicationsHook.ts";
import {
  Application,
  WPMApplication,
  EntitySchema,
  MoveGroup,
  MoveGroupRequest,
  UserAccess,
  Wave,
  WPMAllData,
  WPMJob,
  WPMRule,
  Server,
  Database,
  MoveEntitiesPayload,
  OperationType,
  TargetEntity,
  WPMJobRule,
} from "../../models";
import { DEFAULT_WPM_VALUES, Schemas } from "../../utils/Constants.ts";
import ToolsApiClient from "../../api_clients/toolsApiClient.ts";
import { ErrorWithType, useErrorHandler } from "../../actions/ErrorHandlerHook.ts";
import ManageWaveStep from "./ManageWaveStep.tsx";
import TransferList from "./TransferList.tsx";
import { useGetDatabases } from "../../actions/DatabasesHook.ts";
import { useGetServers } from "../../actions/ServersHook.ts";
import { syncAssetRelationships, stepToIndex, indexToStep, ReadOnlyAlert } from "./JobWizard.util";
import { normalize } from "../../utils/schema-utils.ts";

/**
 * Type definition for JobWizard component props
 * @typedef {Object} JobWizardParams
 * @property {Record<string, EntitySchema>} schemas - Schema definitions for all entity types
 * @property {UserAccess} userEntityAccess - User access permissions for entities
 */
type JobWizardParams = {
  readonly schemas: Record<string, EntitySchema>;
  readonly userEntityAccess: UserAccess;
};

// Default empty job object for initialization
const EMPTY_JOB: WPMJob = { wpm_job_name: "", current_step: indexToStep(0) } as const;

// Helper function to format error messages consistently
const formatErrorMessage = (errors: unknown): string => {
  if (Array.isArray(errors)) {
    return errors
      .map((error) =>
        typeof error === "object" && error !== null && "message" in error ? error.message : String(error)
      )
      .join(", ");
  }
  return typeof errors === "string" ? errors : JSON.stringify(errors) || UNEXPECTED_ERROR;
};

// API client instances
const apiUser = new UserApiClient();
const apiTools = new ToolsApiClient();

// Base path for navigation
const basepath = "/wpm_jobs";

/**
 * JobWizard component - Manages the multi-step process of creating migration jobs
 *
 * @param {JobWizardParams} props - Component properties
 * @returns {React.ReactElement} The rendered wizard component
 */
export const JobWizard = (props: JobWizardParams) => {
  const { setHelpPanelContent } = React.useContext(ToolsContext);
  const { addNotification } = React.useContext(NotificationContext);
  const navigate = useNavigate();
  const handleError = useErrorHandler();

  // Memorize a UserAccess object with readonly permission for WPM Job
  // so as to disable the edit in ItemAmend and ItemTable components
  const readOnlyUserAccess = React.useMemo(
    () => ({
      ...props.userEntityAccess,
      [Schemas.WPMJob.name]: { read: true },
    }),
    [props.userEntityAccess]
  );

  // UI state management
  const [isLoadingNextStep, setIsLoadingNextStep] = React.useState<boolean>(false);
  const [activeStepIndex, setActiveStepIndex] = React.useState(0);

  // Help panel content configuration
  const helpContent = {
    header: "JobCreation",
    content_text:
      "Use this wizard to select applications, create move groups, and organize migration waves for planning your application migration strategy.",
  };

  // Fetch data using custom hooks
  const [getWpmJobState, { update: updateWPMJobs }] = useGetItems(Schemas.WPMJob.name);
  const [getWpmRuleState] = useGetItems(Schemas.WPMRule.name);

  // Get applications, servers and databases by calling hooks
  // refreshServers takes no arg
  const [getServerState, { update: refreshServers }] = useGetServers();
  const [getDatabaseState, { update: updateDatabases }] = useGetDatabases();
  const [getApplicationState, { update: updateApplications }] = useMFApps();
  const [getMoveGroupState, { update: updateMoveGroups }] = useGetItems(Schemas.MoveGroup.name);
  const [getWaveState, { update: updateWave }] = useGetItems(Schemas.Wave.name);

  const refreshWPMJobs = React.useCallback(() => updateWPMJobs(Schemas.WPMJob.name), [updateWPMJobs]);
  const refreshDatabases = React.useCallback(() => updateDatabases(Schemas.Database.name), [updateDatabases]);
  const refreshApplications = React.useCallback(
    () => updateApplications(Schemas.Application.name),
    [updateApplications]
  );
  const refreshMoveGroups = React.useCallback(() => updateMoveGroups(Schemas.MoveGroup.name), [updateMoveGroups]);
  const refreshWaves = React.useCallback(() => updateWave(Schemas.Wave.name), [updateWave]);

  // State management for migration entities
  const [servers, setServers] = React.useState<Server[]>([]);
  const [databases, setDatabases] = React.useState<Database[]>([]);
  const [applications, setApplications] = React.useState<WPMApplication[]>([]);
  // Move group request state - null for new jobs, populated when editing existing jobs
  const [moveGroupRequest, setMoveGroupRequest] = React.useState<MoveGroupRequest>();
  const [moveGroups, setMoveGroups] = React.useState<MoveGroup[]>([]);
  const [waves, setWaves] = React.useState<Wave[]>([]);
  const [availableApps, setAvailableApps] = React.useState<Array<WPMApplication>>([]);
  // Job state - EMPTY_JOB for new jobs, populated when editing existing jobs
  const [job, setJob] = React.useState<WPMJob>(EMPTY_JOB);
  const [jobFormValid, setJobFormValid] = React.useState<boolean>(false);
  // Calculate app rankings state
  const [isRecalculatingRanks, setIsRecalculatingRanks] = React.useState<boolean>(false);

  // Sync API data retrieval state to react state
  // This enables resuming a Job in future (additional changes will be required)
  React.useEffect(() => {
    if (getServerState.data) setServers(getServerState.data);
  }, [getServerState.data]);

  React.useEffect(() => {
    if (getDatabaseState.data) setDatabases(getDatabaseState.data);
  }, [getDatabaseState.data]);

  React.useEffect(() => {
    if (getApplicationState.data) setApplications(getApplicationState.data);
  }, [getApplicationState.data]);

  React.useEffect(() => {
    if (getMoveGroupState.data)
      setMoveGroups(getMoveGroupState.data.filter((mg: MoveGroup) => mg.wpm_job_id === job.wpm_job_id));
  }, [getMoveGroupState.data, job.wpm_job_id]);

  React.useEffect(() => {
    if (getWaveState.data) setWaves(getWaveState.data.filter((w: Wave) => w.wpm_job_id === job.wpm_job_id));
  }, [getWaveState.data, job.wpm_job_id]);

  // Track loading states of all data dependencies
  const loadingStates = React.useMemo(
    () => [
      getApplicationState,
      getDatabaseState,
      getServerState,
      getMoveGroupState,
      getWaveState,
      getWpmJobState,
      getWpmRuleState,
    ],
    [
      getApplicationState,
      getDatabaseState,
      getMoveGroupState,
      getServerState,
      getWaveState,
      getWpmJobState,
      getWpmRuleState,
    ]
  );

  // Combine all data sources into a single object for child components
  const dataAll: WPMAllData = React.useMemo(
    () => ({
      app: getApplicationState,
      database: getDatabaseState,
      rule: getWpmRuleState,
      server: getServerState,
      move_group: getMoveGroupState,
      wave: getWaveState,
      wpm_job: getWpmJobState,
    }),
    [
      getApplicationState,
      getDatabaseState,
      getMoveGroupState,
      getServerState,
      getWaveState,
      getWpmJobState,
      getWpmRuleState,
    ]
  );

  // Update loading state based on any data source still loading
  React.useEffect(() => setIsLoadingNextStep(loadingStates.some((s) => s.isLoading)), [loadingStates]);

  /**
   * Initialize job configuration from rules
   * Loads default job configuration values from the WPM_JOB rule type
   * when available, while preserving any user-entered values
   */
  React.useEffect(() => {
    // Set the default job when jobConfig rule is loaded
    if (!getWpmRuleState.isLoading && getWpmRuleState.data.length > 0) {
      const jobConfigRule: WPMJobRule = getWpmRuleState.data.find(
        (rule: WPMRule) =>
          rule.rule_type === "WPM_JOB" && rule.rule_id === "DEFAULT_WPM_JOB_CONFIG" && rule.status === "ENABLED"
      );
      const jobConfig = jobConfigRule?.configuration;
      if (!jobConfig) {
        return;
      }
      setJob((prevJob: WPMJob) => {
        // Do not override if user already entered data for a field
        const defaultIfUnset = (key: keyof typeof jobConfig, fallback: number): number =>
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (prevJob as any)[key] ?? tryParseFloat(jobConfig[key], fallback);
        return {
          ...prevJob,
          nomination_app_count: defaultIfUnset("nomination_app_count", 0),
          wave_server_capacity: defaultIfUnset("wave_server_capacity", 0),
          wave_storage_capacity: defaultIfUnset("wave_storage_capacity", 0),
          starting_wave_server_capacity: defaultIfUnset("starting_wave_server_capacity", 0),
          wave_server_capacity_increase: defaultIfUnset("wave_server_capacity_increase", 0),
        };
      });
    }
  }, [getWpmRuleState.isLoading, getWpmRuleState.data]);

  // Memorize the sorted apps
  // This filters out completed applications and sorts them by rank (priority).
  const sortedApps = React.useMemo(
    () =>
      getApplicationState.isLoading || !applications.length
        ? []
        : applications
            // Filter out completed applications and keep those that need planning
            .filter((app: WPMApplication) => {
              const noWpmJob = !app.wpm_job_ids?.length; // exclude apps in another job wizard
              const noMoveGroups = !app.move_group_ids?.length;
              const noWaves = !app.wave_ids?.length;
              const notCompleted = app.planning_status != null && app.planning_status !== "COMPLETED";

              // Keep applications belong to this job so that the selected apps can display properly
              // when user navigate back to Manage applications step after apps reloaded from DB
              const currentWpmJob = job.wpm_job_id && app.wpm_job_ids?.includes(job.wpm_job_id);
              return (noWpmJob && noMoveGroups && noWaves) || notCompleted || currentWpmJob;
            })
            // Sort apps by rank (lower rank number means higher priority)
            .sort((a: WPMApplication, b: WPMApplication) => {
              // If one has rank and the other doesn't, prioritize the one with rank
              if (!!a.rank && !b.rank) return -1;
              if (!a.rank && !!b.rank) return 1;

              // If both have ranks or both don't have ranks, compare normally
              const rankA = tryParseFloat(a.rank, DEFAULT_WPM_VALUES.MAX_RANK);
              const rankB = tryParseFloat(b.rank, DEFAULT_WPM_VALUES.MAX_RANK);
              return rankA - rankB;
            })
            // Make a shallow copy so the modification below does not change applications
            .map((app) => ({ ...app })),
    [getApplicationState.isLoading, applications, job.wpm_job_id]
  );

  // Update the available apps if sortedApps change but keep the selection (i.e. `curr_wpm_job_id`)
  React.useEffect(
    () =>
      setAvailableApps((prev) => {
        const selectionMap = new Map(prev.map((app) => [app.app_id, app.curr_wpm_job_id]));
        return sortedApps.map((app) => ({ ...app, curr_wpm_job_id: selectionMap.get(app.app_id) }));
      }),
    [sortedApps]
  );

  React.useEffect(() => {
    // Get the selected apps (i.e. `curr_wpm_job_id` based on `wpm_job_ids` in DB
    const appsOfCurrentJob = sortedApps.filter((app) => app.wpm_job_ids?.includes(job.wpm_job_id ?? ""));
    // If no (i.e. create job) then default to the first x of nominated app count
    const topXApps = sortedApps.slice(0, job.nomination_app_count ?? DEFAULT_WPM_VALUES.NOMINATION_COUNT);
    const selectedApps = appsOfCurrentJob.length ? appsOfCurrentJob : topXApps;
    const selectedAppIdSet = new Set(selectedApps.map((app) => app.app_id));
    setAvailableApps((prev) =>
      prev.map((app) => (selectedAppIdSet.has(app.app_id) ? { ...app, curr_wpm_job_id: job.wpm_job_id } : app))
    );
  }, [job.nomination_app_count, job.wpm_job_id, sortedApps]);

  /**
   * Handle changes to wave assignments
   *
   * Updates the waves, move groups, and related entities when wave assignments change.
   * This ensures all entities maintain consistent relationships.
   * Error handling is delegated to the TransferList pop-up
   *
   * @param {Wave[]} updatedWaves - The updated wave configurations
   * @param {MoveGroup[]} updatedMoveGroups - The updated move group configurations
   */
  const saveManageWaveChanges = React.useCallback(
    async (updatedWaves: Wave[], updatedMoveGroups: MoveGroup[]) => {
      // Track move groups that have changed waves, grouped by source and destination
      const waveTransitions = new Map();

      // Detect move groups that have changed waves
      for (const updatedMoveGroup of updatedMoveGroups) {
        const originalMoveGroup = moveGroups.find((mg) => mg.move_group_id === updatedMoveGroup.move_group_id);

        if (!originalMoveGroup) continue; // Skip if this is a new move group

        // Check if the wave assignment has changed
        if (originalMoveGroup.wave_id !== updatedMoveGroup.wave_id) {
          // Create a key for this source-destination pair
          const transitionKey = `${originalMoveGroup.wave_id || "null"}-${updatedMoveGroup.wave_id || "null"}`;

          if (!waveTransitions.has(transitionKey)) {
            waveTransitions.set(transitionKey, {
              sourceWaveId: originalMoveGroup.wave_id,
              destinationWaveId: updatedMoveGroup.wave_id,
              moveGroups: [],
            });
          }

          // Add this move group to the appropriate transition group
          waveTransitions.get(transitionKey).moveGroups.push({
            entity_type: "move_group",
            entity_id: updatedMoveGroup.move_group_id,
          });
        }
      }

      // Process each wave transition (source-destination pair)
      for (const transition of waveTransitions.values()) {
        // Prepare payload for the manage_entities Lambda function API call
        const payload: MoveEntitiesPayload = {
          operation: OperationType.MOVE,
          source_entity_type: "wave",
          source_entity_id: transition.sourceWaveId,
          destination_entity_type: "wave",
          destination_entity_id: transition.destinationWaveId,
          target_entities: transition.moveGroups,
        };

        // Call the manage_entities Lambda function API
        const result = await apiTools.manageEntities(payload);

        if (!result) {
          throw new Error(UNEXPECTED_ERROR);
        }

        if (result.errors) {
          throw new Error(formatErrorMessage(result.errors));
        }
      }

      // Update local state with the new waves and move groups
      setWaves(updatedWaves);
      setMoveGroups(updatedMoveGroups);

      // Refresh data after successful update
      refreshWaves();
      refreshMoveGroups();
      refreshApplications();
      refreshDatabases();
      refreshServers();

      addNotification({
        type: "success",
        dismissible: true,
        header: "Wave changes saved",
        content: "Wave assignments have been updated successfully.",
      });
    },
    [
      addNotification,
      refreshApplications,
      refreshDatabases,
      refreshMoveGroups,
      refreshServers,
      refreshWaves,
      moveGroups,
    ]
  );

  /**
   * Handle changes to move group assignments
   *
   * Updates move groups and related entities when move group assignments change.
   * Uses the manage_entities Lambda function API call to update all entities at once.
   *
   * @param {MoveGroup} updatedMoveGroup - The updated move group
   * @param {Server[]} servers - Current server configurations
   * @param {Database[]} databases - Current database configurations
   * @returns {Promise<void>} Promise that resolves when changes are saved
   */
  const manageMoveGroupOnChange = React.useCallback(
    async (updatedMoveGroup: MoveGroup, updatedServers: Server[], updatedDatabases: Database[]) => {
      // Update data model corresponding to all entities in this move group
      const updatedAssetRelationshipData = syncAssetRelationships(
        updatedMoveGroup,
        updatedServers,
        updatedDatabases,
        applications
      );

      setDatabases(updatedDatabases);
      setServers(updatedServers);
      // Update moveGroups state with the updated move group
      setMoveGroups((moveGroups) => {
        const updatedMoveGroups = [...moveGroups];
        const index = updatedMoveGroups.findIndex((mg) => mg.move_group_id === updatedMoveGroup.move_group_id);

        if (index !== -1) {
          // Replace existing move group
          updatedMoveGroups[index] = updatedAssetRelationshipData.updatedMoveGroup;
        } else {
          // Add new move group
          updatedMoveGroups.push(updatedAssetRelationshipData.updatedMoveGroup);
        }

        return updatedMoveGroups;
      });

      // Find servers that were removed from the move group
      const currentServerIds = new Set(
        updatedServers.filter((s) => s.move_group_id === updatedMoveGroup.move_group_id).map((s) => s.server_id)
      );
      const previousServerIds = new Set(updatedMoveGroup.server_ids || []);
      const removedServerIds = [...previousServerIds].filter((id) => !currentServerIds.has(id));

      // Find servers that were added to the move group
      const addedServerIds = [...currentServerIds].filter((id) => !previousServerIds.has(id));

      // Find databases that were removed from the move group
      const currentDatabaseIds = new Set(
        updatedDatabases.filter((d) => d.move_group_id === updatedMoveGroup.move_group_id).map((d) => d.database_id)
      );
      const previousDatabaseIds = new Set(updatedMoveGroup.database_ids || []);
      const removedDatabaseIds = [...previousDatabaseIds].filter((id) => !currentDatabaseIds.has(id));

      // Find databases that were added to the move group
      const addedDatabaseIds = [...currentDatabaseIds].filter((id) => !previousDatabaseIds.has(id));

      // Prepare target entities for the API call - only include removed entities
      const removedEntities: TargetEntity[] = [
        // Add removed servers to target entities
        ...removedServerIds.map((serverId) => ({
          // TypeScript does not correctly infer types within mapper functions, use `as const` as a workaround
          entity_type: "server" as const,
          entity_id: serverId,
        })),
        // Add removed databases to target entities
        ...removedDatabaseIds.map((databaseId) => ({
          entity_type: "database" as const,
          entity_id: databaseId,
        })),
      ];

      // Prepare target entities for added assets
      const addedEntities: TargetEntity[] = [
        // Add added servers to target entities
        ...addedServerIds.map((serverId) => ({
          entity_type: "server" as const,
          entity_id: serverId,
        })),
        // Add added databases to target entities
        ...addedDatabaseIds.map((databaseId) => ({
          entity_type: "database" as const,
          entity_id: databaseId,
        })),
      ];

      // Prepare operations to run
      const operations = [];

      if (removedEntities.length) {
        const removedPayload: MoveEntitiesPayload = {
          operation: OperationType.MOVE,
          source_entity_type: "move_group",
          source_entity_id: updatedMoveGroup.move_group_id,
          destination_entity_type: "move_group",
          target_entities: removedEntities,
        };
        operations.push(apiTools.manageEntities(removedPayload));
      }

      if (addedEntities.length) {
        const addedPayload: MoveEntitiesPayload = {
          operation: OperationType.MOVE,
          source_entity_type: "move_group",
          destination_entity_type: "move_group",
          destination_entity_id: updatedMoveGroup.move_group_id,
          target_entities: addedEntities,
        };
        operations.push(apiTools.manageEntities(addedPayload));
      }

      // Run all operations and collect results
      const results = await Promise.allSettled(operations);

      // Collect any errors
      const errors = results
        .filter((result) => result.status === "rejected" || (result.status === "fulfilled" && result.value?.errors))
        .flatMap((result) => {
          if (result.status === "rejected") return [result.reason.message];
          return [formatErrorMessage(result.value.errors)];
        });

      if (errors.length) {
        throw new Error(errors.join(", "));
      }
      // Refresh data after successful update
      refreshMoveGroups();
      refreshApplications();
      refreshDatabases();
      refreshServers();
    },
    [applications, refreshMoveGroups, refreshApplications, refreshDatabases, refreshServers]
  );

  const jobCurrentStepIndex = React.useMemo(() => stepToIndex(job.current_step), [job.current_step]);

  const isStepReadOnly = React.useCallback(
    (stepIndex: number): boolean => jobCurrentStepIndex > stepIndex,
    [jobCurrentStepIndex]
  );

  /**
   * Handle recalculating application ranks
   *
   * Calls the API to recalculate application ranks and refreshes application state
   */
  const handleRecalculateAppRanks = React.useCallback(() => {
    setIsRecalculatingRanks(true);
    apiTools
      .calculateAppRanks()
      .then(() => {
        // Refresh applications to get updated ranks
        refreshApplications();
      })
      .catch((error) => {
        console.error("Failed to recalculate application ranks", error);
        addNotification({
          type: "error",
          dismissible: true,
          header: "Recalculate App Ranks",
          content: "Failed to recalculate application ranks",
        });
      })
      .finally(() => {
        setIsRecalculatingRanks(false);
      });
  }, [refreshApplications, addNotification]);

  /**
   * Define the wizard steps configuration
   *
   * @returns {Array<Object>} Array of step configurations for the wizard
   */
  const getSteps = () => {
    return [
      {
        title: "Create job",
        info: (
          <Link variant="info" onFollow={() => setHelpPanelContent(helpContent, false)}>
            Info
          </Link>
        ),
        description: (
          <SpaceBetween size={"xl"} direction={"vertical"}>
            The system recommends the following applications for this wave plan based on their prioritization rank
          </SpaceBetween>
        ),
        content: (
          <SpaceBetween size={"xl"} direction={"vertical"}>
            {isStepReadOnly(0) ? <ReadOnlyAlert /> : undefined}
            <ItemAmend
              action="Add"
              schemaName={Schemas.WPMJob.name}
              schemas={props.schemas}
              userAccess={isStepReadOnly(0) ? readOnlyUserAccess : props.userEntityAccess}
              item={job}
              handleItemUpdate={setJob}
              handleFormValidationUpdate={setJobFormValid}
            />
          </SpaceBetween>
        ),
      },
      {
        title: "Manage applications",
        content: (
          <SpaceBetween size={"xl"} direction={"vertical"}>
            {isStepReadOnly(1) ? <ReadOnlyAlert /> : undefined}
            <TransferList
              readOnly={isStepReadOnly(1)}
              onUpdate={({ children }) => setAvailableApps(children)}
              header={
                <Box textAlign="right">
                  <ButtonDropdown
                    items={[
                      {
                        id: "recalc-app-ranks",
                        text: "Recalculate app ranks",
                        iconName: "refresh",
                        disabled: isStepReadOnly(1) || isRecalculatingRanks,
                      },
                    ]}
                    variant="icon"
                    ariaLabel="Actions menu"
                    onItemClick={({ detail }) => {
                      if (detail.id === "recalc-app-ranks") {
                        handleRecalculateAppRanks();
                      }
                    }}
                  />
                </Box>
              }
              isLoading={isRecalculatingRanks || getApplicationState.isLoading}
              parent={{
                records: [job],
                labelAttribute: "wpm_job_name",
                valueAttribute: "wpm_job_id",
                selectedValue: job.wpm_job_id ?? "",
              }}
              child={{
                records: availableApps,
                valueAttribute: "app_id",
                relationshipAttribute: "curr_wpm_job_id",
                schemaName: Schemas.Application.name,
                schema: props.schemas[Schemas.Application.name],
                sortByColumn: "rank",
              }}
              hideDropdown={true}
              customLabels={{
                sourceHeader: "Applications included in new job",
                targetHeader: "Unassigned applications",
                sourceButtonText: "Remove from Job",
                targetButtonText: "Add to Job",
              }}
            ></TransferList>
          </SpaceBetween>
        ),
      },
      {
        title: "Manage move groups",
        content: (
          <ManageMoveGroupStep
            readOnly={isStepReadOnly(2)}
            schemas={props.schemas}
            dataAll={dataAll}
            errorLoading={getMoveGroupState.error}
            isLoading={
              getApplicationState.isLoading ||
              getDatabaseState.isLoading ||
              getServerState.isLoading ||
              getMoveGroupState.isLoading
            }
            moveGroupRequest={moveGroupRequest}
            setMoveGroupRequest={setMoveGroupRequest}
            applications={applications}
            moveGroups={moveGroups}
            wpmDatabases={databases}
            wpmServers={servers}
            onConfirm={manageMoveGroupOnChange}
            refreshServers={refreshServers}
            refreshDatabases={refreshDatabases}
            refreshApplications={refreshApplications}
            refreshMoveGroups={refreshMoveGroups}
          />
        ),
      },
      {
        title: "Manage waves",
        content: (
          <ManageWaveStep
            // TODO: `jobCurrentStepIndex` will never be great than 3 as the last step will never be a "previous" step
            // Need further discuss on how to display a completed WPM job, leave it for now
            readOnly={isStepReadOnly(3)}
            schemas={props.schemas}
            dataAll={dataAll}
            isLoading={
              getApplicationState.isLoading ||
              getDatabaseState.isLoading ||
              getServerState.isLoading ||
              getMoveGroupState.isLoading ||
              getWaveState.isLoading
            }
            moveGroups={moveGroups}
            waves={waves}
            applications={applications}
            databases={databases}
            servers={servers}
            onConfirm={saveManageWaveChanges}
          />
        ),
      },
    ];
  };

  /**
   * Creates a new move group request for the specified WPM job
   *
   * @param {string} job_id - The ID of the WPM job
   * @param {Application[]} apps - Array of applications to include in the move group
   * @param {string} status - Initial status of the move group request
   * @returns {Promise<void>} Promise that resolves when the request is created
   * @throws {Error} When the request fails
   */
  const saveMoveGroupRequest = React.useCallback(
    async (job_id: string, apps: Application[], status: string): Promise<MoveGroupRequest> => {
      const app_ids = apps.map((app) => app.app_id);
      const newItem = {
        wpm_job_id: job_id,
        app_ids: app_ids,
        status,
        move_group_request_name: `MoveGroupRequest for WPM Job ${job_id} and ${apps.length} Apps`,
      };

      const result = await apiUser.postItem(newItem, Schemas.MoveGroupRequest.name);

      if (result.errors?.length || !result.newItems[0]?.move_group_request_id) {
        const joinedErrors = parsePUTResponseErrors(result.errors).join(", ") || UNEXPECTED_ERROR;
        throw new Error(joinedErrors);
      }

      setMoveGroupRequest(result.newItems[0]);
      return result.newItems[0];
    },
    []
  );

  /**
   * Save the job changes in the backend and then update the state
   * @returns {Promise<void>} Promise that resolves when the job is saved
   * @throws {Error} When the save operation fails
   */
  const saveJob = React.useCallback(
    async (changes: Partial<WPMJob>): Promise<WPMJob> => {
      let jobToSave: WPMJob = { ...job, ...changes };
      let result;

      if (!jobToSave.wpm_job_id) {
        result = await apiUser.postItem(jobToSave, Schemas.WPMJob.name);
        jobToSave = result.newItems[0];
      } else {
        const jobId = jobToSave.wpm_job_id;
        result = await apiUser.putItem(
          jobId,
          normalize<WPMJob>(jobToSave, props.schemas[Schemas.WPMJob.name], {
            // Remove name to avoid the wrong "name already exists error" from BE
            removeName: true,
          }),
          Schemas.WPMJob.name
        );
      }

      if (result.errors?.length || (!jobToSave.wpm_job_id && !result.newItems?.[0]?.[Schemas.WPMJob.keyAttribute])) {
        const joinedErrors = parsePUTResponseErrors(result.errors).join(", ") || UNEXPECTED_ERROR;
        throw new Error(joinedErrors);
      }
      setJob(jobToSave);
      return jobToSave;
    },
    [job, props.schemas]
  );

  /**
   * Save move group changes and create waves
   *
   * Fetches move groups for the current job and creates waves based on them.
   * This prepares the data for the wave management step.
   *
   * @returns {Promise<void>} Promise that resolves when waves are created
   * @throws {ErrorWithType} When the operation fails or validation fails
   */
  const saveMoveGroupChangesAndCreateWaves = React.useCallback(async (): Promise<Wave[]> => {
    // CloudScape Wizard component does not support disabling the `Next` button so throw a warning
    if (!job.wpm_job_id || moveGroupRequest?.status !== "COMPLETED") {
      throw new ErrorWithType("Please wait till the move group request completes.", "warning");
    }

    if (!moveGroups?.length) {
      throw new ErrorWithType(`No move group found for job ${job.wpm_job_name}`, "warning");
    }
    // Auto create waves based on the given move groups
    const wpmWaves = (await apiTools.createWPMWaves(
      job.wpm_job_id,
      moveGroups.map((mg) => mg.move_group_id)
    )) as Wave[];

    if (!wpmWaves?.length) {
      throw new ErrorWithType(`No waves found for job ${job.wpm_job_name}`, "error");
    }

    // the create-waves API may not return all attributes of waves so reload waves
    refreshWaves();
    refreshMoveGroups();
    refreshApplications();
    refreshDatabases();
    refreshServers();

    return wpmWaves;
  }, [
    job.wpm_job_id,
    job.wpm_job_name,
    moveGroupRequest?.status,
    moveGroups,
    refreshApplications,
    refreshDatabases,
    refreshMoveGroups,
    refreshServers,
    refreshWaves,
  ]);

  /**
   * Handle navigation between wizard steps
   *
   * Controls the flow between steps, performing necessary validations and
   * data operations when moving between steps.
   *
   * @param {NonCancelableCustomEvent<WizardProps.NavigateDetail>} e - Navigation event
   */
  const onNavigateHandler = React.useCallback(
    async (e: NonCancelableCustomEvent<WizardProps.NavigateDetail>) => {
      const { requestedStepIndex } = e.detail;
      const requestedStep = indexToStep(requestedStepIndex);

      // If the job has completed the requested step then just proceed without any action
      if (requestedStepIndex <= jobCurrentStepIndex) setActiveStepIndex(requestedStepIndex);
      else if (requestedStep === "MANAGE_APPLICATIONS") {
        if (jobFormValid) {
          const header = `Add ${Schemas.WPMJob.friendlyName}`;
          setIsLoadingNextStep(true);
          try {
            // Save job and moving to requested step
            const saveJobResult = await saveJob({ wpm_job_id: undefined, current_step: requestedStep });
            setActiveStepIndex(requestedStepIndex);
            addNotification({
              type: "success",
              dismissible: true,
              header,
              content: `${saveJobResult.wpm_job_name} saved successfully.`,
            });
            refreshWPMJobs();
          } catch (e) {
            handleError(e, { header });
          } finally {
            setIsLoadingNextStep(false);
          }
        }
      } else if (requestedStep === "MANAGE_MOVE_GROUPS") {
        // Moving to move group management - create move group request
        // TODO add visual feedback to notify user to select applications
        const selectedApps = availableApps.filter((app) => app.curr_wpm_job_id === job.wpm_job_id);
        if (selectedApps.length > 0 && job.wpm_job_id) {
          const header = `Add ${Schemas.MoveGroupRequest.friendlyName}`;
          setIsLoadingNextStep(true);
          try {
            const saveMoveGroupResult = await saveMoveGroupRequest(job.wpm_job_id, selectedApps, "PENDING");
            await saveJob({ current_step: requestedStep });

            setActiveStepIndex(requestedStepIndex);
            addNotification({
              type: "success",
              dismissible: true,
              header,
              content: `${saveMoveGroupResult.move_group_request_name} saved successfully.`,
            });
          } catch (e) {
            handleError(e, { header });
          } finally {
            setIsLoadingNextStep(false);
          }
        }
      } else if (requestedStep == "MANAGE_WAVES") {
        const header = `Add ${Schemas.Wave.friendlyName}`;
        setIsLoadingNextStep(true);
        try {
          // Moving to wave management - create waves from move groups
          const createWavesResult = await saveMoveGroupChangesAndCreateWaves();
          await saveJob({ current_step: requestedStep });
          setActiveStepIndex(requestedStepIndex);
          addNotification({
            type: "success",
            dismissible: true,
            header,
            content: `${createWavesResult.length} waves created successfully.`,
          });
        } catch (e) {
          handleError(e, { header });
        } finally {
          setIsLoadingNextStep(false);
        }
      }
    },
    [
      jobCurrentStepIndex,
      jobFormValid,
      saveJob,
      addNotification,
      refreshWPMJobs,
      handleError,
      availableApps,
      job.wpm_job_id,
      saveMoveGroupRequest,
      saveMoveGroupChangesAndCreateWaves,
    ]
  );

  /**
   * Handle wizard cancellation
   *
   * Cleans up the job and related resources when the user cancels the wizard.
   * Navigates back to the dashboard after cleanup.
   */
  const handleCancel = React.useCallback(() => {
    // If no job was created yet, just navigate back
    if (!job?.wpm_job_id) {
      navigate({
        pathname: basepath,
      });
      return;
    }

    // Otherwise, clean up the created job
    setIsLoadingNextStep(true);
    apiTools
      .cleanupEntities("wpm_job", [job.wpm_job_id])
      .then(() => {
        addNotification({
          type: "success",
          dismissible: true,
          header: "Job deleted successfully",
          content: job.wpm_job_name + " was deleted.",
        });
        setJob(EMPTY_JOB);
        navigate({
          pathname: basepath,
        });
      })
      .catch((e) =>
        handleError(e, {
          header: "Cancel job failed",
          content: `Failed to cancel ${job.wpm_job_name}.`,
        })
      )
      .finally(() => setIsLoadingNextStep(false));
  }, [addNotification, handleError, job.wpm_job_id, job.wpm_job_name, navigate]);

  /**
   * Handle wizard submission
   *
   * All the changes are saved when the Confirm button in the TransferList pop-up clicked
   * Navigates back to the dashboard after successful completion.
   */
  const handleSubmit = React.useCallback(() => {
    navigate({
      pathname: basepath,
    });
  }, [navigate]);

  return (
    <Wizard
      i18nStrings={{
        stepNumberLabel: (stepNumber) => `Step ${stepNumber}`,
        collapsedStepsLabel: (stepNumber, stepsCount) => `Step ${stepNumber} of ${stepsCount}`,
        cancelButton: "Cancel",
        previousButton: "Previous",
        nextButton: "Next",
        submitButton: "Confirm Wave Plan",
        optional: "optional",
      }}
      isLoadingNextStep={isLoadingNextStep}
      onCancel={handleCancel}
      onSubmit={handleSubmit}
      onNavigate={onNavigateHandler}
      activeStepIndex={activeStepIndex}
      steps={getSteps()}
    />
  );
};

export default React.memo(JobWizard);
