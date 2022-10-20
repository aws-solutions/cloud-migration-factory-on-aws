import React, {useEffect, useState} from "react";
import { Auth } from "aws-amplify";
import AuthRoutes from "./AuthenticatedRoutes";
import PreAuthRoutes from "./PreAuthRoutes";
import AppDialog from "./components/AppDialog";
import Admin from "./actions/admin";
import User from "./actions/user";
import { v4 as uuidv4 } from 'uuid';
import {
  AppLayout,
  Button,
  BreadcrumbGroup,
  HelpPanel,
  SpaceBetween,
  Link,
  StatusIndicator,
  Alert,
  TopNavigation
} from "@awsui/components-react";
import {useSchema} from "./actions/SchemaHook";
import ServiceNavigation from "./components/servicenavigation";
import FlashMessage from "./components/FlashMessage";
import {useAdminPermissions} from "./actions/AdminPermissionsHook";
import {deepEqual} from "./resources/main.js"
import ToolHelp from "./components/ToolHelp";

import { useNavigate } from "react-router-dom";

var websocket = null;
let activityTimerID = null;
let notificationTimerID = null;
//User activity tracking and auto logout.
let lastActivity = Date.now();

const App = (props) => {
  let navigate = useNavigate();
  const myHeaderStyle = {
    postion: 'sticky',
    'z-index': 1999
  }

  let autoLogout = 30;
  // Change default if configuration exists
  // if ('application' in config){
  //   if (config.application.AUTO_LOGOUT !== undefined){
  //     autoLogout = config.application.AUTO_LOGOUT
  //   }
  // }

  let apiAdmin = null;
  const locaStorageKeys = {
    groups: 'user_groups',
    isAuthenticated: 'isAuthenticated',
    isAuthenticating: 'isAuthenticating',
    activityTimerID: 'activityTimerID',
    notificationTimerID: 'notificationTimerID',
    userName: 'userName',
    notifications: 'notifications',
    isReady: 'isReady',
    lastCentralNotificationDateTime: 'lastCentralNotificationDateTime',
  }

  //App Layout state.
  const [toolsOpen, setToolsOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(localStorage[locaStorageKeys.isAuthenticated] ? JSON.parse(localStorage.getItem(locaStorageKeys.isAuthenticated)) : false);
  const [isAuthenticating, setIsAuthenticating] = useState(localStorage[locaStorageKeys.isAuthenticating] ? JSON.parse(localStorage.getItem(locaStorageKeys.isAuthenticating)) : true);

  //Major application error states.
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState(null);

  //App Layout content.
  const [toolsHelpContent, setToolsHelpContent] = useState({header: 'None provided', footer: undefined, content: undefined});

  const [showDialog, setShowDialog] = useState(false);
  const [msg, setSMsg] = useState('');
  const [jwt, setJwt] = useState({});
  const [entityAccess, setEntityAccess] = useState({});
  const [userGroups, setUserGroups] = useState(localStorage[locaStorageKeys.groups] ? JSON.parse(localStorage.getItem(locaStorageKeys.groups)) : []);
  const [userName, setUserName] = useState(localStorage[locaStorageKeys.userName] ? JSON.parse(localStorage.getItem(locaStorageKeys.userName)) : null);
  const [notifications, setNotifications] = useState([]);
  const [isReady, setIsReady] = useState(localStorage[locaStorageKeys.isReady] ? JSON.parse(localStorage.getItem(locaStorageKeys.isReady)) : false);  //True if critical application functionality is available for user
  const [lastCentralNotificationDateTime, setLastCentralNotificationDateTime] = useState(localStorage[locaStorageKeys.lastCentralNotificationDateTime] ? JSON.parse(localStorage.getItem(locaStorageKeys.lastCentralNotificationDateTime)) : null);

  const [{ isLoading: schemaIsLoading, schema: schemaLocal, schemaMetadata, error: schemaError}, { update: schemaUpdate }] = useSchema();
  const [{ isLoading: permissionsIsLoading, data: permissionsData, error: permissionsError}, { update: permissionsUpdate }] = useAdminPermissions();
  var locallastCentralNotificationDateTime = null;


  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.groups, JSON.stringify(userGroups));
  }, [userGroups]);

  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.isAuthenticated, JSON.stringify(isAuthenticated));
  }, [isAuthenticated]);

  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.isAuthenticating, JSON.stringify(isAuthenticating));
  }, [isAuthenticating]);

  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.userName, JSON.stringify(userName));
  }, [userName]);

  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.activityTimerID, JSON.stringify(activityTimerID));
  }, [activityTimerID]);

  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.notificationTimerID, JSON.stringify(notificationTimerID));
  }, [notificationTimerID]);

  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.isReady, JSON.stringify(isReady));
  }, [isReady]);

  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.lastCentralNotificationDateTime, JSON.stringify(lastCentralNotificationDateTime));
  }, [lastCentralNotificationDateTime]);

  //TODO verify this function is required.
  const addNotification = (notification) => {

    setLastCentralNotificationDateTime([notification]);
  };

  //Add or delete notifications across the application.
  //This function is share across all components.
  const updateNotification = (action, notification) => {
    var i;
    let newNotify = []

    switch(action) {
      case 'add':
        newNotify = Array.from(notifications);
        if (!notification.id) {
          notification.id = uuidv4();
        } else {
          //Remove current notification with same id in order to replace.
          newNotify = notifications.filter(function (item){
            return item.id !== notification.id;
          })
        }
        if (notification.actionButtonLink && notification.actionButtonTitle){
          notification.action = (<Button onClick={event => navigateClick(event, notification.actionButtonLink)}>{notification.actionButtonTitle}</Button>)
        }
        notification.onDismiss = () => updateNotification('delete', {id: notification.id});
        newNotify.push(notification);
        setNotifications(newNotify);
        return notification.id;
      case 'delete':
        newNotify = notifications.filter(function (item){
          return item.id !== notification.id;
        })
        // for (i in this.state.notifications) {
        //   if (notification.id !== this.state.notifications[i].id) {
        //     newNotify.push(this.state.notifications[i]);
        //   }
        // }
        setNotifications(newNotify);
        break;

      default:
    }
  }

  function decodeJwt(token) {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace('-', '+').replace('_', '/');
    const decodedJwt = JSON.parse(window.atob(base64));
    setJwt(decodedJwt);
    return decodedJwt;
  }

  async function openUserSession() {

    await schemaUpdate()

    //Clear any existing active user timer.
    if (activityTimerID) {
      clearInterval(activityTimerID);
    }

    activityTimerID = setInterval(
      () => tick(),
      1000
    );

    //Clear any existing notifications check timer.
    if (notificationTimerID) {
      clearInterval(notificationTimerID)
    }

    notificationTimerID = setInterval(
      () => notificationsTick(),
      60000
    );

    //clear existing web socket connection.
    if(websocket != null){
      websocket.close();
      console.log("Jobs web socket closed.")

      websocket = null;
    }

    //Create Jobs web socket connection.
    if ('API_SSMSocket' in window.env) {

      // Check for a valid socket url.
      if (window.env.API_SSMSocket.startsWith('wss://')){
        const session = await Auth.currentSession();
        const token = session.idToken.jwtToken;

        websocket = new WebSocket( window.env.API_SSMSocket);

        // Connection opened
        websocket.addEventListener('open', function (event) {
          console.log('websocket session open');
          const data = {
            "type": 'auth',
            "token": token,
          };
          let message = JSON.stringify(data);
          websocket.send(message);
        });

        if (websocket != null) {
          console.log("Jobs web socket opened.")
          //Authenticating.


          websocket.onmessage = processSocketMessage;
        }
      } else {
        //Invalid socket URL, could be that this is a private deployment so web socket is not deployed.
        console.log('Jobs web socket URL not supported: ' + window.env.API_SSMSocket + '.')
      }

    }
    console.log('Opened Migration Factory UI session.')
  }

  function processSocketMessage (msg) {
    let wsData = null;
    try{
      wsData = JSON.parse(msg)
    } catch {
      wsData = msg.data;
    }

    if (wsData.type === 'error' || wsData.type === 'success') {
      //Notify users of complete or failed job.
      wsData.action = (<Button onClick={event => navigateClick(event, "/automation/jobs/" + wsData.uuid)}>View Job</Button>)
      updateNotification('add', wsData);
    }

    console.log("CMF messaging: " + wsData.type + " - " + msg.data);

    if (wsData.message_type === 'Refresh') {
      console.log(wsData)
    };
  }

  const navigateClick = (event, URL) => {
    event.preventDefault();
    navigate(URL);
  }

  async function closeUserSession () {

    clearInterval(activityTimerID);

    clearInterval(notificationTimerID);

    if(websocket != null){
      websocket.close();
      console.log("Jobs web socket closed.")

      websocket = null;
    }

    console.log('Closed Migration Factory UI session.')
  }


  const tick = async event => {
    if (isAuthenticated){
      const minutesSinceActivity = Math.abs(Date.now() - lastActivity) / 1000 / 60

      if (minutesSinceActivity > autoLogout) {

        console.log('User has been inactivity for '+ minutesSinceActivity + 'mins, reaching timout of ' + autoLogout + ' mins, logging out.')

        clearInterval(activityTimerID);

        clearInterval(notificationTimerID);

        if (websocket != null) {
          websocket.close();
          console.log("Jobs web socket closed.")

          websocket = null;
        }
        try {
          await Auth.signOut({global: true});
        } catch (e) {
          console.log('error signing out: ', e);
        }
        userHasAuthenticated(false);
        navigate("/login");
      }
    }
  }

  const onMouseMove = event => {
    lastActivity = Date.now();
  }

  const notificationsTick = async () => {
    if (isAuthenticated){
      let result = null;
      try {
        const session = await Auth.currentSession();
        const apiUser = new User(session);

        result = await apiUser.getNotifications();
      } catch (error) {
        console.log("Central notification failed. " + error);
        return;
      }

      let currentTime = null;
      if (locallastCentralNotificationDateTime === null){
        //First time checking so assume just logged on so no real changes.
        currentTime = new Date(result.lastChangeDate).valueOf();
        setLastCentralNotificationDateTime(result.lastChangeDate);
        locallastCentralNotificationDateTime = result.lastChangeDate;
      } else {
        currentTime = new Date(locallastCentralNotificationDateTime).valueOf();
      }

      const notificationTime = new Date(result.lastChangeDate).valueOf();

      if (currentTime < notificationTime) {
        //Schema change detected, reload schema.
        console.log("Central notification received: " + result.lastChangeDate);
        reloadSchema();
        setLastCentralNotificationDateTime(result.lastChangeDate);
        locallastCentralNotificationDateTime = result.lastChangeDate;
      }
    }
  }

  const userHasAuthenticated = authenticated => {
    setIsAuthenticated(authenticated);
  }

  async function getPermissions() {
    try {

        // Get list of policies user is authorized for, apply the most priv access over others.

        var entity_access = {};
        for (const role of permissionsData.roles) {
          for (const group of role.groups) {
            if (userGroups.includes(group.group_name)) { //Check if this user has this group membership.
              for (const rolePolicy of role.policies) { // loop through all polices attached to role.
                for (const policy of permissionsData.policies){
                  if (policy.policy_id === rolePolicy.policy_id){ //Is this policy
                    for (const entity of policy.entity_access){ //
                      if (entity_access[entity.schema_name]){

                        //Grant most privileged access on conflict.
                        if (entity_access[entity.schema_name].create == false && entity.create){
                          entity_access[entity.schema_name].create = true;
                        }
                        if (entity_access[entity.schema_name].read == false && entity.read){
                          entity_access[entity.schema_name].read = true;
                        }
                        if (entity_access[entity.schema_name].update == false && entity.update){
                          entity_access[entity.schema_name].update = true;
                        }
                        if (entity_access[entity.schema_name].delete == false && entity.delete){
                          entity_access[entity.schema_name].delete = true;
                        }

                        //Append additional attributes.
                        if (entity.attributes && Array.isArray(entity.attributes)) { //Does policy have attributes defined.

                          if (Array.isArray(entity_access[entity.schema_name].attributes)){
                            if (entity_access[entity.schema_name].attributes.length === 0){
                              entity_access[entity.schema_name].attributes = entity.attributes;
                            } else { //Need to append values to existing.
                              for (const attr of entity.attributes){
                                if (!entity_access[entity.schema_name].attributes.includes(attr)) {
                                  entity_access[entity.schema_name].attributes.push(attr);
                                }
                              }
                            }
                          } else {
                            entity_access[entity.schema_name].attributes = entity.attributes;
                          }
                        }


                      } else {
                        entity_access[entity.schema_name] = {
                          create: entity.create,
                          read: entity.read,
                          update: entity.update,
                          delete: entity.delete,
                          attributes: entity.attributes ? entity.attributes : []
                        };
                      }
                    }

                  }
                }
              }
            }
          }
        }

        setEntityAccess(entity_access);

    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        showError(e.response.data);
      } else{
        console.log()
        showError('Unknown error occurred')
      }
    }
  }

  const reloadSchema = async () => {
    await schemaUpdate();
  }

  const onLoadMenu = async event => {
    const session = await Auth.currentSession();
    const token = session.idToken.jwtToken;
    apiAdmin = await new Admin(session);
  }

  const onClickMenu = async event => {
    event.preventDefault();
    const action = event.detail.id;
    switch(action) {
      case 'signout':
        try {
          await Auth.signOut({global: true});
        } catch (e) {
          console.log('error signing out: ', e);
        }
        userHasAuthenticated(false);
        await closeUserSession();
        navigate("/login");
        break;
      case 'changepassword':
        navigate("/change/pwd");
        break;
      default:
        break;
    }
  }

  const openInNewTab = (url) => {
    const newWindow = window.open(url, '_blank', 'noopener,noreferrer')
    if (newWindow) newWindow.opener = null
  }

  const signOutUser = async () => {
    try {
      await Auth.signOut({global: true});
    } catch (e) {
      console.log('error signing out: ', e);
    }
    userHasAuthenticated(false);
    await closeUserSession();
    navigate("/login");
  }

  const onClickUpdate = event => {
    setShowDialog(false);
  }

  const hideError = event => {
    event.preventDefault();
    setIsError(false);
    setError(null);
  }

  const showError = message => {
    if(message === Object(message)){
      message = JSON.stringify(message);
    }
    setIsError(true);
    setError(message);

  }

  async function handleHelpContentChange(content, silent = true){

    if (!toolsOpen && !silent) {
      //Open tools panel as user has clicked info link.
      setToolsOpen(true);
    } else if (toolsOpen && !silent){
      //Close tools panel as user has clicked info link again and content has not changed then close panel.
      if (deepEqual(content, toolsHelpContent)){
        setToolsOpen(false);
        return;
      }
    }

    setToolsHelpContent(content);
  }

    //Validate that the user is not authenticating currently and that schema is loaded without errors, if so set application to available for use.
    useEffect( () => {
    if(isAuthenticating || schemaIsLoading){
      setIsReady(false);
    } else if (schemaError == null && !schemaIsLoading)  {
      setIsReady(true);
    } else {
      setIsReady(false);
      if (schemaError != 'No current user') {
        setError('MF Schema could not be loaded, please close and reopen browser. If this problem persists contact your administrator with the following error details : ' + schemaError);
        console.log('MF Schema could not be loaded, please close and reopen browser. If this problem persists contact your administrator with the following error details : ' + schemaError);
      }

    }
    
  },[schemaError, schemaIsLoading, isAuthenticating]);

  // if reload of schema happens and fails then this effect with render the application unavailable.
  useEffect( () => {
    if (schemaError !== null){
      setIsReady(false);
      if (schemaError != 'No current user' && isAuthenticating){
        setError('MF Schema could not be loaded, please close and reopen browser. If this problem persists contact your administrator with the following error details : ' + schemaError);
        console.log('MF Schema could not be loaded, please close and reopen browser. If this problem persists contact your administrator with the following error details : ' + schemaError);
      }
    }
  },[schemaError, isAuthenticating]);


  //update of permissions when permissions change.
  useEffect(() => {
    getPermissions();
  },[permissionsData]);


  //Change in user authentication happened.
  useEffect( () => {
    let cancelledRequest;

    if (isAuthenticated && !isAuthenticating)
    {
      let session = null;

      (async () => {
          try {
            session = await Auth.currentSession();
            if (cancelledRequest) return;

            userHasAuthenticated(true);
            setIsAuthenticating(false);
          } catch (e) {
            if (cancelledRequest) return;
            if (e !== 'No current user') {
              alert(e);
              userHasAuthenticated(false);
              setIsAuthenticating(true);
              //navigate("/login");
              return;
            }
          }

          //Check session is set, if not set authenticated back to false.
          if (session == null) {
            setIsAuthenticated(false);
            await closeUserSession();
            if (cancelledRequest) return;
          } else {
            const token = session.idToken.jwtToken;
            apiAdmin = await new Admin(session);
            if (cancelledRequest) return;
            let lJwt = decodeJwt(token);

            const userGroups = lJwt['cognito:groups'];
            //Set username to email address
            if (lJwt.email) {
              setUserName(lJwt.email);
            } else {
              setUserName('Profile');
            }
            if (userGroups == undefined) {
              setUserGroups([]);
            } else {
              setUserGroups(userGroups);
              await permissionsUpdate()
            }

            //await schemaUpdate();
            await openUserSession();
            //setIsReady(true);
          }
      })();
    } else if(!isAuthenticated) {
      (async () => {
        await closeUserSession();
        if (cancelledRequest) return;
        setIsAuthenticating(false);
      })();
    }

    return () => {
      cancelledRequest = true;
    };

  },[isAuthenticated]);


  const childProps = {
    isAuthenticated: isAuthenticated,
    userHasAuthenticated: userHasAuthenticated,
    showError: showError,
    updateNotification: updateNotification,
    notifications: notifications,
    schema: schemaLocal,
    schemaIsLoading: schemaIsLoading,
    schemaMetadata: schemaMetadata,
    reloadSchema:reloadSchema,
    reloadPermissions: permissionsUpdate,
    isReady: isReady,
    appError: error,
    userGroups: userGroups,
    userEntityAccess: entityAccess,
    setHelpPanelContent: handleHelpContentChange,
  };

  // Breadcrumb content
  const Breadcrumbs = () => (
    <BreadcrumbGroup
      items={[
        {
          text: 'Migration Management',
          href: '/applications'
        },
        {
          text: 'Applications',
          href: '/applications'
        }
      ]}
    />
  );

  // Help (right) panel content
  const Tools = [
    toolsHelpContent
      ?
        <HelpPanel
          header={<h2>{toolsHelpContent.header}</h2>}
          footer={
            <div>
              <h3>
                Learn more
              </h3>
              <SpaceBetween>
                {toolsHelpContent.content_links ? toolsHelpContent.content_links.map(item => {return (
                    <Link
                      external
                      externalIconAriaLabel="Opens in a new tab"
                      href={item['value']}
                    >
                      {item['key']}
                    </Link>
                  )}
                ) : undefined}
              </SpaceBetween>
            </div>}
        >
          {toolsHelpContent.content_html ? <div dangerouslySetInnerHTML={{ __html: toolsHelpContent.content_html.replaceAll('\n', '<br>') }} /> : undefined}
          {toolsHelpContent.content_text ? toolsHelpContent.content_text.replaceAll('\n', '<br>') : undefined}
          {toolsHelpContent.content_md ? toolsHelpContent.content_md : undefined}
        </HelpPanel>
      :
        undefined
  ];

  return (
    !isAuthenticating &&
    <div onMouseMove={onMouseMove}>
      {showDialog &&
        <AppDialog
          showDialog={showDialog}
          msg={msg}
          onClickUpdate={onClickUpdate}
        />
      }
      {isError?<div className="alert-box alert alert-danger">{error}<span onClick={hideError} className="alert-box-close btn">X</span></div>:null}
      <TopNavigation id='h' style={myHeaderStyle}
                     identity={{
                       href: "/",
                       title: " ",
                       logo: {
                         src:
                           "data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4NCjwhLS0gR2VuZXJhdG9yOiBBZG9iZSBJbGx1c3RyYXRvciAxOS4wLjEsIFNWRyBFeHBvcnQgUGx1Zy1JbiAuIFNWRyBWZXJzaW9uOiA2LjAwIEJ1aWxkIDApICAtLT4NCjxzdmcgd2lkdGg9IjMwMCIgaGVpZ2h0PSIzMDAiIHZlcnNpb249IjEuMSIgaWQ9IkxheWVyXzEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4Ig0KCSB2aWV3Qm94PSIwIDAgMzA0IDE4MiIgc3R5bGU9ImVuYWJsZS1iYWNrZ3JvdW5kOm5ldyAwIDAgMzA0IDE4MjsiIHhtbDpzcGFjZT0icHJlc2VydmUiPg0KPHN0eWxlIHR5cGU9InRleHQvY3NzIj4NCgkuc3Qwe2ZpbGw6I0ZGRkZGRjt9DQoJLnN0MXtmaWxsLXJ1bGU6ZXZlbm9kZDtjbGlwLXJ1bGU6ZXZlbm9kZDtmaWxsOiNGRjk5MDA7fQ0KPC9zdHlsZT4NCjxnPg0KCTxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik04Ni40LDY2LjRjMCwzLjcsMC40LDYuNywxLjEsOC45YzAuOCwyLjIsMS44LDQuNiwzLjIsNy4yYzAuNSwwLjgsMC43LDEuNiwwLjcsMi4zYzAsMS0wLjYsMi0xLjksM2wtNi4zLDQuMg0KCQljLTAuOSwwLjYtMS44LDAuOS0yLjYsMC45Yy0xLDAtMi0wLjUtMy0xLjRDNzYuMiw5MCw3NSw4OC40LDc0LDg2LjhjLTEtMS43LTItMy42LTMuMS01LjljLTcuOCw5LjItMTcuNiwxMy44LTI5LjQsMTMuOA0KCQljLTguNCwwLTE1LjEtMi40LTIwLTcuMmMtNC45LTQuOC03LjQtMTEuMi03LjQtMTkuMmMwLTguNSwzLTE1LjQsOS4xLTIwLjZjNi4xLTUuMiwxNC4yLTcuOCwyNC41LTcuOGMzLjQsMCw2LjksMC4zLDEwLjYsMC44DQoJCWMzLjcsMC41LDcuNSwxLjMsMTEuNSwyLjJ2LTcuM2MwLTcuNi0xLjYtMTIuOS00LjctMTZjLTMuMi0zLjEtOC42LTQuNi0xNi4zLTQuNmMtMy41LDAtNy4xLDAuNC0xMC44LDEuM2MtMy43LDAuOS03LjMsMi0xMC44LDMuNA0KCQljLTEuNiwwLjctMi44LDEuMS0zLjUsMS4zYy0wLjcsMC4yLTEuMiwwLjMtMS42LDAuM2MtMS40LDAtMi4xLTEtMi4xLTMuMXYtNC45YzAtMS42LDAuMi0yLjgsMC43LTMuNWMwLjUtMC43LDEuNC0xLjQsMi44LTIuMQ0KCQljMy41LTEuOCw3LjctMy4zLDEyLjYtNC41YzQuOS0xLjMsMTAuMS0xLjksMTUuNi0xLjljMTEuOSwwLDIwLjYsMi43LDI2LjIsOC4xYzUuNSw1LjQsOC4zLDEzLjYsOC4zLDI0LjZWNjYuNHogTTQ1LjgsODEuNg0KCQljMy4zLDAsNi43LTAuNiwxMC4zLTEuOGMzLjYtMS4yLDYuOC0zLjQsOS41LTYuNGMxLjYtMS45LDIuOC00LDMuNC02LjRjMC42LTIuNCwxLTUuMywxLTguN3YtNC4yYy0yLjktMC43LTYtMS4zLTkuMi0xLjcNCgkJYy0zLjItMC40LTYuMy0wLjYtOS40LTAuNmMtNi43LDAtMTEuNiwxLjMtMTQuOSw0Yy0zLjMsMi43LTQuOSw2LjUtNC45LDExLjVjMCw0LjcsMS4yLDguMiwzLjcsMTAuNg0KCQlDMzcuNyw4MC40LDQxLjIsODEuNiw0NS44LDgxLjZ6IE0xMjYuMSw5Mi40Yy0xLjgsMC0zLTAuMy0zLjgtMWMtMC44LTAuNi0xLjUtMi0yLjEtMy45TDk2LjcsMTAuMmMtMC42LTItMC45LTMuMy0wLjktNA0KCQljMC0xLjYsMC44LTIuNSwyLjQtMi41aDkuOGMxLjksMCwzLjIsMC4zLDMuOSwxYzAuOCwwLjYsMS40LDIsMiwzLjlsMTYuOCw2Ni4ybDE1LjYtNjYuMmMwLjUtMiwxLjEtMy4zLDEuOS0zLjljMC44LTAuNiwyLjItMSw0LTENCgkJaDhjMS45LDAsMy4yLDAuMyw0LDFjMC44LDAuNiwxLjUsMiwxLjksMy45bDE1LjgsNjdsMTcuMy02N2MwLjYtMiwxLjMtMy4zLDItMy45YzAuOC0wLjYsMi4xLTEsMy45LTFoOS4zYzEuNiwwLDIuNSwwLjgsMi41LDIuNQ0KCQljMCwwLjUtMC4xLDEtMC4yLDEuNmMtMC4xLDAuNi0wLjMsMS40LTAuNywyLjVsLTI0LjEsNzcuM2MtMC42LDItMS4zLDMuMy0yLjEsMy45Yy0wLjgsMC42LTIuMSwxLTMuOCwxaC04LjZjLTEuOSwwLTMuMi0wLjMtNC0xDQoJCWMtMC44LTAuNy0xLjUtMi0xLjktNEwxNTYsMjNsLTE1LjQsNjQuNGMtMC41LDItMS4xLDMuMy0xLjksNGMtMC44LDAuNy0yLjIsMS00LDFIMTI2LjF6IE0yNTQuNiw5NS4xYy01LjIsMC0xMC40LTAuNi0xNS40LTEuOA0KCQljLTUtMS4yLTguOS0yLjUtMTEuNS00Yy0xLjYtMC45LTIuNy0xLjktMy4xLTIuOGMtMC40LTAuOS0wLjYtMS45LTAuNi0yLjh2LTUuMWMwLTIuMSwwLjgtMy4xLDIuMy0zLjFjMC42LDAsMS4yLDAuMSwxLjgsMC4zDQoJCWMwLjYsMC4yLDEuNSwwLjYsMi41LDFjMy40LDEuNSw3LjEsMi43LDExLDMuNWM0LDAuOCw3LjksMS4yLDExLjksMS4yYzYuMywwLDExLjItMS4xLDE0LjYtMy4zYzMuNC0yLjIsNS4yLTUuNCw1LjItOS41DQoJCWMwLTIuOC0wLjktNS4xLTIuNy03Yy0xLjgtMS45LTUuMi0zLjYtMTAuMS01LjJMMjQ2LDUyYy03LjMtMi4zLTEyLjctNS43LTE2LTEwLjJjLTMuMy00LjQtNS05LjMtNS0xNC41YzAtNC4yLDAuOS03LjksMi43LTExLjENCgkJYzEuOC0zLjIsNC4yLTYsNy4yLTguMmMzLTIuMyw2LjQtNCwxMC40LTUuMmM0LTEuMiw4LjItMS43LDEyLjYtMS43YzIuMiwwLDQuNSwwLjEsNi43LDAuNGMyLjMsMC4zLDQuNCwwLjcsNi41LDEuMQ0KCQljMiwwLjUsMy45LDEsNS43LDEuNmMxLjgsMC42LDMuMiwxLjIsNC4yLDEuOGMxLjQsMC44LDIuNCwxLjYsMywyLjVjMC42LDAuOCwwLjksMS45LDAuOSwzLjN2NC43YzAsMi4xLTAuOCwzLjItMi4zLDMuMg0KCQljLTAuOCwwLTIuMS0wLjQtMy44LTEuMmMtNS43LTIuNi0xMi4xLTMuOS0xOS4yLTMuOWMtNS43LDAtMTAuMiwwLjktMTMuMywyLjhjLTMuMSwxLjktNC43LDQuOC00LjcsOC45YzAsMi44LDEsNS4yLDMsNy4xDQoJCWMyLDEuOSw1LjcsMy44LDExLDUuNWwxNC4yLDQuNWM3LjIsMi4zLDEyLjQsNS41LDE1LjUsOS42YzMuMSw0LjEsNC42LDguOCw0LjYsMTRjMCw0LjMtMC45LDguMi0yLjYsMTEuNg0KCQljLTEuOCwzLjQtNC4yLDYuNC03LjMsOC44Yy0zLjEsMi41LTYuOCw0LjMtMTEuMSw1LjZDMjY0LjQsOTQuNCwyNTkuNyw5NS4xLDI1NC42LDk1LjF6Ii8+DQoJPGc+DQoJCTxwYXRoIGNsYXNzPSJzdDEiIGQ9Ik0yNzMuNSwxNDMuN2MtMzIuOSwyNC4zLTgwLjcsMzcuMi0xMjEuOCwzNy4yYy01Ny42LDAtMTA5LjUtMjEuMy0xNDguNy01Ni43Yy0zLjEtMi44LTAuMy02LjYsMy40LTQuNA0KCQkJYzQyLjQsMjQuNiw5NC43LDM5LjUsMTQ4LjgsMzkuNWMzNi41LDAsNzYuNi03LjYsMTEzLjUtMjMuMkMyNzQuMiwxMzMuNiwyNzguOSwxMzkuNywyNzMuNSwxNDMuN3oiLz4NCgkJPHBhdGggY2xhc3M9InN0MSIgZD0iTTI4Ny4yLDEyOC4xYy00LjItNS40LTI3LjgtMi42LTM4LjUtMS4zYy0zLjIsMC40LTMuNy0yLjQtMC44LTQuNWMxOC44LTEzLjIsNDkuNy05LjQsNTMuMy01DQoJCQljMy42LDQuNS0xLDM1LjQtMTguNiw1MC4yYy0yLjcsMi4zLTUuMywxLjEtNC4xLTEuOUMyODIuNSwxNTUuNywyOTEuNCwxMzMuNCwyODcuMiwxMjguMXoiLz4NCgk8L2c+DQo8L2c+DQo8L3N2Zz4NCg==",
                         alt: "AWS"
                       }
                     }}
                     utilities={isAuthenticated ? [
                       {
                         type: "menu-dropdown",
                         text: "Documentation",
                         items: [
                           { id: "cmf-overview", text: "AWS Cloud Migration Factory Solution", external: true, href: "https://aws.amazon.com/solutions/implementations/aws-cloudendure-migration-factory-solution/"},
                           { id: "lm", text: "Guide for AWS large migrations", external: true, href: "https://aws.amazon.com/prescriptive-guidance/large-migrations"},
                           { id: "lab", text: "Cloud Migration Factory Lab", external: true, href: "https://cloud-migration-factory.s3.amazonaws.com/apg-public/workshop/index.html"}
                         ]
                       },
                       {
                         type: "menu-dropdown",
                         description: userName,
                         iconName: "user-profile",
                         onItemClick: (event) => onClickMenu(event),
                         items: [
                           { id: "changepassword", text: "Change Password"},
                           { id: "signout", text: "Sign out"}
                         ]
                       }
                     ]:
                       [{
                         type: "menu-dropdown",
                         text: "Documentation",
                         items: [
                           { id: "cmf-overview", text: "AWS Cloud Migration Factory Solution", external: true, href: "https://aws.amazon.com/solutions/implementations/aws-cloudendure-migration-factory-solution/"},
                           { id: "lm", text: "Guide for AWS large migrations", external: true, href: "https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/welcome.html"}
                         ]
                       }]}
                     i18nStrings={{
                       searchIconAriaLabel: "Search",
                       searchDismissIconAriaLabel: "Close search",
                       overflowMenuTriggerText: "More"
                     }}
      />
      <SpaceBetween direction={'vertical'}>

      {!isAuthenticated
        ?
        <PreAuthRoutes childProps={childProps}/>
        :
        isReady && schemaLocal && schemaError == null?
            <AppLayout
              headerSelector="#h"
              navigation={<ServiceNavigation
                userGroups={userGroups}
                schemaMetadata={schemaMetadata}
                open={false}
              />}
              notifications={<FlashMessage
                notifications={notifications}/>}
              //breadcrumbs={<Breadcrumbs/>} TODO Implement new dynamic breadcrumbs functions in future.
              content={<AuthRoutes childProps={childProps}/>}
              contentType="table"
              tools={<ToolHelp
                      helpContent={toolsHelpContent}
                      />}
              toolsHide={toolsHelpContent ? false : true}
              disableBodyScroll={true}
              onToolsChange={({detail}) => setToolsOpen(detail.open)}
              toolsOpen={toolsOpen}
            />
          :
            <center>
              {error == null
                ?
                <StatusIndicator type="loading">
                  Loading
                </StatusIndicator>
                :
                <Alert
                  visible={true}
                  type="error"
                  header="Application Error"
                >
                  {error}
                </Alert>
              }
            </center>
      }
      </SpaceBetween>

      <div id='modal-root' />
    </div>
  );
}

export default App;
