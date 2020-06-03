import React, { Component } from "react";
import { Auth } from "aws-amplify";
import User from "../actions/user";
import Admin from "../actions/admin";

export default class SelectStageDialog extends Component {
  constructor(props) {
    super(props);

    this.state = {
      selectedStage: this.props.selectedStage + 1,
      stages : [],
      showDialog: this.props.showDialog
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.apiAdmin = await new Admin(session);
    this.apiUser = await new User(session);
    this.getStages();
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      showDialog: nextProps.showDialog
    });
  }

  async getStages() {
    try {
      var response = await this.apiAdmin.getStages();
      this.setState({ stages : response});
    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
  }

  onClickCancelDialog = event => {
    this.setState({
      selectedStage: this.props.selectedStage
    });
    this.props.closeDialog();
  }

  onClickUpdateStage = event => {
    this.props.closeDialog();
    this.props.onClickUpdateStage(this.state.selectedStage);
  }

  onChangeDialog = event => {
        const stage_id = event.target.value;
        this.setState({selectedStage: stage_id});
  }

  render() {

    return (
      <div>

        {this.state.showDialog &&
          <div>
            <div className="block-events-full"> </div>

            <div className="dialog-box">
              <div className="pb-4"><b>Select Stage</b> <span onClick={this.onClickCancelDialog} className="onhover float-right">X</span></div>
              <div style={{height:"220px",overflow:"auto"}}>
                <div className="row">

                    <div className="col-6">
                      <hr />
                      <ul style={{listStyleType: "none"}} className="p-0 m-0">
                        {this.state.stages.map((item, index) => {
                          if (item.stage_name === "stage_name" || item.stage_id === "stage_id") {
                            return null
                          }

                          return (
                            <li key={item.stage_id}>
                              <input
                                onChange={this.onChangeDialog}
                                type="radio"
                                name={item.stage_name}
                                checked={this.state.selectedStage === item.stage_id}
                                className="mr-3"
                                value = {item.stage_id}
                              />
                              {item.stage_name}
                            </li>
                          )
                        })}
                      </ul>
                    </div>
                  </div>

              </div>
              <hr />
              <input
                className="btn btn-primary btn-outline mt-3 mr-3 float-right"
                type="button"
                value="Update Stage"
                onClick={this.onClickUpdateStage}
              />
            </div>
          </div>
        }

    </div>
    )
  }
}
