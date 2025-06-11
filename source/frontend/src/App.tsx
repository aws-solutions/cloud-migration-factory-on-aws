/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useEffect, useState } from "react";
import { Auth } from "@aws-amplify/auth";
import AuthRoutes from "./AuthenticatedRoutes";
import UserApiClient from "./api_clients/userApiClient";
import { AppLayout, Button, Flashbar, StatusIndicator } from "@cloudscape-design/components";
import { useSchema } from "./actions/SchemaHook";
import ServiceNavigation from "./components/servicenavigation";
import { useAdminPermissions } from "./actions/AdminPermissionsHook";
import ToolHelp from "./components/ToolHelp";
import { useNavigate } from "react-router-dom";
import { SessionContext } from "./contexts/SessionContext";
import { AppChildProps } from "./models/AppChildProps";
import { entityAccessFromPermissions } from "./utils/entity-access-from-permissions";
import { NotificationContext } from "./contexts/NotificationContext";
import { CMFTopNavigation } from "./components/CMFTopNavigation";
import { ToolsContext } from "./contexts/ToolsContext";
import { SplitPanelContext } from "./contexts/SplitPanelContext";

let websocket: WebSocket | null = null;
let activityTimerID: ReturnType<typeof setInterval> | null = null;
let serverNotificationTimerID: ReturnType<typeof setInterval> | null = null;
//User activity tracking and auto logout.
let lastActivity = Date.now();

function clearTimers() {
  if (activityTimerID) clearInterval(activityTimerID);

  if (serverNotificationTimerID) clearInterval(serverNotificationTimerID);
}

const App = () => {
  const { idToken, userName, userGroups } = useContext(SessionContext);
  const { notifications, addNotification } = useContext(NotificationContext);
  const { toolsState, setToolsOpen } = useContext(ToolsContext);
  const { splitPanelState, setSplitPanelOpen } = useContext(SplitPanelContext);
  const navigate = useNavigate();

  const locaStorageKeys = {
    groups: "user_groups",
    activityTimerID: "activityTimerID",
    notificationTimerID: "notificationTimerID",
    lastCentralNotificationDateTime: "lastCentralNotificationDateTime",
  };

  const [entityAccess, setEntityAccess] = useState({});

  const localStorageLastNotificationDateTime = localStorage.getItem(locaStorageKeys.lastCentralNotificationDateTime);
  const [lastCentralNotificationDateTime, setLastCentralNotificationDateTime] = useState(
    localStorageLastNotificationDateTime ? JSON.parse(localStorageLastNotificationDateTime) : null
  );

  const [schemaState, { update: schemaUpdate }] = useSchema();
  const { isLoading: schemaIsLoading, schemas, schemaMetadata, error: schemaError } = schemaState;
  const [{ data: permissionsData }, { update: permissionsUpdate }] = useAdminPermissions();
  let locallastCentralNotificationDateTime: Date | null = null;

  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.activityTimerID, JSON.stringify(activityTimerID));
  }, [activityTimerID]);

  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.notificationTimerID, JSON.stringify(serverNotificationTimerID));
  }, [serverNotificationTimerID]);

  React.useEffect(() => {
    localStorage.setItem(
      locaStorageKeys.lastCentralNotificationDateTime,
      JSON.stringify(lastCentralNotificationDateTime)
    );
  }, [lastCentralNotificationDateTime]);

  async function openUserSession(idToken: string) {
    await schemaUpdate();

    //Clear any existing active user timer.
    if (activityTimerID) {
      clearInterval(activityTimerID);
    }

    lastActivity = Date.now();
    activityTimerID = setInterval(() => tick(), 1000);

    //Clear any existing notifications check timer.
    if (serverNotificationTimerID) {
      clearInterval(serverNotificationTimerID);
    }

    serverNotificationTimerID = setInterval(() => serverNotificationsTick(), 60000);

    //clear existing web socket connection.
    if (websocket !== null) {
      websocket.close();
      console.log("Jobs web socket closed.");

      websocket = null;
    }

    //Create Jobs web socket connection.
    const environment = (window as any).env;
    if ("API_SSMSocket" in environment) {
      // Check for a valid socket url.
      if (environment.API_VPCE_ID === "") {
        // ATTN: move WebSocket out of App.tsx to decouple for testability
        websocket = new WebSocket(
          "wss://" + environment.API_SSMSocket + ".execute-api." + environment.API_REGION + ".amazonaws.com/prod"
        );

        // Connection opened
        websocket.addEventListener("open", function (event) {
          console.log("websocket session open");
          const data = {
            type: "auth",
            token: idToken,
          };
          let message = JSON.stringify(data);
          websocket!.send(message);
        });

        console.log("Jobs web socket opened.");
        //Authenticating.

        websocket.onmessage = processSocketMessage;
      } else {
        //Invalid socket URL, could be that this is a private deployment so web socket is not deployed.
        console.info(
          "Jobs web socket not supported when using VPCE specified, no push notifications will be received."
        );
      }
    }
    console.log("Opened Migration Factory UI session.");
  }

  function processSocketMessage(msg: any) {
    let wsData: any = null;
    try {
      wsData = JSON.parse(msg.data);
    } catch {
      wsData = msg.data;
    }

    if (wsData.type === "error" || wsData.type === "success") {
      //Notify users of complete or failed job.
      wsData.action = (
        <Button onClick={(event) => navigateClick(event, "/automation/jobs/" + wsData.uuid)}>View Job</Button>
      );
      addNotification(wsData);
    }

    console.log("CMF messaging: " + wsData.type + " - " + msg.data);

    if (wsData.message_type === "Refresh") {
      console.log(wsData);
    }
  }

  const navigateClick = (event: CustomEvent<any>, URL: any) => {
    event.preventDefault();
    navigate(URL);
  };

  async function closeUserSession() {
    clearTimers();

    if (websocket !== null) {
      websocket.close();
      console.log("Jobs web socket closed.");

      websocket = null;
    }

    console.log("Closed Migration Factory UI session.");
  }

  const autoLogoutMinutes = parseInt(process.env.AUTO_LOGOUT_MINUTES || "30");
  const tick = async () => {
    const minutesSinceActivity = Math.abs(Date.now() - lastActivity) / 1000 / 60;

    if (minutesSinceActivity > autoLogoutMinutes) {
      console.log(
        "User has been inactive for " +
          minutesSinceActivity +
          "mins, reaching timeout of " +
          autoLogoutMinutes +
          " mins, logging out."
      );

      clearTimers();

      if (websocket !== null) {
        websocket.close();
        console.log("Jobs web socket closed.");

        websocket = null;
      }
      try {
        await Auth.signOut({ global: true });
      } catch (e: any) {
        console.log("error signing out: ", e);
      }
      navigate("/login");
    }
  };

  const onMouseMove = () => {
    lastActivity = Date.now();
  };

  const serverNotificationsTick = async () => {
    let serverNotifications = null;
    try {
      const apiUser = new UserApiClient();

      serverNotifications = await apiUser.getNotifications();
    } catch (error) {
      console.log("Central notification failed. " + error);
      return;
    }

    let currentTime;
    if (locallastCentralNotificationDateTime === null) {
      //First time checking so assume just logged on so no real changes.
      currentTime = new Date(serverNotifications.lastChangeDate).valueOf();
      setLastCentralNotificationDateTime(serverNotifications.lastChangeDate);
      locallastCentralNotificationDateTime = serverNotifications.lastChangeDate;
    } else {
      currentTime = new Date(locallastCentralNotificationDateTime).valueOf();
    }

    const notificationTime = new Date(serverNotifications.lastChangeDate).valueOf();

    if (currentTime < notificationTime) {
      //Schema change detected, reload schema.
      console.log("Central notification received: " + serverNotifications.lastChangeDate);
      await schemaUpdate();
      setLastCentralNotificationDateTime(serverNotifications.lastChangeDate);
      locallastCentralNotificationDateTime = serverNotifications.lastChangeDate;
    }
  };

  const onClickMenu = async (event: CustomEvent<any>) => {
    event.preventDefault();
    const action = event.detail.id;
    switch (action) {
      case "signout":
        try {
          await Auth.signOut({ global: true });
        } finally {
          await closeUserSession();
          navigate("/login");
        }
        break;
      case "changepassword":
        navigate("/change/pwd");
        break;
    }
  };

  useEffect(() => {
    if (!schemaIsLoading && schemaError) {
      addNotification({ header: "Schema could not be loaded.", content: schemaError });
      console.log("Schema could not be loaded." + schemaError);
    }
  }, [schemaError]);

  //update of permissions when permissions change.
  useEffect(() => {
    try {
      setEntityAccess(entityAccessFromPermissions(permissionsData, userGroups));
    } catch (e: any) {
      console.error(e);
      addNotification({
        header: "Error",
        content: e.response?.data || "Unknown error occurred",
      });
    }
  }, [permissionsData]);

  //Change in user authentication happened.
  useEffect(() => {
    openUserSession(idToken);

    // returned function will be called on component unmount
    return () => {
      closeUserSession();
    };
  }, [idToken]);

  useEffect(() => {
    if (userGroups) {
      permissionsUpdate();
    }
  }, [userGroups]);

  function displayAuthenticatedMainUI() {
    if (schemaIsLoading && !schemaError) {
      return (
        <center>
          <StatusIndicator type="loading">Loading</StatusIndicator>
        </center>
      );
    }

    if (schemaError || !schemas || !schemaMetadata) {
      return (
        <center>
          <StatusIndicator type="error">{schemaError}</StatusIndicator>
        </center>
      );
    }

    const childProps: AppChildProps = {
      schemas: schemas,
      schemaIsLoading: schemaIsLoading,
      schemaMetadata: schemaMetadata,
      reloadSchema: schemaUpdate,
      reloadPermissions: permissionsUpdate,
      isReady: !schemaIsLoading && !schemaError,
      userGroups: userGroups,
      userEntityAccess: entityAccess,
    };

    return (
      <AppLayout
        headerSelector="#h"
        navigation={<ServiceNavigation userGroups={userGroups} schemaMetadata={schemaMetadata} />}
        notifications={<Flashbar items={notifications} />}
        //breadcrumbs={<Breadcrumbs/>} ATTN: Implement new dynamic breadcrumbs functions in future.
        content={<AuthRoutes childProps={childProps} />}
        contentType="table"
        tools={<ToolHelp helpContent={toolsState.toolsHelpContent} />}
        toolsHide={!toolsState.toolsHelpContent}
        disableBodyScroll={true}
        onToolsChange={({ detail }) => setToolsOpen(detail.open)}
        toolsOpen={toolsState.toolsOpen}
        splitPanelOpen={!splitPanelState.splitPanelContent || splitPanelState.splitPanelOpen}
        splitPanel={splitPanelState.splitPanelContent}
        splitPanelPreferences={{ position: "side" }}
        onSplitPanelToggle={({ detail }) => setSplitPanelOpen(detail.open)}
      />
    );
  }

  const utilities: any = [
    {
      type: "menu-dropdown",
      text: "Documentation",
      items: [
        {
          id: "cmf-overview",
          text: "AWS Cloud Migration Factory Solution",
          external: true,
          href: "https://aws.amazon.com/solutions/implementations/cloud-migration-factory-on-aws/",
        },
        {
          id: "lm",
          text: "Guide for AWS large migrations",
          external: true,
          href: "https://aws.amazon.com/prescriptive-guidance/large-migrations",
        },
        {
          id: "lab",
          text: "Cloud Migration Factory Lab",
          external: true,
          href: "https://cloud-migration-factory.s3.amazonaws.com/apg-public/workshop/index.html",
        },
      ],
    },
    {
      type: "menu-dropdown",
      description: userName,
      iconName: "user-profile",
      onItemClick: onClickMenu,
      items: [
        { id: "changepassword", text: "Change Password" },
        { id: "signout", text: "Sign out" },
      ],
    },
  ];

  return (
    <div onMouseMove={onMouseMove}>
      <CMFTopNavigation utilities={utilities} />
      {displayAuthenticatedMainUI()}
      <div id="modal-root" />
    </div>
  );
};
export default App;
