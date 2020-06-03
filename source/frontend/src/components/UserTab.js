import React from "react";
import { Auth } from "aws-amplify";
import Admin from "../actions/admin";
import UserTabApp from "../components/UserTabApp";
import UserTabServer from "../components/UserTabServer";

export default class UserTab extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      stage: props.stage,
      app: {},
      waves: props.waves,
      appServers: [],
      isLoading: true,
      tabId: 'app',
      schemaApp: [],
      schemaServer: [],
      allowCreate: this.props
    };
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      isLoading: nextProps.isLoading,
      app: nextProps.app,
      appServers: nextProps.appServers,
      allowCreate: nextProps.allowCreate
    });

    if (nextProps.stage !== this.props.stage){
      this.setState({
        stage: nextProps.stage
      });
    };

    if (nextProps.waves !== this.props.waves){
      this.setState({
        waves: nextProps.waves,
      });
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.api = await new Admin(session);

    this.getSchema();

    this.setState({ isLoading: false });
  }

  async getSchema() {
    try {
      var response = await this.api.getSchemaApp();
      this.setState({ schemaApp : response['attributes']});

      response = await this.api.getSchemaServer();
      this.setState({ schemaServer : response['attributes']});

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
  }

  setIsLoading = status => {
    this.setState({isLoading: status});
  }

  onClickChangeTab = tabId => event => {
    event.preventDefault();
    this.setState({tabId: tabId});
  }

  render() {
    var appLoaded = false;
    if (Object.keys(this.state.app).length > 0){
      appLoaded = true;
    }

    return (
      <div>
        {this.state.isLoading && <div className="block-events" ></div>}
        <div className="pt-3">

          <h4>> {appLoaded?this.state.app.app_name:'No application selected'}</h4>
        </div>

        <div id="factory-tab" className="container-fluid rounded  py-3 px-0">
          <ul className="nav nav-tabs">
            <li className="nav-item">
              <a className={'nav-link '+(this.state.tabId==='app'?'active':'')} onClick={this.onClickChangeTab('app')} href=".">Application Info</a>
            </li>
            {this.state.app.app_id !== null &&
              <li className="nav-item">
                <a className={'nav-link '+(this.state.tabId==='server'?'active':'')} onClick={this.onClickChangeTab('server')} href=".">Servers</a>
              </li>
            }
          </ul>
            { ( appLoaded && this.state.tabId === 'app' )&&
              <UserTabApp
                setIsLoading={this.setIsLoading}
                app={this.state.app}
                stage={this.state.stage}
                waves={this.state.waves}
                attributeType={this.state.tabId}
                showError={this.props.showError}
                updateAppList={this.props.updateAppList}
                schema={this.state.schemaApp}
                allowCreate={this.props.allowCreate}
              />
            }
            { ( appLoaded && this.state.tabId === 'server' )&&
              <UserTabServer
                setIsLoading={this.setIsLoading}
                app={this.state.app}
                stage={this.state.stage}
                attributeType={this.state.tabId}
                showError={this.props.showError}
                updateAppList={this.props.updateAppList}
                appServers={this.props.appServers}
                updateServerList={this.props.updateServerList}
                schema={this.state.schemaServer}
                allowCreate={this.props.allowCreate}
              />
            }
        </div>
      </div>

    );
  }
};
