/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState, useMemo } from "react";
import SideNavigation, { SideNavigationProps } from "@cloudscape-design/components/side-navigation";
import { capitalize, capitalizeAndPluralize } from "../resources/main";
import { To, useLocation, useNavigate } from "react-router-dom";

// Define props interface for the component
interface ServiceNavigationProps {
  userGroups?: string[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  schemaMetadata?: any[];
  versionUi?: string;
  enabledModules: string[];
}

// Move static data outside the component to prevent recreation on each render
const defaultAutomationItems: SideNavigationProps.Link[] = [
  { type: "link", text: "Jobs", href: "/automation/jobs" },
  { type: "link", text: "Scripts", href: "/automation/scripts" },
];

// Define base navigation structures as functions that accept version text and wpmEnabled flag
const getItemsUser = (wpmEnabled: boolean, versionText?: string): SideNavigationProps.Item[] => {
  const baseItems: SideNavigationProps.Item[] = [
    {
      type: "section",
      text: "Overview",
      items: [{ type: "link", text: "Dashboard", href: "/" }],
    },
    {
      type: "section",
      text: "Migration Management",
      items: [],
    },
    {
      type: "section",
      text: "Custom Assets",
      items: [],
    },
  ];

  // Add Wave Planning section only if wpmEnabled is true
  if (wpmEnabled) {
    baseItems.push({
      type: "section",
      text: "Wave Planning",
      items: [
        { type: "link", text: "Planning Jobs", href: "/wpm_jobs" },
        { type: "link", text: "Import", href: "/wave-planning/data-import" },
      ],
    });
  }

  baseItems.push(
    {
      type: "section",
      text: "Automation",
      items: [],
    },
    { type: "divider" },
    {
      type: "link",
      text: versionText ?? "",
      href: "",
    }
  );

  return baseItems;
};

const getItemsAdmin = (wpmEnabled: boolean, versionText?: string): SideNavigationProps.Item[] => {
  const baseItems: SideNavigationProps.Item[] = [
    {
      type: "section",
      text: "Overview",
      items: [{ type: "link", text: "Dashboard", href: "/" }],
    },
    {
      type: "section",
      text: "Migration Management",
      items: [],
    },
    {
      type: "section",
      text: "Custom Assets",
      items: [],
    },
  ];

  // Add Wave Planning section only if wpmEnabled is true
  if (wpmEnabled) {
    baseItems.push({
      type: "section",
      text: "Wave Planning",
      items: [
        { type: "link", text: "Planning Jobs", href: "/wpm_jobs" },
        { type: "link", text: "Import", href: "/wave-planning/data-import" },
      ],
    });
  }

  baseItems.push(
    {
      type: "section",
      text: "Automation",
      items: [],
    },
    {
      type: "section",
      text: "Administration",
      items: [
        { type: "link", text: "Permissions", href: "/admin/policy" },
        { type: "link", text: "Attributes", href: "/admin/attribute" },
        {
          type: "link",
          text: "Credential Manager",
          href: "/admin/credential-manager",
        },
        ...(wpmEnabled ? [{ type: "link" as const, text: "Wave Planning", href: "/admin/wave-planning" }] : []),
      ],
    },
    { type: "divider" },
    {
      type: "link",
      text: versionText ?? "",
      href: "",
    }
  );

  return baseItems;
};

function ServiceNavigation(props: ServiceNavigationProps) {
  const navigate = useNavigate();
  const [items, setItems] = useState<SideNavigationProps.Item[]>([]);
  const location = useLocation();

  const wpmEnabled = props.enabledModules.includes("WPM");

  // Optimize the navigation handler with a more concise implementation
  const onFollowHandler = (ev: { preventDefault: () => void; detail: { href: To } }) => {
    ev.preventDefault();
    // Only navigate if href is provided
    if (ev.detail.href) {
      navigate(ev.detail.href);
    }
  };

  // Memoize the version text to prevent recalculation on each render
  const versionText = useMemo(() => {
    return props.versionUi ? `Version: ${props.versionUi}` : undefined;
  }, [props.versionUi]);

  // Memoize the base navigation items based on user groups and wpmEnabled
  const baseNavItems = useMemo(() => {
    // Select admin or user navigation based on user groups
    return props.userGroups?.includes("admin")
      ? getItemsAdmin(wpmEnabled, versionText)
      : getItemsUser(wpmEnabled, versionText);
  }, [props.userGroups, versionText, wpmEnabled]);

  // Extract and memoize schema processing logic to improve readability and performance
  const processedSchemaItems = useMemo(() => {
    // Return early if no schema metadata is available
    if (!props.schemaMetadata || props.schemaMetadata.length === 0) {
      return { navSchemaItems: [], customAssetItems: [], automationItems: [...defaultAutomationItems] };
    }

    const navSchemaItems: SideNavigationProps.Item[] = [];
    const customAssetItems: SideNavigationProps.Item[] = [];
    const automationItems: SideNavigationProps.Item[] = [...defaultAutomationItems];

    // Process each schema to build navigation items
    for (const schema of props.schemaMetadata) {
      if (schema["schema_type"] === "custom") {
        // Add custom asset schemas to the custom assets navigation
        customAssetItems.push({
          type: "link",
          text: schema["friendly_name"] || capitalize(schema["schema_name"]),
          href: "/custom/" + schema["schema_name"] + "s",
        });
      } else if (schema["schema_type"] === "user") {
        // Handle special cases for pipeline and pipeline_template
        if (["pipeline", "pipeline_template"].includes(schema["schema_name"])) {
          automationItems.push({
            type: "link",
            text: schema["friendly_name"] || capitalizeAndPluralize(schema["schema_name"]),
            href: "/" + schema["schema_name"] + "s",
          });
        } else if (["move_group_request", "wpm_job", "rule", "data_source"].includes(schema["schema_name"])) {
          // Skip move_group_request and wpm_job schemas
          continue;
        } else {
          // Add regular user schemas to navigation
          navSchemaItems.push({
            type: "link",
            text: schema["friendly_name"] || capitalize(schema["schema_name"]),
            href: "/" + schema["schema_name"] + "s",
          });
        }
      }
    }

    // Add static items to the end of the navigation
    navSchemaItems.push({ type: "link", text: "Import", href: "/import" });
    navSchemaItems.push({ type: "link", text: "Export", href: "/export" });

    return { navSchemaItems, customAssetItems, automationItems };
  }, [props.schemaMetadata]); // Only recalculate when schemaMetadata changes

  // Update navigation items when dependencies change
  useEffect(() => {
    // Return early if no schema metadata is available
    if (!props.schemaMetadata) return;

    // Create a deep copy of the base navigation items to avoid mutation issues
    const updatedNavItems = JSON.parse(JSON.stringify(baseNavItems));
    const { navSchemaItems, customAssetItems, automationItems } = processedSchemaItems;

    // Update the navigation sections with processed items
    const migrationManagementIndex = updatedNavItems.findIndex(
      (item: { text: string }) => item.text === "Migration Management"
    );

    if (migrationManagementIndex !== -1) updatedNavItems[migrationManagementIndex].items = navSchemaItems;

    const customAssetsIndex = updatedNavItems.findIndex((item: { text: string }) => item.text === "Custom Assets");
    // Remove Custom Assets section if there are no custom asset items
    if (customAssetsIndex !== -1) {
      if (customAssetItems.length > 0) {
        updatedNavItems[customAssetsIndex].items = customAssetItems;
      } else {
        updatedNavItems.splice(customAssetsIndex, 1);
      }
    }

    // Find automation index after potentially removing custom assets section
    const automationIndex = updatedNavItems.findIndex((item: { text: string }) => item.text === "Automation");
    if (automationIndex !== -1) updatedNavItems[automationIndex].items = automationItems;

    // Update state with the new navigation items
    setItems(updatedNavItems);
  }, [baseNavItems, processedSchemaItems, props.schemaMetadata]);

  // Render the side navigation component
  return (
    <SideNavigation
      header={{ text: "Migration Factory", href: "/" }}
      items={items}
      activeHref={`${location.pathname}`}
      onFollow={onFollowHandler}
    />
  );
}

// Wrap the component with React.memo to prevent unnecessary re-renders
export default React.memo(ServiceNavigation);
