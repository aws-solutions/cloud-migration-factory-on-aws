/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from "react";
import SideNavigation from "@cloudscape-design/components/side-navigation";
import { capitalize, capitalizeAndPluralize } from "../resources/main";
import { To, useLocation, useNavigate } from "react-router-dom";

interface ServiceNavigationProps {
  userGroups?: string[];
  schemaMetadata?: any[];
}

function ServiceNavigation(props: ServiceNavigationProps) {
  let navigate = useNavigate();
  const [items, setItems] = useState<any[]>([]);
  let location = useLocation();

  // If the provided link is empty, do not redirect pages
  function onFollowHandler(ev: { preventDefault: () => void; detail: { href: To } }) {
    ev.preventDefault();
    if (ev.detail.href) {
      navigate(ev.detail.href);
    }
  }

  useEffect(() => {
    let navItems = [];

    if (props.userGroups?.includes("admin")) {
      navItems = itemsAdmin;
    } else {
      navItems = itemsUser;
    }

    let navSchemaItems = [];
    let automationItems = [
      { type: "link", text: "Jobs", href: "/automation/jobs" },
      { type: "link", text: "Scripts", href: "/automation/scripts" },
    ];
    if (props.schemaMetadata) {
      if (props.schemaMetadata.length > 0) {
        //Add user schemas to the navigation.

        for (const schema of props.schemaMetadata) {
          if (schema["schema_type"] === "user") {
            //Only add user schemas to navigation.
            if (["pipeline", "pipeline_template"].includes(schema["schema_name"])) {
              automationItems.push({
                type: "link",
                text: schema["friendly_name"] ? schema["friendly_name"] : capitalizeAndPluralize(schema["schema_name"]),
                href: "/" + schema["schema_name"] + "s",
              });
            } else {
              navSchemaItems.push({
                type: "link",
                text: schema["friendly_name"] ? schema["friendly_name"] : capitalize(schema["schema_name"]),
                href: "/" + schema["schema_name"] + "s",
              });
            }
          }
        }
        // navSchemaItems.push({type: "link", text: "Pipeline", href: "/pipeline"});
        navSchemaItems.push({ type: "link", text: "Import", href: "/import" });
        navSchemaItems.push({ type: "link", text: "Export", href: "/export" });

        navItems[1].items = navSchemaItems;
        navItems[2].items = automationItems;
      }
    }

    setItems(navItems);
  }, [props.userGroups, props.schemaMetadata]);

  return (
    <SideNavigation
      header={{ text: "Migration Factory", href: "/" }}
      items={items}
      activeHref={`${location.pathname}`}
      onFollow={onFollowHandler}
    />
  );
}

const env = (window as any).env;
const itemsUser = [
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
    text: "Automation",
    items: [],
  },
  { type: "divider" },
  {
    type: "link",
    text: "VERSION_UI" in env ? "Version: " + env.VERSION_UI : null,
  },
];

const itemsAdmin = [
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
    text: "Automation",
    items: [],
  },
  {
    type: "section",
    text: "Administration",
    //defaultExpanded: false,
    items: [
      { type: "link", text: "Permissions", href: "/admin/policy" },
      { type: "link", text: "Attributes", href: "/admin/attribute" },
      {
        type: "link",
        text: "Credential Manager",
        href: "/admin/credential-manager",
      },
    ],
  },
  { type: "divider" },
  {
    type: "link",
    text: "VERSION_UI" in env ? "Version: " + env.VERSION_UI : null,
  },
];

export default ServiceNavigation;
