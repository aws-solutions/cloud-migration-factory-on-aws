import React, { Component } from "react";
import { Auth } from "aws-amplify";
import User from "../actions/user";
import Tools from "../actions/tools"
import NavBar from "../components/NavBar";
import ToolsNav from "../components/ToolsNav";
import ToolsCELaunch from "../components/ToolsCELaunch"

export default class ToolsCloudEndure extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isAuthenticated: props.isAuthenticated,
      isLoading: true,
      activeNav: 'ce',
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.apiUser = await new User(session);
    this.apiTools = await new Tools(session);
    this.setState({ isLoading: false });
  }

  onClickChangeActiveNav = event => {
    event.preventDefault();
    switch(event.target.id) {
      case 'ce':
        this.props.history.push("/tools/cloudendure");
        break;
      case 'ams':
        this.props.history.push("/tools/ams");
        break;
      case 'mgn':
        this.props.history.push("/tools/mgn");
        break;
      default:
        break;
    }
  }

  render() {
    if (!this.state.isAuthenticated){
      this.props.history.push("/login");
    }

    return (
      <div>
        <NavBar
          onClick={this.props.onClickMenu}
          selection="Tools"
        />
        <ToolsNav onClick={this.onClickChangeActiveNav} active={this.state.activeNav}/>

        <div className="container-fluid pt-1 px-5">
          <ToolsCELaunch
            isLoading={this.state.isLoading}
            showError={this.props.showError}
          />
        </div>
      </div>
    );
  }
}
